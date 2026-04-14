"""Microsoft Entra ID (Azure AD) token validation.

Fetches JWKS from Microsoft, validates the ID token signature and claims.
"""
import logging
from typing import Any

import httpx
from jose import JWTError, jwt
from jose.exceptions import ExpiredSignatureError

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Module-level JWKS cache (refreshed on each app restart — fine for 8-hour TTL sessions)
_jwks_cache: dict | None = None


async def _get_jwks() -> dict:
    global _jwks_cache
    if _jwks_cache is None:
        async with httpx.AsyncClient() as client:
            resp = await client.get(settings.jwks_uri, timeout=10.0)
            resp.raise_for_status()
            _jwks_cache = resp.json()
    return _jwks_cache


async def exchange_code_for_tokens(code: str, redirect_uri: str) -> dict[str, Any]:
    """Exchange an authorization code for tokens via Microsoft token endpoint.

    Returns the token response dict containing id_token, access_token, etc.
    Raises httpx.HTTPStatusError on failure.
    """
    payload = {
        "client_id": settings.auth_client_id,
        "client_secret": settings.auth_client_secret,
        "code": code,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
        "scope": "openid profile email",
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(settings.token_endpoint, data=payload, timeout=15.0)
        resp.raise_for_status()
        return resp.json()


async def validate_id_token(id_token: str) -> dict[str, Any]:
    """Decode and validate a Microsoft ID token.

    Validates:
    - Signature against Microsoft JWKS
    - iss (issuer) matches expected tenant
    - aud (audience) matches AUTH_CLIENT_ID
    - exp (expiry) has not passed
    - email domain is in AUTH_ALLOWED_DOMAINS

    Returns the decoded claims dict.
    Raises ValueError with a human-readable message on any failure.
    """
    try:
        jwks = await _get_jwks()
        claims = jwt.decode(
            id_token,
            jwks,
            algorithms=["RS256"],
            audience=settings.auth_client_id,
            options={"verify_at_hash": False},
        )
    except ExpiredSignatureError:
        raise ValueError("ID token has expired")
    except JWTError as exc:
        logger.warning("JWT validation failed: %s", exc)
        raise ValueError(f"Invalid ID token: {exc}")

    # Verify issuer — Microsoft uses two formats
    expected_issuers = [
        f"https://login.microsoftonline.com/{settings.auth_tenant_id}/v2.0",
        f"https://sts.windows.net/{settings.auth_tenant_id}/",
    ]
    if claims.get("iss") not in expected_issuers:
        raise ValueError(f"Unexpected issuer: {claims.get('iss')}")

    # Verify email domain
    email = claims.get("email") or claims.get("preferred_username", "")
    if not email:
        raise ValueError("No email claim in token")

    domain = email.split("@")[-1].lower()
    if domain not in settings.allowed_domains_list:
        raise ValueError(f"Email domain '{domain}' is not permitted")

    return claims

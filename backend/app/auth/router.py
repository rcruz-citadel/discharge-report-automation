"""Auth endpoints: callback, logout, me."""
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.entra import exchange_code_for_tokens, validate_id_token
from app.auth.session import (
    COOKIE_NAME,
    create_session,
    get_current_user,
)
from app.config import get_settings
from app.database import get_db
from app.models.db import AppSession, AppUser
from app.models.schemas import AuthCallbackRequest, AuthCallbackResponse, LogoutResponse, MeResponse

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/callback", response_model=AuthCallbackResponse)
async def auth_callback(
    body: AuthCallbackRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> AuthCallbackResponse:
    """Exchange Microsoft authorization code for a server-side session cookie.

    1. Exchange code for tokens via Microsoft token endpoint
    2. Validate ID token (signature, issuer, audience, domain)
    3. Look up user in discharge_app.app_user
    4. Create session in discharge_app.app_session
    5. Set httpOnly session cookie
    """
    # ── Stub mode: skip Entra ID entirely ─────────────────────────────────────
    if settings.auth_stub_enabled:
        token = await create_session(
            db,
            user_email=settings.auth_stub_email,
            user_name=settings.auth_stub_name,
            user_role=settings.auth_stub_role,
        )
        _set_session_cookie(response, token)
        return AuthCallbackResponse()

    # ── Exchange code for tokens ───────────────────────────────────────────────
    try:
        token_response = await exchange_code_for_tokens(body.code, body.redirect_uri)
    except Exception as exc:
        logger.warning("Token exchange failed: %s", exc)
        raise HTTPException(status_code=400, detail="Token exchange failed")

    id_token = token_response.get("id_token")
    if not id_token:
        raise HTTPException(status_code=400, detail="No id_token in response")

    # ── Validate ID token ──────────────────────────────────────────────────────
    try:
        claims = await validate_id_token(id_token)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc))

    email = (claims.get("email") or claims.get("preferred_username", "")).lower()
    name = claims.get("name") or email

    # ── Look up user role in discharge_app.app_user ────────────────────────────
    result = await db.execute(
        select(AppUser).where(AppUser.user_email == email).where(AppUser.is_active == True)  # noqa: E712
    )
    app_user = result.scalar_one_or_none()

    # Unknown user — allow login but with null role (read-only access)
    user_role = app_user.role if app_user else None

    # ── Create session ─────────────────────────────────────────────────────────
    session_token = await create_session(db, user_email=email, user_name=name, user_role=user_role)
    _set_session_cookie(response, session_token)

    logger.info("Login: %s (role=%s)", email, user_role)
    return AuthCallbackResponse()


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    user: MeResponse = Depends(get_current_user),
) -> LogoutResponse:
    """Delete the server-side session and clear the cookie."""
    token = request.cookies.get(COOKIE_NAME)
    if token:
        await db.execute(delete(AppSession).where(AppSession.token == token))
    else:
        # Fallback: delete all sessions for this user (e.g. stub mode)
        await db.execute(delete(AppSession).where(AppSession.user_email == user.email))
    await db.commit()
    _clear_session_cookie(response)
    logger.info("Logout: %s", user.email)
    return LogoutResponse()


@router.get("/me", response_model=MeResponse)
async def me(user: MeResponse = Depends(get_current_user)) -> MeResponse:
    """Return the currently authenticated user's identity.

    Called by the React AuthProvider on every app load to hydrate auth context.
    Returns 401 if no valid session cookie present.
    """
    return user


# ── Cookie helpers ─────────────────────────────────────────────────────────────


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=settings.session_max_age_seconds,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/",
    )


def _clear_session_cookie(response: Response) -> None:
    response.set_cookie(
        key=COOKIE_NAME,
        value="",
        max_age=0,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/",
    )

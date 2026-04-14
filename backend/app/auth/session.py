"""Session management: create, validate, and destroy httpOnly cookie sessions.

Sessions are stored in discharge_app.app_session. Token is a 32-byte random
hex string (not a JWT). Session lookup is O(1) via the token index.
"""
import asyncio
import logging
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, Request
from sqlalchemy import func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models.db import AppSession
from app.models.schemas import MeResponse

logger = logging.getLogger(__name__)
settings = get_settings()

COOKIE_NAME = "session"


def generate_session_token() -> str:
    """Generate a cryptographically random 32-byte hex session token."""
    return secrets.token_hex(32)


async def create_session(
    db: AsyncSession,
    user_email: str,
    user_name: str,
    user_role: str | None,
) -> str:
    """Insert a new session row and return the token string."""
    token = generate_session_token()
    now = datetime.now(tz=timezone.utc)
    expires_at = now + timedelta(seconds=settings.session_max_age_seconds)

    session = AppSession(
        token=token,
        user_email=user_email,
        user_name=user_name,
        user_role=user_role,
        created_at=now,
        expires_at=expires_at,
        last_seen_at=now,
    )
    db.add(session)
    await db.commit()
    return token


async def delete_session(db: AsyncSession, token: str) -> None:
    """Delete a session row by token."""
    result = await db.execute(
        select(AppSession).where(AppSession.token == token)
    )
    session = result.scalar_one_or_none()
    if session:
        await db.delete(session)
        await db.commit()


async def _touch_session(session_id: int, db: AsyncSession) -> None:
    """Update last_seen_at for an active session (fire-and-forget)."""
    try:
        await db.execute(
            update(AppSession)
            .where(AppSession.id == session_id)
            .values(last_seen_at=func.now())
        )
        await db.commit()
    except Exception as exc:
        logger.debug("touch_session failed (non-critical): %s", exc)


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> MeResponse:
    """FastAPI dependency: validates session cookie and returns the current user.

    In stub mode (AUTH_STUB_ENABLED=true), returns a hardcoded test user.
    This allows frontend development without a live Entra ID tenant.
    """
    # ── Dev stub mode ──────────────────────────────────────────────────────────
    if settings.auth_stub_enabled:
        return MeResponse(
            email=settings.auth_stub_email,
            name=settings.auth_stub_name,
            role=settings.auth_stub_role,
        )

    # ── Production: validate cookie session ────────────────────────────────────
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    result = await db.execute(
        select(AppSession)
        .where(AppSession.token == token)
        .where(AppSession.expires_at > func.now())
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=401, detail="Session expired or invalid")

    # Fire-and-forget touch (non-blocking)
    asyncio.create_task(_touch_session(session.id, db))

    return MeResponse(
        email=session.user_email,
        name=session.user_name,
        role=session.user_role,
    )


async def get_current_manager(
    user: MeResponse = Depends(get_current_user),
) -> MeResponse:
    """FastAPI dependency: requires manager or admin role."""
    if user.role not in ("manager", "admin"):
        raise HTTPException(status_code=403, detail="Manager role required")
    return user

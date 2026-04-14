"""FastAPI application factory.

Architecture:
  nginx (port 443) -> /api/* -> uvicorn (port 8000)
  20 concurrent users on internal LAN, ~17k discharge records.
"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.auth.router import router as auth_router
from app.config import get_settings
from app.database import AsyncSessionLocal
from app.routers.discharges import router as discharges_router
from app.routers.manager import router as manager_router
from app.routers.meta import router as meta_router
from app.routers.outreach import router as outreach_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

settings = get_settings()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Discharge Report API",
        version="3.0.0",
        description="V3 React + FastAPI discharge report dashboard for Citadel Health / Aylo Health.",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )

    # ── CORS ───────────────────────────────────────────────────────────────────
    # Only allow the React frontend origin. Credentials (httpOnly cookies) require
    # explicit origin list — wildcard "*" is not allowed with credentials.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list + ["http://localhost:5173"],  # Vite dev
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
    )

    # ── Routers ────────────────────────────────────────────────────────────────
    app.include_router(auth_router, prefix="/api")
    app.include_router(discharges_router, prefix="/api")
    app.include_router(outreach_router, prefix="/api")
    app.include_router(meta_router, prefix="/api")
    app.include_router(manager_router, prefix="/api")

    # ── Startup ────────────────────────────────────────────────────────────────
    @app.on_event("startup")
    async def on_startup() -> None:
        logger.info("Discharge Report API v3.0 starting up...")
        if settings.auth_stub_enabled:
            logger.warning(
                "AUTH_STUB_ENABLED=true — all requests authenticated as %s (%s). "
                "NEVER use in production.",
                settings.auth_stub_name,
                settings.auth_stub_email,
            )
        await _cleanup_expired_sessions()

    async def _cleanup_expired_sessions() -> None:
        """Delete expired session rows on startup. Keeps the table lean."""
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    text("DELETE FROM discharge_app.app_session WHERE expires_at < now()")
                )
                await db.commit()
                logger.info("Cleaned up %d expired sessions.", result.rowcount)
        except Exception as exc:
            # Non-fatal — don't prevent startup if discharge_app schema isn't yet migrated
            logger.warning("Session cleanup skipped (table may not exist yet): %s", exc)

    # ── Health check ───────────────────────────────────────────────────────────
    @app.get("/api/health", tags=["health"])
    async def health() -> dict:
        return {"status": "ok", "version": "3.0.0"}

    return app


app = create_app()

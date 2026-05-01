"""FastAPI application factory.

Architecture:
  nginx (port 443) -> /api/* -> uvicorn (port 8000)
  20 concurrent users on internal LAN, ~17k discharge records.
"""
import asyncio
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
from app.tasks.auto_fail import run_auto_fail
from app.tasks.auto_late_delivery import run_auto_late_delivery

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

settings = get_settings()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Discharge Report API",
        version="3.1.0",
        description="V3 React + FastAPI discharge report dashboard for Citadel Health / Aylo Health.",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )

    # ── CORS ───────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list + ["http://localhost:5173"],
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
        logger.info("Discharge Report API v3.1 starting up...")
        if settings.auth_stub_enabled:
            logger.warning(
                "AUTH_STUB_ENABLED=true — all requests authenticated as %s (%s). "
                "NEVER use in production.",
                settings.auth_stub_name,
                settings.auth_stub_email,
            )
        await _cleanup_expired_sessions()
        await _run_auto_fail_once()
        await _run_auto_late_delivery_once()
        asyncio.create_task(_auto_fail_loop())
        asyncio.create_task(_auto_late_delivery_loop())

    async def _cleanup_expired_sessions() -> None:
        """Delete expired session rows on startup. Keeps the table lean."""
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    text(f"DELETE FROM {settings.app_schema}.app_session WHERE expires_at < now()")
                )
                await db.commit()
                logger.info("Cleaned up %d expired sessions.", result.rowcount)
        except Exception as exc:
            logger.warning("Session cleanup skipped (table may not exist yet): %s", exc)

    async def _run_auto_fail_once() -> None:
        """Run auto-fail on startup to catch any records that aged out overnight."""
        try:
            async with AsyncSessionLocal() as db:
                updated, inserted = await run_auto_fail(db)
                logger.info("Startup auto_fail complete: updated=%d inserted=%d", updated, inserted)
        except Exception as exc:
            logger.warning("Startup auto_fail skipped: %s", exc)

    async def _auto_fail_loop() -> None:
        """Re-run auto-fail every 24 hours."""
        while True:
            await asyncio.sleep(24 * 60 * 60)
            try:
                async with AsyncSessionLocal() as db:
                    await run_auto_fail(db)
            except Exception as exc:
                logger.error("auto_fail loop error: %s", exc)

    async def _run_auto_late_delivery_once() -> None:
        """Run auto-late-delivery on startup to catch any late summaries overnight."""
        try:
            async with AsyncSessionLocal() as db:
                updated, inserted = await run_auto_late_delivery(db)
                logger.info(
                    "Startup auto_late_delivery complete: updated=%d inserted=%d",
                    updated,
                    inserted,
                )
        except Exception as exc:
            logger.warning("Startup auto_late_delivery skipped: %s", exc)

    async def _auto_late_delivery_loop() -> None:
        """Re-run auto-late-delivery every 24 hours."""
        while True:
            await asyncio.sleep(24 * 60 * 60)
            try:
                async with AsyncSessionLocal() as db:
                    await run_auto_late_delivery(db)
            except Exception as exc:
                logger.error("auto_late_delivery loop error: %s", exc)

    # ── Health check ───────────────────────────────────────────────────────────
    @app.get("/api/health", tags=["health"])
    async def health() -> dict:
        return {"status": "ok", "version": "3.1.0"}

    return app


app = create_app()

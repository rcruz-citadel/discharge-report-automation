"""SQLAlchemy async engine and session factory.

Pool settings sized for ~20 concurrent users on internal LAN.
"""
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    pool_size=10,       # 10 persistent connections
    max_overflow=5,     # up to 5 extra under burst
    pool_pre_ping=True, # detect stale connections
    pool_recycle=1800,  # recycle connections every 30 min
    echo=False,
)

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async DB session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

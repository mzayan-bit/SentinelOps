"""
SentinelOps — Database Connection & Session Management
======================================================
Provides SQLAlchemy asynchronous engine configuration and session factories.
"""

import logging
from typing import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config.settings import settings

logger = logging.getLogger("sentinelops.db")

# 1. Create the asynchronous engine
engine = create_async_engine(
    settings.async_database_url,
    pool_pre_ping=True,
    echo=(settings.log_level == "DEBUG"),
)

# 2. Create a session factory bound to this engine
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields an asynchronous database session.
    Automatically handles closing the session after the request finishes.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def check_database() -> bool:
    """Run a lightweight connectivity check against the configured database."""
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception:
        logger.exception("Database connectivity check failed")
        return False


async def dispose_engine() -> None:
    """Close pooled database connections during application shutdown."""
    await engine.dispose()

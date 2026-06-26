"""
SentinelOps — Database Unit Tests
=================================
Tests that the database connection and generic repository logic
initialize successfully.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.db.database import engine, get_db
from app.db.base import Base


@pytest.mark.asyncio
async def test_database_engine_initializes():
    """Verify that the engine builds successfully from settings."""
    assert engine is not None
    assert engine.name in ["sqlite", "postgresql"]


@pytest.mark.asyncio
async def test_session_generator_yields_session():
    """Verify that get_db yields a valid AsyncSession."""
    generator = get_db()
    session = await anext(generator)
    assert isinstance(session, AsyncSession)
    assert session.is_active

    # Close session
    try:
        await anext(generator)
    except StopAsyncIteration:
        pass


@pytest.mark.asyncio
async def test_base_metadata():
    """Verify that the DeclarativeBase is correctly wired."""
    assert hasattr(Base, "metadata")

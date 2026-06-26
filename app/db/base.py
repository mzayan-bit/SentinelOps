"""
SentinelOps — Database Declarative Base
=========================================
SQLAlchemy declarative base class for all ORM models.
"""

from typing import Any
from datetime import datetime, timezone

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import DateTime
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy declarative models."""

    # Provide common timestamp columns for all tables
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

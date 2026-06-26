"""
SentinelOps — Centralised Settings
=====================================
Single source of truth for project-wide configuration.
Leverages pydantic-settings for type validation and dynamic 
environment loading.

Usage::

    from config.settings import settings

    print(settings.model_path)
    print(settings.alerts_dir)
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger("sentinelops.settings")

# ---------------------------------------------------------------------------
# Valid choices for runtime evaluation
# ---------------------------------------------------------------------------
_VALID_LOG_LEVELS: set[str] = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
_VALID_DEVICES: set[str] = {"auto", "cpu", "cuda", "mps"}

# Determine active environment (defaults to dev)
_ENV = os.getenv("ENVIRONMENT", "dev").lower()
_ENV_FILE = f"config/environments/.env.{_ENV}"

# If root .env exists, it can override specific fields, 
# so we load the environment-specific file first, then .env
_ENV_FILES = (_ENV_FILE, ".env")


class Settings(BaseSettings):
    """Immutable, validated project settings.

    Uses pydantic-settings to validate required paths and secrets.
    """

    # Environment
    environment: Literal["dev", "prod", "test"] = Field(default="dev", alias="ENVIRONMENT")

    # API configuration
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)

    # Core logic configuration
    confidence_threshold: float = Field(default=0.25, ge=0.0, le=1.0)
    log_level: str = Field(default="INFO")
    device: str = Field(default="auto")
    
    # MLflow Tracking
    mlflow_tracking_uri: str = Field(default="http://localhost:5000")

    # ---------------------------------------------------------
    # Hardcoded Paths (Required: No Defaults)
    # ---------------------------------------------------------
    model_path: Path
    alerts_dir: Path
    reports_dir: Path
    snapshots_dir: Path
    events_dir: Path
    registry_dir: Path
    
    # ---------------------------------------------------------
    # Infrastructure (Database & Redis) - optional depending on env
    # ---------------------------------------------------------
    postgres_user: str | None = None
    postgres_password: str | None = None
    postgres_db: str | None = None
    postgres_host: str | None = None
    postgres_port: int | None = None
    
    redis_host: str | None = None
    redis_port: int | None = None

    model_config = SettingsConfigDict(
        env_file=_ENV_FILES,
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def __post_init__(self):
        """Additional manual validations that Pydantic Field constraints don't cover easily."""
        if self.log_level not in _VALID_LOG_LEVELS:
            raise ValueError(f"LOG_LEVEL must be one of {sorted(_VALID_LOG_LEVELS)}, got '{self.log_level}'")
        if self.device not in _VALID_DEVICES:
            raise ValueError(f"DEVICE must be one of {sorted(_VALID_DEVICES)}, got '{self.device}'")

    def configure_logging(self) -> None:
        """Apply `log_level` to the root logger."""
        logging.basicConfig(
            level=getattr(logging, self.log_level.upper(), logging.INFO),
            format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            force=True,
        )


# Global singleton
settings = Settings()

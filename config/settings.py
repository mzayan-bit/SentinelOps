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

from pydantic import Field, field_validator, model_validator
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
    api_version: str = Field(default="1.0.0")
    cors_allow_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    cors_allow_credentials: bool = Field(default=True)
    request_id_header: str = Field(default="X-Request-ID")
    structured_json_logs: bool = Field(default=True)

    # Core logic configuration
    confidence_threshold: float = Field(default=0.25, ge=0.0, le=1.0)
    log_level: str = Field(default="INFO")
    device: str = Field(default="auto")
    enable_privacy_mode: bool = Field(default=False, description="Blur faces in output video/snapshots")
    alert_cooldown_seconds: int = Field(default=60, ge=0, description="Cooldown period (seconds) to suppress duplicate alerts for the same worker/camera/type.")
    alert_cooldown_profiles: dict[str, int] = Field(default_factory=dict, description="Cooldown overrides by alert type (in seconds).")
    escalate_to_medium_threshold: int = Field(default=3, description="Duplicates needed to escalate to Medium")
    escalate_to_high_threshold: int = Field(default=5, description="Duplicates needed to escalate to High")
    escalate_to_critical_threshold: int = Field(default=10, description="Duplicates needed to escalate to Critical")
    rate_limit_rpm: int = Field(default=60, ge=0, description="Max API requests per minute per client IP (0 = unlimited).")
    rate_limit_enabled: bool = Field(default=True, description="Enable/disable API rate limiting.")
    task_worker_max_workers: int = Field(default=4, ge=1, le=32)
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

    # ---------------------------------------------------------
    # Authentication & Security
    # ---------------------------------------------------------
    secret_key: str = Field(default="dev-super-secret-key-change-me-in-production")
    jwt_algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=15)
    refresh_token_expire_minutes: int = Field(default=60 * 24 * 7) # 7 days
    
    # ---------------------------------------------------------
    # Email Notifications (SMTP)
    # ---------------------------------------------------------
    smtp_host: str | None = None
    smtp_port: int = Field(default=587)
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_tls: bool = Field(default=True)
    smtp_from_email: str | None = None
    
    notify_emails: list[str] = Field(default_factory=list)
    notify_severity_threshold: str = Field(default="high")  # low, medium, high, critical

    # ---------------------------------------------------------
    # Slack Notifications
    # ---------------------------------------------------------
    slack_webhook_url: str | None = None
    slack_bot_token: str | None = None
    slack_channel: str | None = None
    slack_severity_threshold: str = Field(default="high")  # low, medium, high, critical

    # ---------------------------------------------------------
    # MS Teams Notifications
    # ---------------------------------------------------------
    teams_webhook_url: str | None = None
    teams_severity_threshold: str = Field(default="high")  # low, medium, high, critical

    @property
    def async_database_url(self) -> str:
        """Compile the asyncpg connection string from settings."""
        if not all([self.postgres_user, self.postgres_password, self.postgres_db, self.postgres_host]):
            return "sqlite+aiosqlite:///sentinelops_dev.db"  # File-based fallback for dev/testing
        
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_url(self) -> str:
        """Compile the Redis connection string from settings."""
        if self.redis_host:
            port = self.redis_port or 6379
            return f"redis://{self.redis_host}:{port}/0"
        return "redis://localhost:6379/0"

    model_config = SettingsConfigDict(
        env_file=_ENV_FILES,
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def is_dev(self) -> bool:
        return self.environment == "dev"

    @property
    def is_prod(self) -> bool:
        return self.environment == "prod"

    @property
    def is_test(self) -> bool:
        return self.environment == "test"

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        normalized = value.upper()
        if normalized not in _VALID_LOG_LEVELS:
            raise ValueError(f"LOG_LEVEL must be one of {sorted(_VALID_LOG_LEVELS)}, got '{value}'")
        return normalized

    @field_validator("device")
    @classmethod
    def validate_device(cls, value: str) -> str:
        normalized = value.lower()
        if normalized not in _VALID_DEVICES:
            raise ValueError(f"DEVICE must be one of {sorted(_VALID_DEVICES)}, got '{value}'")
        return normalized

    @field_validator("cors_allow_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @model_validator(mode="after")
    def validate_environment_defaults(self) -> "Settings":
        if self.is_prod and "*" in self.cors_allow_origins:
            raise ValueError("CORS_ALLOW_ORIGINS cannot contain '*' in production")
        if self.is_prod and self.secret_key == "dev-super-secret-key-change-me-in-production":
            raise ValueError("SECRET_KEY must be overridden with a secure random string in production")
        if self.postgres_port is not None and self.postgres_port <= 0:
            raise ValueError("POSTGRES_PORT must be positive")
        return self

    def configure_logging(self) -> None:
        """Apply `log_level` to the root logger."""
        from app.core.logging import configure_logging

        configure_logging(self.log_level, json_logs=self.structured_json_logs)


# Global singleton
settings = Settings()

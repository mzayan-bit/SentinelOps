"""
SentinelOps — Centralised Settings
=====================================
Single source of truth for project-wide configuration.
Values are read from environment variables (or ``.env`` file),
with sensible defaults for local development.

Usage::

    from config.settings import settings

    print(settings.model_path)
    print(settings.confidence_threshold)
    print(settings.log_level)
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("sentinelops.settings")

# ---------------------------------------------------------------------------
# Valid choices
# ---------------------------------------------------------------------------
_VALID_LOG_LEVELS: set[str] = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
_VALID_DEVICES: set[str] = {"auto", "cpu", "cuda", "mps"}


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Settings:
    """Immutable, validated project settings.

    Every field maps to an environment variable. If the variable is
    unset, the default shown below is used.

    Attributes
    ----------
    model_path : Path
        Path to YOLO model weights.  Env: ``MODEL_PATH``
    confidence_threshold : float
        Minimum detection confidence.  Env: ``CONFIDENCE_THRESHOLD``
    log_level : str
        Python logging level.  Env: ``LOG_LEVEL``
    device : str
        Inference device.  Env: ``DEVICE``
    api_host : str
        FastAPI bind address.  Env: ``API_HOST``
    api_port : int
        FastAPI bind port.  Env: ``API_PORT``
    mlflow_tracking_uri : str
        MLflow server URI.  Env: ``MLFLOW_TRACKING_URI``
    artifacts_dir : Path
        Root directory for generated artifacts.  Env: ``ARTIFACTS_DIR``
    """

    model_path: Path = field(default_factory=lambda: Path(os.getenv("MODEL_PATH", "models/best.pt")))
    confidence_threshold: float = field(default_factory=lambda: float(os.getenv("CONFIDENCE_THRESHOLD", "0.25")))
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO").upper())
    device: str = field(default_factory=lambda: os.getenv("DEVICE", "auto").lower())
    api_host: str = field(default_factory=lambda: os.getenv("API_HOST", "0.0.0.0"))
    api_port: int = field(default_factory=lambda: int(os.getenv("API_PORT", "8000")))
    mlflow_tracking_uri: str = field(default_factory=lambda: os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000"))
    artifacts_dir: Path = field(default_factory=lambda: Path(os.getenv("ARTIFACTS_DIR", "artifacts")))

    def __post_init__(self) -> None:
        """Validate all fields after initialisation."""
        errors: list[str] = []

        if self.confidence_threshold < 0.0 or self.confidence_threshold > 1.0:
            errors.append(
                f"CONFIDENCE_THRESHOLD must be in [0, 1], got {self.confidence_threshold}"
            )

        if self.log_level not in _VALID_LOG_LEVELS:
            errors.append(
                f"LOG_LEVEL must be one of {sorted(_VALID_LOG_LEVELS)}, got '{self.log_level}'"
            )

        if self.device not in _VALID_DEVICES:
            errors.append(
                f"DEVICE must be one of {sorted(_VALID_DEVICES)}, got '{self.device}'"
            )

        if self.api_port < 1 or self.api_port > 65535:
            errors.append(
                f"API_PORT must be in [1, 65535], got {self.api_port}"
            )

        if errors:
            raise ValueError(
                "Invalid configuration:\n  • " + "\n  • ".join(errors)
            )

        logger.debug("Settings loaded: %s", self)

    def configure_logging(self) -> None:
        """Apply :attr:`log_level` to the root logger."""
        logging.basicConfig(
            level=getattr(logging, self.log_level),
            format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            force=True,
        )


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------
settings = Settings()

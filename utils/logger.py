"""
SentinelOps — Project Logger
===============================
Configures and provides a reusable logger for every module in the
project.  Log level is read from :pydata:`config.settings.settings`.

Usage::

    from utils.logger import get_logger

    logger = get_logger(__name__)
    logger.info("Pipeline started")
    logger.warning("Low confidence detection")
    logger.error("Model file not found")
"""

from __future__ import annotations

import logging
import sys

from config.settings import settings

# ---------------------------------------------------------------------------
# Format
# ---------------------------------------------------------------------------
LOG_FORMAT: str = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S"

# ---------------------------------------------------------------------------
# Root configuration (runs once on first import)
# ---------------------------------------------------------------------------
_configured: bool = False


def _configure_root() -> None:
    """Set up the root logger with console output and the project format."""
    global _configured
    if _configured:
        return

    root = logging.getLogger()
    root.setLevel(getattr(logging, settings.log_level, logging.INFO))

    # Avoid duplicate handlers if module is re-imported
    if not root.handlers:
        console = logging.StreamHandler(sys.stdout)
        console.setLevel(getattr(logging, settings.log_level, logging.INFO))
        console.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
        root.addHandler(console)

    _configured = True


_configure_root()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def get_logger(name: str) -> logging.Logger:
    """Return a named logger under the project hierarchy.

    Parameters
    ----------
    name : str
        Typically ``__name__`` of the calling module.

    Returns
    -------
    logging.Logger
        Configured logger instance.
    """
    return logging.getLogger(name)

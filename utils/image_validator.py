"""
SentinelOps — Image Validator
================================
Security-focused validation for uploaded image files.

Usage::

    from utils.image_validator import validate_image

    # From a file path
    validate_image(Path("photo.jpg"))

    # From raw bytes (e.g. FastAPI UploadFile)
    validate_image_bytes(data, filename="upload.png")
"""

from __future__ import annotations

from pathlib import Path

from utils.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
ALLOWED_EXTENSIONS: set[str] = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
MAX_FILE_SIZE_MB: float = 20.0
MAX_FILE_SIZE_BYTES: int = int(MAX_FILE_SIZE_MB * 1024 * 1024)

# JPEG: FF D8 FF | PNG: 89 50 4E 47 | BMP: 42 4D | WEBP: 52 49 46 46
_MAGIC_BYTES: dict[str, list[bytes]] = {
    ".jpg": [b"\xff\xd8\xff"],
    ".jpeg": [b"\xff\xd8\xff"],
    ".png": [b"\x89PNG"],
    ".bmp": [b"BM"],
    ".webp": [b"RIFF"],
}


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------
class ImageValidationError(ValueError):
    """Raised when an image fails a validation check."""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def validate_image(path: Path) -> None:
    """Validate an image file on disk.

    Parameters
    ----------
    path : Path
        Path to the image file.

    Raises
    ------
    ImageValidationError
        If any check fails.
    """
    if not path.exists():
        raise ImageValidationError(f"File not found: {path}")

    _check_extension(path.name)
    _check_file_size(path.stat().st_size, path.name)
    _check_magic_bytes(path.read_bytes()[:16], path.name)

    logger.debug("Image validated: %s", path.name)


def validate_image_bytes(
    data: bytes,
    filename: str = "upload",
) -> None:
    """Validate raw image bytes (e.g. from an HTTP upload).

    Parameters
    ----------
    data : bytes
        Raw file content.
    filename : str
        Original filename (used for extension check).

    Raises
    ------
    ImageValidationError
        If any check fails.
    """
    _check_extension(filename)
    _check_file_size(len(data), filename)
    _check_magic_bytes(data[:16], filename)

    logger.debug("Image bytes validated: %s (%d bytes)", filename, len(data))


# ---------------------------------------------------------------------------
# Internal checks
# ---------------------------------------------------------------------------
def _check_extension(filename: str) -> None:
    """Reject files whose extension is not in the allow-list."""
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ImageValidationError(
            f"Unsupported file type '{ext}'. "
            f"Allowed: {sorted(ALLOWED_EXTENSIONS)}"
        )


def _check_file_size(size: int, filename: str) -> None:
    """Reject files exceeding the maximum size."""
    if size > MAX_FILE_SIZE_BYTES:
        mb = size / (1024 * 1024)
        raise ImageValidationError(
            f"File '{filename}' is {mb:.1f} MB, "
            f"exceeding the {MAX_FILE_SIZE_MB:.0f} MB limit."
        )
    if size == 0:
        raise ImageValidationError(f"File '{filename}' is empty (0 bytes).")


def _check_magic_bytes(header: bytes, filename: str) -> None:
    """Verify the file's magic bytes match its extension."""
    ext = Path(filename).suffix.lower()
    expected = _MAGIC_BYTES.get(ext, [])

    if expected and not any(header.startswith(m) for m in expected):
        raise ImageValidationError(
            f"File '{filename}' content does not match '{ext}' format. "
            "The file may be corrupted or misnamed."
        )

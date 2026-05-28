import base64
import os
from pathlib import Path

from config import SUPPORTED_IMAGE_EXTENSIONS, MIME_TYPES
from utils import get_logger

logger = get_logger(__name__)


def load_image(path: str) -> dict:
    """Load an image from disk and return its base64 encoding with metadata."""
    file_path = Path(path)

    if not file_path.exists():
        raise FileNotFoundError(f"Image file not found: {path}")

    ext = file_path.suffix.lower()
    if ext not in SUPPORTED_IMAGE_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type '{ext}'. Allowed: {', '.join(sorted(SUPPORTED_IMAGE_EXTENSIONS))}"
        )

    logger.info(f"Loading image: {file_path.name}")
    raw_bytes = file_path.read_bytes()
    encoded = base64.b64encode(raw_bytes).decode("utf-8")

    return {
        "filename": file_path.name,
        "base64": encoded,
        "mime_type": MIME_TYPES[ext],
    }

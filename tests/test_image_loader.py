import base64
import os
import sys
import tempfile
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from image_loader import load_image


def _write_temp_image(suffix: str, content: bytes = b"fake-image-data") -> str:
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    tmp.write(content)
    tmp.close()
    return tmp.name


def test_valid_jpg_returns_correct_structure():
    path = _write_temp_image(".jpg")
    try:
        result = load_image(path)
        assert "filename" in result
        assert "base64" in result
        assert "mime_type" in result
        assert result["mime_type"] == "image/jpeg"
        assert result["filename"].endswith(".jpg")
    finally:
        os.unlink(path)


def test_valid_jpeg_extension():
    path = _write_temp_image(".jpeg")
    try:
        result = load_image(path)
        assert result["mime_type"] == "image/jpeg"
    finally:
        os.unlink(path)


def test_valid_png_returns_correct_structure():
    path = _write_temp_image(".png")
    try:
        result = load_image(path)
        assert result["mime_type"] == "image/png"
    finally:
        os.unlink(path)


def test_valid_webp_returns_correct_structure():
    path = _write_temp_image(".webp")
    try:
        result = load_image(path)
        assert result["mime_type"] == "image/webp"
    finally:
        os.unlink(path)


def test_base64_output_is_nonempty_string():
    path = _write_temp_image(".jpg", b"some-real-ish-bytes")
    try:
        result = load_image(path)
        assert isinstance(result["base64"], str)
        assert len(result["base64"]) > 0
    finally:
        os.unlink(path)


def test_base64_is_decodable():
    content = b"hello idlipeek"
    path = _write_temp_image(".png", content)
    try:
        result = load_image(path)
        decoded = base64.b64decode(result["base64"])
        assert decoded == content
    finally:
        os.unlink(path)


def test_nonexistent_file_raises_file_not_found():
    with pytest.raises(FileNotFoundError):
        load_image("/tmp/does_not_exist_abc123.jpg")


def test_unsupported_extension_gif_raises_value_error():
    path = _write_temp_image(".gif")
    try:
        with pytest.raises(ValueError):
            load_image(path)
    finally:
        os.unlink(path)


def test_unsupported_extension_pdf_raises_value_error():
    path = _write_temp_image(".pdf")
    try:
        with pytest.raises(ValueError):
            load_image(path)
    finally:
        os.unlink(path)


def test_filename_preserved_in_result():
    path = _write_temp_image(".png")
    try:
        result = load_image(path)
        assert result["filename"] == os.path.basename(path)
    finally:
        os.unlink(path)

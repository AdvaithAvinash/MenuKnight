import base64
import cgi
import io
import json
import os
import sys

# Netlify bundles the shared modules alongside this file (see netlify.toml included_files)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gemini_client import extract_dishes_from_image
from parser import parse_dish_list

SUPPORTED_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
MIME_MAP = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}
MAX_BYTES = 4 * 1024 * 1024  # 4 MB (Netlify base64-encodes bodies, so ~6 MB raw limit)


def _cors(status: int, body: str) -> dict:
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        },
        "body": body,
    }


def _parse_upload(event: dict):
    """Return (raw_bytes, filename) from a multipart/form-data Netlify event."""
    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
    content_type = headers.get("content-type", "")

    body = event.get("body") or ""
    if event.get("isBase64Encoded", False):
        raw_body = base64.b64decode(body)
    else:
        raw_body = body.encode("utf-8") if isinstance(body, str) else body

    environ = {
        "REQUEST_METHOD": "POST",
        "CONTENT_TYPE": content_type,
        "CONTENT_LENGTH": str(len(raw_body)),
    }
    form = cgi.FieldStorage(fp=io.BytesIO(raw_body), environ=environ, keep_blank_values=True)

    if "image" not in form:
        raise ValueError("No 'image' field found in the form. Use field name 'image'.")

    item = form["image"]
    return item.file.read(), item.filename or "upload"


def handler(event, context):
    method = (event.get("httpMethod") or "GET").upper()

    if method == "OPTIONS":
        return _cors(200, "")

    if method == "GET":
        return _cors(200, json.dumps({"status": "ok", "service": "IdliPeek"}))

    if method != "POST":
        return _cors(405, json.dumps({"error": "Method not allowed"}))

    try:
        raw_bytes, filename = _parse_upload(event)
    except ValueError as e:
        return _cors(400, json.dumps({"error": str(e)}))

    ext = os.path.splitext(filename)[1].lower()
    if ext not in SUPPORTED_EXTS:
        return _cors(400, json.dumps({
            "error": f"Unsupported file type '{ext}'. Allowed: jpg, jpeg, png, webp"
        }))

    if len(raw_bytes) > MAX_BYTES:
        return _cors(400, json.dumps({"error": "Image too large. Max 4 MB."}))

    try:
        encoded = base64.b64encode(raw_bytes).decode("utf-8")
        mime_type = MIME_MAP[ext]
        raw_text = extract_dishes_from_image(encoded, mime_type)
        dishes = parse_dish_list(raw_text)
    except Exception as e:
        return _cors(500, json.dumps({"error": str(e)}))

    return _cors(200, json.dumps({
        "filename": filename,
        "dishes": dishes,
        "count": len(dishes),
        "raw_gemini_output": raw_text,
    }))

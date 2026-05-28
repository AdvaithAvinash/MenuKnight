"""
Self-contained Netlify Function — no imports from the repo root.
All logic is inlined here so there are no module-path issues at deploy time.
"""
import base64
import cgi
import io
import json
import os
import re

import requests

# ── Config ────────────────────────────────────────────────────────────────────
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-2.5-flash-preview-05-20"
GEMINI_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent"
)
EXTRACT_PROMPT = (
    "You are a menu reader. Extract only the food dish names from this menu image. "
    "Ignore prices, calorie counts, section headers, and descriptions. "
    "Return one dish name per line, nothing else."
)

SUPPORTED_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
MIME_MAP = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}
MAX_BYTES = 4 * 1024 * 1024  # 4 MB

# ── Gemini Vision ─────────────────────────────────────────────────────────────
def _extract_dishes(b64: str, mime: str) -> str:
    if not GEMINI_API_KEY:
        raise EnvironmentError("GEMINI_API_KEY environment variable is not set in Netlify")

    payload = {
        "contents": [{
            "parts": [
                {"text": EXTRACT_PROMPT},
                {"inlineData": {"mimeType": mime, "data": b64}},
            ]
        }]
    }
    resp = requests.post(
        GEMINI_URL,
        params={"key": GEMINI_API_KEY},
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["candidates"][0]["content"]["parts"][0]["text"]


# ── Dish Parser ───────────────────────────────────────────────────────────────
_PRICE_RE = re.compile(r"^[\$₹£€]?\s*\d+(\.\d+)?\s*$|Rs\.?\s*\d+")
_NOISE_RE = re.compile(r"^[\d\.\)\-\*•]+\s*$")


def _parse_dishes(raw: str) -> list:
    if not raw or not raw.strip():
        return []

    lines = []
    for chunk in raw.splitlines():
        lines.extend(chunk.split(","))

    dishes, seen = [], set()
    for line in lines:
        cleaned = re.sub(r"^[\s\d\.\)\-\*•]+", "", line).strip()
        cleaned = re.sub(
            r"[\$₹£€]\s*\d+(\.\d+)?|Rs\.?\s*\d+|\d+(\.\d+)?\s*(rs|₹|\$)?$",
            "", cleaned, flags=re.IGNORECASE,
        ).strip()
        if not cleaned or len(cleaned) < 2:
            continue
        if _PRICE_RE.match(cleaned) or _NOISE_RE.match(cleaned):
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        dishes.append(cleaned.title())

    return dishes


# ── Multipart Upload Parser ───────────────────────────────────────────────────
def _parse_upload(event: dict):
    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
    content_type = headers.get("content-type", "")

    body = event.get("body") or ""
    if event.get("isBase64Encoded", False):
        raw = base64.b64decode(body)
    else:
        raw = body.encode("utf-8") if isinstance(body, str) else body

    form = cgi.FieldStorage(
        fp=io.BytesIO(raw),
        environ={
            "REQUEST_METHOD": "POST",
            "CONTENT_TYPE": content_type,
            "CONTENT_LENGTH": str(len(raw)),
        },
        keep_blank_values=True,
    )

    if "image" not in form:
        raise ValueError("No 'image' field in form data. Use field name 'image'.")

    item = form["image"]
    return item.file.read(), item.filename or "upload"


# ── Response Helper ───────────────────────────────────────────────────────────
def _resp(status: int, data: dict) -> dict:
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        },
        "body": json.dumps(data),
    }


# ── Handler ───────────────────────────────────────────────────────────────────
def handler(event, context):
    method = (event.get("httpMethod") or "GET").upper()

    if method == "OPTIONS":
        return _resp(200, {})

    if method == "GET":
        return _resp(200, {"status": "ok", "service": "IdliPeek"})

    if method != "POST":
        return _resp(405, {"error": "Method not allowed"})

    try:
        raw_bytes, filename = _parse_upload(event)
    except ValueError as e:
        return _resp(400, {"error": str(e)})

    ext = os.path.splitext(filename)[1].lower()
    if ext not in SUPPORTED_EXTS:
        return _resp(400, {"error": f"Unsupported file type '{ext}'. Allowed: jpg, jpeg, png, webp"})

    if len(raw_bytes) > MAX_BYTES:
        return _resp(400, {"error": "Image too large. Max 4 MB."})

    try:
        encoded = base64.b64encode(raw_bytes).decode("utf-8")
        raw_text = _extract_dishes(encoded, MIME_MAP[ext])
        dishes = _parse_dishes(raw_text)
    except Exception as e:
        return _resp(500, {"error": str(e)})

    return _resp(200, {
        "filename": filename,
        "dishes": dishes,
        "count": len(dishes),
        "raw_gemini_output": raw_text,
    })

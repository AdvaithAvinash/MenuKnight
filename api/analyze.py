import base64
import cgi
import io
import json
import os
import sys

from http.server import BaseHTTPRequestHandler

# Repo root is one level up from api/ — gives access to shared modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gemini_client import extract_dishes_from_image
from parser import parse_dish_list

SUPPORTED_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
MIME_MAP = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}
MAX_BYTES = 4 * 1024 * 1024  # Vercel request body limit is ~4.5 MB


class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self._cors(200)
        self.end_headers()

    def do_GET(self):
        self._json(200, {"status": "ok", "service": "IdliPeek"})

    def do_POST(self):
        content_type = self.headers.get("Content-Type", "")
        content_length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(content_length)

        environ = {
            "REQUEST_METHOD": "POST",
            "CONTENT_TYPE": content_type,
            "CONTENT_LENGTH": str(len(raw_body)),
        }
        form = cgi.FieldStorage(
            fp=io.BytesIO(raw_body), environ=environ, keep_blank_values=True
        )

        if "image" not in form:
            self._json(400, {"error": "No 'image' field found. Use field name 'image'."})
            return

        item = form["image"]
        filename = item.filename or "upload"
        ext = os.path.splitext(filename)[1].lower()

        if ext not in SUPPORTED_EXTS:
            self._json(400, {
                "error": f"Unsupported file type '{ext}'. Allowed: jpg, jpeg, png, webp"
            })
            return

        file_bytes = item.file.read()
        if len(file_bytes) > MAX_BYTES:
            self._json(400, {"error": "Image too large. Max 4 MB."})
            return

        try:
            encoded = base64.b64encode(file_bytes).decode("utf-8")
            raw_text = extract_dishes_from_image(encoded, MIME_MAP[ext])
            dishes = parse_dish_list(raw_text)
        except Exception as e:
            self._json(500, {"error": str(e)})
            return

        self._json(200, {
            "filename": filename,
            "dishes": dishes,
            "count": len(dishes),
            "raw_gemini_output": raw_text,
        })

    def _cors(self, status: int):
        self.send_response(status)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")

    def _json(self, status: int, data: dict):
        body = json.dumps(data).encode()
        self._cors(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass  # suppress noisy default access logs

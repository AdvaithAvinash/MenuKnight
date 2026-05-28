import base64
import io
import json
import os

from flask import Flask, request, jsonify
from PIL import Image

from config import SUPPORTED_IMAGE_EXTENSIONS, MIME_TYPES
from gemini_client import extract_dishes_from_image
from parser import parse_dish_list
from utils import get_logger

logger = get_logger(__name__)
app = Flask(__name__)

MAX_FILE_SIZE_MB = 10
ALLOWED_MIMES = {"image/jpeg", "image/png", "image/webp"}


@app.get("/")
def health():
    return jsonify({"status": "ok", "service": "IdliPeek"})


@app.post("/analyze")
def analyze():
    if "image" not in request.files:
        return jsonify({"error": "No image file provided. Use field name 'image'."}), 400

    file = request.files["image"]
    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in SUPPORTED_IMAGE_EXTENSIONS:
        return jsonify({
            "error": f"Unsupported file type '{ext}'. Allowed: jpg, jpeg, png, webp"
        }), 400

    raw_bytes = file.read()
    if len(raw_bytes) > MAX_FILE_SIZE_MB * 1024 * 1024:
        return jsonify({"error": f"File too large. Max {MAX_FILE_SIZE_MB}MB"}), 400

    mime_type = MIME_TYPES[ext]
    encoded = base64.b64encode(raw_bytes).decode("utf-8")

    logger.info(f"Analyzing: {file.filename} ({mime_type}, {len(raw_bytes)} bytes)")

    raw_text = extract_dishes_from_image(encoded, mime_type)
    dishes = parse_dish_list(raw_text)

    return jsonify({
        "filename": file.filename,
        "dishes": dishes,
        "count": len(dishes),
        "raw_gemini_output": raw_text,
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

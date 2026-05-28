import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY", "")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")
SPOONACULAR_API_KEY = os.getenv("SPOONACULAR_API_KEY", "")
SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")

SUPPORTED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MIME_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}

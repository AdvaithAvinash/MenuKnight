import requests
from config import GEMINI_API_KEY
from utils import get_logger

logger = get_logger(__name__)

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


def extract_dishes_from_image(base64_image: str, mime_type: str) -> str:
    """Call Gemini Vision and return raw text of dish names."""
    if not GEMINI_API_KEY:
        raise EnvironmentError("GEMINI_API_KEY is not set")

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": EXTRACT_PROMPT},
                    {"inlineData": {"mimeType": mime_type, "data": base64_image}},
                ]
            }
        ]
    }

    logger.info(f"Calling Gemini Vision ({GEMINI_MODEL})")
    try:
        response = requests.post(
            GEMINI_URL,
            params={"key": GEMINI_API_KEY},
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
    except requests.exceptions.Timeout:
        raise RuntimeError("Gemini API request timed out after 30s")
    except requests.exceptions.HTTPError as e:
        raise RuntimeError(f"Gemini API error {response.status_code}: {response.text}") from e

    data = response.json()
    try:
        raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError) as e:
        raise RuntimeError(f"Unexpected Gemini response structure: {data}") from e

    logger.info(f"Gemini returned {len(raw_text.splitlines())} lines")
    return raw_text

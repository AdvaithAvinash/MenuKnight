import json
import requests
from config import GEMINI_API_KEY
from utils import get_logger

logger = get_logger(__name__)

GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent"
)

EXTRACT_PROMPT = (
    "You are a menu reader. Extract only the food dish names from this menu image. "
    "Ignore prices, calorie counts, section headers, and descriptions. "
    "Return one dish name per line, nothing else."
)

DESCRIBE_PROMPT = (
    "For each dish in the list below, write a 1-2 sentence description that helps "
    "a first-time traveler understand what the dish is. Be friendly and specific.\n"
    "Return ONLY a valid JSON array with no markdown or extra text:\n"
    '[{{"dish": "Dish Name", "description": "Description."}}]\n\n'
    "Dishes:\n{dish_list}"
)


def _post(payload: dict) -> dict:
    if not GEMINI_API_KEY:
        raise EnvironmentError("GEMINI_API_KEY is not set")
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
    return response.json()


def extract_dishes_from_image(base64_image: str, mime_type: str) -> str:
    """Call Gemini Vision and return raw text of dish names."""
    logger.info(f"Calling Gemini Vision ({GEMINI_MODEL})")
    data = _post({
        "contents": [{
            "parts": [
                {"text": EXTRACT_PROMPT},
                {"inlineData": {"mimeType": mime_type, "data": base64_image}},
            ]
        }]
    })
    try:
        raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError) as e:
        raise RuntimeError(f"Unexpected Gemini response structure: {data}") from e
    logger.info(f"Gemini returned {len(raw_text.splitlines())} lines")
    return raw_text


def describe_dishes(dish_names: list) -> dict:
    """Return {dish_name: description} for all dishes in a single batched API call."""
    if not dish_names:
        return {}

    logger.info(f"Generating descriptions for {len(dish_names)} dishes")
    prompt = DESCRIBE_PROMPT.format(
        dish_list="\n".join(f"- {d}" for d in dish_names)
    )
    data = _post({"contents": [{"parts": [{"text": prompt}]}]})

    try:
        raw = data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        logger.warning("Unexpected Gemini response for descriptions")
        return {}

    # Extract the JSON array from the response (tolerates markdown fences)
    import re
    match = re.search(r"\[[\s\S]*\]", raw)
    if not match:
        logger.warning(f"Could not find JSON array in description response: {raw[:200]}")
        return {}

    try:
        items = json.loads(match.group())
        return {item["dish"]: item["description"] for item in items if "dish" in item}
    except (json.JSONDecodeError, KeyError) as e:
        logger.warning(f"Failed to parse description JSON: {e}")
        return {}

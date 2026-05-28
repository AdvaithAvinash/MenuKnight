import requests
from config import SERPAPI_KEY
from utils import get_logger

logger = get_logger(__name__)

_URL = "https://serpapi.com/search"


def search_serpapi(dish_name: str) -> str | None:
    if not SERPAPI_KEY:
        raise EnvironmentError("SERPAPI_KEY is not set")

    try:
        resp = requests.get(
            _URL,
            params={
                "q": dish_name,
                "tbm": "isch",
                "num": 1,
                "api_key": SERPAPI_KEY,
            },
            timeout=15,
        )
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        logger.warning(f"SerpAPI failed for '{dish_name}': {e}")
        return None

    images = resp.json().get("images_results", [])
    if not images:
        logger.info(f"SerpAPI: no results for '{dish_name}'")
        return None

    url = images[0].get("original") or images[0].get("thumbnail")
    logger.info(f"SerpAPI hit for '{dish_name}'")
    return url

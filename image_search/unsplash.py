import requests
from config import UNSPLASH_ACCESS_KEY
from utils import get_logger

logger = get_logger(__name__)

_URL = "https://api.unsplash.com/search/photos"


def search_unsplash(dish_name: str) -> str | None:
    if not UNSPLASH_ACCESS_KEY:
        raise EnvironmentError("UNSPLASH_ACCESS_KEY is not set")

    try:
        resp = requests.get(
            _URL,
            params={"query": dish_name, "per_page": 1, "orientation": "landscape"},
            headers={"Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"},
            timeout=10,
        )
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        logger.warning(f"Unsplash failed for '{dish_name}': {e}")
        return None

    results = resp.json().get("results", [])
    if not results:
        logger.info(f"Unsplash: no results for '{dish_name}'")
        return None

    url = results[0]["urls"]["regular"]
    logger.info(f"Unsplash hit for '{dish_name}'")
    return url

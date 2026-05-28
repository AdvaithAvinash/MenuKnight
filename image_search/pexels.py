import requests
from config import PEXELS_API_KEY
from utils import get_logger

logger = get_logger(__name__)

_URL = "https://api.pexels.com/v1/search"


def search_pexels(dish_name: str) -> str | None:
    if not PEXELS_API_KEY:
        raise EnvironmentError("PEXELS_API_KEY is not set")

    try:
        resp = requests.get(
            _URL,
            params={"query": dish_name, "per_page": 1, "orientation": "landscape"},
            headers={"Authorization": PEXELS_API_KEY},
            timeout=10,
        )
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        logger.warning(f"Pexels failed for '{dish_name}': {e}")
        return None

    photos = resp.json().get("photos", [])
    if not photos:
        logger.info(f"Pexels: no results for '{dish_name}'")
        return None

    url = photos[0]["src"]["medium"]
    logger.info(f"Pexels hit for '{dish_name}'")
    return url

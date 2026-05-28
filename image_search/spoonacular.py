import requests
from config import SPOONACULAR_API_KEY
from utils import get_logger

logger = get_logger(__name__)

_URL = "https://api.spoonacular.com/food/search"


def search_spoonacular(dish_name: str) -> str | None:
    if not SPOONACULAR_API_KEY:
        raise EnvironmentError("SPOONACULAR_API_KEY is not set")

    try:
        resp = requests.get(
            _URL,
            params={"query": dish_name, "number": 1, "apiKey": SPOONACULAR_API_KEY},
            timeout=10,
        )
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        logger.warning(f"Spoonacular failed for '{dish_name}': {e}")
        return None

    products = resp.json().get("searchResults", [])
    for section in products:
        results = section.get("results", [])
        if results and results[0].get("image"):
            logger.info(f"Spoonacular hit for '{dish_name}'")
            return results[0]["image"]

    logger.info(f"Spoonacular: no results for '{dish_name}'")
    return None

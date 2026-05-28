from utils import get_logger
from image_search.spoonacular import search_spoonacular
from image_search.unsplash import search_unsplash
from image_search.pexels import search_pexels
from image_search.serpapi import search_serpapi

logger = get_logger(__name__)

def get_best_dish_image(dish_name: str) -> dict:
    """Try each image source in order and return the first successful result."""
    # Build at call time so unit-test patches on these names take effect
    sources = [
        ("spoonacular", search_spoonacular),
        ("unsplash", search_unsplash),
        ("pexels", search_pexels),
        ("serpapi", search_serpapi),
    ]
    for source_name, search_fn in sources:
        try:
            url = search_fn(dish_name)
        except EnvironmentError:
            # API key not configured — skip silently
            logger.debug(f"Skipping {source_name}: API key not set")
            continue
        except Exception as e:
            logger.warning(f"{source_name} error for '{dish_name}': {e}")
            continue

        if url:
            return {"image_url": url, "source": source_name, "found": True}

    logger.info(f"No image found for '{dish_name}' across all sources")
    return {"image_url": None, "source": None, "found": False}

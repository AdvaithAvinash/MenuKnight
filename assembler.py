from cache import cache_get, cache_set
from gemini_client import describe_dishes
from image_search.resolver import get_best_dish_image
from utils import get_logger

logger = get_logger(__name__)


def assemble_results(dish_names: list) -> list:
    """Fetch image + description for each dish, using cache where available."""
    if not dish_names:
        return []

    # Split into cached and uncached
    cached, uncached = {}, []
    for dish in dish_names:
        hit = cache_get(dish)
        if hit:
            cached[dish] = hit
        else:
            uncached.append(dish)

    logger.info(f"Cache hits: {len(cached)} | to fetch: {len(uncached)}")

    # Batch description call for uncached dishes only
    descriptions = describe_dishes(uncached) if uncached else {}

    results = []
    for dish in dish_names:
        if dish in cached:
            results.append(cached[dish])
            continue

        image_result = get_best_dish_image(dish)
        entry = {
            "dish": dish,
            "description": descriptions.get(dish, ""),
            "image_url": image_result["image_url"],
            "image_source": image_result["source"],
            "image_found": image_result["found"],
        }
        cache_set(dish, entry)
        results.append(entry)
        logger.info(f"Assembled: {dish} | img={image_result['source']} | desc={bool(descriptions.get(dish))}")

    return results

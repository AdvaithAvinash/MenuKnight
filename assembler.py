from gemini_client import describe_dishes
from image_search.resolver import get_best_dish_image
from utils import get_logger

logger = get_logger(__name__)


def assemble_results(dish_names: list) -> list:
    """For each dish, fetch image + description and return a structured list."""
    if not dish_names:
        return []

    # Batch all descriptions in one API call
    descriptions = describe_dishes(dish_names)

    results = []
    for dish in dish_names:
        image_result = get_best_dish_image(dish)
        results.append({
            "dish": dish,
            "description": descriptions.get(dish, ""),
            "image_url": image_result["image_url"],
            "image_source": image_result["source"],
            "image_found": image_result["found"],
        })
        logger.info(f"Assembled: {dish} | img={image_result['source']} | desc={bool(descriptions.get(dish))}")

    return results

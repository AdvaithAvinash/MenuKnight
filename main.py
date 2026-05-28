import argparse
import json
import sys

from image_loader import load_image
from gemini_client import extract_dishes_from_image
from parser import parse_dish_list
from utils import get_logger

logger = get_logger(__name__)


def run_pipeline(image_path: str) -> dict:
    logger.info("=== IdliPeek pipeline start ===")

    image_data = load_image(image_path)
    logger.info(f"Loaded: {image_data['filename']} ({image_data['mime_type']})")

    raw_text = extract_dishes_from_image(image_data["base64"], image_data["mime_type"])
    logger.info(f"Raw Gemini output:\n{raw_text}")

    dishes = parse_dish_list(raw_text)
    logger.info(f"Extracted dishes: {dishes}")

    return {"filename": image_data["filename"], "dishes": dishes, "count": len(dishes)}


def main():
    parser = argparse.ArgumentParser(
        description="IdliPeek — peek at a menu before you pick"
    )
    parser.add_argument("image", help="Path to menu image (jpg/png/webp)")
    args = parser.parse_args()

    result = run_pipeline(args.image)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

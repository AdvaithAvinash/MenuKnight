import argparse
import json
import sys

from image_loader import load_image
from utils import get_logger

logger = get_logger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="IdliPeek — peek at a menu before you pick"
    )
    parser.add_argument("image", help="Path to menu image (jpg/png/webp)")
    args = parser.parse_args()

    logger.info("Starting IdliPeek pipeline")

    image_data = load_image(args.image)
    logger.info(f"Loaded: {image_data['filename']} ({image_data['mime_type']})")
    logger.info(f"Base64 length: {len(image_data['base64'])} chars")

    # Phases 2–8 will extend this pipeline
    result = {
        "filename": image_data["filename"],
        "mime_type": image_data["mime_type"],
        "base64_length": len(image_data["base64"]),
        "status": "image loaded — Gemini extraction not yet implemented",
    }

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

import re
from utils import get_logger

logger = get_logger(__name__)

# Matches standalone prices like ₹120, $5.00, Rs.80, 120, 12.5
_PRICE_RE = re.compile(r"^[\$₹£€]?\s*\d+(\.\d+)?\s*$|Rs\.?\s*\d+")
# Matches lines that are just numbering like "1.", "2)", "•", "-"
_NOISE_RE = re.compile(r"^[\d\.\)\-\*•]+\s*$")


def parse_dish_list(raw_text: str) -> list:
    """Convert raw Gemini output into a clean, deduplicated list of dish names."""
    if not raw_text or not raw_text.strip():
        return []

    lines = []
    for chunk in raw_text.splitlines():
        lines.extend(chunk.split(","))

    dishes = []
    seen = set()

    for line in lines:
        # Strip bullet points and leading numbering (e.g. "1. Dosa" → "Dosa")
        cleaned = re.sub(r"^[\s\d\.\)\-\*•]+", "", line).strip()
        # Remove inline prices (e.g. "Dosa ₹60" → "Dosa")
        cleaned = re.sub(r"[\$₹£€]\s*\d+(\.\d+)?|Rs\.?\s*\d+|\d+(\.\d+)?\s*(rs|₹|\$)?$", "", cleaned, flags=re.IGNORECASE).strip()

        if not cleaned:
            continue
        if len(cleaned) < 2:
            continue
        if _PRICE_RE.match(cleaned):
            continue
        if _NOISE_RE.match(cleaned):
            continue

        title_cased = cleaned.title()
        key = title_cased.lower()
        if key in seen:
            continue
        seen.add(key)
        dishes.append(title_cased)

    logger.info(f"Parsed {len(dishes)} dishes from raw text")
    return dishes

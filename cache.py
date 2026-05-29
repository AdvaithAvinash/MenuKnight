import time
from utils import get_logger

logger = get_logger(__name__)

_store: dict = {}
TTL = 86400  # 24 hours


def _key(raw: str) -> str:
    return raw.lower().strip()


def cache_get(dish: str) -> dict | None:
    k = _key(dish)
    entry = _store.get(k)
    if entry is None:
        return None
    if time.time() - entry["ts"] > TTL:
        del _store[k]
        logger.debug(f"Cache expired: {k}")
        return None
    logger.info(f"Cache hit: {k}")
    return entry["data"]


def cache_set(dish: str, value: dict) -> None:
    k = _key(dish)
    _store[k] = {"data": value, "ts": time.time()}
    logger.info(f"Cache set: {k}")


def cache_size() -> int:
    return len(_store)


def cache_clear() -> None:
    _store.clear()

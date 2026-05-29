import os
import sys
import time
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


def setup_function():
    from cache import cache_clear
    cache_clear()


def test_cache_miss_returns_none():
    from cache import cache_get
    assert cache_get("masala dosa") is None


def test_cache_set_and_get():
    from cache import cache_get, cache_set
    data = {"dish": "Idli", "description": "Soft rice cakes."}
    cache_set("Idli", data)
    assert cache_get("Idli") == data


def test_cache_key_is_case_insensitive():
    from cache import cache_get, cache_set
    cache_set("Dosa", {"dish": "Dosa"})
    assert cache_get("dosa") is not None
    assert cache_get("DOSA") is not None
    assert cache_get("Dosa") is not None


def test_cache_key_strips_whitespace():
    from cache import cache_get, cache_set
    cache_set("  Vada  ", {"dish": "Vada"})
    assert cache_get("vada") is not None


def test_expired_entry_returns_none():
    import time
    import cache as c
    from cache import cache_get, TTL
    # Plant an entry whose timestamp is already past the TTL
    c._store["sambar"] = {"data": {"dish": "Sambar"}, "ts": time.time() - TTL - 1}
    assert cache_get("Sambar") is None


def test_cache_size_reflects_entries():
    from cache import cache_set, cache_size
    cache_set("Uttapam", {"dish": "Uttapam"})
    cache_set("Pongal",  {"dish": "Pongal"})
    assert cache_size() >= 2


def test_cache_clear_empties_store():
    from cache import cache_set, cache_size, cache_clear
    cache_set("Rasam", {"dish": "Rasam"})
    cache_clear()
    assert cache_size() == 0

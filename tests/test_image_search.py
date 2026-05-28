import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# ── Unsplash ──────────────────────────────────────────────────────────────────

@patch("image_search.unsplash.UNSPLASH_ACCESS_KEY", "fake-key")
@patch("image_search.unsplash.requests.get")
def test_unsplash_returns_url_on_hit(mock_get):
    mock_get.return_value = MagicMock(
        status_code=200,
        json=lambda: {"results": [{"urls": {"regular": "https://unsplash.com/photo.jpg"}}]},
    )
    from image_search.unsplash import search_unsplash
    url = search_unsplash("Pizza")
    assert url == "https://unsplash.com/photo.jpg"


@patch("image_search.unsplash.UNSPLASH_ACCESS_KEY", "fake-key")
@patch("image_search.unsplash.requests.get")
def test_unsplash_returns_none_on_empty_results(mock_get):
    mock_get.return_value = MagicMock(status_code=200, json=lambda: {"results": []})
    from image_search.unsplash import search_unsplash
    assert search_unsplash("xyzabc123") is None


@patch("image_search.unsplash.UNSPLASH_ACCESS_KEY", "fake-key")
@patch("image_search.unsplash.requests.get")
def test_unsplash_returns_none_on_network_error(mock_get):
    import requests as req
    mock_get.side_effect = req.exceptions.ConnectionError("network down")
    from image_search.unsplash import search_unsplash
    assert search_unsplash("Biryani") is None


def test_unsplash_raises_when_key_missing():
    with patch("image_search.unsplash.UNSPLASH_ACCESS_KEY", ""):
        from image_search.unsplash import search_unsplash
        with pytest.raises(EnvironmentError):
            search_unsplash("Dosa")


# ── Pexels ────────────────────────────────────────────────────────────────────

@patch("image_search.pexels.PEXELS_API_KEY", "fake-key")
@patch("image_search.pexels.requests.get")
def test_pexels_returns_url_on_hit(mock_get):
    mock_get.return_value = MagicMock(
        status_code=200,
        json=lambda: {"photos": [{"src": {"medium": "https://pexels.com/photo.jpg"}}]},
    )
    from image_search.pexels import search_pexels
    assert search_pexels("Idli") == "https://pexels.com/photo.jpg"


@patch("image_search.pexels.PEXELS_API_KEY", "fake-key")
@patch("image_search.pexels.requests.get")
def test_pexels_returns_none_on_empty(mock_get):
    mock_get.return_value = MagicMock(status_code=200, json=lambda: {"photos": []})
    from image_search.pexels import search_pexels
    assert search_pexels("xyzabc") is None


# ── Spoonacular ───────────────────────────────────────────────────────────────

@patch("image_search.spoonacular.SPOONACULAR_API_KEY", "fake-key")
@patch("image_search.spoonacular.requests.get")
def test_spoonacular_returns_url_on_hit(mock_get):
    mock_get.return_value = MagicMock(
        status_code=200,
        json=lambda: {
            "searchResults": [{"results": [{"image": "https://spoonacular.com/food.jpg"}]}]
        },
    )
    from image_search.spoonacular import search_spoonacular
    assert search_spoonacular("Biryani") == "https://spoonacular.com/food.jpg"


@patch("image_search.spoonacular.SPOONACULAR_API_KEY", "fake-key")
@patch("image_search.spoonacular.requests.get")
def test_spoonacular_returns_none_on_empty(mock_get):
    mock_get.return_value = MagicMock(status_code=200, json=lambda: {"searchResults": []})
    from image_search.spoonacular import search_spoonacular
    assert search_spoonacular("xyzabc") is None


# ── SerpAPI ───────────────────────────────────────────────────────────────────

@patch("image_search.serpapi.SERPAPI_KEY", "fake-key")
@patch("image_search.serpapi.requests.get")
def test_serpapi_returns_url_on_hit(mock_get):
    mock_get.return_value = MagicMock(
        status_code=200,
        json=lambda: {"images_results": [{"original": "https://example.com/food.jpg"}]},
    )
    from image_search.serpapi import search_serpapi
    assert search_serpapi("Vada") == "https://example.com/food.jpg"


@patch("image_search.serpapi.SERPAPI_KEY", "fake-key")
@patch("image_search.serpapi.requests.get")
def test_serpapi_returns_none_on_empty(mock_get):
    mock_get.return_value = MagicMock(status_code=200, json=lambda: {"images_results": []})
    from image_search.serpapi import search_serpapi
    assert search_serpapi("xyzabc") is None


# ── Resolver (fallback chain) ─────────────────────────────────────────────────

@patch("image_search.resolver.search_spoonacular", return_value=None)
@patch("image_search.resolver.search_unsplash", return_value="https://unsplash.com/img.jpg")
@patch("image_search.resolver.search_pexels")
@patch("image_search.resolver.search_serpapi")
def test_resolver_uses_unsplash_when_spoonacular_fails(mock_serp, mock_pexels, mock_unsplash, mock_spoon):
    from image_search.resolver import get_best_dish_image
    result = get_best_dish_image("Masala Dosa")
    assert result["found"] is True
    assert result["source"] == "unsplash"
    assert result["image_url"] == "https://unsplash.com/img.jpg"
    mock_pexels.assert_not_called()
    mock_serp.assert_not_called()


@patch("image_search.resolver.search_spoonacular", return_value=None)
@patch("image_search.resolver.search_unsplash", return_value=None)
@patch("image_search.resolver.search_pexels", return_value="https://pexels.com/img.jpg")
@patch("image_search.resolver.search_serpapi")
def test_resolver_falls_through_to_pexels(mock_serp, mock_pexels, mock_unsplash, mock_spoon):
    from image_search.resolver import get_best_dish_image
    result = get_best_dish_image("Uttapam")
    assert result["source"] == "pexels"
    mock_serp.assert_not_called()


@patch("image_search.resolver.search_spoonacular", return_value=None)
@patch("image_search.resolver.search_unsplash", return_value=None)
@patch("image_search.resolver.search_pexels", return_value=None)
@patch("image_search.resolver.search_serpapi", return_value=None)
def test_resolver_returns_not_found_when_all_fail(mock_serp, mock_pexels, mock_unsplash, mock_spoon):
    from image_search.resolver import get_best_dish_image
    result = get_best_dish_image("xyzabc123")
    assert result == {"image_url": None, "source": None, "found": False}


@patch("image_search.resolver.search_spoonacular", side_effect=EnvironmentError("no key"))
@patch("image_search.resolver.search_unsplash", return_value="https://unsplash.com/img.jpg")
@patch("image_search.resolver.search_pexels")
@patch("image_search.resolver.search_serpapi")
def test_resolver_skips_unconfigured_source(mock_serp, mock_pexels, mock_unsplash, mock_spoon):
    from image_search.resolver import get_best_dish_image
    result = get_best_dish_image("Dosa")
    assert result["source"] == "unsplash"


@patch("image_search.resolver.search_spoonacular", return_value=None)
@patch("image_search.resolver.search_unsplash", return_value=None)
@patch("image_search.resolver.search_pexels", return_value=None)
@patch("image_search.resolver.search_serpapi", return_value="https://serpapi.com/img.jpg")
def test_resolver_source_field_is_accurate(mock_serp, mock_pexels, mock_unsplash, mock_spoon):
    from image_search.resolver import get_best_dish_image
    result = get_best_dish_image("Sambar")
    assert result["source"] == "serpapi"
    assert result["found"] is True

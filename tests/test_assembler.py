import os
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


_FAKE_DESCRIPTIONS = {
    "Masala Dosa": "A crispy rice crepe from South India.",
    "Idli": "Soft steamed rice cakes served with sambar.",
}

_FAKE_IMAGE = {"image_url": "https://example.com/img.jpg", "source": "unsplash", "found": True}
_NO_IMAGE = {"image_url": None, "source": None, "found": False}


@patch("assembler.describe_dishes", return_value=_FAKE_DESCRIPTIONS)
@patch("assembler.get_best_dish_image", return_value=_FAKE_IMAGE)
def test_assemble_returns_correct_length(mock_img, mock_desc):
    from assembler import assemble_results
    results = assemble_results(["Masala Dosa", "Idli"])
    assert len(results) == 2


@patch("assembler.describe_dishes", return_value=_FAKE_DESCRIPTIONS)
@patch("assembler.get_best_dish_image", return_value=_FAKE_IMAGE)
def test_assemble_result_has_all_fields(mock_img, mock_desc):
    from assembler import assemble_results
    r = assemble_results(["Masala Dosa"])[0]
    assert r["dish"] == "Masala Dosa"
    assert r["description"] == "A crispy rice crepe from South India."
    assert r["image_url"] == "https://example.com/img.jpg"
    assert r["image_source"] == "unsplash"
    assert r["image_found"] is True


@patch("assembler.describe_dishes", return_value={})
@patch("assembler.get_best_dish_image", return_value=_NO_IMAGE)
def test_assemble_handles_missing_description_and_image(mock_img, mock_desc):
    from assembler import assemble_results
    r = assemble_results(["Unknown Dish"])[0]
    assert r["description"] == ""
    assert r["image_found"] is False
    assert r["image_url"] is None


def test_assemble_empty_input_returns_empty_list():
    from assembler import assemble_results
    assert assemble_results([]) == []


@patch("assembler.describe_dishes", return_value=_FAKE_DESCRIPTIONS)
@patch("assembler.get_best_dish_image", return_value=_FAKE_IMAGE)
def test_assemble_calls_describe_once_for_all_dishes(mock_img, mock_desc):
    from assembler import assemble_results
    assemble_results(["Masala Dosa", "Idli", "Vada"])
    # describe_dishes should be called once (batched), not once per dish
    mock_desc.assert_called_once()

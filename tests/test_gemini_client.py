import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


def _mock_response(text):
    return MagicMock(
        status_code=200,
        json=lambda: {"candidates": [{"content": {"parts": [{"text": text}]}}]},
        raise_for_status=lambda: None,
    )


# ── describe_dishes ───────────────────────────────────────────────────────────

@patch("gemini_client.GEMINI_API_KEY", "fake-key")
@patch("gemini_client.requests.post")
def test_describe_dishes_returns_dict(mock_post):
    mock_post.return_value = _mock_response(
        '[{"dish": "Masala Dosa", "description": "A crispy crepe."}]'
    )
    from gemini_client import describe_dishes
    result = describe_dishes(["Masala Dosa"])
    assert "Masala Dosa" in result
    assert "crispy" in result["Masala Dosa"].lower()


@patch("gemini_client.GEMINI_API_KEY", "fake-key")
@patch("gemini_client.requests.post")
def test_describe_dishes_handles_multiple(mock_post):
    mock_post.return_value = _mock_response(
        '[{"dish": "Idli", "description": "Steamed rice cakes."}, '
        '{"dish": "Vada", "description": "Crispy lentil donuts."}]'
    )
    from gemini_client import describe_dishes
    result = describe_dishes(["Idli", "Vada"])
    assert len(result) == 2
    assert "Idli" in result
    assert "Vada" in result


@patch("gemini_client.GEMINI_API_KEY", "fake-key")
@patch("gemini_client.requests.post")
def test_describe_dishes_tolerates_markdown_fences(mock_post):
    mock_post.return_value = _mock_response(
        '```json\n[{"dish": "Biryani", "description": "Fragrant rice dish."}]\n```'
    )
    from gemini_client import describe_dishes
    result = describe_dishes(["Biryani"])
    assert "Biryani" in result


@patch("gemini_client.GEMINI_API_KEY", "fake-key")
@patch("gemini_client.requests.post")
def test_describe_dishes_returns_empty_on_bad_json(mock_post):
    mock_post.return_value = _mock_response("Sorry, I cannot help with that.")
    from gemini_client import describe_dishes
    result = describe_dishes(["Dosa"])
    assert result == {}


def test_describe_dishes_empty_input_skips_api():
    from gemini_client import describe_dishes
    result = describe_dishes([])
    assert result == {}


def test_describe_dishes_raises_without_key():
    with patch("gemini_client.GEMINI_API_KEY", ""):
        from gemini_client import describe_dishes
        with pytest.raises(EnvironmentError):
            describe_dishes(["Dosa"])

import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from parser import parse_dish_list


def test_clean_output_parses_correctly():
    result = parse_dish_list("Masala Dosa\nIdli Sambar\nVada")
    assert result == ["Masala Dosa", "Idli Sambar", "Vada"]


def test_prices_are_removed():
    result = parse_dish_list("Masala Dosa ₹60\nIdli $3\nVada Rs.25")
    assert all("₹" not in d and "$" not in d and "Rs" not in d for d in result)
    assert len(result) == 3


def test_bullet_points_stripped():
    result = parse_dish_list("• Paneer Butter Masala\n- Dal Makhani\n1. Biryani")
    assert "Paneer Butter Masala" in result
    assert "Dal Makhani" in result
    assert "Biryani" in result


def test_numbering_stripped():
    result = parse_dish_list("1. Dosa\n2. Uttapam\n3. Pongal")
    assert result == ["Dosa", "Uttapam", "Pongal"]


def test_duplicates_removed():
    result = parse_dish_list("Dosa\ndosa\nDOSA\nIdli")
    assert result.count("Dosa") == 1
    assert len(result) == 2


def test_empty_string_returns_empty_list():
    assert parse_dish_list("") == []


def test_whitespace_only_returns_empty_list():
    assert parse_dish_list("   \n  \n  ") == []


def test_noise_only_returns_empty_list():
    assert parse_dish_list("---\n•\n1.\n2.") == []


def test_title_case_normalization():
    result = parse_dish_list("masala dosa\nPANEER TIKKA")
    assert "Masala Dosa" in result
    assert "Paneer Tikka" in result


def test_comma_separated_items():
    result = parse_dish_list("Dosa, Idli, Vada")
    assert "Dosa" in result
    assert "Idli" in result
    assert "Vada" in result

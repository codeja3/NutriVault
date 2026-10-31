import sqlite3

import pytest

from src.db import init_db
from src.grounding import (
    GroundingEngine,
    GroundingMatch,
    normalize_food_text,
)


@pytest.fixture
def populated_usda_conn():
    """Create in-memory SQLite with seed USDA reference data."""
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    cursor = conn.cursor()

    # Seed representative USDA rows
    foods = [
        (
            1001,
            "Rice, brown, long-grain, cooked",
            "Cereal Grains and Pasta",
            "cooked",
            112.0,
            2.3,
            23.5,
            0.8,
            1.6,
            '{"potassium_mg": 79.0, "magnesium_mg": 43.0}',
        ),
        (
            1002,
            "Rice, brown, long-grain, raw",
            "Cereal Grains and Pasta",
            "raw",
            365.0,
            7.5,
            77.2,
            2.7,
            3.4,
            '{"potassium_mg": 250.0, "magnesium_mg": 143.0}',
        ),
        (
            1003,
            "Chicken, broiler or fryers, breast, meat only, cooked, roasted",
            "Poultry Products",
            "cooked",
            165.0,
            31.0,
            0.0,
            3.6,
            0.0,
            '{"iron_mg": 1.0, "sodium_mg": 74.0}',
        ),
        (
            1004,
            "Broccoli, raw",
            "Vegetables and Vegetable Products",
            "raw",
            34.0,
            2.8,
            6.6,
            0.4,
            2.6,
            '{"calcium_mg": 47.0, "potassium_mg": 316.0}',
        ),
        (
            1005,
            "Broccoli, cooked, boiled, drained, without salt",
            "Vegetables and Vegetable Products",
            "cooked",
            35.0,
            2.4,
            7.2,
            0.4,
            3.3,
            '{"calcium_mg": 40.0, "potassium_mg": 293.0}',
        ),
    ]

    cursor.executemany(
        """
        INSERT INTO usda_foods (
            fdc_id, description, food_category, preparation_state,
            calories_per_100g, protein_g_per_100g, carbs_g_per_100g,
            fat_g_per_100g, fiber_g_per_100g, micros_per_100g_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        foods,
    )
    conn.commit()
    return conn


def test_normalize_food_text():
    """Verify text normalization strips punctuation, lowercases, and tokenizes."""
    raw = "Steamed Brown Rice, Cooked!!"
    tokens = normalize_food_text(raw)
    assert tokens == ["steamed", "brown", "rice", "cooked"]


def test_grounding_cooked_first_default(populated_usda_conn):
    """When query has no explicit raw qualifier, cooked/prepared items must take precedence."""
    engine = GroundingEngine(populated_usda_conn)

    # Query without explicit state: cooked brown rice (1001) must outrank raw (1002)
    matches = engine.search_candidates("brown rice", limit=3)
    assert len(matches) > 0
    top_match = matches[0]
    assert isinstance(top_match, GroundingMatch)
    assert top_match.fdc_id == 1001
    assert top_match.preparation_state == "cooked"
    assert "cooked" in top_match.description.lower()


def test_grounding_explicit_raw_matching(populated_usda_conn):
    """When query specifies 'raw', raw candidate must outrank cooked."""
    engine = GroundingEngine(populated_usda_conn)

    matches = engine.search_candidates("raw brown rice", limit=3)
    assert len(matches) > 0
    top_match = matches[0]
    assert top_match.fdc_id == 1002
    assert top_match.preparation_state == "raw"


def test_grounding_fuzzy_token_overlap(populated_usda_conn):
    """Assert query matches with reversed order and descriptive tokens."""
    engine = GroundingEngine(populated_usda_conn)

    # VLM output: "roasted chicken breast" -> matches roasted chicken item (1003)
    matches = engine.search_candidates("roasted chicken breast", limit=3)
    assert len(matches) > 0
    assert matches[0].fdc_id == 1003
    assert matches[0].score > 0.5

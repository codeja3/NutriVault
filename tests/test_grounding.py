import sqlite3

import pytest

from src.db import init_db
from src.grounding import (
    GroundingEngine,
    GroundingMatch,
    calculate_linear_nutrients,
    normalize_food_text,
    resolve_food_item,
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


def test_calculate_linear_nutrients():
    """Verify linear scaling against USDA per-100g values: Nutrient = USDA * (grams / 100)."""
    match = GroundingMatch(
        fdc_id=1001,
        description="Rice, brown, long-grain, cooked",
        food_category="Cereal Grains and Pasta",
        preparation_state="cooked",
        calories_per_100g=112.0,
        protein_g_per_100g=2.3,
        carbs_g_per_100g=23.5,
        fat_g_per_100g=0.8,
        fiber_g_per_100g=1.6,
        micros_per_100g={"potassium_mg": 79.0, "magnesium_mg": 43.0},
        score=0.95,
    )

    # Scale to 200g (factor = 2.0)
    nutrients_200g = calculate_linear_nutrients(match, grams=200.0)
    assert nutrients_200g.grams == 200.0
    assert nutrients_200g.calories == 224.0
    assert nutrients_200g.protein_g == 4.6
    assert nutrients_200g.carbs_g == 47.0
    assert nutrients_200g.fat_g == 1.6
    assert nutrients_200g.fiber_g == 3.2
    assert nutrients_200g.micronutrients["potassium_mg"] == 158.0
    assert nutrients_200g.micronutrients["magnesium_mg"] == 86.0

    # Scale to 50g (factor = 0.5)
    nutrients_50g = calculate_linear_nutrients(match, grams=50.0)
    assert nutrients_50g.calories == 56.0
    assert nutrients_50g.protein_g == 1.15
    assert nutrients_50g.carbs_g == 11.75
    assert nutrients_50g.fat_g == 0.4
    assert nutrients_50g.fiber_g == 0.8
    assert nutrients_50g.micronutrients["potassium_mg"] == 39.5


def test_calculate_linear_nutrients_rejects_negative_grams():
    """calculate_linear_nutrients must reject negative gram values."""
    match = GroundingMatch(
        fdc_id=1001,
        description="Rice, brown, cooked",
        food_category="Cereal Grains",
        preparation_state="cooked",
        calories_per_100g=112.0,
        protein_g_per_100g=2.3,
        carbs_g_per_100g=23.5,
        fat_g_per_100g=0.8,
        fiber_g_per_100g=1.6,
        micros_per_100g={},
        score=1.0,
    )
    with pytest.raises(ValueError, match="non-negative"):
        calculate_linear_nutrients(match, grams=-50.0)


def test_resolve_food_item_end_to_end(populated_usda_conn):
    """Verify end-to-end resolution from extracted item and mass to grounded nutrient profile."""
    engine = GroundingEngine(populated_usda_conn)

    resolved = resolve_food_item(
        engine=engine,
        item_name="steamed broccoli",
        estimated_grams=150.0,
    )

    assert resolved is not None
    assert resolved.item_name == "steamed broccoli"
    assert resolved.matched_fdc_id == 1005
    assert resolved.nutrients.grams == 150.0
    assert resolved.nutrients.calories == 52.5
    assert resolved.nutrients.protein_g == round(2.4 * 1.5, 2)
    assert resolved.nutrients.carbs_g == round(7.2 * 1.5, 2)
    assert resolved.nutrients.micronutrients["calcium_mg"] == round(40.0 * 1.5, 2)


def test_grounding_engine_token_cache(populated_usda_conn):
    """GroundingEngine caches pre-tokenized USDA entries in RAM to avoid table scans."""
    engine = GroundingEngine(populated_usda_conn)
    assert engine.is_cached is False

    # First search populates cache
    m1 = engine.search_candidates("brown rice", limit=3)
    assert len(m1) > 0
    assert engine.is_cached is True
    cache_len = len(engine._cache)
    assert cache_len > 0

    # Subsequent search uses cached tokens
    m2 = engine.search_candidates("cooked brown rice", limit=3)
    assert len(m2) > 0
    assert engine.is_cached is True

    # Explicit cache invalidation clears cache
    engine.invalidate_cache()
    assert engine.is_cached is False
    m3 = engine.search_candidates("raw brown rice", limit=3)
    assert len(m3) > 0
    assert engine.is_cached is True


def test_grounding_engine_queries_attached_usda_schema_without_shadowing(tmp_path):
    """GroundingEngine resolves to usda.usda_foods when attached, avoiding main table shadowing."""
    from src.db import attach_usda_reference

    # Main database has empty usda_foods table from init_db
    main_conn = sqlite3.connect(":memory:")
    init_db(main_conn)

    # Secondary USDA database has populated usda_foods
    usda_path = str(tmp_path / "usda_reference.db")
    usda_conn = sqlite3.connect(usda_path)
    init_db(usda_conn)
    usda_conn.execute(
        """
        INSERT INTO usda_foods (
            fdc_id, description, food_category, preparation_state,
            calories_per_100g, protein_g_per_100g, carbs_g_per_100g,
            fat_g_per_100g, fiber_g_per_100g, micros_per_100g_json
        ) VALUES (
            9001, 'Attached Organic Quinoa, cooked', 'Grains', 'cooked',
            120.0, 4.4, 21.3, 1.9, 2.8, '{}'
        );
        """
    )
    usda_conn.commit()
    usda_conn.close()

    attach_usda_reference(main_conn, usda_path, schema_name="usda")

    engine = GroundingEngine(main_conn)
    matches = engine.search_candidates("quinoa", limit=1)
    assert len(matches) == 1
    assert matches[0].fdc_id == 9001
    assert matches[0].description == "Attached Organic Quinoa, cooked"


def test_grounding_engine_queries_attached_usda_reference_schema(tmp_path):
    """GroundingEngine resolves to usda_reference.usda_foods when attached as usda_reference."""
    from src.db import attach_usda_reference

    main_conn = sqlite3.connect(":memory:")
    init_db(main_conn)

    usda_path = str(tmp_path / "usda_ref_alt.db")
    usda_conn = sqlite3.connect(usda_path)
    init_db(usda_conn)
    usda_conn.execute(
        """
        INSERT INTO usda_foods (
            fdc_id, description, food_category, preparation_state,
            calories_per_100g, protein_g_per_100g, carbs_g_per_100g,
            fat_g_per_100g, fiber_g_per_100g, micros_per_100g_json
        ) VALUES (
            9002, 'Lentils, mature seeds, cooked, boiled', 'Legumes', 'cooked',
            116.0, 9.0, 20.1, 0.4, 7.9, '{}'
        );
        """
    )
    usda_conn.commit()
    usda_conn.close()

    attach_usda_reference(main_conn, usda_path, schema_name="usda_reference")

    engine = GroundingEngine(main_conn)
    matches = engine.search_candidates("lentils", limit=1)
    assert len(matches) == 1
    assert matches[0].fdc_id == 9002
    assert matches[0].description == "Lentils, mature seeds, cooked, boiled"

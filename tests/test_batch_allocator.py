import sqlite3

import pytest

from src.batch_allocator import (
    BatchDish,
    BatchDishAllocator,
    DishIngredient,
    InvalidPortionSumError,
    ProfilePortionAllocation,
)
from src.db import init_db


@pytest.fixture
def db_conn():
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    return conn


def test_batch_dish_creation(db_conn):
    """Verify dish persistence in the dishes table."""
    allocator = BatchDishAllocator(db_conn)

    ingredients = [
        DishIngredient(
            item_name="brown rice",
            fdc_id=1001,
            grams=400.0,
            calories=448.0,
            protein_g=9.2,
            carbs_g=94.0,
            fat_g=3.2,
            fiber_g=6.4,
            micros={"potassium_mg": 316.0},
        ),
        DishIngredient(
            item_name="chicken breast",
            fdc_id=1003,
            grams=300.0,
            calories=495.0,
            protein_g=93.0,
            carbs_g=0.0,
            fat_g=10.8,
            fiber_g=0.0,
            micros={"iron_mg": 3.0},
        ),
    ]

    dish = allocator.create_dish(name="Chicken and Rice Casserole", ingredients=ingredients)

    assert dish.id is not None
    assert dish.name == "Chicken and Rice Casserole"
    assert dish.total_estimated_grams == 700.0
    assert dish.total_calories == 943.0
    assert dish.total_protein_g == 102.2
    assert dish.total_carbs_g == 94.0
    assert dish.total_fat_g == 14.0
    assert dish.total_fiber_g == 6.4
    assert dish.total_micros["potassium_mg"] == 316.0


def test_validate_portion_allocations_sum_ceiling():
    """Fractional allocations sum must be > 0.0 and <= 1.0 (rejecting sum > 1.0 or <= 0.0)."""
    allocator = BatchDishAllocator(sqlite3.connect(":memory:"))

    valid_allocs = [
        ProfilePortionAllocation(profile_id="p1", fraction=0.4),
        ProfilePortionAllocation(profile_id="p2", fraction=0.4),
        ProfilePortionAllocation(profile_id="p3", fraction=0.2),
    ]
    # Sum == 1.0 is valid
    allocator.validate_portion_allocations(valid_allocs)

    partial_allocs = [
        ProfilePortionAllocation(profile_id="p1", fraction=0.3),
        ProfilePortionAllocation(profile_id="p2", fraction=0.3),
    ]
    # Sum == 0.6 is valid (leftovers preserved)
    allocator.validate_portion_allocations(partial_allocs)

    # Sum > 1.0 must fail
    invalid_over = [
        ProfilePortionAllocation(profile_id="p1", fraction=0.6),
        ProfilePortionAllocation(profile_id="p2", fraction=0.5),
    ]
    with pytest.raises(InvalidPortionSumError) as exc_info:
        allocator.validate_portion_allocations(invalid_over)
    assert exc_info.value.error_code == "ERR_INVALID_PORTION_SUM"

    # Sum <= 0.0 must fail
    invalid_zero = [
        ProfilePortionAllocation(profile_id="p1", fraction=0.0),
    ]
    with pytest.raises(InvalidPortionSumError):
        allocator.validate_portion_allocations(invalid_zero)


def test_calculate_profile_nutrients_from_dish():
    """Assert fractional multiplication scales dish totals to individual profile portions."""
    allocator = BatchDishAllocator(sqlite3.connect(":memory:"))

    dish = BatchDish(
        id="d1",
        name="Casserole",
        total_estimated_grams=1000.0,
        total_calories=1000.0,
        total_protein_g=100.0,
        total_carbs_g=100.0,
        total_fat_g=20.0,
        total_fiber_g=10.0,
        total_micros={"potassium_mg": 500.0},
        raw_ingredients=[],
    )

    p_nutrients = allocator.calculate_profile_nutrients(dish, fraction=0.25)
    assert p_nutrients.calories == 250.0
    assert p_nutrients.protein_g == 25.0
    assert p_nutrients.carbs_g == 25.0
    assert p_nutrients.fat_g == 5.0
    assert p_nutrients.fiber_g == 2.5
    assert p_nutrients.micronutrients["potassium_mg"] == 125.0

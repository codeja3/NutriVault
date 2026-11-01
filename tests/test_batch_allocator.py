import sqlite3

import pytest

from src.batch_allocator import (
    BatchDish,
    BatchDishAllocator,
    DishIngredient,
    InvalidPortionSumError,
    ProfilePortionAllocation,
)
from src.db import ProfileRepository, init_db


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


def test_atomic_multi_profile_batch_commit(db_conn):
    """Verify committing batch dish split logs meal_logs entries for each profile."""
    repo = ProfileRepository(db_conn)
    p1 = repo.create_profile(name="Parent A", profile_type="standard")
    p2 = repo.create_profile(name="Parent B", profile_type="athletic")
    p3 = repo.create_profile(name="Child", profile_type="standard")

    allocator = BatchDishAllocator(db_conn)
    dish = allocator.create_dish(
        name="Family Pasta",
        ingredients=[
            DishIngredient(
                item_name="pasta",
                fdc_id=2001,
                grams=500.0,
                calories=750.0,
                protein_g=25.0,
                carbs_g=150.0,
                fat_g=5.0,
                fiber_g=10.0,
                micros={},
            )
        ],
    )

    allocations = [
        ProfilePortionAllocation(profile_id=p1.id, fraction=0.4, meal_type="dinner"),
        ProfilePortionAllocation(profile_id=p2.id, fraction=0.4, meal_type="dinner"),
        ProfilePortionAllocation(profile_id=p3.id, fraction=0.2, meal_type="dinner"),
    ]

    meal_log_ids = allocator.commit_batch_allocations(dish=dish, allocations=allocations)
    assert len(meal_log_ids) == 3

    cursor = db_conn.cursor()
    # Check parent A meal log
    cursor.execute(
        "SELECT calories, carbs_g, portion_fraction FROM meal_logs WHERE profile_id = ?;",
        (p1.id,),
    )
    row_p1 = cursor.fetchone()
    assert row_p1[0] == 300.0  # 750 * 0.4
    assert row_p1[1] == 60.0  # 150 * 0.4
    assert row_p1[2] == 0.4

    # Check child meal log
    cursor.execute(
        "SELECT calories, carbs_g, portion_fraction FROM meal_logs WHERE profile_id = ?;",
        (p3.id,),
    )
    row_p3 = cursor.fetchone()
    assert row_p3[0] == 150.0  # 750 * 0.2
    assert row_p3[1] == 30.0  # 150 * 0.2
    assert row_p3[2] == 0.2


def test_atomic_rollback_on_failure(db_conn):
    """If one insertion fails, all allocations roll back atomically."""
    repo = ProfileRepository(db_conn)
    p1 = repo.create_profile(name="Parent A", profile_type="standard")

    allocator = BatchDishAllocator(db_conn)
    dish = allocator.create_dish(
        name="Test Dish",
        ingredients=[
            DishIngredient(
                item_name="soup",
                fdc_id=3001,
                grams=300.0,
                calories=150.0,
                protein_g=5.0,
                carbs_g=20.0,
                fat_g=2.0,
                fiber_g=2.0,
                micros={},
            )
        ],
    )

    # Valid profile + Non-existent profile (violates FK PRAGMA foreign_keys = ON)
    bad_allocations = [
        ProfilePortionAllocation(profile_id=p1.id, fraction=0.5),
        ProfilePortionAllocation(profile_id="non_existent_profile_uuid", fraction=0.5),
    ]

    with pytest.raises(sqlite3.IntegrityError):
        allocator.commit_batch_allocations(dish=dish, allocations=bad_allocations)

    # Assert p1 meal log was rolled back and NOT committed
    cursor = db_conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM meal_logs WHERE profile_id = ?;", (p1.id,))
    count = cursor.fetchone()[0]
    assert count == 0


def test_commit_meal_atomic_rollback_on_portion_error(db_conn):
    """commit_meal must leave 0 rows in dishes when portion validation fails."""
    allocator = BatchDishAllocator(db_conn)
    ingredients = [
        DishIngredient(
            item_name="rice",
            fdc_id=1001,
            grams=200.0,
            calories=200.0,
            protein_g=4.0,
            carbs_g=40.0,
            fat_g=1.0,
            fiber_g=2.0,
            micros={},
        )
    ]
    invalid_allocs = [
        ProfilePortionAllocation(profile_id="p1", fraction=0.7),
        ProfilePortionAllocation(profile_id="p2", fraction=0.6),
    ]

    with pytest.raises(InvalidPortionSumError):
        allocator.commit_meal("Failed Dish", ingredients, invalid_allocs)

    cursor = db_conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM dishes;")
    assert cursor.fetchone()[0] == 0


def test_commit_meal_atomic_rollback_on_fk_error(db_conn):
    """commit_meal must roll back both dishes and meal_logs on FK constraint failure."""
    allocator = BatchDishAllocator(db_conn)
    ingredients = [
        DishIngredient(
            item_name="curry",
            fdc_id=2001,
            grams=300.0,
            calories=300.0,
            protein_g=10.0,
            carbs_g=20.0,
            fat_g=15.0,
            fiber_g=3.0,
            micros={},
        )
    ]
    bad_allocs = [
        ProfilePortionAllocation(profile_id="non_existent_profile_id", fraction=0.5),
    ]

    with pytest.raises(sqlite3.IntegrityError):
        allocator.commit_meal("Curry Batch", ingredients, bad_allocs)

    cursor = db_conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM dishes;")
    assert cursor.fetchone()[0] == 0
    cursor.execute("SELECT COUNT(*) FROM meal_logs;")
    assert cursor.fetchone()[0] == 0


def test_commit_meal_persists_custom_logged_at(db_conn):
    """commit_meal should store custom ISO-8601 logged_at timestamps."""
    profile_repo = ProfileRepository(db_conn)
    profile = profile_repo.create_profile("Time Traveler", "standard")

    allocator = BatchDishAllocator(db_conn)
    ingredients = [
        DishIngredient(
            item_name="oatmeal",
            fdc_id=3001,
            grams=100.0,
            calories=150.0,
            protein_g=5.0,
            carbs_g=27.0,
            fat_g=2.5,
            fiber_g=4.0,
            micros={},
        )
    ]
    custom_ts = "2026-03-15T08:30:00"
    allocs = [
        ProfilePortionAllocation(
            profile_id=profile.id,
            fraction=1.0,
            meal_type="breakfast",
            logged_at=custom_ts,
        )
    ]

    dish, log_ids = allocator.commit_meal("Morning Oats", ingredients, allocs)
    assert len(log_ids) == 1

    cursor = db_conn.cursor()
    cursor.execute("SELECT logged_at FROM meal_logs WHERE id = ?;", (log_ids[0],))
    row = cursor.fetchone()
    assert row[0] == custom_ts


def test_batch_dish_preserves_three_decimal_micronutrient_precision(db_conn):
    """BatchDish aggregation must preserve 3-decimal micronutrient precision."""
    allocator = BatchDishAllocator(db_conn)
    ingredients = [
        DishIngredient(
            item_name="nutritional yeast",
            fdc_id=4001,
            grams=15.0,
            calories=60.0,
            protein_g=8.0,
            carbs_g=5.0,
            fat_g=0.5,
            fiber_g=3.0,
            micros={"vitamin_b12_mcg": 0.125, "selenium_mcg": 0.044},
        ),
        DishIngredient(
            item_name="hemp seeds",
            fdc_id=4002,
            grams=30.0,
            calories=166.0,
            protein_g=9.5,
            carbs_g=2.6,
            fat_g=14.6,
            fiber_g=1.2,
            micros={"vitamin_b12_mcg": 0.003, "selenium_mcg": 0.012},
        ),
    ]
    dish = allocator.create_dish("Superfood Topping", ingredients)
    assert dish.total_micros["vitamin_b12_mcg"] == 0.128
    assert dish.total_micros["selenium_mcg"] == 0.056

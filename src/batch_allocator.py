"""Family batch portion allocator: cook-once shared dish ledger and fractional splitting."""

import json
import sqlite3
import uuid
from dataclasses import asdict, dataclass
from typing import Any

from src.grounding import NutrientProfile


class InvalidPortionSumError(ValueError):
    """Raised when fractional allocations across family members sum to <= 0.0 or > 1.0."""

    def __init__(self, current_sum: float):
        self.error_code = "ERR_INVALID_PORTION_SUM"
        super().__init__(f"Portion allocations must sum to between 0.0 and 1.0; got {current_sum}.")


@dataclass(frozen=True)
class DishIngredient:
    item_name: str
    fdc_id: int
    grams: float
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    fiber_g: float
    micros: dict[str, float]


@dataclass(frozen=True)
class BatchDish:
    id: str
    name: str
    total_estimated_grams: float
    total_calories: float
    total_protein_g: float
    total_carbs_g: float
    total_fat_g: float
    total_fiber_g: float
    total_micros: dict[str, float]
    raw_ingredients: list[dict[str, Any]]
    created_at: str | None = None


@dataclass(frozen=True)
class ProfilePortionAllocation:
    profile_id: str
    fraction: float
    meal_type: str = "dinner"
    logged_at: str | None = None


class BatchDishAllocator:
    """Manages batch dish creation and fractional portion distribution across family profiles."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def _build_dish(
        self, name: str, ingredients: list[DishIngredient]
    ) -> tuple[
        BatchDish,
        str,
        str,
        float,
        float,
        float,
        float,
        float,
        float,
    ]:
        dish_id = str(uuid.uuid4())
        total_grams = sum(ing.grams for ing in ingredients)
        total_cal = sum(ing.calories for ing in ingredients)
        total_pro = sum(ing.protein_g for ing in ingredients)
        total_carb = sum(ing.carbs_g for ing in ingredients)
        total_fat = sum(ing.fat_g for ing in ingredients)
        total_fib = sum(ing.fiber_g for ing in ingredients)

        total_micros: dict[str, float] = {}
        for ing in ingredients:
            for m_key, m_val in ing.micros.items():
                total_micros[m_key] = round(total_micros.get(m_key, 0.0) + m_val, 2)

        raw_ingredients_data = [asdict(ing) for ing in ingredients]
        raw_json = json.dumps(raw_ingredients_data)
        micros_json = json.dumps(total_micros)

        dish = BatchDish(
            id=dish_id,
            name=name,
            total_estimated_grams=round(total_grams, 2),
            total_calories=round(total_cal, 2),
            total_protein_g=round(total_pro, 2),
            total_carbs_g=round(total_carb, 2),
            total_fat_g=round(total_fat, 2),
            total_fiber_g=round(total_fib, 2),
            total_micros=total_micros,
            raw_ingredients=raw_ingredients_data,
        )
        return (
            dish,
            raw_json,
            micros_json,
            total_grams,
            total_cal,
            total_pro,
            total_carb,
            total_fat,
            total_fib,
        )

    def _insert_dish(
        self,
        cursor: sqlite3.Cursor,
        dish: BatchDish,
        raw_json: str,
        micros_json: str,
        total_grams: float,
        total_cal: float,
        total_pro: float,
        total_carb: float,
        total_fat: float,
        total_fib: float,
    ) -> None:
        cursor.execute(
            """
            INSERT INTO dishes (
                id, name, total_estimated_grams, total_calories,
                total_protein_g, total_carbs_g, total_fat_g, total_fiber_g,
                total_micros_json, raw_ingredients_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                dish.id,
                dish.name,
                total_grams,
                total_cal,
                total_pro,
                total_carb,
                total_fat,
                total_fib,
                micros_json,
                raw_json,
            ),
        )

    def _insert_allocations(
        self,
        cursor: sqlite3.Cursor,
        dish: BatchDish,
        allocations: list[ProfilePortionAllocation],
    ) -> list[str]:
        inserted_log_ids: list[str] = []
        for alloc in allocations:
            nutrients = self.calculate_profile_nutrients(dish, alloc.fraction)
            log_id = str(uuid.uuid4())
            alloc_micros_json = json.dumps(nutrients.micronutrients)

            if alloc.logged_at is not None:
                cursor.execute(
                    """
                    INSERT INTO meal_logs (
                        id, profile_id, dish_id, meal_type, portion_fraction,
                        calories, protein_g, carbs_g, fat_g, fiber_g, micros_json, logged_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        log_id,
                        alloc.profile_id,
                        dish.id,
                        alloc.meal_type,
                        alloc.fraction,
                        nutrients.calories,
                        nutrients.protein_g,
                        nutrients.carbs_g,
                        nutrients.fat_g,
                        nutrients.fiber_g,
                        alloc_micros_json,
                        alloc.logged_at,
                    ),
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO meal_logs (
                        id, profile_id, dish_id, meal_type, portion_fraction,
                        calories, protein_g, carbs_g, fat_g, fiber_g, micros_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        log_id,
                        alloc.profile_id,
                        dish.id,
                        alloc.meal_type,
                        alloc.fraction,
                        nutrients.calories,
                        nutrients.protein_g,
                        nutrients.carbs_g,
                        nutrients.fat_g,
                        nutrients.fiber_g,
                        alloc_micros_json,
                    ),
                )
            inserted_log_ids.append(log_id)
        return inserted_log_ids

    def create_dish(self, name: str, ingredients: list[DishIngredient]) -> BatchDish:
        """Aggregate ingredients into a dish and persist in the dishes table."""
        (
            dish,
            raw_json,
            micros_json,
            tg,
            tc,
            tp,
            tcb,
            tf,
            tfb,
        ) = self._build_dish(name, ingredients)
        cursor = self.conn.cursor()
        self._insert_dish(cursor, dish, raw_json, micros_json, tg, tc, tp, tcb, tf, tfb)
        self.conn.commit()
        return dish

    def commit_meal(
        self,
        name: str,
        ingredients: list[DishIngredient],
        allocations: list[ProfilePortionAllocation],
    ) -> tuple[BatchDish, list[str]]:
        """Atomically persist dish and profile allocations within a single transaction."""
        self.validate_portion_allocations(allocations)
        (
            dish,
            raw_json,
            micros_json,
            tg,
            tc,
            tp,
            tcb,
            tf,
            tfb,
        ) = self._build_dish(name, ingredients)
        cursor = self.conn.cursor()
        try:
            self._insert_dish(cursor, dish, raw_json, micros_json, tg, tc, tp, tcb, tf, tfb)
            inserted_log_ids = self._insert_allocations(cursor, dish, allocations)
            self.conn.commit()
            return dish, inserted_log_ids
        except Exception:
            self.conn.rollback()
            raise

    def validate_portion_allocations(
        self,
        allocations: list[ProfilePortionAllocation],
    ) -> None:
        """Validate fractional sum lies strictly in (0.0, 1.0]."""
        if not allocations:
            raise InvalidPortionSumError(0.0)

        for a in allocations:
            if a.fraction <= 0.0 or a.fraction > 1.0:
                raise InvalidPortionSumError(a.fraction)

        total_sum = round(sum(a.fraction for a in allocations), 6)
        if total_sum <= 0.0 or total_sum > 1.0:
            raise InvalidPortionSumError(total_sum)

    def calculate_profile_nutrients(
        self,
        dish: BatchDish,
        fraction: float,
    ) -> NutrientProfile:
        """Deterministically scale dish total nutrients by fractional portion."""
        scaled_micros = {k: round(v * fraction, 3) for k, v in dish.total_micros.items()}
        return NutrientProfile(
            grams=round(dish.total_estimated_grams * fraction, 2),
            calories=round(dish.total_calories * fraction, 2),
            protein_g=round(dish.total_protein_g * fraction, 2),
            carbs_g=round(dish.total_carbs_g * fraction, 2),
            fat_g=round(dish.total_fat_g * fraction, 2),
            fiber_g=round(dish.total_fiber_g * fraction, 2),
            micronutrients=scaled_micros,
        )

    def commit_batch_allocations(
        self,
        dish: BatchDish,
        allocations: list[ProfilePortionAllocation],
    ) -> list[str]:
        """Atomically persist meal_logs for allocations, rolling back entirely on error."""
        self.validate_portion_allocations(allocations)
        cursor = self.conn.cursor()
        try:
            inserted_log_ids = self._insert_allocations(cursor, dish, allocations)
            self.conn.commit()
            return inserted_log_ids
        except Exception:
            self.conn.rollback()
            raise

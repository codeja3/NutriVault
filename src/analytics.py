"""Tabular analytics engine: rolling EMA calculations and target adherence deltas."""

import sqlite3
from dataclasses import dataclass

from src.db import ProfileRepository


@dataclass(frozen=True)
class RollingEMAResult:
    profile_id: str
    days: int
    calories_ema: float
    protein_g_ema: float
    carbs_g_ema: float
    fat_g_ema: float
    fiber_g_ema: float
    target_deltas: dict[str, float]


def _compute_series_ema(values: list[float], smoothing_weight: float = 2.0) -> float:
    """Compute standard exponential moving average (EMA) across a chronological series."""
    if not values:
        return 0.0
    if len(values) == 1:
        return round(values[0], 2)

    # Multiplier: alpha = 2 / (N + 1)
    k = smoothing_weight / (len(values) + 1)
    ema = values[0]
    for val in values[1:]:
        ema = (val * k) + (ema * (1.0 - k))
    return round(ema, 2)


class AnalyticsEngine:
    """Computes relational analytics and moving averages over meal_logs."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.repo = ProfileRepository(conn)

    def calculate_rolling_ema(self, profile_id: str, days: int = 7) -> RollingEMAResult:
        """Calculate EMA for calories and macronutrients over rolling days."""
        cursor = self.conn.cursor()

        # Query daily sums grouped by date in chronological order using idx_meal_logs_profile_time
        cursor.execute(
            """
            SELECT DATE(logged_at) AS meal_date,
                   SUM(calories) AS day_calories,
                   SUM(protein_g) AS day_protein,
                   SUM(carbs_g) AS day_carbs,
                   SUM(fat_g) AS day_fat,
                   SUM(fiber_g) AS day_fiber
            FROM meal_logs
            WHERE profile_id = ?
            GROUP BY DATE(logged_at)
            ORDER BY meal_date ASC
            LIMIT ?;
            """,
            (profile_id, days),
        )
        rows = cursor.fetchall()

        if not rows:
            return RollingEMAResult(
                profile_id=profile_id,
                days=days,
                calories_ema=0.0,
                protein_g_ema=0.0,
                carbs_g_ema=0.0,
                fat_g_ema=0.0,
                fiber_g_ema=0.0,
                target_deltas={},
            )

        cal_series = [r[1] for r in rows]
        pro_series = [r[2] for r in rows]
        carb_series = [r[3] for r in rows]
        fat_series = [r[4] for r in rows]
        fib_series = [r[5] for r in rows]

        cal_ema = _compute_series_ema(cal_series)
        pro_ema = _compute_series_ema(pro_series)
        carb_ema = _compute_series_ema(carb_series)
        fat_ema = _compute_series_ema(fat_series)
        fib_ema = _compute_series_ema(fib_series)

        # Calculate deltas against active target envelope if present
        target_envelope = self.repo.get_active_target_envelope(profile_id)
        target_deltas: dict[str, float] = {}

        if target_envelope:
            target_deltas["calories"] = round(cal_ema - target_envelope.calories_target, 2)
            target_deltas["protein_g"] = round(pro_ema - target_envelope.protein_g_target, 2)
            target_deltas["carbs_g"] = round(carb_ema - target_envelope.carbs_g_target, 2)
            target_deltas["fat_g"] = round(fat_ema - target_envelope.fat_g_target, 2)
            target_deltas["fiber_g"] = round(fib_ema - target_envelope.fiber_g_target, 2)

        return RollingEMAResult(
            profile_id=profile_id,
            days=days,
            calories_ema=cal_ema,
            protein_g_ema=pro_ema,
            carbs_g_ema=carb_ema,
            fat_g_ema=fat_ema,
            fiber_g_ema=fib_ema,
            target_deltas=target_deltas,
        )

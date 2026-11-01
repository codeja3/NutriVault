"""Tabular analytics engine: rolling EMA calculations, target adherence, and chrononutrition."""

import sqlite3
from dataclasses import dataclass
from datetime import datetime

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


@dataclass(frozen=True)
class DailyFeedingInterval:
    date: str
    first_meal_time: str
    last_meal_time: str
    eating_window_hours: float
    overnight_fast_hours: float | None


def _compute_series_ema(values: list[float], smoothing_weight: float = 2.0) -> float:
    """Compute standard exponential moving average (EMA) across a chronological series."""
    if not values:
        return 0.0
    if len(values) == 1:
        return round(values[0], 2)

    k = smoothing_weight / (len(values) + 1)
    ema = values[0]
    for val in values[1:]:
        ema = (val * k) + (ema * (1.0 - k))
    return round(ema, 2)


def calculate_chrononutrition_windows(
    conn: sqlite3.Connection,
    profile_id: str,
) -> list[DailyFeedingInterval]:
    """Calculate daily eating windows and inter-day overnight fasting intervals."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT DATE(logged_at) as meal_date,
               MIN(logged_at) as first_ts,
               MAX(logged_at) as last_ts
        FROM meal_logs
        WHERE profile_id = ?
        GROUP BY DATE(logged_at)
        ORDER BY meal_date ASC;
        """,
        (profile_id,),
    )
    rows = cursor.fetchall()
    if not rows:
        return []

    intervals: list[DailyFeedingInterval] = []
    prev_last_dt: datetime | None = None

    for row in rows:
        date_str = row[0]
        first_dt = datetime.fromisoformat(row[1])
        last_dt = datetime.fromisoformat(row[2])

        # Eating window: delta between first and last meal of that day
        window_seconds = (last_dt - first_dt).total_seconds()
        window_hours = round(window_seconds / 3600.0, 2)

        # Overnight fast: delta from previous day's last meal to current day's first meal
        fast_hours = None
        if prev_last_dt is not None:
            day_diff = (first_dt.date() - prev_last_dt.date()).days
            if day_diff == 1:
                fast_seconds = (first_dt - prev_last_dt).total_seconds()
                if fast_seconds > 0:
                    fast_hours = round(fast_seconds / 3600.0, 2)

        intervals.append(
            DailyFeedingInterval(
                date=date_str,
                first_meal_time=first_dt.strftime("%H:%M:%S"),
                last_meal_time=last_dt.strftime("%H:%M:%S"),
                eating_window_hours=window_hours,
                overnight_fast_hours=fast_hours,
            )
        )
        prev_last_dt = last_dt

    return intervals


class AnalyticsEngine:
    """Computes relational analytics and moving averages over meal_logs."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.repo = ProfileRepository(conn)

    def calculate_rolling_ema(self, profile_id: str, days: int = 7) -> RollingEMAResult:
        """Calculate EMA for calories and macronutrients over rolling days."""
        if days < 1:
            raise ValueError(f"Parameter 'days' must be an integer >= 1, got {days}.")
        cursor = self.conn.cursor()

        cursor.execute(
            """
            SELECT meal_date, day_calories, day_protein, day_carbs, day_fat, day_fiber
            FROM (
                SELECT DATE(logged_at) AS meal_date,
                       SUM(calories) AS day_calories,
                       SUM(protein_g) AS day_protein,
                       SUM(carbs_g) AS day_carbs,
                       SUM(fat_g) AS day_fat,
                       SUM(fiber_g) AS day_fiber
                FROM meal_logs
                WHERE profile_id = ?
                GROUP BY DATE(logged_at)
                ORDER BY meal_date DESC
                LIMIT ?
            )
            ORDER BY meal_date ASC;
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

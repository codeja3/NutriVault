import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from src.analytics import (
    AnalyticsEngine,
    DailyFeedingInterval,
    RollingEMAResult,
    calculate_chrononutrition_windows,
)
from src.db import ProfileRepository, init_db


@pytest.fixture
def populated_analytics_db():
    """Populate database with 7 days of historical meals for a profile."""
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    repo = ProfileRepository(conn)

    profile = repo.create_profile(name="Sam", profile_type="standard")
    repo.set_active_target_envelope(
        profile_id=profile.id,
        calories_target=2000,
        protein_g_target=150.0,
        carbs_g_target=200.0,
        fat_g_target=65.0,
        fiber_g_target=30.0,
    )

    cursor = conn.cursor()
    base_time = datetime(2026, 10, 24, 12, 0, 0, tzinfo=timezone.utc)

    # Insert 7 daily meals
    # Days 0..6: calories alternating between 1800 and 2200 (mean = 2000)
    for day in range(7):
        logged_at = (base_time + timedelta(days=day)).strftime("%Y-%m-%d %H:%M:%S")
        calories = 1800.0 if day % 2 == 0 else 2200.0
        cursor.execute(
            """
            INSERT INTO meal_logs (
                id, profile_id, meal_type, portion_fraction,
                calories, protein_g, carbs_g, fat_g, fiber_g, logged_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                f"log_{day}",
                profile.id,
                "dinner",
                1.0,
                calories,
                150.0,
                200.0,
                65.0,
                30.0,
                logged_at,
            ),
        )
    conn.commit()
    return conn, profile.id


def test_calculate_rolling_ema(populated_analytics_db):
    """Verify 7-day rolling EMA calculation and target adherence deltas."""
    conn, profile_id = populated_analytics_db
    analytics = AnalyticsEngine(conn)

    result = analytics.calculate_rolling_ema(profile_id=profile_id, days=7)
    assert isinstance(result, RollingEMAResult)
    assert result.profile_id == profile_id
    assert result.days == 7
    assert 1800.0 <= result.calories_ema <= 2200.0
    assert result.protein_g_ema == 150.0
    assert result.carbs_g_ema == 200.0
    assert result.fat_g_ema == 65.0
    assert result.fiber_g_ema == 30.0

    # Target deltas: delta = EMA - target
    # Calories target is 2000
    assert result.target_deltas is not None
    assert "calories" in result.target_deltas
    assert abs(result.target_deltas["calories"]) < 200.0
    assert result.target_deltas["protein_g"] == 0.0


def test_calculate_rolling_ema_empty_profile(populated_analytics_db):
    """Profile with zero logged meals returns zeroed EMA result without raising error."""
    conn, _ = populated_analytics_db
    repo = ProfileRepository(conn)
    empty_profile = repo.create_profile(name="New User", profile_type="standard")

    analytics = AnalyticsEngine(conn)
    result = analytics.calculate_rolling_ema(profile_id=empty_profile.id, days=7)
    assert result.calories_ema == 0.0
    assert result.protein_g_ema == 0.0
    assert result.target_deltas == {}


def test_calculate_chrononutrition_windows(populated_analytics_db):
    """Verify daily feeding interval (last - first) and overnight fast calculations."""
    conn, profile_id = populated_analytics_db
    cursor = conn.cursor()

    # Clear previous meals and add specific timestamped meals for two consecutive days
    cursor.execute("DELETE FROM meal_logs WHERE profile_id = ?;", (profile_id,))

    # Day 1: 2026-10-25 (08:00 to 18:00 -> 10h eating window)
    meals_day1 = [
        ("m1", "2026-10-25 08:00:00", "breakfast", 400.0),
        ("m2", "2026-10-25 12:30:00", "lunch", 600.0),
        ("m3", "2026-10-25 18:00:00", "dinner", 800.0),
    ]
    # Day 2: 2026-10-26 (09:00 to 19:00 -> 10h window, overnight fast 18:00 to 09:00 = 15h)
    meals_day2 = [
        ("m4", "2026-10-26 09:00:00", "breakfast", 500.0),
        ("m5", "2026-10-26 19:00:00", "dinner", 900.0),
    ]

    for m_id, logged_at, m_type, cal in meals_day1 + meals_day2:
        cursor.execute(
            """
            INSERT INTO meal_logs (
                id, profile_id, meal_type, portion_fraction,
                calories, protein_g, carbs_g, fat_g, fiber_g, logged_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (m_id, profile_id, m_type, 1.0, cal, 30.0, 50.0, 15.0, 5.0, logged_at),
        )
    conn.commit()

    intervals = calculate_chrononutrition_windows(conn, profile_id=profile_id)
    assert len(intervals) == 2

    # Day 1
    d1 = intervals[0]
    assert isinstance(d1, DailyFeedingInterval)
    assert d1.date == "2026-10-25"
    assert d1.first_meal_time == "08:00:00"
    assert d1.last_meal_time == "18:00:00"
    assert d1.eating_window_hours == 10.0
    assert d1.overnight_fast_hours is None  # First recorded day has no prior night

    # Day 2
    d2 = intervals[1]
    assert d2.date == "2026-10-26"
    assert d2.first_meal_time == "09:00:00"
    assert d2.last_meal_time == "19:00:00"
    assert d2.eating_window_hours == 10.0
    # Fast from 2026-10-25 18:00 to 2026-10-26 09:00 is exactly 15 hours
    assert d2.overnight_fast_hours == 15.0

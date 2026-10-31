import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from src.analytics import (
    AnalyticsEngine,
    RollingEMAResult,
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

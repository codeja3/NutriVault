"""Database initialization, schema migrations, and SQLite CRUD repositories."""

import json
import sqlite3
import uuid
from dataclasses import dataclass

# Complete schema for nutrivault.db & usda_reference.db
SCHEMA_DDL = """
PRAGMA foreign_keys = ON;

-- 1. USDA Foods Reference Table (usda_reference.db / in-memory join)
CREATE TABLE IF NOT EXISTS usda_foods (
    fdc_id INTEGER PRIMARY KEY,
    description TEXT NOT NULL,
    food_category TEXT,
    preparation_state TEXT NOT NULL DEFAULT 'unknown' CHECK (
        preparation_state IN ('cooked', 'raw', 'prepared', 'unknown')
    ),
    calories_per_100g REAL NOT NULL CHECK (calories_per_100g >= 0.0),
    protein_g_per_100g REAL NOT NULL CHECK (protein_g_per_100g >= 0.0),
    carbs_g_per_100g REAL NOT NULL CHECK (carbs_g_per_100g >= 0.0),
    fat_g_per_100g REAL NOT NULL CHECK (fat_g_per_100g >= 0.0),
    fiber_g_per_100g REAL NOT NULL CHECK (fiber_g_per_100g >= 0.0),
    micros_per_100g_json TEXT NOT NULL DEFAULT '{}'
);

-- 2. Household Profiles Table
CREATE TABLE IF NOT EXISTS profiles (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    birth_date DATE,
    profile_type TEXT NOT NULL CHECK (
        profile_type IN ('standard', 'athletic', 'chronic_condition')
    ),
    condition_notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Dietary Target Envelopes Table
CREATE TABLE IF NOT EXISTS target_envelopes (
    id TEXT PRIMARY KEY,
    profile_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    calories_target INTEGER NOT NULL CHECK (calories_target >= 0),
    protein_g_target REAL NOT NULL CHECK (protein_g_target >= 0.0),
    carbs_g_target REAL NOT NULL CHECK (carbs_g_target >= 0.0),
    fat_g_target REAL NOT NULL CHECK (fat_g_target >= 0.0),
    fiber_g_target REAL NOT NULL CHECK (fiber_g_target >= 0.0),
    micronutrients_json TEXT NOT NULL DEFAULT '{}',
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Cook-Once Shared Dishes Table
CREATE TABLE IF NOT EXISTS dishes (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    total_estimated_grams REAL NOT NULL CHECK (total_estimated_grams >= 0.0),
    total_calories REAL NOT NULL CHECK (total_calories >= 0.0),
    total_protein_g REAL NOT NULL CHECK (total_protein_g >= 0.0),
    total_carbs_g REAL NOT NULL CHECK (total_carbs_g >= 0.0),
    total_fat_g REAL NOT NULL CHECK (total_fat_g >= 0.0),
    total_fiber_g REAL NOT NULL CHECK (total_fiber_g >= 0.0),
    total_micros_json TEXT NOT NULL DEFAULT '{}',
    raw_ingredients_json TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. Immutable Meal Event Journal
CREATE TABLE IF NOT EXISTS meal_logs (
    id TEXT PRIMARY KEY,
    profile_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    dish_id TEXT REFERENCES dishes(id) ON DELETE SET NULL,
    meal_type TEXT NOT NULL CHECK (
        meal_type IN ('breakfast', 'lunch', 'dinner', 'snack', 'pre_workout', 'post_workout')
    ),
    portion_fraction REAL NOT NULL DEFAULT 1.0 CHECK (
        portion_fraction > 0.0 AND portion_fraction <= 1.0
    ),
    calories REAL NOT NULL CHECK (calories >= 0.0),
    protein_g REAL NOT NULL CHECK (protein_g >= 0.0),
    carbs_g REAL NOT NULL CHECK (carbs_g >= 0.0),
    fat_g REAL NOT NULL CHECK (fat_g >= 0.0),
    fiber_g REAL NOT NULL CHECK (fiber_g >= 0.0),
    micros_json TEXT NOT NULL DEFAULT '{}',
    logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indices for Temporal Analytics, Search, and Constraints
CREATE INDEX IF NOT EXISTS idx_meal_logs_profile_time
ON meal_logs (profile_id, logged_at);

CREATE INDEX IF NOT EXISTS idx_target_envelopes_profile
ON target_envelopes (profile_id, is_active);

CREATE UNIQUE INDEX IF NOT EXISTS idx_single_active_envelope
ON target_envelopes (profile_id) WHERE is_active = 1;

CREATE INDEX IF NOT EXISTS idx_usda_foods_description
ON usda_foods (description);
"""


def init_db(conn: sqlite3.Connection) -> None:
    """Initialize database schemas and enforce foreign key pragma."""
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        conn.execute("PRAGMA journal_mode = WAL;")
    except sqlite3.OperationalError:
        pass
    conn.executescript(SCHEMA_DDL)
    conn.commit()


@dataclass(frozen=True)
class Profile:
    id: str
    name: str
    birth_date: str | None
    profile_type: str
    condition_notes: str | None
    created_at: str | None = None
    updated_at: str | None = None


@dataclass(frozen=True)
class TargetEnvelope:
    id: str
    profile_id: str
    calories_target: int
    protein_g_target: float
    carbs_g_target: float
    fat_g_target: float
    fiber_g_target: float
    micronutrients: dict[str, float]
    is_active: bool
    created_at: str | None = None


class ProfileRepository:
    """Repository handling CRUD for profiles and target envelopes with parameterization."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def create_profile(
        self,
        name: str,
        profile_type: str,
        birth_date: str | None = None,
        condition_notes: str | None = None,
    ) -> Profile:
        profile_id = str(uuid.uuid4())
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO profiles (id, name, birth_date, profile_type, condition_notes)
            VALUES (?, ?, ?, ?, ?);
            """,
            (profile_id, name, birth_date, profile_type, condition_notes),
        )
        self.conn.commit()
        return self.get_profile(profile_id)  # type: ignore

    def get_profile(self, profile_id: str) -> Profile | None:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT id, name, birth_date, profile_type, condition_notes, created_at, updated_at
            FROM profiles WHERE id = ?;
            """,
            (profile_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return Profile(
            id=row[0],
            name=row[1],
            birth_date=row[2],
            profile_type=row[3],
            condition_notes=row[4],
            created_at=row[5],
            updated_at=row[6],
        )

    def list_profiles(self) -> list[Profile]:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT id, name, birth_date, profile_type, condition_notes, created_at, updated_at
            FROM profiles ORDER BY created_at ASC;
            """
        )
        rows = cursor.fetchall()
        return [
            Profile(
                id=r[0],
                name=r[1],
                birth_date=r[2],
                profile_type=r[3],
                condition_notes=r[4],
                created_at=r[5],
                updated_at=r[6],
            )
            for r in rows
        ]

    def update_profile(
        self,
        profile_id: str,
        name: str | None = None,
        birth_date: str | None = None,
        profile_type: str | None = None,
        condition_notes: str | None = None,
    ) -> Profile:
        existing = self.get_profile(profile_id)
        if not existing:
            raise KeyError(f"Profile with id '{profile_id}' not found.")

        new_name = name if name is not None else existing.name
        new_bdate = birth_date if birth_date is not None else existing.birth_date
        new_ptype = profile_type if profile_type is not None else existing.profile_type
        new_cnotes = condition_notes if condition_notes is not None else existing.condition_notes

        cursor = self.conn.cursor()
        cursor.execute(
            """
            UPDATE profiles
            SET name = ?, birth_date = ?, profile_type = ?, condition_notes = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?;
            """,
            (new_name, new_bdate, new_ptype, new_cnotes, profile_id),
        )
        self.conn.commit()
        return self.get_profile(profile_id)  # type: ignore

    def delete_profile(self, profile_id: str) -> None:
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM profiles WHERE id = ?;", (profile_id,))
        self.conn.commit()

    def set_active_target_envelope(
        self,
        profile_id: str,
        calories_target: int,
        protein_g_target: float,
        carbs_g_target: float,
        fat_g_target: float,
        fiber_g_target: float,
        micronutrients: dict[str, float] | None = None,
    ) -> TargetEnvelope:
        """Atomically deactivates any existing active envelope and creates the new active one."""
        micros = micronutrients or {}
        micros_json = json.dumps(micros)
        envelope_id = str(uuid.uuid4())

        cursor = self.conn.cursor()
        try:
            # 1. Deactivate old active envelope for this profile
            cursor.execute(
                "UPDATE target_envelopes SET is_active = 0 WHERE profile_id = ? AND is_active = 1;",
                (profile_id,),
            )
            # 2. Insert new active envelope
            cursor.execute(
                """
                INSERT INTO target_envelopes (
                    id, profile_id, calories_target, protein_g_target,
                    carbs_g_target, fat_g_target, fiber_g_target,
                    micronutrients_json, is_active
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1);
                """,
                (
                    envelope_id,
                    profile_id,
                    calories_target,
                    protein_g_target,
                    carbs_g_target,
                    fat_g_target,
                    fiber_g_target,
                    micros_json,
                ),
            )
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

        return self.get_active_target_envelope(profile_id)  # type: ignore

    def get_active_target_envelope(self, profile_id: str) -> TargetEnvelope | None:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT id, profile_id, calories_target, protein_g_target, carbs_g_target,
                   fat_g_target, fiber_g_target, micronutrients_json, is_active, created_at
            FROM target_envelopes
            WHERE profile_id = ? AND is_active = 1;
            """,
            (profile_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return TargetEnvelope(
            id=row[0],
            profile_id=row[1],
            calories_target=row[2],
            protein_g_target=row[3],
            carbs_g_target=row[4],
            fat_g_target=row[5],
            fiber_g_target=row[6],
            micronutrients=json.loads(row[7]),
            is_active=bool(row[8]),
            created_at=row[9],
        )


def attach_usda_reference(
    conn: sqlite3.Connection,
    usda_db_path: str,
    schema_name: str = "usda",
) -> None:
    """Attach external USDA reference SQLite database as a named schema."""
    cursor = conn.cursor()
    cursor.execute(f"ATTACH DATABASE ? AS {schema_name};", (usda_db_path,))

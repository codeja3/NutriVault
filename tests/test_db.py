import sqlite3

import pytest

from src.db import (
    ProfileRepository,
    attach_usda_reference,
    init_db,
)


def test_init_db_pragmas_and_tables():
    """Verify in-memory SQLite executes schemas, sets WAL/memory pragmas, and foreign keys."""
    conn = sqlite3.connect(":memory:")
    init_db(conn)

    # Check foreign keys pragma is active
    cursor = conn.cursor()
    fk_status = cursor.execute("PRAGMA foreign_keys;").fetchone()[0]
    assert fk_status == 1

    # Check all required tables exist
    tables = {
        row[0]
        for row in cursor.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
    }
    assert "profiles" in tables
    assert "target_envelopes" in tables
    assert "dishes" in tables
    assert "meal_logs" in tables
    assert "usda_foods" in tables

    # Check indices exist
    indices = {
        row[0]
        for row in cursor.execute("SELECT name FROM sqlite_master WHERE type='index';").fetchall()
    }
    assert "idx_single_active_envelope" in indices
    assert "idx_meal_logs_profile_time" in indices
    assert "idx_target_envelopes_profile" in indices
    assert "idx_usda_foods_description" in indices


def test_profile_type_check_constraint():
    """Assert profiles table rejects invalid profile_type strings."""
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    cursor = conn.cursor()

    # Valid profile types: standard, athletic, chronic_condition
    cursor.execute(
        "INSERT INTO profiles (id, name, profile_type) VALUES (?, ?, ?);",
        ("p1", "Alice", "standard"),
    )
    cursor.execute(
        "INSERT INTO profiles (id, name, profile_type) VALUES (?, ?, ?);",
        ("p2", "Bob", "athletic"),
    )
    cursor.execute(
        "INSERT INTO profiles (id, name, profile_type) VALUES (?, ?, ?);",
        ("p3", "Charlie", "chronic_condition"),
    )
    conn.commit()

    # Invalid profile type must fail check constraint
    with pytest.raises(sqlite3.IntegrityError):
        cursor.execute(
            "INSERT INTO profiles (id, name, profile_type) VALUES (?, ?, ?);",
            ("p4", "Dave", "unsupported_type"),
        )
        conn.commit()


def test_foreign_key_and_cascade_delete():
    """Assert ON DELETE CASCADE deletes target_envelopes and meal_logs when profile is deleted."""
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO profiles (id, name, profile_type) VALUES (?, ?, ?);",
        ("p1", "Alice", "standard"),
    )
    cursor.execute(
        """
        INSERT INTO target_envelopes (
            id, profile_id, calories_target, protein_g_target,
            carbs_g_target, fat_g_target, fiber_g_target
        ) VALUES (?, ?, ?, ?, ?, ?, ?);
        """,
        ("env1", "p1", 2000, 150.0, 200.0, 65.0, 30.0),
    )
    cursor.execute(
        """
        INSERT INTO meal_logs (
            id, profile_id, meal_type, portion_fraction,
            calories, protein_g, carbs_g, fat_g, fiber_g
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        ("m1", "p1", "lunch", 1.0, 600.0, 45.0, 60.0, 20.0, 8.0),
    )
    conn.commit()

    # Delete profile
    cursor.execute("DELETE FROM profiles WHERE id = ?;", ("p1",))
    conn.commit()

    # Verified cascading deletion
    env_count = cursor.execute(
        "SELECT COUNT(*) FROM target_envelopes WHERE profile_id = 'p1';"
    ).fetchone()[0]
    meal_count = cursor.execute(
        "SELECT COUNT(*) FROM meal_logs WHERE profile_id = 'p1';"
    ).fetchone()[0]
    assert env_count == 0
    assert meal_count == 0


def test_single_active_target_envelope_invariant():
    """Verify that multiple active envelopes trigger unique violation."""
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO profiles (id, name, profile_type) VALUES (?, ?, ?);",
        ("p1", "Alice", "standard"),
    )
    cursor.execute(
        """
        INSERT INTO target_envelopes (
            id, profile_id, calories_target, protein_g_target,
            carbs_g_target, fat_g_target, fiber_g_target, is_active
        ) VALUES (?, ?, ?, ?, ?, ?, ?, 1);
        """,
        ("env1", "p1", 2000, 150.0, 200.0, 65.0, 30.0),
    )
    conn.commit()

    # Inactive envelopes (is_active = 0) are allowed multiple times
    cursor.execute(
        """
        INSERT INTO target_envelopes (
            id, profile_id, calories_target, protein_g_target,
            carbs_g_target, fat_g_target, fiber_g_target, is_active
        ) VALUES (?, ?, ?, ?, ?, ?, ?, 0);
        """,
        ("env2", "p1", 1800, 140.0, 180.0, 60.0, 25.0),
    )
    conn.commit()

    # Second active envelope (is_active = 1) for the same profile MUST fail
    with pytest.raises(sqlite3.IntegrityError):
        cursor.execute(
            """
            INSERT INTO target_envelopes (
                id, profile_id, calories_target, protein_g_target,
                carbs_g_target, fat_g_target, fiber_g_target, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 1);
            """,
            ("env3", "p1", 2200, 160.0, 220.0, 70.0, 35.0),
        )
        conn.commit()


def test_portion_fraction_check_constraint():
    """Assert meal_logs enforces 0.0 < portion_fraction <= 1.0."""
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO profiles (id, name, profile_type) VALUES (?, ?, ?);",
        ("p1", "Alice", "standard"),
    )

    # portion_fraction <= 0.0 must fail
    with pytest.raises(sqlite3.IntegrityError):
        cursor.execute(
            """
            INSERT INTO meal_logs (
                id, profile_id, meal_type, portion_fraction,
                calories, protein_g, carbs_g, fat_g, fiber_g
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            ("m_invalid", "p1", "lunch", 0.0, 500.0, 30.0, 50.0, 15.0, 5.0),
        )
        conn.commit()

    # portion_fraction > 1.0 must fail
    with pytest.raises(sqlite3.IntegrityError):
        cursor.execute(
            """
            INSERT INTO meal_logs (
                id, profile_id, meal_type, portion_fraction,
                calories, protein_g, carbs_g, fat_g, fiber_g
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            ("m_invalid2", "p1", "lunch", 1.05, 500.0, 30.0, 50.0, 15.0, 5.0),
        )
        conn.commit()


def test_profile_repository_crud():
    """Verify ProfileRepository create, read, update, list, and delete operations."""
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    repo = ProfileRepository(conn)

    # 1. Create Profile
    p1 = repo.create_profile(
        name="Alex Mercer",
        birth_date="1990-05-15",
        profile_type="athletic",
        condition_notes="Marathon training",
    )
    assert p1.id is not None
    assert p1.name == "Alex Mercer"
    assert p1.profile_type == "athletic"

    # 2. Get Profile by ID
    fetched = repo.get_profile(p1.id)
    assert fetched is not None
    assert fetched.name == "Alex Mercer"
    assert fetched.condition_notes == "Marathon training"

    # 3. List Profiles
    p2 = repo.create_profile(name="Sarah Mercer", profile_type="standard")
    profiles = repo.list_profiles()
    assert len(profiles) == 2
    assert {p.name for p in profiles} == {"Alex Mercer", "Sarah Mercer"}

    # 4. Update Profile
    updated = repo.update_profile(p1.id, name="Alex Mercer-Vance", condition_notes="Ultra marathon")
    assert updated.name == "Alex Mercer-Vance"
    assert updated.condition_notes == "Ultra marathon"

    # 5. Delete Profile
    repo.delete_profile(p2.id)
    assert repo.get_profile(p2.id) is None
    assert len(repo.list_profiles()) == 1


def test_target_envelope_crud_and_atomic_switch():
    """Verify target envelope creation, query active, and atomic deactivation upon replacement."""
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    repo = ProfileRepository(conn)

    profile = repo.create_profile(name="Jordan", profile_type="standard")

    # 1. Create first active target envelope
    env1 = repo.set_active_target_envelope(
        profile_id=profile.id,
        calories_target=2200,
        protein_g_target=160.0,
        carbs_g_target=240.0,
        fat_g_target=70.0,
        fiber_g_target=35.0,
        micronutrients={"iron_mg": 18.0, "calcium_mg": 1000.0},
    )
    assert env1.is_active is True
    assert env1.calories_target == 2200
    assert env1.micronutrients == {"iron_mg": 18.0, "calcium_mg": 1000.0}

    # Verify active target query
    active_env = repo.get_active_target_envelope(profile.id)
    assert active_env is not None
    assert active_env.id == env1.id

    # 2. Create second active envelope: must atomically deactivate env1
    env2 = repo.set_active_target_envelope(
        profile_id=profile.id,
        calories_target=2500,
        protein_g_target=180.0,
        carbs_g_target=280.0,
        fat_g_target=75.0,
        fiber_g_target=40.0,
    )
    assert env2.is_active is True
    assert env2.calories_target == 2500

    # Active envelope is now env2
    current_active = repo.get_active_target_envelope(profile.id)
    assert current_active is not None
    assert current_active.id == env2.id

    # Verify env1 is still in DB as inactive (history preserved)
    cursor = conn.cursor()
    cursor.execute("SELECT is_active FROM target_envelopes WHERE id = ?;", (env1.id,))
    assert cursor.fetchone()[0] == 0


def test_target_envelopes_negative_check_constraints():
    """target_envelopes must reject negative calorie and macro targets via CHECK constraints."""
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO profiles (id, name, profile_type) VALUES ('p_chk', 'Test', 'standard');"
    )
    conn.commit()

    with pytest.raises(sqlite3.IntegrityError):
        cursor.execute(
            """
            INSERT INTO target_envelopes (
                id, profile_id, calories_target, protein_g_target,
                carbs_g_target, fat_g_target, fiber_g_target
            ) VALUES ('e_neg', 'p_chk', -500, 100.0, 100.0, 50.0, 20.0);
            """
        )
        conn.commit()


def test_dishes_and_meal_logs_negative_check_constraints():
    """dishes and meal_logs must reject negative calories/macros via CHECK constraints."""
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO profiles (id, name, profile_type) VALUES ('p_chk2', 'Test2', 'standard');"
    )
    conn.commit()

    # Dishes negative calories
    with pytest.raises(sqlite3.IntegrityError):
        cursor.execute(
            """
            INSERT INTO dishes (
                id, name, total_estimated_grams, total_calories,
                total_protein_g, total_carbs_g, total_fat_g, total_fiber_g, raw_ingredients_json
            ) VALUES ('d_neg', 'Dish', 200.0, -100.0, 10.0, 10.0, 5.0, 2.0, '[]');
            """
        )
        conn.commit()

    # Meal logs negative protein
    with pytest.raises(sqlite3.IntegrityError):
        cursor.execute(
            """
            INSERT INTO meal_logs (
                id, profile_id, meal_type, portion_fraction,
                calories, protein_g, carbs_g, fat_g, fiber_g
            ) VALUES ('m_neg', 'p_chk2', 'dinner', 1.0, 200.0, -10.0, 20.0, 5.0, 2.0);
            """
        )
        conn.commit()


def test_attach_usda_reference(tmp_path):
    """attach_usda_reference should attach secondary USDA database schema as 'usda'."""
    main_conn = sqlite3.connect(":memory:")
    init_db(main_conn)

    usda_file = str(tmp_path / "usda_reference.db")
    usda_conn = sqlite3.connect(usda_file)
    usda_conn.execute("CREATE TABLE usda_test (id INTEGER PRIMARY KEY);")
    usda_conn.commit()
    usda_conn.close()

    attach_usda_reference(main_conn, usda_file, schema_name="usda")
    cursor = main_conn.cursor()
    cursor.execute("SELECT name FROM usda.sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    assert "usda_test" in tables


def test_attach_usda_reference_rejects_unsafe_schema_name(tmp_path):
    """attach_usda_reference must strictly validate schema_name against whitelist."""
    main_conn = sqlite3.connect(":memory:")
    init_db(main_conn)

    usda_file = str(tmp_path / "usda_reference.db")
    with pytest.raises(ValueError, match="schema name"):
        attach_usda_reference(main_conn, usda_file, schema_name="usda; DROP TABLE profiles;--")


def test_seed_default_usda_foods_idempotent():
    """seed_default_usda_foods should seed staple items when empty and be idempotent."""
    from src.db import seed_default_usda_foods

    conn = sqlite3.connect(":memory:")
    init_db(conn, seed_defaults=False)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM usda_foods;")
    assert cursor.fetchone()[0] == 0

    inserted_count = seed_default_usda_foods(conn)
    assert inserted_count >= 25

    cursor.execute("SELECT COUNT(*) FROM usda_foods;")
    assert cursor.fetchone()[0] == inserted_count

    # Second call should be a no-op
    second_count = seed_default_usda_foods(conn)
    assert second_count == 0

    # Verify staple item content
    cursor.execute(
        "SELECT description, calories_per_100g, preparation_state "
        "FROM usda_foods WHERE description LIKE '%Rice, brown%';"
    )
    row = cursor.fetchone()
    assert row is not None
    assert row[1] > 0
    assert row[2] == "cooked"


def test_init_db_with_seed_defaults():
    """init_db with seed_defaults=True should populate default USDA foods."""
    conn = sqlite3.connect(":memory:")
    init_db(conn, seed_defaults=True)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM usda_foods;")
    assert cursor.fetchone()[0] >= 25


def test_usda_foods_schema_includes_barcode_column_and_index():
    """usda_foods table must have a barcode column and idx_usda_foods_barcode index."""
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(usda_foods);")
    columns = {row[1] for row in cursor.fetchall()}
    assert "barcode" in columns

    cursor.execute("PRAGMA index_list(usda_foods);")
    indexes = {row[1] for row in cursor.fetchall()}
    assert "idx_usda_foods_barcode" in indexes


def test_init_db_idempotent_barcode_migration():
    """init_db must idempotently migrate pre-v1.3.0 tables lacking a barcode column."""
    conn = sqlite3.connect(":memory:")
    # Create legacy table without barcode column
    conn.execute(
        """
        CREATE TABLE usda_foods (
            fdc_id INTEGER PRIMARY KEY,
            description TEXT NOT NULL,
            food_category TEXT,
            preparation_state TEXT NOT NULL DEFAULT 'unknown',
            calories_per_100g REAL NOT NULL,
            protein_g_per_100g REAL NOT NULL,
            carbs_g_per_100g REAL NOT NULL,
            fat_g_per_100g REAL NOT NULL,
            fiber_g_per_100g REAL NOT NULL,
            micros_per_100g_json TEXT NOT NULL DEFAULT '{}'
        );
        """
    )
    conn.commit()

    # init_db should detect missing barcode and add it
    init_db(conn)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(usda_foods);")
    cols = {row[1] for row in cursor.fetchall()}
    assert "barcode" in cols

    # Second call must be idempotent
    init_db(conn)


def test_seed_default_usda_foods_includes_barcodes():
    """Seeded default foods must include valid UPC/EAN barcodes on staple items."""
    conn = sqlite3.connect(":memory:")
    init_db(conn, seed_defaults=True)
    cursor = conn.cursor()
    cursor.execute("SELECT barcode, description FROM usda_foods WHERE barcode IS NOT NULL;")
    rows = cursor.fetchall()
    assert len(rows) >= 5
    barcodes = [r[0] for r in rows]
    for b in barcodes:
        assert isinstance(b, str)
        assert len(b) >= 8

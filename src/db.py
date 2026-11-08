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
    micros_per_100g_json TEXT NOT NULL DEFAULT '{}',
    barcode TEXT
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

CREATE INDEX IF NOT EXISTS idx_usda_foods_barcode
ON usda_foods (barcode);
"""

# Curated catalog of staple raw and cooked foods for out-of-the-box operation
DEFAULT_USDA_FOODS: list[dict[str, object]] = [
    {
        "fdc_id": 1001,
        "description": "Rice, brown, long-grain, cooked",
        "food_category": "Cereal Grains and Pasta",
        "preparation_state": "cooked",
        "calories_per_100g": 123.0,
        "protein_g_per_100g": 2.74,
        "carbs_g_per_100g": 25.58,
        "fat_g_per_100g": 0.97,
        "fiber_g_per_100g": 1.6,
        "micros_per_100g_json": json.dumps(
            {"potassium_mg": 86.0, "magnesium_mg": 44.0, "iron_mg": 0.56, "sodium_mg": 4.0}
        ),
    },
    {
        "fdc_id": 1002,
        "description": "Rice, white, long-grain, regular, cooked",
        "food_category": "Cereal Grains and Pasta",
        "preparation_state": "cooked",
        "calories_per_100g": 130.0,
        "protein_g_per_100g": 2.69,
        "carbs_g_per_100g": 28.17,
        "fat_g_per_100g": 0.28,
        "fiber_g_per_100g": 0.4,
        "micros_per_100g_json": json.dumps(
            {"potassium_mg": 35.0, "magnesium_mg": 12.0, "iron_mg": 1.2, "sodium_mg": 1.0}
        ),
    },
    {
        "fdc_id": 1003,
        "description": "Oats, rolled, cooked with water",
        "food_category": "Cereal Grains and Pasta",
        "preparation_state": "cooked",
        "calories_per_100g": 71.0,
        "protein_g_per_100g": 2.54,
        "carbs_g_per_100g": 12.0,
        "fat_g_per_100g": 1.52,
        "fiber_g_per_100g": 1.7,
        "micros_per_100g_json": json.dumps(
            {"potassium_mg": 68.0, "magnesium_mg": 26.0, "iron_mg": 0.9, "calcium_mg": 10.0}
        ),
        "barcode": "0030000010204",
    },
    {
        "fdc_id": 1004,
        "description": "Quinoa, cooked",
        "food_category": "Cereal Grains and Pasta",
        "preparation_state": "cooked",
        "calories_per_100g": 120.0,
        "protein_g_per_100g": 4.4,
        "carbs_g_per_100g": 21.3,
        "fat_g_per_100g": 1.92,
        "fiber_g_per_100g": 2.8,
        "micros_per_100g_json": json.dumps(
            {"potassium_mg": 172.0, "magnesium_mg": 64.0, "iron_mg": 1.49, "sodium_mg": 7.0}
        ),
        "barcode": "0070552190134",
    },
    {
        "fdc_id": 1005,
        "description": "Bread, whole-wheat, commercially prepared",
        "food_category": "Baked Products",
        "preparation_state": "prepared",
        "calories_per_100g": 247.0,
        "protein_g_per_100g": 12.96,
        "carbs_g_per_100g": 41.27,
        "fat_g_per_100g": 3.38,
        "fiber_g_per_100g": 6.8,
        "micros_per_100g_json": json.dumps(
            {"sodium_mg": 472.0, "potassium_mg": 248.0, "magnesium_mg": 82.0, "iron_mg": 2.47}
        ),
        "barcode": "0072250037129",
    },
    {
        "fdc_id": 1006,
        "description": "Chicken breast, roasted, skinless, meat only",
        "food_category": "Poultry Products",
        "preparation_state": "cooked",
        "calories_per_100g": 165.0,
        "protein_g_per_100g": 31.02,
        "carbs_g_per_100g": 0.0,
        "fat_g_per_100g": 3.57,
        "fiber_g_per_100g": 0.0,
        "micros_per_100g_json": json.dumps(
            {"potassium_mg": 256.0, "magnesium_mg": 29.0, "iron_mg": 1.04, "sodium_mg": 74.0}
        ),
    },
    {
        "fdc_id": 1007,
        "description": "Turkey breast, meat only, roasted",
        "food_category": "Poultry Products",
        "preparation_state": "cooked",
        "calories_per_100g": 135.0,
        "protein_g_per_100g": 30.06,
        "carbs_g_per_100g": 0.0,
        "fat_g_per_100g": 0.74,
        "fiber_g_per_100g": 0.0,
        "micros_per_100g_json": json.dumps(
            {"potassium_mg": 293.0, "magnesium_mg": 30.0, "iron_mg": 1.36, "sodium_mg": 55.0}
        ),
    },
    {
        "fdc_id": 1008,
        "description": "Salmon, Atlantic, wild, cooked, dry heat",
        "food_category": "Finfish and Shellfish Products",
        "preparation_state": "cooked",
        "calories_per_100g": 182.0,
        "protein_g_per_100g": 25.44,
        "carbs_g_per_100g": 0.0,
        "fat_g_per_100g": 8.13,
        "fiber_g_per_100g": 0.0,
        "micros_per_100g_json": json.dumps(
            {"potassium_mg": 628.0, "magnesium_mg": 37.0, "sodium_mg": 56.0, "iron_mg": 0.8}
        ),
    },
    {
        "fdc_id": 1009,
        "description": "Tuna, light, canned in water, drained solids",
        "food_category": "Finfish and Shellfish Products",
        "preparation_state": "prepared",
        "calories_per_100g": 116.0,
        "protein_g_per_100g": 25.51,
        "carbs_g_per_100g": 0.0,
        "fat_g_per_100g": 0.82,
        "fiber_g_per_100g": 0.0,
        "micros_per_100g_json": json.dumps(
            {"potassium_mg": 237.0, "sodium_mg": 338.0, "iron_mg": 1.54, "magnesium_mg": 31.0}
        ),
        "barcode": "0080000001103",
    },
    {
        "fdc_id": 1010,
        "description": "Beef, ground, 90% lean meat / 10% fat, loaf, cooked",
        "food_category": "Beef Products",
        "preparation_state": "cooked",
        "calories_per_100g": 204.0,
        "protein_g_per_100g": 26.6,
        "carbs_g_per_100g": 0.0,
        "fat_g_per_100g": 10.1,
        "fiber_g_per_100g": 0.0,
        "micros_per_100g_json": json.dumps(
            {"potassium_mg": 340.0, "iron_mg": 2.65, "zinc_mg": 5.92, "sodium_mg": 66.0}
        ),
    },
    {
        "fdc_id": 1011,
        "description": "Egg, whole, hard-boiled",
        "food_category": "Dairy and Egg Products",
        "preparation_state": "cooked",
        "calories_per_100g": 155.0,
        "protein_g_per_100g": 12.58,
        "carbs_g_per_100g": 1.12,
        "fat_g_per_100g": 10.61,
        "fiber_g_per_100g": 0.0,
        "micros_per_100g_json": json.dumps(
            {"potassium_mg": 126.0, "calcium_mg": 50.0, "iron_mg": 1.19, "sodium_mg": 124.0}
        ),
    },
    {
        "fdc_id": 1012,
        "description": "Milk, whole, 3.25% milkfat",
        "food_category": "Dairy and Egg Products",
        "preparation_state": "prepared",
        "calories_per_100g": 61.0,
        "protein_g_per_100g": 3.15,
        "carbs_g_per_100g": 4.8,
        "fat_g_per_100g": 3.25,
        "fiber_g_per_100g": 0.0,
        "micros_per_100g_json": json.dumps(
            {"calcium_mg": 113.0, "potassium_mg": 132.0, "magnesium_mg": 10.0, "sodium_mg": 43.0}
        ),
        "barcode": "0070042000035",
    },
    {
        "fdc_id": 1013,
        "description": "Yogurt, Greek, plain, nonfat",
        "food_category": "Dairy and Egg Products",
        "preparation_state": "prepared",
        "calories_per_100g": 59.0,
        "protein_g_per_100g": 10.19,
        "carbs_g_per_100g": 3.6,
        "fat_g_per_100g": 0.39,
        "fiber_g_per_100g": 0.0,
        "micros_per_100g_json": json.dumps(
            {"calcium_mg": 110.0, "potassium_mg": 141.0, "magnesium_mg": 11.0, "sodium_mg": 36.0}
        ),
        "barcode": "0036632026116",
    },
    {
        "fdc_id": 1014,
        "description": "Cheese, cheddar",
        "food_category": "Dairy and Egg Products",
        "preparation_state": "prepared",
        "calories_per_100g": 403.0,
        "protein_g_per_100g": 24.9,
        "carbs_g_per_100g": 1.28,
        "fat_g_per_100g": 33.14,
        "fiber_g_per_100g": 0.0,
        "micros_per_100g_json": json.dumps(
            {"calcium_mg": 721.0, "potassium_mg": 98.0, "sodium_mg": 621.0, "magnesium_mg": 28.0}
        ),
        "barcode": "0021000604647",
    },
    {
        "fdc_id": 1015,
        "description": "Tofu, firm, prepared with calcium sulfate and magnesium chloride",
        "food_category": "Legumes and Legume Products",
        "preparation_state": "prepared",
        "calories_per_100g": 83.0,
        "protein_g_per_100g": 9.98,
        "carbs_g_per_100g": 1.9,
        "fat_g_per_100g": 5.26,
        "fiber_g_per_100g": 0.9,
        "micros_per_100g_json": json.dumps(
            {"calcium_mg": 282.0, "iron_mg": 2.04, "potassium_mg": 121.0, "magnesium_mg": 58.0}
        ),
        "barcode": "0025484000108",
    },
    {
        "fdc_id": 1016,
        "description": "Black beans, mature seeds, cooked, boiled, without salt",
        "food_category": "Legumes and Legume Products",
        "preparation_state": "cooked",
        "calories_per_100g": 132.0,
        "protein_g_per_100g": 8.86,
        "carbs_g_per_100g": 23.71,
        "fat_g_per_100g": 0.54,
        "fiber_g_per_100g": 8.7,
        "micros_per_100g_json": json.dumps(
            {"potassium_mg": 355.0, "magnesium_mg": 60.0, "iron_mg": 2.1, "calcium_mg": 27.0}
        ),
        "barcode": "0041415124036",
    },
    {
        "fdc_id": 1017,
        "description": "Lentils, mature seeds, cooked, boiled, without salt",
        "food_category": "Legumes and Legume Products",
        "preparation_state": "cooked",
        "calories_per_100g": 116.0,
        "protein_g_per_100g": 9.02,
        "carbs_g_per_100g": 20.13,
        "fat_g_per_100g": 0.38,
        "fiber_g_per_100g": 7.9,
        "micros_per_100g_json": json.dumps(
            {"potassium_mg": 369.0, "magnesium_mg": 36.0, "iron_mg": 3.33, "sodium_mg": 2.0}
        ),
    },
    {
        "fdc_id": 1018,
        "description": "Chickpeas (garbanzo beans, bengal gram), mature seeds, cooked, boiled",
        "food_category": "Legumes and Legume Products",
        "preparation_state": "cooked",
        "calories_per_100g": 164.0,
        "protein_g_per_100g": 8.86,
        "carbs_g_per_100g": 27.42,
        "fat_g_per_100g": 2.59,
        "fiber_g_per_100g": 7.6,
        "micros_per_100g_json": json.dumps(
            {"potassium_mg": 291.0, "magnesium_mg": 48.0, "iron_mg": 2.89, "calcium_mg": 49.0}
        ),
    },
    {
        "fdc_id": 1019,
        "description": "Broccoli, steamed",
        "food_category": "Vegetables and Vegetable Products",
        "preparation_state": "cooked",
        "calories_per_100g": 35.0,
        "protein_g_per_100g": 2.38,
        "carbs_g_per_100g": 7.18,
        "fat_g_per_100g": 0.41,
        "fiber_g_per_100g": 3.3,
        "micros_per_100g_json": json.dumps(
            {"vitamin_c_mg": 64.9, "potassium_mg": 293.0, "calcium_mg": 40.0, "iron_mg": 0.67}
        ),
    },
    {
        "fdc_id": 1020,
        "description": "Spinach, raw",
        "food_category": "Vegetables and Vegetable Products",
        "preparation_state": "raw",
        "calories_per_100g": 23.0,
        "protein_g_per_100g": 2.86,
        "carbs_g_per_100g": 3.63,
        "fat_g_per_100g": 0.39,
        "fiber_g_per_100g": 2.2,
        "micros_per_100g_json": json.dumps(
            {"iron_mg": 2.71, "calcium_mg": 99.0, "potassium_mg": 558.0, "magnesium_mg": 79.0}
        ),
    },
    {
        "fdc_id": 1021,
        "description": "Carrots, raw",
        "food_category": "Vegetables and Vegetable Products",
        "preparation_state": "raw",
        "calories_per_100g": 41.0,
        "protein_g_per_100g": 0.93,
        "carbs_g_per_100g": 9.58,
        "fat_g_per_100g": 0.24,
        "fiber_g_per_100g": 2.8,
        "micros_per_100g_json": json.dumps(
            {"potassium_mg": 320.0, "calcium_mg": 33.0, "sodium_mg": 69.0, "magnesium_mg": 12.0}
        ),
    },
    {
        "fdc_id": 1022,
        "description": "Sweet potato, cooked, baked in skin, flesh, without salt",
        "food_category": "Vegetables and Vegetable Products",
        "preparation_state": "cooked",
        "calories_per_100g": 90.0,
        "protein_g_per_100g": 2.01,
        "carbs_g_per_100g": 20.71,
        "fat_g_per_100g": 0.15,
        "fiber_g_per_100g": 3.3,
        "micros_per_100g_json": json.dumps(
            {"potassium_mg": 475.0, "magnesium_mg": 27.0, "calcium_mg": 38.0, "sodium_mg": 36.0}
        ),
    },
    {
        "fdc_id": 1023,
        "description": "Potatoes, russet, flesh and skin, baked",
        "food_category": "Vegetables and Vegetable Products",
        "preparation_state": "cooked",
        "calories_per_100g": 97.0,
        "protein_g_per_100g": 2.57,
        "carbs_g_per_100g": 21.55,
        "fat_g_per_100g": 0.13,
        "fiber_g_per_100g": 2.3,
        "micros_per_100g_json": json.dumps(
            {"potassium_mg": 535.0, "magnesium_mg": 28.0, "iron_mg": 1.08, "sodium_mg": 9.0}
        ),
    },
    {
        "fdc_id": 1024,
        "description": "Peppers, sweet, red, raw",
        "food_category": "Vegetables and Vegetable Products",
        "preparation_state": "raw",
        "calories_per_100g": 31.0,
        "protein_g_per_100g": 0.99,
        "carbs_g_per_100g": 6.03,
        "fat_g_per_100g": 0.3,
        "fiber_g_per_100g": 2.1,
        "micros_per_100g_json": json.dumps(
            {"vitamin_c_mg": 127.7, "potassium_mg": 211.0, "magnesium_mg": 12.0, "calcium_mg": 7.0}
        ),
    },
    {
        "fdc_id": 1025,
        "description": "Apples, raw, with skin",
        "food_category": "Fruits and Fruit Juices",
        "preparation_state": "raw",
        "calories_per_100g": 52.0,
        "protein_g_per_100g": 0.26,
        "carbs_g_per_100g": 13.81,
        "fat_g_per_100g": 0.17,
        "fiber_g_per_100g": 2.4,
        "micros_per_100g_json": json.dumps(
            {"potassium_mg": 107.0, "calcium_mg": 6.0, "magnesium_mg": 5.0, "vitamin_c_mg": 4.6}
        ),
    },
    {
        "fdc_id": 1026,
        "description": "Bananas, raw",
        "food_category": "Fruits and Fruit Juices",
        "preparation_state": "raw",
        "calories_per_100g": 89.0,
        "protein_g_per_100g": 1.09,
        "carbs_g_per_100g": 22.84,
        "fat_g_per_100g": 0.33,
        "fiber_g_per_100g": 2.6,
        "micros_per_100g_json": json.dumps(
            {"potassium_mg": 358.0, "magnesium_mg": 27.0, "vitamin_c_mg": 8.7, "iron_mg": 0.26}
        ),
    },
    {
        "fdc_id": 1027,
        "description": "Blueberries, raw",
        "food_category": "Fruits and Fruit Juices",
        "preparation_state": "raw",
        "calories_per_100g": 57.0,
        "protein_g_per_100g": 0.74,
        "carbs_g_per_100g": 14.49,
        "fat_g_per_100g": 0.33,
        "fiber_g_per_100g": 2.4,
        "micros_per_100g_json": json.dumps(
            {"potassium_mg": 77.0, "vitamin_c_mg": 9.7, "calcium_mg": 6.0, "magnesium_mg": 6.0}
        ),
    },
    {
        "fdc_id": 1028,
        "description": "Avocados, raw, all commercial varieties",
        "food_category": "Fruits and Fruit Juices",
        "preparation_state": "raw",
        "calories_per_100g": 160.0,
        "protein_g_per_100g": 2.0,
        "carbs_g_per_100g": 8.53,
        "fat_g_per_100g": 14.66,
        "fiber_g_per_100g": 6.7,
        "micros_per_100g_json": json.dumps(
            {"potassium_mg": 485.0, "magnesium_mg": 29.0, "calcium_mg": 12.0, "sodium_mg": 7.0}
        ),
    },
    {
        "fdc_id": 1029,
        "description": "Nuts, almonds, dry roasted, without salt",
        "food_category": "Nut and Seed Products",
        "preparation_state": "prepared",
        "calories_per_100g": 598.0,
        "protein_g_per_100g": 21.15,
        "carbs_g_per_100g": 21.01,
        "fat_g_per_100g": 52.54,
        "fiber_g_per_100g": 10.9,
        "micros_per_100g_json": json.dumps(
            {"potassium_mg": 733.0, "magnesium_mg": 279.0, "calcium_mg": 269.0, "iron_mg": 3.71}
        ),
        "barcode": "0041570054641",
    },
    {
        "fdc_id": 1030,
        "description": "Oil, olive, extra virgin",
        "food_category": "Fats and Oils",
        "preparation_state": "raw",
        "calories_per_100g": 884.0,
        "protein_g_per_100g": 0.0,
        "carbs_g_per_100g": 0.0,
        "fat_g_per_100g": 100.0,
        "fiber_g_per_100g": 0.0,
        "micros_per_100g_json": json.dumps(
            {"potassium_mg": 1.0, "sodium_mg": 2.0, "iron_mg": 0.56}
        ),
        "barcode": "0074847000105",
    },
]


def seed_default_usda_foods(conn: sqlite3.Connection) -> int:
    """Seed default USDA reference foods if usda_foods table is currently empty."""
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM usda_foods;")
    row = cursor.fetchone()
    if row and row[0] > 0:
        return 0

    insert_sql = """
    INSERT INTO usda_foods (
        fdc_id, description, food_category, preparation_state,
        calories_per_100g, protein_g_per_100g, carbs_g_per_100g,
        fat_g_per_100g, fiber_g_per_100g, micros_per_100g_json, barcode
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """
    rows_to_insert = [
        (
            food["fdc_id"],
            food["description"],
            food["food_category"],
            food["preparation_state"],
            food["calories_per_100g"],
            food["protein_g_per_100g"],
            food["carbs_g_per_100g"],
            food["fat_g_per_100g"],
            food["fiber_g_per_100g"],
            food["micros_per_100g_json"],
            food.get("barcode"),
        )
        for food in DEFAULT_USDA_FOODS
    ]
    cursor.executemany(insert_sql, rows_to_insert)
    conn.commit()
    return len(rows_to_insert)


def init_db(conn: sqlite3.Connection, seed_defaults: bool = False) -> None:
    """Initialize database schemas and enforce foreign key pragma."""
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        conn.execute("PRAGMA journal_mode = WAL;")
    except sqlite3.OperationalError:
        pass

    # Idempotent migration for pre-v1.3.0 databases missing barcode column
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='usda_foods';")
    if cursor.fetchone()[0] > 0:
        cursor.execute("PRAGMA table_info(usda_foods);")
        cols = {row[1] for row in cursor.fetchall()}
        if cols and "barcode" not in cols:
            conn.execute("ALTER TABLE usda_foods ADD COLUMN barcode TEXT;")

    conn.executescript(SCHEMA_DDL)
    conn.commit()
    if seed_defaults:
        seed_default_usda_foods(conn)


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
    if schema_name == "usda":
        cursor.execute("ATTACH DATABASE ? AS usda;", (usda_db_path,))
    elif schema_name == "usda_reference":
        cursor.execute("ATTACH DATABASE ? AS usda_reference;", (usda_db_path,))
    else:
        raise ValueError(
            f"Invalid schema name '{schema_name}'. Must be 'usda' or 'usda_reference'."
        )

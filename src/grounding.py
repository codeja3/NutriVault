"""Neuro-symbolic grounding engine: token normalization and USDA candidate ranking."""

import difflib
import json
import re
import sqlite3
from dataclasses import dataclass
from typing import Any

STATE_TOKENS = {"cooked", "steamed", "roasted", "boiled", "fried", "raw", "prepared", "baked"}
PREPARED_STATES = {"cooked", "prepared", "steamed", "roasted", "boiled", "fried", "baked"}


class BarcodeNotFoundError(ValueError):
    """Raised when an exact barcode lookup fails to find a matching product."""

    error_code = "ERR_BARCODE_NOT_FOUND"


def normalize_barcode(code: str) -> str:
    """Normalize and validate a barcode string."""
    cleaned = code.strip()
    if not cleaned or not re.fullmatch(r"[A-Za-z0-9_-]{4,32}", cleaned):
        raise ValueError(
            f"Invalid barcode format '{code}'. Must be 4-32 alphanumeric characters, "
            "dashes, or underscores."
        )
    return cleaned


@dataclass(frozen=True)
class GroundedFoodCandidate:
    fdc_id: int
    description: str
    food_category: str | None
    preparation_state: str
    barcode: str | None
    nutrients: "NutrientProfile"


@dataclass(frozen=True)
class GroundingMatch:
    fdc_id: int
    description: str
    food_category: str | None
    preparation_state: str
    calories_per_100g: float
    protein_g_per_100g: float
    carbs_g_per_100g: float
    fat_g_per_100g: float
    fiber_g_per_100g: float
    micros_per_100g: dict[str, float]
    score: float


@dataclass(frozen=True)
class NutrientProfile:
    grams: float
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    fiber_g: float
    micronutrients: dict[str, float]


@dataclass(frozen=True)
class ResolvedFoodItem:
    item_name: str
    matched_fdc_id: int
    matched_description: str
    nutrients: NutrientProfile
    confidence_score: float


def normalize_food_text(text: str) -> list[str]:
    """Strip punctuation, lowercase, and tokenize food item text."""
    clean = re.sub(r"[^\w\s]", " ", text.lower())
    return [t for t in clean.split() if t]


def calculate_linear_nutrients(match: GroundingMatch, grams: float) -> NutrientProfile:
    """Deterministically scale nutrients against USDA per-100g reference values."""
    if grams < 0.0:
        raise ValueError(f"Portion weight in grams must be non-negative; got {grams}.")
    factor = grams / 100.0
    scaled_micros = {
        nutrient: round(val * factor, 3) for nutrient, val in match.micros_per_100g.items()
    }

    return NutrientProfile(
        grams=round(grams, 2),
        calories=round(match.calories_per_100g * factor, 2),
        protein_g=round(match.protein_g_per_100g * factor, 2),
        carbs_g=round(match.carbs_g_per_100g * factor, 2),
        fat_g=round(match.fat_g_per_100g * factor, 2),
        fiber_g=round(match.fiber_g_per_100g * factor, 2),
        micronutrients=scaled_micros,
    )


@dataclass(frozen=True)
class CachedFoodEntry:
    fdc_id: int
    description: str
    food_category: str | None
    preparation_state: str
    barcode: str | None
    calories_per_100g: float
    protein_g_per_100g: float
    carbs_g_per_100g: float
    fat_g_per_100g: float
    fiber_g_per_100g: float
    micros: dict[str, float]
    clean_desc_str: str
    desc_tokens: list[str]
    desc_set: set[str]


class GroundingEngine:
    """Matches free-text VLM food entity strings against USDA FoodData Central reference tables."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self._cache: list[CachedFoodEntry] | None = None

    @property
    def is_cached(self) -> bool:
        return self._cache is not None

    def invalidate_cache(self) -> None:
        self._cache = None

    def _load_cache_if_needed(self) -> list[CachedFoodEntry]:
        if self._cache is not None:
            return self._cache

        cursor = self.conn.cursor()
        cursor.execute("PRAGMA database_list;")
        attached_schemas = {row[1] for row in cursor.fetchall()}
        active_schema = "main"

        cursor.execute("SELECT COUNT(*) FROM main.usda_foods;")
        main_count = cursor.fetchone()[0]

        if main_count == 0:
            if "usda" in attached_schemas:
                cursor.execute(
                    "SELECT COUNT(*) FROM usda.sqlite_master "
                    "WHERE type='table' AND name='usda_foods';"
                )
                if cursor.fetchone()[0] > 0:
                    active_schema = "usda"
            elif "usda_reference" in attached_schemas:
                cursor.execute(
                    "SELECT COUNT(*) FROM usda_reference.sqlite_master "
                    "WHERE type='table' AND name='usda_foods';"
                )
                if cursor.fetchone()[0] > 0:
                    active_schema = "usda_reference"

        if active_schema == "usda":
            cursor.execute("PRAGMA usda.table_info(usda_foods);")
            cols = {row[1] for row in cursor.fetchall()}
            if "barcode" in cols:
                cursor.execute(
                    """
                    SELECT fdc_id, description, food_category, preparation_state,
                           barcode,
                           calories_per_100g, protein_g_per_100g, carbs_g_per_100g,
                           fat_g_per_100g, fiber_g_per_100g, micros_per_100g_json
                    FROM usda.usda_foods;
                    """
                )
            else:
                cursor.execute(
                    """
                    SELECT fdc_id, description, food_category, preparation_state,
                           NULL AS barcode,
                           calories_per_100g, protein_g_per_100g, carbs_g_per_100g,
                           fat_g_per_100g, fiber_g_per_100g, micros_per_100g_json
                    FROM usda.usda_foods;
                    """
                )
        elif active_schema == "usda_reference":
            cursor.execute("PRAGMA usda_reference.table_info(usda_foods);")
            cols = {row[1] for row in cursor.fetchall()}
            if "barcode" in cols:
                cursor.execute(
                    """
                    SELECT fdc_id, description, food_category, preparation_state,
                           barcode,
                           calories_per_100g, protein_g_per_100g, carbs_g_per_100g,
                           fat_g_per_100g, fiber_g_per_100g, micros_per_100g_json
                    FROM usda_reference.usda_foods;
                    """
                )
            else:
                cursor.execute(
                    """
                    SELECT fdc_id, description, food_category, preparation_state,
                           NULL AS barcode,
                           calories_per_100g, protein_g_per_100g, carbs_g_per_100g,
                           fat_g_per_100g, fiber_g_per_100g, micros_per_100g_json
                    FROM usda_reference.usda_foods;
                    """
                )
        else:
            cursor.execute("PRAGMA main.table_info(usda_foods);")
            cols = {row[1] for row in cursor.fetchall()}
            if "barcode" in cols:
                cursor.execute(
                    """
                    SELECT fdc_id, description, food_category, preparation_state,
                           barcode,
                           calories_per_100g, protein_g_per_100g, carbs_g_per_100g,
                           fat_g_per_100g, fiber_g_per_100g, micros_per_100g_json
                    FROM usda_foods;
                    """
                )
            else:
                cursor.execute(
                    """
                    SELECT fdc_id, description, food_category, preparation_state,
                           NULL AS barcode,
                           calories_per_100g, protein_g_per_100g, carbs_g_per_100g,
                           fat_g_per_100g, fiber_g_per_100g, micros_per_100g_json
                    FROM usda_foods;
                    """
                )
        rows = cursor.fetchall()
        cache: list[CachedFoodEntry] = []
        for r in rows:
            desc = r[1]
            desc_tokens = normalize_food_text(desc)
            desc_set = set(desc_tokens)
            clean_desc_str = " ".join(desc_tokens)
            micros = json.loads(r[10]) if r[10] else {}
            cache.append(
                CachedFoodEntry(
                    fdc_id=r[0],
                    description=desc,
                    food_category=r[2],
                    preparation_state=r[3],
                    barcode=r[4],
                    calories_per_100g=r[5],
                    protein_g_per_100g=r[6],
                    carbs_g_per_100g=r[7],
                    fat_g_per_100g=r[8],
                    fiber_g_per_100g=r[9],
                    micros=micros,
                    clean_desc_str=clean_desc_str,
                    desc_tokens=desc_tokens,
                    desc_set=desc_set,
                )
            )
        self._cache = cache
        return self._cache

    def lookup_barcode(self, barcode: str, grams: float = 100.0) -> GroundedFoodCandidate | None:
        """Lookup an exact barcode match and scale nutrients deterministically to portion grams."""
        if grams < 0.0:
            raise ValueError(f"Portion weight in grams must be non-negative; got {grams}.")
        normalized = normalize_barcode(barcode)
        entries = self._load_cache_if_needed()
        matched_entry: CachedFoodEntry | None = None
        for entry in entries:
            if entry.barcode == normalized:
                matched_entry = entry
                break
        if matched_entry is None:
            return None

        dummy_match = GroundingMatch(
            fdc_id=matched_entry.fdc_id,
            description=matched_entry.description,
            food_category=matched_entry.food_category,
            preparation_state=matched_entry.preparation_state,
            calories_per_100g=matched_entry.calories_per_100g,
            protein_g_per_100g=matched_entry.protein_g_per_100g,
            carbs_g_per_100g=matched_entry.carbs_g_per_100g,
            fat_g_per_100g=matched_entry.fat_g_per_100g,
            fiber_g_per_100g=matched_entry.fiber_g_per_100g,
            micros_per_100g=matched_entry.micros,
            score=1.0,
        )
        nutrients = calculate_linear_nutrients(dummy_match, grams)
        return GroundedFoodCandidate(
            fdc_id=matched_entry.fdc_id,
            description=matched_entry.description,
            food_category=matched_entry.food_category,
            preparation_state=matched_entry.preparation_state,
            barcode=matched_entry.barcode,
            nutrients=nutrients,
        )

    def register_barcode(
        self,
        barcode: str,
        description: str,
        calories_per_100g: float,
        protein_g_per_100g: float,
        carbs_g_per_100g: float,
        fat_g_per_100g: float,
        fiber_g_per_100g: float,
        micros_per_100g: dict[str, float] | None = None,
        food_category: str = "Packaged Foods",
        preparation_state: str = "prepared",
    ) -> GroundedFoodCandidate:
        """Upsert a packaged food barcode and nutrient profile into SQLite, invalidating cache."""
        normalized = normalize_barcode(barcode)
        micros = micros_per_100g or {}
        micros_json = json.dumps(micros)

        cursor = self.conn.cursor()
        cursor.execute("SELECT fdc_id FROM usda_foods WHERE barcode = ?;", (normalized,))
        existing = cursor.fetchone()

        if existing:
            fdc_id = existing[0]
            cursor.execute(
                """
                UPDATE usda_foods
                SET description = ?, food_category = ?, preparation_state = ?,
                    calories_per_100g = ?, protein_g_per_100g = ?, carbs_g_per_100g = ?,
                    fat_g_per_100g = ?, fiber_g_per_100g = ?, micros_per_100g_json = ?
                WHERE fdc_id = ?;
                """,
                (
                    description,
                    food_category,
                    preparation_state,
                    calories_per_100g,
                    protein_g_per_100g,
                    carbs_g_per_100g,
                    fat_g_per_100g,
                    fiber_g_per_100g,
                    micros_json,
                    fdc_id,
                ),
            )
        else:
            cursor.execute("SELECT COALESCE(MAX(fdc_id), 900000) FROM usda_foods;")
            max_id = cursor.fetchone()[0]
            fdc_id = max(max_id + 1, 900001)
            cursor.execute(
                """
                INSERT INTO usda_foods (
                    fdc_id, description, food_category, preparation_state, barcode,
                    calories_per_100g, protein_g_per_100g, carbs_g_per_100g,
                    fat_g_per_100g, fiber_g_per_100g, micros_per_100g_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    fdc_id,
                    description,
                    food_category,
                    preparation_state,
                    normalized,
                    calories_per_100g,
                    protein_g_per_100g,
                    carbs_g_per_100g,
                    fat_g_per_100g,
                    fiber_g_per_100g,
                    micros_json,
                ),
            )

        self.conn.commit()
        self.invalidate_cache()

        candidate_match = GroundingMatch(
            fdc_id=fdc_id,
            description=description,
            food_category=food_category,
            preparation_state=preparation_state,
            calories_per_100g=calories_per_100g,
            protein_g_per_100g=protein_g_per_100g,
            carbs_g_per_100g=carbs_g_per_100g,
            fat_g_per_100g=fat_g_per_100g,
            fiber_g_per_100g=fiber_g_per_100g,
            micros_per_100g=micros,
            score=1.0,
        )
        return GroundedFoodCandidate(
            fdc_id=fdc_id,
            description=description,
            food_category=food_category,
            preparation_state=preparation_state,
            barcode=normalized,
            nutrients=calculate_linear_nutrients(candidate_match, 100.0),
        )

    def export_offline_catalog(self) -> list[dict[str, Any]]:
        """Export all reference and custom food items formatted for client-side offline caching."""
        entries = self._load_cache_if_needed()
        return [
            {
                "fdc_id": e.fdc_id,
                "description": e.description,
                "food_category": e.food_category,
                "preparation_state": e.preparation_state,
                "barcode": e.barcode,
                "calories_per_100g": e.calories_per_100g,
                "protein_g_per_100g": e.protein_g_per_100g,
                "carbs_g_per_100g": e.carbs_g_per_100g,
                "fat_g_per_100g": e.fat_g_per_100g,
                "fiber_g_per_100g": e.fiber_g_per_100g,
                "micros_per_100g": e.micros,
            }
            for e in entries
        ]

    def search_candidates(self, query: str, limit: int = 5) -> list[GroundingMatch]:
        """Rank USDA food records against query using token overlap and state weighting."""
        query_tokens = normalize_food_text(query)
        if not query_tokens:
            return []

        query_set = set(query_tokens)
        query_has_raw = "raw" in query_set

        entries = self._load_cache_if_needed()

        scored_matches: list[GroundingMatch] = []
        clean_query_str = " ".join(query_tokens)

        for entry in entries:
            # 1. Token overlap score
            overlap = query_set.intersection(entry.desc_set)
            if not overlap:
                continue

            base_score = len(overlap) / len(query_set)

            # 2. String sequence similarity (difflib ratio)
            seq_ratio = difflib.SequenceMatcher(None, clean_query_str, entry.clean_desc_str).ratio()
            total_score = (base_score * 0.7) + (seq_ratio * 0.3)

            # 3. Preparation state weighting (1.5x) and Cooked-First default
            if not query_has_raw and entry.preparation_state in PREPARED_STATES:
                total_score *= 1.5
            elif query_has_raw and entry.preparation_state == "raw":
                total_score *= 1.5

            common_states = query_set.intersection(STATE_TOKENS).intersection(entry.desc_set)
            if common_states:
                total_score += 0.2

            scored_matches.append(
                GroundingMatch(
                    fdc_id=entry.fdc_id,
                    description=entry.description,
                    food_category=entry.food_category,
                    preparation_state=entry.preparation_state,
                    calories_per_100g=entry.calories_per_100g,
                    protein_g_per_100g=entry.protein_g_per_100g,
                    carbs_g_per_100g=entry.carbs_g_per_100g,
                    fat_g_per_100g=entry.fat_g_per_100g,
                    fiber_g_per_100g=entry.fiber_g_per_100g,
                    micros_per_100g=entry.micros,
                    score=round(total_score, 4),
                )
            )

        scored_matches.sort(key=lambda m: m.score, reverse=True)
        return scored_matches[:limit]


def resolve_food_item(
    engine: GroundingEngine,
    item_name: str,
    estimated_grams: float,
) -> ResolvedFoodItem | None:
    """Finds best USDA match for an item and deterministically scales nutrients."""
    matches = engine.search_candidates(item_name, limit=1)
    if not matches:
        return None

    best_match = matches[0]
    nutrients = calculate_linear_nutrients(best_match, estimated_grams)

    return ResolvedFoodItem(
        item_name=item_name,
        matched_fdc_id=best_match.fdc_id,
        matched_description=best_match.description,
        nutrients=nutrients,
        confidence_score=best_match.score,
    )

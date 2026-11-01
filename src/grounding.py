"""Neuro-symbolic grounding engine: token normalization and USDA candidate ranking."""

import difflib
import json
import re
import sqlite3
from dataclasses import dataclass

STATE_TOKENS = {"cooked", "steamed", "roasted", "boiled", "fried", "raw", "prepared", "baked"}
PREPARED_STATES = {"cooked", "prepared", "steamed", "roasted", "boiled", "fried", "baked"}


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
        cursor.execute(
            """
            SELECT fdc_id, description, food_category, preparation_state,
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
            micros = json.loads(r[9]) if r[9] else {}
            cache.append(
                CachedFoodEntry(
                    fdc_id=r[0],
                    description=desc,
                    food_category=r[2],
                    preparation_state=r[3],
                    calories_per_100g=r[4],
                    protein_g_per_100g=r[5],
                    carbs_g_per_100g=r[6],
                    fat_g_per_100g=r[7],
                    fiber_g_per_100g=r[8],
                    micros=micros,
                    clean_desc_str=clean_desc_str,
                    desc_tokens=desc_tokens,
                    desc_set=desc_set,
                )
            )
        self._cache = cache
        return self._cache

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

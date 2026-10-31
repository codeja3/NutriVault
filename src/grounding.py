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


class GroundingEngine:
    """Matches free-text VLM food entity strings against USDA FoodData Central reference tables."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def search_candidates(self, query: str, limit: int = 5) -> list[GroundingMatch]:
        """Rank USDA food records against query using token overlap and state weighting."""
        query_tokens = normalize_food_text(query)
        if not query_tokens:
            return []

        query_set = set(query_tokens)
        query_has_raw = "raw" in query_set

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

        scored_matches: list[GroundingMatch] = []
        clean_query_str = " ".join(query_tokens)

        for row in rows:
            desc = row[1]
            prep_state = row[3]
            desc_tokens = normalize_food_text(desc)
            desc_set = set(desc_tokens)
            clean_desc_str = " ".join(desc_tokens)

            # 1. Token overlap score
            overlap = query_set.intersection(desc_set)
            if not overlap:
                continue

            base_score = len(overlap) / len(query_set)

            # 2. String sequence similarity (difflib ratio)
            seq_ratio = difflib.SequenceMatcher(None, clean_query_str, clean_desc_str).ratio()
            total_score = (base_score * 0.7) + (seq_ratio * 0.3)

            # 3. Preparation state weighting (1.5x) and Cooked-First default
            if not query_has_raw and prep_state in PREPARED_STATES:
                total_score *= 1.5
            elif query_has_raw and prep_state == "raw":
                total_score *= 1.5

            common_states = query_set.intersection(STATE_TOKENS).intersection(desc_set)
            if common_states:
                total_score += 0.2

            micros = json.loads(row[9]) if row[9] else {}

            scored_matches.append(
                GroundingMatch(
                    fdc_id=row[0],
                    description=desc,
                    food_category=row[2],
                    preparation_state=prep_state,
                    calories_per_100g=row[4],
                    protein_g_per_100g=row[5],
                    carbs_g_per_100g=row[6],
                    fat_g_per_100g=row[7],
                    fiber_g_per_100g=row[8],
                    micros_per_100g=micros,
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

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


def normalize_food_text(text: str) -> list[str]:
    """Strip punctuation, lowercase, and tokenize food item text."""
    clean = re.sub(r"[^\w\s]", " ", text.lower())
    return [t for t in clean.split() if t]


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

            # 1. Token overlap score (Jaccard-like with weighting)
            overlap = query_set.intersection(desc_set)
            if not overlap:
                continue

            base_score = len(overlap) / len(query_set)

            # 2. String sequence similarity (Levenshtein/difflib ratio)
            seq_ratio = difflib.SequenceMatcher(None, clean_query_str, clean_desc_str).ratio()

            total_score = (base_score * 0.7) + (seq_ratio * 0.3)

            # 3. Preparation state weighting (1.5x) and Cooked-First default
            if not query_has_raw and prep_state in PREPARED_STATES:
                total_score *= 1.5
            elif query_has_raw and prep_state == "raw":
                total_score *= 1.5

            # Extra weight if explicit state token in query matches item description
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

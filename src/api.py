"""Local REST API router and request dispatcher for NutriVault services."""

import json
import re
import sqlite3
import urllib.parse
from dataclasses import asdict
from typing import Any

from src.advisory import (
    ClinicalAdvisoryViolationError,
    generate_athletic_targets,
)
from src.analytics import (
    AnalyticsEngine,
    calculate_chrononutrition_windows,
)
from src.batch_allocator import (
    BatchDishAllocator,
    DishIngredient,
    InvalidPortionSumError,
    ProfilePortionAllocation,
)
from src.db import ProfileRepository
from src.grounding import (
    GroundingEngine,
    resolve_food_item,
)
from src.hardware import (
    HardwareProfile,
    probe_hardware,
    resolve_model_tier,
)
from src.vision_pipeline import (
    EphemeralImageBuffer,
    ImagePayloadTooLargeError,
    VLMClient,
    VLMInvalidJSONError,
    VLMUnavailableError,
)


class NutriVaultAPI:
    """Dispatches and handles REST API requests strictly in-process offline."""

    def __init__(
        self,
        conn: sqlite3.Connection,
        hardware_profile: HardwareProfile | None = None,
        vlm_client: VLMClient | None = None,
    ):
        self.conn = conn
        self.hardware_profile = hardware_profile or probe_hardware()
        self.active_tier_ceiling = resolve_model_tier(self.hardware_profile)
        self.repo = ProfileRepository(conn)
        self.grounding_engine = GroundingEngine(conn)
        self.vlm_client = vlm_client or VLMClient()
        self.batch_allocator = BatchDishAllocator(conn)
        self.analytics_engine = AnalyticsEngine(conn)

    def handle_request(
        self,
        method: str,
        path: str,
        body: str | None = None,
        raw_body: bytes | None = None,
        content_type: str = "application/json",
    ) -> tuple[int, str]:
        """Route request and return (status_code, response_body_json)."""
        method = method.upper()

        parsed_url = urllib.parse.urlparse(path)
        route_path = parsed_url.path
        query_params = urllib.parse.parse_qs(parsed_url.query)

        try:
            # 1. GET /api/v1/hardware
            if method == "GET" and route_path == "/api/v1/hardware":
                return self._handle_get_hardware()

            # 2. GET /api/v1/profiles
            if method == "GET" and route_path == "/api/v1/profiles":
                return self._handle_list_profiles()

            # 3. POST /api/v1/profiles
            if method == "POST" and route_path == "/api/v1/profiles":
                data = json.loads(body or "{}")
                return self._handle_create_profile(data)

            # 4. PUT /api/v1/profiles/{id}/targets
            target_match = re.match(r"^/api/v1/profiles/([^/]+)/targets$", route_path)
            if method == "PUT" and target_match:
                profile_id = target_match.group(1)
                data = json.loads(body or "{}")
                return self._handle_set_targets(profile_id, data)

            # 5. POST /api/v1/advisory/fitness-targets
            if method == "POST" and route_path == "/api/v1/advisory/fitness-targets":
                data = json.loads(body or "{}")
                return self._handle_advisory_targets(data)

            # 6. POST /api/v1/meals/parse-image
            if method == "POST" and route_path == "/api/v1/meals/parse-image":
                return self._handle_parse_image(raw_body)

            # 7. POST /api/v1/meals/commit
            if method == "POST" and route_path == "/api/v1/meals/commit":
                data = json.loads(body or "{}")
                return self._handle_commit_meal(data)

            # 8. GET /api/v1/analytics/rolling
            if method == "GET" and route_path == "/api/v1/analytics/rolling":
                profile_id = query_params.get("profile_id", [None])[0]
                days_param = query_params.get("days", [7])[0]
                days = int(days_param) if days_param else 7
                if not profile_id:
                    raise ValueError("Query parameter 'profile_id' is required.")
                return self._handle_get_analytics(profile_id, days)

            return 404, json.dumps({"error": f"Endpoint not found: {method} {path}"})

        except ClinicalAdvisoryViolationError as e:
            return 403, json.dumps(
                {"error_code": e.error_code, "error": str(e), "disclaimer": e.disclaimer}
            )
        except InvalidPortionSumError as e:
            return 400, json.dumps({"error_code": e.error_code, "error": str(e)})
        except ImagePayloadTooLargeError as e:
            return 413, json.dumps({"error_code": e.error_code, "error": str(e)})
        except VLMInvalidJSONError as e:
            return 422, json.dumps({"error_code": e.error_code, "error": str(e)})
        except VLMUnavailableError as e:
            return 503, json.dumps({"error_code": e.error_code, "error": str(e)})
        except KeyError as e:
            return 404, json.dumps({"error": str(e)})
        except ValueError as e:
            return 400, json.dumps({"error": str(e)})
        except Exception as e:
            return 500, json.dumps({"error": f"Internal server error: {e}"})

    def _handle_get_hardware(self) -> tuple[int, str]:
        resp = {
            "os_name": self.hardware_profile.os_name,
            "total_ram_gb": self.hardware_profile.total_ram_gb,
            "accelerator": self.hardware_profile.accelerator.value,
            "vram_gb": self.hardware_profile.vram_gb,
            "cpu_cores": self.hardware_profile.cpu_cores,
            "active_tier_ceiling": self.active_tier_ceiling.value,
        }
        return 200, json.dumps(resp)

    def _handle_list_profiles(self) -> tuple[int, str]:
        profiles = self.repo.list_profiles()
        return 200, json.dumps([asdict(p) for p in profiles])

    def _handle_create_profile(self, data: dict[str, Any]) -> tuple[int, str]:
        profile = self.repo.create_profile(
            name=data["name"],
            profile_type=data["profile_type"],
            birth_date=data.get("birth_date"),
            condition_notes=data.get("condition_notes"),
        )
        return 201, json.dumps(asdict(profile))

    def _handle_set_targets(self, profile_id: str, data: dict[str, Any]) -> tuple[int, str]:
        envelope = self.repo.set_active_target_envelope(
            profile_id=profile_id,
            calories_target=int(data["calories_target"]),
            protein_g_target=float(data["protein_g_target"]),
            carbs_g_target=float(data["carbs_g_target"]),
            fat_g_target=float(data["fat_g_target"]),
            fiber_g_target=float(data["fiber_g_target"]),
            micronutrients=data.get("micronutrients"),
        )
        return 200, json.dumps(asdict(envelope))

    def _handle_advisory_targets(self, data: dict[str, Any]) -> tuple[int, str]:
        profile_id = data["profile_id"]
        profile = self.repo.get_profile(profile_id)
        if not profile:
            raise KeyError(f"Profile '{profile_id}' not found.")

        response = generate_athletic_targets(
            profile=profile,
            athletic_goal=data.get("athletic_goal", "general"),
            weight_kg=float(data["weight_kg"]),
        )
        return 200, json.dumps(asdict(response))

    def _handle_parse_image(self, raw_body: bytes | None) -> tuple[int, str]:
        if not raw_body:
            raise ValueError("No image payload provided.")

        with EphemeralImageBuffer.from_bytes(raw_body) as buffer:
            candidate_items = self.vlm_client.parse_meal_image(buffer)

        grounded_items = []
        for c in candidate_items:
            resolved = resolve_food_item(
                engine=self.grounding_engine,
                item_name=c.item_name,
                estimated_grams=c.estimated_grams,
            )
            if resolved:
                grounded_items.append(asdict(resolved))
            else:
                grounded_items.append(
                    {
                        "item_name": c.item_name,
                        "matched_fdc_id": None,
                        "matched_description": None,
                        "nutrients": {
                            "grams": c.estimated_grams,
                            "calories": 0.0,
                            "protein_g": 0.0,
                            "carbs_g": 0.0,
                            "fat_g": 0.0,
                            "fiber_g": 0.0,
                            "micronutrients": {},
                        },
                        "confidence_score": 0.0,
                    }
                )

        return 200, json.dumps({"items": grounded_items})

    def _handle_commit_meal(self, data: dict[str, Any]) -> tuple[int, str]:
        dish_name = data["dish_name"]
        ingredients = [
            DishIngredient(
                item_name=ing["item_name"],
                fdc_id=int(ing["fdc_id"]),
                grams=float(ing["grams"]),
                calories=float(ing["calories"]),
                protein_g=float(ing["protein_g"]),
                carbs_g=float(ing["carbs_g"]),
                fat_g=float(ing["fat_g"]),
                fiber_g=float(ing["fiber_g"]),
                micros=ing.get("micros", {}),
            )
            for ing in data["ingredients"]
        ]

        dish = self.batch_allocator.create_dish(name=dish_name, ingredients=ingredients)

        allocations = [
            ProfilePortionAllocation(
                profile_id=a["profile_id"],
                fraction=float(a["fraction"]),
                meal_type=a.get("meal_type", "dinner"),
            )
            for a in data["allocations"]
        ]

        log_ids = self.batch_allocator.commit_batch_allocations(dish=dish, allocations=allocations)

        return 201, json.dumps({"dish_id": dish.id, "meal_log_ids": log_ids})

    def _handle_get_analytics(self, profile_id: str, days: int) -> tuple[int, str]:
        ema_result = self.analytics_engine.calculate_rolling_ema(profile_id=profile_id, days=days)
        feeding_intervals = calculate_chrononutrition_windows(self.conn, profile_id=profile_id)

        resp = asdict(ema_result)
        resp["feeding_intervals"] = [asdict(interval) for interval in feeding_intervals]

        return 200, json.dumps(resp)

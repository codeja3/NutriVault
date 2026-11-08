"""Local REST API router and request dispatcher for NutriVault services."""

import http.server
import json
import re
import sqlite3
import threading
import urllib.parse
from dataclasses import asdict
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

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
from src.db import ProfileRepository, init_db
from src.grounding import (
    BarcodeNotFoundError,
    GroundingEngine,
    calculate_linear_nutrients,
    normalize_barcode,
    resolve_food_item,
)
from src.hardware import (
    HardwareProfile,
    build_managed_vlm_command,
    format_vlm_setup_guide,
    get_default_vlm_spec,
    get_recommended_models,
    probe_hardware,
    resolve_model_tier,
)
from src.ui import GET_PWA_HTML, GET_PWA_MANIFEST, GET_PWA_SERVICE_WORKER
from src.vision_pipeline import (
    EphemeralImageBuffer,
    ImagePayloadTooLargeError,
    VLMClient,
    VLMInvalidJSONError,
    VLMUnavailableError,
)

ProfileType = Literal["standard", "athletic", "chronic_condition"]
MealType = Literal["breakfast", "lunch", "dinner", "snack", "pre_workout", "post_workout"]


class ProfileCreateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1)
    profile_type: ProfileType
    birth_date: str | None = None
    condition_notes: str | None = None


class TargetEnvelopeRequest(BaseModel):
    calories_target: int = Field(ge=0)
    protein_g_target: float = Field(ge=0.0)
    carbs_g_target: float = Field(ge=0.0)
    fat_g_target: float = Field(ge=0.0)
    fiber_g_target: float = Field(ge=0.0)
    micronutrients: dict[str, float] | None = None
    is_ai_generated: bool = False
    acknowledged: bool = False


class FitnessAdvisoryRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    profile_id: str = Field(min_length=1)
    athletic_goal: str = "general"
    weight_kg: float = Field(gt=0.0)


class DishIngredientRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    item_name: str = Field(min_length=1)
    fdc_id: int
    grams: float = Field(ge=0.0)
    calories: float = Field(ge=0.0)
    protein_g: float = Field(ge=0.0)
    carbs_g: float = Field(ge=0.0)
    fat_g: float = Field(ge=0.0)
    fiber_g: float = Field(ge=0.0)
    micros: dict[str, float] = Field(default_factory=dict)


class ProfilePortionAllocationRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    profile_id: str = Field(min_length=1)
    fraction: float
    meal_type: MealType = "dinner"
    logged_at: str | None = None

    @field_validator("logged_at")
    @classmethod
    def validate_logged_at_iso(cls, v: str | None) -> str | None:
        if v is not None:
            try:
                datetime.fromisoformat(v)
            except ValueError as e:
                raise ValueError(f"Invalid ISO-8601 timestamp: {v}") from e
        return v


class MealCommitRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    dish_name: str = Field(min_length=1)
    ingredients: list[DishIngredientRequest] = Field(min_length=1)
    allocations: list[ProfilePortionAllocationRequest] = Field(min_length=1)


class BarcodeRegisterRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    description: str = Field(min_length=1)
    calories_per_100g: float = Field(ge=0.0)
    protein_g_per_100g: float = Field(ge=0.0)
    carbs_g_per_100g: float = Field(ge=0.0)
    fat_g_per_100g: float = Field(ge=0.0)
    fiber_g_per_100g: float = Field(default=0.0, ge=0.0)
    micros_per_100g: dict[str, float] = Field(default_factory=dict)
    food_category: str = "Packaged Foods"
    preparation_state: str = "prepared"


class QueuedBarcodeItemRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    barcode: str = Field(min_length=4)
    grams: float = Field(gt=0.0)
    dish_name: str | None = None
    allocations: list[ProfilePortionAllocationRequest] = Field(min_length=1)


class OfflineSyncBatchRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    queued_meals: list[MealCommitRequest] = Field(default_factory=list)
    queued_barcodes: list[QueuedBarcodeItemRequest] = Field(default_factory=list)


def _extract_image_bytearray(raw_body: bytes | bytearray, content_type: str) -> bytearray:
    """Extract raw image binary bytes into a mutable bytearray from multipart or direct payload."""
    ba = bytearray(raw_body)
    if not content_type or "multipart/form-data" not in content_type:
        return ba

    boundary = None
    for part in content_type.split(";"):
        part = part.strip()
        if part.startswith("boundary="):
            boundary = part.split("boundary=", 1)[1].strip('"').strip("'")
            break

    boundary_bytes = (f"--{boundary}" if boundary else "--").encode("utf-8")
    parts = ba.split(boundary_bytes)
    extracted: bytearray | None = None
    try:
        for p in parts:
            if not p or p in (b"--\r\n", b"--", b"\r\n"):
                continue
            if b"\r\n\r\n" in p:
                hdr, body = p.split(b"\r\n\r\n", 1)
            elif b"\n\n" in p:
                hdr, body = p.split(b"\n\n", 1)
            else:
                continue

            hdr_str = bytes(hdr).decode("utf-8", errors="ignore").lower()
            if 'name="image"' in hdr_str or "filename=" in hdr_str or "image/" in hdr_str:
                if body.endswith(b"\r\n"):
                    body = body[:-2]
                elif body.endswith(b"\n"):
                    body = body[:-1]
                extracted = bytearray(body)
                return extracted
    finally:
        for p in parts:
            p[:] = b"\x00" * len(p)
        if extracted is not None:
            ba[:] = b"\x00" * len(ba)

    return ba


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
        self._lock = threading.Lock()

    def handle_request(
        self,
        method: str,
        path: str,
        body: str | None = None,
        raw_body: bytes | None = None,
        content_type: str = "application/json",
    ) -> tuple[int, str]:
        """Route request and return (status_code, response_body_json)."""
        with self._lock:
            return self._handle_request_locked(
                method=method,
                path=path,
                body=body,
                raw_body=raw_body,
                content_type=content_type,
            )

    def _handle_request_locked(
        self,
        method: str,
        path: str,
        body: str | None = None,
        raw_body: bytes | None = None,
        content_type: str = "application/json",
    ) -> tuple[int, str]:
        method = method.upper()

        parsed_url = urllib.parse.urlparse(path)
        route_path = parsed_url.path
        query_params = urllib.parse.parse_qs(parsed_url.query)

        try:
            # 0. GET / and GET /manifest.json (Progressive Web App)
            if method == "GET" and route_path == "/":
                return 200, GET_PWA_HTML()

            if method == "GET" and route_path == "/manifest.json":
                return 200, GET_PWA_MANIFEST()

            if method == "GET" and route_path == "/sw.js":
                return 200, GET_PWA_SERVICE_WORKER()

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
                return self._handle_parse_image(raw_body, content_type)

            # 7. POST /api/v1/meals/commit
            if method == "POST" and route_path == "/api/v1/meals/commit":
                data = json.loads(body or "{}")
                return self._handle_commit_meal(data)

            # 8. GET /api/v1/analytics/rolling
            if method == "GET" and route_path == "/api/v1/analytics/rolling":
                profile_id = query_params.get("profile_id", [None])[0]
                days_param = query_params.get("days", ["7"])[0]
                try:
                    days = int(days_param) if days_param else 7
                except ValueError:
                    raise ValueError(f"Invalid 'days' query parameter: {days_param}")
                if days < 1:
                    raise ValueError("Query parameter 'days' must be an integer >= 1.")
                if not profile_id:
                    raise ValueError("Query parameter 'profile_id' is required.")
                return self._handle_get_analytics(profile_id, days)

            # 9. GET /api/v1/foods/search
            if method == "GET" and route_path == "/api/v1/foods/search":
                q_param = query_params.get("q", [None])[0]
                if q_param is None or not q_param.strip():
                    raise ValueError("Search query parameter 'q' must be a non-empty string.")
                grams_param = query_params.get("grams", ["100.0"])[0]
                try:
                    grams = float(grams_param)
                    if grams <= 0.0:
                        raise ValueError("Query parameter 'grams' must be a float > 0.0.")
                except (ValueError, TypeError):
                    raise ValueError("Query parameter 'grams' must be a float > 0.0.")
                limit_param = query_params.get("limit", ["10"])[0]
                try:
                    limit = int(limit_param)
                    if limit < 1 or limit > 50:
                        raise ValueError(
                            "Query parameter 'limit' must be an integer between 1 and 50."
                        )
                except (ValueError, TypeError):
                    raise ValueError("Query parameter 'limit' must be an integer between 1 and 50.")
                return self._handle_search_foods(q=q_param.strip(), grams=grams, limit=limit)

            # 10. GET /api/v1/foods/catalog
            if method == "GET" and route_path == "/api/v1/foods/catalog":
                return self._handle_get_catalog()

            # 11. GET & PUT /api/v1/foods/barcode/{code}
            barcode_match = re.match(r"^/api/v1/foods/barcode/([^/]+)$", route_path)
            if barcode_match:
                barcode_code = barcode_match.group(1)
                if method == "GET":
                    grams_param = query_params.get("grams", ["100.0"])[0]
                    try:
                        grams = float(grams_param)
                        if grams <= 0.0:
                            raise ValueError("Query parameter 'grams' must be a float > 0.0.")
                    except (ValueError, TypeError):
                        raise ValueError("Query parameter 'grams' must be a float > 0.0.")
                    return self._handle_get_barcode(barcode_code, grams)
                if method == "PUT":
                    data = json.loads(body or "{}")
                    return self._handle_put_barcode(barcode_code, data)

            # 12. POST /api/v1/sync/batch
            if method == "POST" and route_path == "/api/v1/sync/batch":
                data = json.loads(body or "{}")
                return self._handle_sync_batch(data)

            return 404, json.dumps({"error": f"Endpoint not found: {method} {path}"})

        except ClinicalAdvisoryViolationError as e:
            return 403, json.dumps(
                {"error_code": e.error_code, "error": str(e), "disclaimer": e.disclaimer}
            )
        except InvalidPortionSumError as e:
            return 400, json.dumps({"error_code": e.error_code, "error": str(e)})
        except BarcodeNotFoundError as e:
            return 404, json.dumps({"error_code": e.error_code, "error": str(e)})
        except (ValidationError, json.JSONDecodeError) as e:
            return 400, json.dumps({"error": str(e)})
        except ImagePayloadTooLargeError as e:
            return 413, json.dumps({"error_code": e.error_code, "error": str(e)})
        except VLMInvalidJSONError as e:
            return 422, json.dumps({"error_code": e.error_code, "error": str(e)})
        except VLMUnavailableError as e:
            return 503, json.dumps({"error_code": e.error_code, "error": str(e)})
        except sqlite3.IntegrityError as e:
            return 400, json.dumps({"error": f"Database integrity violation: {e}"})
        except KeyError as e:
            return 404, json.dumps({"error": str(e)})
        except ValueError as e:
            return 400, json.dumps({"error": str(e)})
        except Exception:
            return 500, json.dumps({"error": "Internal server error."})

    def _handle_get_hardware(self) -> tuple[int, str]:
        default_vlm = get_default_vlm_spec(self.active_tier_ceiling)
        cmd_tokens = build_managed_vlm_command(
            self.active_tier_ceiling, port=8081, host="127.0.0.1"
        )
        resp = {
            "os_name": self.hardware_profile.os_name,
            "total_ram_gb": self.hardware_profile.total_ram_gb,
            "accelerator": self.hardware_profile.accelerator.value,
            "vram_gb": self.hardware_profile.vram_gb,
            "cpu_cores": self.hardware_profile.cpu_cores,
            "active_tier_ceiling": self.active_tier_ceiling.value,
            "recommended_models": get_recommended_models(self.active_tier_ceiling),
            "default_vlm": asdict(default_vlm),
            "managed_vlm_command": " ".join(cmd_tokens),
        }
        return 200, json.dumps(resp)

    def _handle_search_foods(self, q: str, grams: float, limit: int) -> tuple[int, str]:
        matches = self.grounding_engine.search_candidates(q, limit=limit)
        results = []
        for match in matches:
            nutrients = calculate_linear_nutrients(match, grams)
            results.append(
                {
                    "fdc_id": match.fdc_id,
                    "description": match.description,
                    "food_category": match.food_category,
                    "preparation_state": match.preparation_state,
                    "confidence_score": round(match.score, 2),
                    "nutrients": asdict(nutrients),
                }
            )
        return 200, json.dumps({"results": results})

    def _handle_list_profiles(self) -> tuple[int, str]:
        profiles = self.repo.list_profiles()
        return 200, json.dumps([asdict(p) for p in profiles])

    def _handle_create_profile(self, data: dict[str, Any]) -> tuple[int, str]:
        req = ProfileCreateRequest.model_validate(data)
        profile = self.repo.create_profile(
            name=req.name,
            profile_type=req.profile_type,
            birth_date=req.birth_date,
            condition_notes=req.condition_notes,
        )
        return 201, json.dumps(asdict(profile))

    def _handle_set_targets(self, profile_id: str, data: dict[str, Any]) -> tuple[int, str]:
        profile = self.repo.get_profile(profile_id)
        if not profile:
            raise KeyError(f"Profile '{profile_id}' not found.")

        req = TargetEnvelopeRequest.model_validate(data)
        if req.is_ai_generated:
            if profile.profile_type == "chronic_condition":
                raise ClinicalAdvisoryViolationError()
            if profile.profile_type == "athletic" and not req.acknowledged:
                raise ValueError(
                    "Athletic AI-generated target envelope requires explicit "
                    "acknowledgment (acknowledged: true)."
                )

        envelope = self.repo.set_active_target_envelope(
            profile_id=profile_id,
            calories_target=req.calories_target,
            protein_g_target=req.protein_g_target,
            carbs_g_target=req.carbs_g_target,
            fat_g_target=req.fat_g_target,
            fiber_g_target=req.fiber_g_target,
            micronutrients=req.micronutrients,
        )
        return 200, json.dumps(asdict(envelope))

    def _handle_advisory_targets(self, data: dict[str, Any]) -> tuple[int, str]:
        req = FitnessAdvisoryRequest.model_validate(data)
        profile = self.repo.get_profile(req.profile_id)
        if not profile:
            raise KeyError(f"Profile '{req.profile_id}' not found.")

        response = generate_athletic_targets(
            profile=profile,
            athletic_goal=req.athletic_goal,
            weight_kg=req.weight_kg,
        )
        return 200, json.dumps(asdict(response))

    def _handle_parse_image(
        self,
        raw_body: bytes | bytearray | None,
        content_type: str = "application/json",
    ) -> tuple[int, str]:
        if not raw_body:
            raise ValueError("No image payload provided.")

        try:
            image_ba = _extract_image_bytearray(raw_body, content_type)
            try:
                with EphemeralImageBuffer.from_bytes(image_ba) as buffer:
                    candidate_items = self.vlm_client.parse_meal_image(buffer)
            finally:
                image_ba[:] = b"\x00" * len(image_ba)
        finally:
            if isinstance(raw_body, bytearray):
                raw_body[:] = b"\x00" * len(raw_body)

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
        req = MealCommitRequest.model_validate(data)
        ingredients = [
            DishIngredient(
                item_name=ing.item_name,
                fdc_id=ing.fdc_id,
                grams=ing.grams,
                calories=ing.calories,
                protein_g=ing.protein_g,
                carbs_g=ing.carbs_g,
                fat_g=ing.fat_g,
                fiber_g=ing.fiber_g,
                micros=ing.micros,
            )
            for ing in req.ingredients
        ]

        allocations = [
            ProfilePortionAllocation(
                profile_id=a.profile_id,
                fraction=a.fraction,
                meal_type=a.meal_type,
                logged_at=a.logged_at,
            )
            for a in req.allocations
        ]

        dish, log_ids = self.batch_allocator.commit_meal(
            name=req.dish_name,
            ingredients=ingredients,
            allocations=allocations,
        )

        return 201, json.dumps({"dish_id": dish.id, "meal_log_ids": log_ids})

    def _handle_get_analytics(self, profile_id: str, days: int) -> tuple[int, str]:
        ema_result = self.analytics_engine.calculate_rolling_ema(profile_id=profile_id, days=days)
        feeding_intervals = calculate_chrononutrition_windows(
            self.conn, profile_id=profile_id, days=days
        )

        resp = asdict(ema_result)
        resp["feeding_intervals"] = [asdict(interval) for interval in feeding_intervals]

        return 200, json.dumps(resp)

    def _handle_get_catalog(self) -> tuple[int, str]:
        catalog = self.grounding_engine.export_offline_catalog()
        return 200, json.dumps({"items": catalog})

    def _handle_get_barcode(self, code: str, grams: float) -> tuple[int, str]:
        norm_code = normalize_barcode(code)
        match = self.grounding_engine.lookup_barcode(norm_code, grams=grams)
        if not match:
            raise BarcodeNotFoundError(f"Barcode '{code}' not found in food catalog.")
        return 200, json.dumps(asdict(match))

    def _handle_put_barcode(self, code: str, data: dict[str, Any]) -> tuple[int, str]:
        norm_code = normalize_barcode(code)
        req = BarcodeRegisterRequest.model_validate(data)
        registered = self.grounding_engine.register_barcode(
            barcode=norm_code,
            description=req.description,
            calories_per_100g=req.calories_per_100g,
            protein_g_per_100g=req.protein_g_per_100g,
            carbs_g_per_100g=req.carbs_g_per_100g,
            fat_g_per_100g=req.fat_g_per_100g,
            fiber_g_per_100g=req.fiber_g_per_100g,
            micros_per_100g=req.micros_per_100g,
            food_category=req.food_category,
            preparation_state=req.preparation_state,
        )
        return 200, json.dumps(asdict(registered))

    def _handle_sync_batch(self, data: dict[str, Any]) -> tuple[int, str]:
        req = OfflineSyncBatchRequest.model_validate(data)
        all_log_ids: list[str] = []
        synced_meals_count = 0
        unresolved: list[dict[str, Any]] = []

        for qm in req.queued_meals:
            ingredients = [
                DishIngredient(
                    item_name=ing.item_name,
                    fdc_id=ing.fdc_id,
                    grams=ing.grams,
                    calories=ing.calories,
                    protein_g=ing.protein_g,
                    carbs_g=ing.carbs_g,
                    fat_g=ing.fat_g,
                    fiber_g=ing.fiber_g,
                    micros=ing.micros,
                )
                for ing in qm.ingredients
            ]
            allocations = [
                ProfilePortionAllocation(
                    profile_id=a.profile_id,
                    fraction=a.fraction,
                    meal_type=a.meal_type,
                    logged_at=a.logged_at,
                )
                for a in qm.allocations
            ]
            dish, log_ids = self.batch_allocator.commit_meal(
                name=qm.dish_name,
                ingredients=ingredients,
                allocations=allocations,
            )
            all_log_ids.extend(log_ids)
            synced_meals_count += 1

        for qb in req.queued_barcodes:
            candidate = None
            try:
                candidate = self.grounding_engine.lookup_barcode(qb.barcode, grams=qb.grams)
            except ValueError:
                candidate = None

            if candidate is not None:
                dish_name = qb.dish_name or candidate.description
                ingredient = DishIngredient(
                    item_name=candidate.description,
                    fdc_id=candidate.fdc_id,
                    grams=candidate.nutrients.grams,
                    calories=candidate.nutrients.calories,
                    protein_g=candidate.nutrients.protein_g,
                    carbs_g=candidate.nutrients.carbs_g,
                    fat_g=candidate.nutrients.fat_g,
                    fiber_g=candidate.nutrients.fiber_g,
                    micros=candidate.nutrients.micronutrients,
                )
                allocations = [
                    ProfilePortionAllocation(
                        profile_id=a.profile_id,
                        fraction=a.fraction,
                        meal_type=a.meal_type,
                        logged_at=a.logged_at,
                    )
                    for a in qb.allocations
                ]
                dish, log_ids = self.batch_allocator.commit_meal(
                    name=dish_name,
                    ingredients=[ingredient],
                    allocations=allocations,
                )
                all_log_ids.extend(log_ids)
                synced_meals_count += 1
            else:
                unresolved.append(
                    {
                        "barcode": qb.barcode,
                        "grams": qb.grams,
                        "allocations": [a.model_dump() for a in qb.allocations],
                    }
                )

        return 200, json.dumps(
            {
                "synced_meals_count": synced_meals_count,
                "meal_log_ids": all_log_ids,
                "unresolved_barcodes": unresolved,
            }
        )


class NutriVaultHTTPHandler(http.server.BaseHTTPRequestHandler):
    """Standard library HTTP server handler dispatching requests to NutriVaultAPI."""

    api: NutriVaultAPI

    def do_GET(self) -> None:
        self._dispatch("GET")

    def do_POST(self) -> None:
        self._dispatch("POST")

    def do_PUT(self) -> None:
        self._dispatch("PUT")

    def do_DELETE(self) -> None:
        self._dispatch("DELETE")

    def _send_json(self, status_code: int, data: dict[str, Any]) -> None:
        body = json.dumps(data).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _dispatch(self, method: str) -> None:
        cl_header = self.headers.get("Content-Length")
        content_length = 0
        if cl_header is not None:
            try:
                content_length = int(cl_header.strip())
                if content_length < 0:
                    raise ValueError("Negative Content-Length")
            except ValueError:
                self._send_json(400, {"error": "Invalid Content-Length header."})
                return

        from src.vision_pipeline import MAX_IMAGE_SIZE_BYTES

        if content_length > MAX_IMAGE_SIZE_BYTES:
            self._send_json(
                413,
                {
                    "error_code": "ERR_IMAGE_PAYLOAD_TOO_LARGE",
                    "error": (
                        f"Image payload size ({content_length} bytes) exceeds "
                        f"maximum allowable memory limit of {MAX_IMAGE_SIZE_BYTES} bytes."
                    ),
                },
            )
            return

        content_type = self.headers.get("Content-Type", "application/json")
        raw_body = bytearray(self.rfile.read(content_length)) if content_length > 0 else None
        try:
            body = (
                raw_body.decode("utf-8", errors="ignore")
                if raw_body and "multipart" not in content_type
                else None
            )

            status_code, response_body = self.api.handle_request(
                method=method,
                path=self.path,
                body=body,
                raw_body=raw_body,
                content_type=content_type,
            )
        finally:
            if raw_body is not None and "multipart" in content_type:
                raw_body[:] = b"\x00" * len(raw_body)

        clean_path = self.path.split("?")[0]
        if method == "GET" and status_code == 200 and clean_path == "/":
            response_content_type = "text/html; charset=utf-8"
        elif method == "GET" and status_code == 200 and clean_path == "/manifest.json":
            response_content_type = "application/manifest+json"
        elif method == "GET" and status_code == 200 and clean_path == "/sw.js":
            response_content_type = "application/javascript; charset=utf-8"
        else:
            response_content_type = "application/json"

        self.send_response(status_code)
        self.send_header("Content-Type", response_content_type)
        self.send_header("Content-Length", str(len(response_body.encode("utf-8"))))
        self.end_headers()
        self.wfile.write(response_body.encode("utf-8"))

    def log_message(self, format: str, *args: Any) -> None:
        # Suppress noisy standard HTTP access logs
        pass


def run_server(
    host: str = "0.0.0.0",
    port: int = 8080,
    db_path: str = "data/nutrivault.db",
) -> None:
    """Run NutriVault local REST service daemon."""
    import os

    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    init_db(conn, seed_defaults=True)

    api_instance = NutriVaultAPI(conn=conn)

    class CustomHandler(NutriVaultHTTPHandler):
        api = api_instance

    server = http.server.ThreadingHTTPServer((host, port), CustomHandler)
    print(f"NutriVault service running at http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down NutriVault service...")
    finally:
        server.server_close()
        conn.close()


def main(argv: list[str] | None = None) -> None:
    """CLI entrypoint for NutriVault service and VLM setup guidance."""
    import os
    import sys

    args = sys.argv if argv is None else argv

    if "--help" in args:
        print("Usage: python -m src.api [host] [port] [db_path] | --vlm-guide")
        sys.exit(0)

    if "--vlm-guide" in args:
        print(format_vlm_setup_guide())
        sys.exit(0)

    host_arg = os.environ.get("NUTRIVAULT_HOST", "0.0.0.0")
    port_arg = int(os.environ.get("NUTRIVAULT_PORT", "8080"))
    db_arg = os.environ.get("NUTRIVAULT_DB", "data/nutrivault.db")

    non_flag_args = [a for a in args[1:] if not a.startswith("-")]
    if len(non_flag_args) > 0:
        host_arg = non_flag_args[0]
    if len(non_flag_args) > 1:
        port_arg = int(non_flag_args[1])
    if len(non_flag_args) > 2:
        db_arg = non_flag_args[2]

    run_server(host=host_arg, port=port_arg, db_path=db_arg)


if __name__ == "__main__":
    main()

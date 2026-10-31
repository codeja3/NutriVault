"""Local REST API router and request dispatcher for NutriVault services."""

import json
import re
import sqlite3
from dataclasses import asdict
from typing import Any

from src.advisory import (
    ClinicalAdvisoryViolationError,
    generate_athletic_targets,
)
from src.db import ProfileRepository
from src.hardware import (
    HardwareProfile,
    probe_hardware,
    resolve_model_tier,
)


class NutriVaultAPI:
    """Dispatches and handles REST API requests strictly in-process offline."""

    def __init__(
        self,
        conn: sqlite3.Connection,
        hardware_profile: HardwareProfile | None = None,
    ):
        self.conn = conn
        self.hardware_profile = hardware_profile or probe_hardware()
        self.active_tier_ceiling = resolve_model_tier(self.hardware_profile)
        self.repo = ProfileRepository(conn)

    def handle_request(
        self,
        method: str,
        path: str,
        body: str | None = None,
        content_type: str = "application/json",
    ) -> tuple[int, str]:
        """Route request and return (status_code, response_body_json)."""
        method = method.upper()

        try:
            # 1. GET /api/v1/hardware
            if method == "GET" and path == "/api/v1/hardware":
                return self._handle_get_hardware()

            # 2. GET /api/v1/profiles
            if method == "GET" and path == "/api/v1/profiles":
                return self._handle_list_profiles()

            # 3. POST /api/v1/profiles
            if method == "POST" and path == "/api/v1/profiles":
                data = json.loads(body or "{}")
                return self._handle_create_profile(data)

            # 4. PUT /api/v1/profiles/{id}/targets
            target_match = re.match(r"^/api/v1/profiles/([^/]+)/targets$", path)
            if method == "PUT" and target_match:
                profile_id = target_match.group(1)
                data = json.loads(body or "{}")
                return self._handle_set_targets(profile_id, data)

            # 5. POST /api/v1/advisory/fitness-targets
            if method == "POST" and path == "/api/v1/advisory/fitness-targets":
                data = json.loads(body or "{}")
                return self._handle_advisory_targets(data)

            return 404, json.dumps({"error": f"Endpoint not found: {method} {path}"})

        except ClinicalAdvisoryViolationError as e:
            return 403, json.dumps(
                {"error_code": e.error_code, "error": str(e), "disclaimer": e.disclaimer}
            )
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

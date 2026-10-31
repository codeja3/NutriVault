import json
import sqlite3

import pytest

from src.api import NutriVaultAPI
from src.db import init_db
from src.hardware import AcceleratorType, HardwareProfile


@pytest.fixture
def api_instance():
    """Create in-memory SQLite NutriVaultAPI instance with hardware mock."""
    conn = sqlite3.connect(":memory:")
    init_db(conn)

    mock_profile = HardwareProfile(
        os_name="Darwin",
        total_ram_gb=16.0,
        accelerator=AcceleratorType.APPLE_SILICON,
        vram_gb=16.0,
        cpu_cores=8,
    )
    return NutriVaultAPI(conn=conn, hardware_profile=mock_profile)


def test_api_get_hardware(api_instance):
    """GET /api/v1/hardware returns hardware specs and model tier ceiling."""
    status, body = api_instance.handle_request(method="GET", path="/api/v1/hardware")
    assert status == 200
    data = json.loads(body)
    assert data["os_name"] == "Darwin"
    assert data["total_ram_gb"] == 16.0
    assert data["accelerator"] == "apple_silicon"
    assert data["active_tier_ceiling"] == "tier_2_mid"


def test_api_profiles_crud(api_instance):
    """POST /api/v1/profiles and GET /api/v1/profiles."""
    # 1. Create Profile
    create_payload = {
        "name": "Jordan",
        "birth_date": "1994-03-20",
        "profile_type": "standard",
        "condition_notes": None,
    }
    status, body = api_instance.handle_request(
        method="POST",
        path="/api/v1/profiles",
        body=json.dumps(create_payload),
    )
    assert status == 201
    profile_data = json.loads(body)
    assert profile_data["name"] == "Jordan"
    profile_id = profile_data["id"]

    # 2. List Profiles
    status_list, body_list = api_instance.handle_request(method="GET", path="/api/v1/profiles")
    assert status_list == 200
    profiles = json.loads(body_list)
    assert len(profiles) == 1
    assert profiles[0]["id"] == profile_id


def test_api_put_target_envelope(api_instance):
    """PUT /api/v1/profiles/{id}/targets updates active target envelope."""
    # Create profile
    _, p_body = api_instance.handle_request(
        method="POST",
        path="/api/v1/profiles",
        body=json.dumps({"name": "Sam", "profile_type": "standard"}),
    )
    profile_id = json.loads(p_body)["id"]

    # Update targets
    target_payload = {
        "calories_target": 2300,
        "protein_g_target": 160.0,
        "carbs_g_target": 250.0,
        "fat_g_target": 70.0,
        "fiber_g_target": 35.0,
        "micronutrients": {"calcium_mg": 1000.0},
    }
    status, body = api_instance.handle_request(
        method="PUT",
        path=f"/api/v1/profiles/{profile_id}/targets",
        body=json.dumps(target_payload),
    )
    assert status == 200
    env_data = json.loads(body)
    assert env_data["calories_target"] == 2300
    assert env_data["profile_id"] == profile_id
    assert env_data["micronutrients"]["calcium_mg"] == 1000.0


def test_api_advisory_fitness_targets_success(api_instance):
    """POST /api/v1/advisory/fitness-targets generates targets and advisory wire."""
    # Create athletic profile
    _, p_body = api_instance.handle_request(
        method="POST",
        path="/api/v1/profiles",
        body=json.dumps({"name": "Runner", "profile_type": "athletic"}),
    )
    profile_id = json.loads(p_body)["id"]

    payload = {
        "profile_id": profile_id,
        "athletic_goal": "endurance",
        "weight_kg": 65.0,
    }
    status, body = api_instance.handle_request(
        method="POST",
        path="/api/v1/advisory/fitness-targets",
        body=json.dumps(payload),
    )
    assert status == 200
    resp_data = json.loads(body)
    assert resp_data["calories_target"] > 0
    assert "certified fitness trainer" in resp_data["advisory_wire"]
    assert "search.brave.com/ask" in resp_data["advisory_wire"]
    assert resp_data["requires_acknowledgment"] is True


def test_api_advisory_clinical_hard_lock(api_instance):
    """POST /api/v1/advisory/fitness-targets on chronic condition returns HTTP 403."""
    # Create chronic condition profile
    _, p_body = api_instance.handle_request(
        method="POST",
        path="/api/v1/profiles",
        body=json.dumps({"name": "Charlie", "profile_type": "chronic_condition"}),
    )
    profile_id = json.loads(p_body)["id"]

    payload = {
        "profile_id": profile_id,
        "athletic_goal": "hypertrophy",
        "weight_kg": 75.0,
    }
    status, body = api_instance.handle_request(
        method="POST",
        path="/api/v1/advisory/fitness-targets",
        body=json.dumps(payload),
    )
    assert status == 403
    err_data = json.loads(body)
    assert err_data["error_code"] == "ERR_CLINICAL_AI_RESTRICTED"
    assert "Nutritional goals for chronic conditions must be established" in err_data["error"]

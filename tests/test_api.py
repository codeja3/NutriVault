import json
import sqlite3

import pytest

from src.api import NutriVaultAPI
from src.db import init_db
from src.hardware import AcceleratorType, HardwareProfile
from src.vision_pipeline import ExtractedCandidateItem


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

    status_list, body_list = api_instance.handle_request(method="GET", path="/api/v1/profiles")
    assert status_list == 200
    profiles = json.loads(body_list)
    assert len(profiles) == 1
    assert profiles[0]["id"] == profile_id


def test_api_put_target_envelope(api_instance):
    """PUT /api/v1/profiles/{id}/targets updates active target envelope."""
    _, p_body = api_instance.handle_request(
        method="POST",
        path="/api/v1/profiles",
        body=json.dumps({"name": "Sam", "profile_type": "standard"}),
    )
    profile_id = json.loads(p_body)["id"]

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


def test_api_put_target_envelope_unknown_profile(api_instance):
    """PUT /api/v1/profiles/{id}/targets with unknown profile returns 404."""
    status, body = api_instance.handle_request(
        method="PUT",
        path="/api/v1/profiles/unknown-uuid/targets",
        body=json.dumps(
            {
                "calories_target": 2000,
                "protein_g_target": 150.0,
                "carbs_g_target": 200.0,
                "fat_g_target": 65.0,
                "fiber_g_target": 30.0,
            }
        ),
    )
    assert status == 404
    data = json.loads(body)
    assert "not found" in data["error"].lower()


def test_api_put_target_envelope_ai_chronic_condition_restriction(api_instance):
    """PUT /api/v1/profiles/{id}/targets rejects AI targets on chronic condition profiles (403)."""
    _, p_body = api_instance.handle_request(
        method="POST",
        path="/api/v1/profiles",
        body=json.dumps({"name": "Patient", "profile_type": "chronic_condition"}),
    )
    p_id = json.loads(p_body)["id"]

    target_payload = {
        "calories_target": 2100,
        "protein_g_target": 120.0,
        "carbs_g_target": 220.0,
        "fat_g_target": 60.0,
        "fiber_g_target": 25.0,
        "is_ai_generated": True,
    }
    status, body = api_instance.handle_request(
        method="PUT",
        path=f"/api/v1/profiles/{p_id}/targets",
        body=json.dumps(target_payload),
    )
    assert status == 403
    err_data = json.loads(body)
    assert err_data["error_code"] == "ERR_CLINICAL_AI_RESTRICTED"


def test_api_put_target_envelope_ai_athletic_acknowledgment(api_instance):
    """Athletic AI-generated target commits require acknowledged: true."""
    _, p_body = api_instance.handle_request(
        method="POST",
        path="/api/v1/profiles",
        body=json.dumps({"name": "Athlete1", "profile_type": "athletic"}),
    )
    p_id = json.loads(p_body)["id"]

    unack_payload = {
        "calories_target": 2800,
        "protein_g_target": 180.0,
        "carbs_g_target": 350.0,
        "fat_g_target": 70.0,
        "fiber_g_target": 40.0,
        "is_ai_generated": True,
        "acknowledged": False,
    }
    status, body = api_instance.handle_request(
        method="PUT",
        path=f"/api/v1/profiles/{p_id}/targets",
        body=json.dumps(unack_payload),
    )
    assert status == 400
    assert "acknowledgment" in json.loads(body)["error"].lower()

    # With acknowledged: true, commit succeeds
    ack_payload = {**unack_payload, "acknowledged": True}
    status_ok, body_ok = api_instance.handle_request(
        method="PUT",
        path=f"/api/v1/profiles/{p_id}/targets",
        body=json.dumps(ack_payload),
    )
    assert status_ok == 200
    assert json.loads(body_ok)["calories_target"] == 2800


def test_api_missing_fields_return_400_bad_request(api_instance):
    """Missing required keys in JSON body must return 400 Bad Request, not 404."""
    # POST /api/v1/profiles with empty dict
    status, body = api_instance.handle_request(
        method="POST",
        path="/api/v1/profiles",
        body=json.dumps({}),
    )
    assert status == 400
    assert "field required" in body.lower() or "missing" in body.lower() or "error" in body.lower()

    # POST /api/v1/meals/commit with missing fields
    status2, body2 = api_instance.handle_request(
        method="POST",
        path="/api/v1/meals/commit",
        body=json.dumps({"dish_name": "Incomplete"}),
    )
    assert status2 == 400


def test_api_advisory_fitness_targets_success(api_instance):
    """POST /api/v1/advisory/fitness-targets generates targets and advisory wire."""
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


def test_api_parse_image(api_instance, mocker):
    """POST /api/v1/meals/parse-image parses image via in-memory VLM and grounds candidates."""
    cursor = api_instance.conn.cursor()
    cursor.execute(
        """
        INSERT INTO usda_foods (
            fdc_id, description, food_category, preparation_state,
            calories_per_100g, protein_g_per_100g, carbs_g_per_100g,
            fat_g_per_100g, fiber_g_per_100g, micros_per_100g_json
        ) VALUES (
            1001, 'Rice, brown, long-grain, cooked', 'Grains', 'cooked',
            112.0, 2.3, 23.5, 0.8, 1.6, '{}'
        );
        """
    )
    api_instance.conn.commit()

    mock_candidates = [ExtractedCandidateItem(item_name="brown rice", estimated_grams=200.0)]
    mocker.patch.object(api_instance.vlm_client, "parse_meal_image", return_value=mock_candidates)

    image_bytes = b"fake_png_header_and_data"
    status, body = api_instance.handle_request(
        method="POST",
        path="/api/v1/meals/parse-image",
        raw_body=image_bytes,
        content_type="multipart/form-data",
    )
    assert status == 200
    data = json.loads(body)
    assert "items" in data
    assert len(data["items"]) == 1
    item = data["items"][0]
    assert item["item_name"] == "brown rice"
    assert item["matched_fdc_id"] == 1001
    assert item["nutrients"]["calories"] == 224.0
    assert item["nutrients"]["protein_g"] == 4.6


def test_api_commit_meal(api_instance):
    """POST /api/v1/meals/commit records dish and fractional allocations across profiles."""
    _, p1_res = api_instance.handle_request(
        "POST", "/api/v1/profiles", json.dumps({"name": "A", "profile_type": "standard"})
    )
    _, p2_res = api_instance.handle_request(
        "POST", "/api/v1/profiles", json.dumps({"name": "B", "profile_type": "standard"})
    )
    p1_id = json.loads(p1_res)["id"]
    p2_id = json.loads(p2_res)["id"]

    commit_payload = {
        "dish_name": "Shared Salad",
        "ingredients": [
            {
                "item_name": "spinach",
                "fdc_id": 9999,
                "grams": 200.0,
                "calories": 50.0,
                "protein_g": 6.0,
                "carbs_g": 8.0,
                "fat_g": 0.8,
                "fiber_g": 4.0,
                "micros": {},
            }
        ],
        "allocations": [
            {"profile_id": p1_id, "fraction": 0.6, "meal_type": "lunch"},
            {"profile_id": p2_id, "fraction": 0.4, "meal_type": "lunch"},
        ],
    }

    status, body = api_instance.handle_request(
        method="POST",
        path="/api/v1/meals/commit",
        body=json.dumps(commit_payload),
    )
    assert status == 201
    res_data = json.loads(body)
    assert res_data["dish_id"] is not None
    assert len(res_data["meal_log_ids"]) == 2


def test_api_commit_meal_invalid_portion_sum(api_instance):
    """POST /api/v1/meals/commit with invalid portion sum returns ERR_INVALID_PORTION_SUM."""
    commit_payload = {
        "dish_name": "Shared Salad",
        "ingredients": [
            {
                "item_name": "spinach",
                "fdc_id": 9999,
                "grams": 200.0,
                "calories": 50.0,
                "protein_g": 6.0,
                "carbs_g": 8.0,
                "fat_g": 0.8,
                "fiber_g": 4.0,
                "micros": {},
            }
        ],
        "allocations": [
            {"profile_id": "dummy_p1", "fraction": 0.8, "meal_type": "lunch"},
            {"profile_id": "dummy_p2", "fraction": 0.5, "meal_type": "lunch"},
        ],
    }

    status, body = api_instance.handle_request(
        method="POST",
        path="/api/v1/meals/commit",
        body=json.dumps(commit_payload),
    )
    assert status == 400
    res_data = json.loads(body)
    assert res_data["error_code"] == "ERR_INVALID_PORTION_SUM"

    # Must NOT leave an orphaned dish in the database
    cursor = api_instance.conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM dishes;")
    assert cursor.fetchone()[0] == 0


def test_api_parse_image_multipart_framing(api_instance, mocker):
    """POST /api/v1/meals/parse-image must strip multipart boundary framing to raw bytes."""
    boundary = "----WebKitFormBoundaryXyZ123"
    actual_image_data = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR_real_image_bytes"
    multipart_body = (
        (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="image"; filename="meal.png"\r\n'
            f"Content-Type: image/png\r\n\r\n"
        ).encode("utf-8")
        + actual_image_data
        + f"\r\n--{boundary}--\r\n".encode("utf-8")
    )

    captured_bytes = None

    def mock_parse(buf):
        nonlocal captured_bytes
        captured_bytes = buf._stream.getvalue()
        return [ExtractedCandidateItem(item_name="brown rice", estimated_grams=150.0)]

    mocker.patch.object(api_instance.vlm_client, "parse_meal_image", side_effect=mock_parse)

    status, body = api_instance.handle_request(
        method="POST",
        path="/api/v1/meals/parse-image",
        raw_body=multipart_body,
        content_type=f"multipart/form-data; boundary={boundary}",
    )
    assert status == 200
    # Captured image bytes in memory must be the raw image bytes without multipart headers
    assert captured_bytes == actual_image_data


def test_api_get_rolling_analytics(api_instance):
    """GET /api/v1/analytics/rolling returns 7-day EMA, deltas, and chrononutrition windows."""
    _, p_res = api_instance.handle_request(
        "POST", "/api/v1/profiles", json.dumps({"name": "Athlete", "profile_type": "standard"})
    )
    p_id = json.loads(p_res)["id"]

    cursor = api_instance.conn.cursor()
    cursor.execute(
        """
        INSERT INTO meal_logs (
            id, profile_id, meal_type, portion_fraction,
            calories, protein_g, carbs_g, fat_g, fiber_g, logged_at
        ) VALUES (
            'm_anal', ?, 'dinner', 1.0, 700.0, 40.0, 80.0, 20.0, 10.0, '2026-10-31 18:00:00'
        );
        """,
        (p_id,),
    )
    api_instance.conn.commit()

    status, body = api_instance.handle_request(
        method="GET",
        path=f"/api/v1/analytics/rolling?profile_id={p_id}&days=7",
    )
    assert status == 200
    res_data = json.loads(body)
    assert res_data["profile_id"] == p_id
    assert res_data["calories_ema"] == 700.0
    assert "feeding_intervals" in res_data
    assert len(res_data["feeding_intervals"]) == 1
    assert res_data["feeding_intervals"][0]["date"] == "2026-10-31"


def test_api_internal_server_error_sanitization(api_instance, mocker):
    """500 Internal Server Error must not leak raw exceptions or database internals."""
    err = sqlite3.OperationalError("syntax error in SQL: table secret_users not found")
    mocker.patch.object(api_instance.repo, "list_profiles", side_effect=err)
    status, body = api_instance.handle_request(method="GET", path="/api/v1/profiles")
    assert status == 500
    data = json.loads(body)
    assert data == {"error": "Internal server error."}
    assert "secret_users" not in body
    assert "syntax error" not in body


def test_http_handler_dispatch(api_instance):
    """NutriVaultHTTPHandler properly handles incoming HTTP requests via handle_request."""
    import io
    from unittest.mock import Mock

    from src.api import NutriVaultHTTPHandler

    handler = NutriVaultHTTPHandler.__new__(NutriVaultHTTPHandler)
    handler.api = api_instance
    handler.command = "GET"
    handler.path = "/api/v1/hardware"
    handler.headers = {"Content-Length": "0"}
    handler.rfile = io.BytesIO()
    handler.wfile = io.BytesIO()
    handler.request_version = "HTTP/1.1"

    handler.send_response = Mock()
    handler.send_header = Mock()
    handler.end_headers = Mock()

    handler.do_GET()

    handler.send_response.assert_called_once_with(200)
    output = handler.wfile.getvalue().decode("utf-8")
    assert "active_tier_ceiling" in output

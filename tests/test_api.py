import json
import sqlite3

import pytest

from src.api import NutriVaultAPI, NutriVaultHTTPHandler
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


def test_api_parse_image_zeroes_mutable_bytearray_input(api_instance, mocker):
    """Passing a mutable bytearray to parse-image must zero out the buffer in memory upon exit."""
    mocker.patch.object(
        api_instance.vlm_client,
        "parse_meal_image",
        return_value=[ExtractedCandidateItem(item_name="rice", estimated_grams=100.0)],
    )
    raw_payload = bytearray(b"sensitive_image_bytes_to_be_zeroed_1234567890")
    orig_len = len(raw_payload)

    status, _ = api_instance.handle_request(
        method="POST",
        path="/api/v1/meals/parse-image",
        raw_body=raw_payload,
        content_type="image/jpeg",
    )
    assert status == 200
    # The bytearray in memory must be explicitly overwritten with 0x00
    assert bytes(raw_payload) == b"\x00" * orig_len


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


def test_http_handler_malformed_content_length_returns_400(api_instance):
    """NutriVaultHTTPHandler rejects malformed Content-Length header with HTTP 400."""
    import io
    from unittest.mock import Mock

    from src.api import NutriVaultHTTPHandler

    handler = NutriVaultHTTPHandler.__new__(NutriVaultHTTPHandler)
    handler.api = api_instance
    handler.command = "POST"
    handler.path = "/api/v1/profiles"
    handler.headers = {"Content-Length": "invalid_number"}
    handler.rfile = io.BytesIO(b"some_body")
    handler.wfile = io.BytesIO()
    handler.request_version = "HTTP/1.1"

    handler.send_response = Mock()
    handler.send_header = Mock()
    handler.end_headers = Mock()

    handler.do_POST()

    handler.send_response.assert_called_once_with(400)
    output = json.loads(handler.wfile.getvalue().decode("utf-8"))
    assert "content-length" in output["error"].lower()


def test_http_handler_oversized_content_length_returns_413_without_reading(api_instance):
    """NutriVaultHTTPHandler rejects Content-Length > 15 MB with 413 without reading payload."""
    import io
    from unittest.mock import Mock

    from src.api import NutriVaultHTTPHandler

    handler = NutriVaultHTTPHandler.__new__(NutriVaultHTTPHandler)
    handler.api = api_instance
    handler.command = "POST"
    handler.path = "/api/v1/meals/parse-image"
    # 50 MB declared Content-Length
    handler.headers = {
        "Content-Length": "52428800",
        "Content-Type": "multipart/form-data; boundary=xyz",
    }
    rfile_mock = Mock()
    handler.rfile = rfile_mock
    handler.wfile = io.BytesIO()
    handler.request_version = "HTTP/1.1"

    handler.send_response = Mock()
    handler.send_header = Mock()
    handler.end_headers = Mock()

    handler.do_POST()

    handler.send_response.assert_called_once_with(413)
    # Ensure server never attempted to allocate 50 MB by calling rfile.read(...)
    rfile_mock.read.assert_not_called()
    output = json.loads(handler.wfile.getvalue().decode("utf-8"))
    assert output["error_code"] == "ERR_IMAGE_PAYLOAD_TOO_LARGE"


def test_api_thread_safety_lock(api_instance):
    """NutriVaultAPI must possess a threading lock to protect SQLite connections."""
    import threading

    assert hasattr(api_instance, "_lock")
    assert isinstance(api_instance._lock, type(threading.Lock()))


def test_api_create_profile_invalid_type_returns_400(api_instance):
    """POST /api/v1/profiles with invalid profile_type returns 400 Bad Request."""
    status, body = api_instance.handle_request(
        method="POST",
        path="/api/v1/profiles",
        body=json.dumps({"name": "Invalid", "profile_type": "alien_profile"}),
    )
    assert status == 400
    assert "profile_type" in body.lower() or "input should be" in body.lower()


def test_api_commit_meal_invalid_meal_type_returns_400(api_instance):
    """POST /api/v1/meals/commit with invalid meal_type returns 400 Bad Request."""
    _, p_body = api_instance.handle_request(
        "POST", "/api/v1/profiles", json.dumps({"name": "User", "profile_type": "standard"})
    )
    p_id = json.loads(p_body)["id"]

    payload = {
        "dish_name": "Midnight Snack",
        "ingredients": [
            {
                "item_name": "apple",
                "fdc_id": 100,
                "grams": 100.0,
                "calories": 50.0,
                "protein_g": 0.5,
                "carbs_g": 12.0,
                "fat_g": 0.2,
                "fiber_g": 2.0,
                "micros": {},
            }
        ],
        "allocations": [{"profile_id": p_id, "fraction": 1.0, "meal_type": "invalid_meal_type"}],
    }
    status, body = api_instance.handle_request(
        method="POST",
        path="/api/v1/meals/commit",
        body=json.dumps(payload),
    )
    assert status == 400


def test_api_integrity_error_mapped_to_400_not_500(api_instance, mocker):
    """Database IntegrityError must return HTTP 400 Bad Request instead of HTTP 500."""
    mocker.patch.object(
        api_instance.repo,
        "create_profile",
        side_effect=sqlite3.IntegrityError("CHECK constraint failed: profiles"),
    )
    status, body = api_instance.handle_request(
        method="POST",
        path="/api/v1/profiles",
        body=json.dumps({"name": "Test", "profile_type": "standard"}),
    )
    assert status == 400
    data = json.loads(body)
    assert "integrity violation" in data["error"].lower()


def test_api_analytics_negative_or_zero_days_returns_400(api_instance):
    """GET /api/v1/analytics/rolling with days <= 0 must return HTTP 400 Bad Request."""
    _, p_body = api_instance.handle_request(
        "POST", "/api/v1/profiles", json.dumps({"name": "User", "profile_type": "standard"})
    )
    p_id = json.loads(p_body)["id"]

    status1, body1 = api_instance.handle_request(
        method="GET", path=f"/api/v1/analytics/rolling?profile_id={p_id}&days=0"
    )
    assert status1 == 400
    assert "days" in json.loads(body1)["error"].lower()

    status2, body2 = api_instance.handle_request(
        method="GET", path=f"/api/v1/analytics/rolling?profile_id={p_id}&days=-5"
    )
    assert status2 == 400
    assert "days" in json.loads(body2)["error"].lower()


def test_api_commit_meal_invalid_timestamp_returns_400(api_instance):
    """POST /api/v1/meals/commit with malformed ISO-8601 logged_at returns HTTP 400."""
    _, p_body = api_instance.handle_request(
        "POST", "/api/v1/profiles", json.dumps({"name": "User", "profile_type": "standard"})
    )
    p_id = json.loads(p_body)["id"]

    payload = {
        "dish_name": "Lunch Dish",
        "ingredients": [
            {
                "item_name": "rice",
                "fdc_id": 100,
                "grams": 100.0,
                "calories": 100.0,
                "protein_g": 2.0,
                "carbs_g": 20.0,
                "fat_g": 1.0,
                "fiber_g": 1.0,
                "micros": {},
            }
        ],
        "allocations": [
            {
                "profile_id": p_id,
                "fraction": 1.0,
                "meal_type": "lunch",
                "logged_at": "invalid-datetime-string",
            }
        ],
    }
    status, body = api_instance.handle_request(
        method="POST",
        path="/api/v1/meals/commit",
        body=json.dumps(payload),
    )
    assert status == 400
    err = json.loads(body)["error"].lower()
    assert "timestamp" in err or "iso" in err


def test_api_rejects_empty_names_and_empty_ingredient_lists(api_instance):
    """Empty strings for profile name/dish name or empty ingredients list must return HTTP 400."""
    # 1. Blank profile name
    status1, _ = api_instance.handle_request(
        method="POST",
        path="/api/v1/profiles",
        body=json.dumps({"name": "   ", "profile_type": "standard"}),
    )
    assert status1 == 400

    # Create valid profile for meal commit tests
    _, p_body = api_instance.handle_request(
        "POST", "/api/v1/profiles", json.dumps({"name": "Valid", "profile_type": "standard"})
    )
    p_id = json.loads(p_body)["id"]

    # 2. Empty ingredients list
    status2, _ = api_instance.handle_request(
        method="POST",
        path="/api/v1/meals/commit",
        body=json.dumps(
            {
                "dish_name": "Empty Dish",
                "ingredients": [],
                "allocations": [{"profile_id": p_id, "fraction": 1.0}],
            }
        ),
    )
    assert status2 == 400

    # 3. Blank dish_name
    status3, _ = api_instance.handle_request(
        method="POST",
        path="/api/v1/meals/commit",
        body=json.dumps(
            {
                "dish_name": "   ",
                "ingredients": [
                    {
                        "item_name": "rice",
                        "fdc_id": 100,
                        "grams": 100.0,
                        "calories": 100.0,
                        "protein_g": 2.0,
                        "carbs_g": 20.0,
                        "fat_g": 1.0,
                        "fiber_g": 1.0,
                    }
                ],
                "allocations": [{"profile_id": p_id, "fraction": 1.0}],
            }
        ),
    )
    assert status3 == 400


def test_api_rolling_analytics_bounds_feeding_intervals_to_days(api_instance):
    """GET /api/v1/analytics/rolling?days=2 bounds feeding_intervals to the most recent 2 days."""
    _, p_res = api_instance.handle_request(
        "POST", "/api/v1/profiles", json.dumps({"name": "WindowUser", "profile_type": "standard"})
    )
    p_id = json.loads(p_res)["id"]

    cursor = api_instance.conn.cursor()
    for day in (25, 26, 27, 28):
        cursor.execute(
            """
            INSERT INTO meal_logs (
                id, profile_id, meal_type, portion_fraction,
                calories, protein_g, carbs_g, fat_g, fiber_g, logged_at
            ) VALUES (?, ?, 'dinner', 1.0, 600.0, 30.0, 60.0, 20.0, 8.0, ?);
            """,
            (f"w_{day}", p_id, f"2026-10-{day} 18:00:00"),
        )
    api_instance.conn.commit()

    status, body = api_instance.handle_request(
        method="GET",
        path=f"/api/v1/analytics/rolling?profile_id={p_id}&days=2",
    )
    assert status == 200
    res_data = json.loads(body)
    assert len(res_data["feeding_intervals"]) == 2
    assert [i["date"] for i in res_data["feeding_intervals"]] == ["2026-10-27", "2026-10-28"]


def test_api_get_hardware_includes_recommended_models(api_instance):
    """GET /api/v1/hardware should include recommended_models list."""
    status, body = api_instance.handle_request("GET", "/api/v1/hardware")
    assert status == 200
    data = json.loads(body)
    assert "recommended_models" in data
    assert isinstance(data["recommended_models"], list)
    assert len(data["recommended_models"]) > 0


def test_api_get_hardware_includes_predefined_vlm_and_command(api_instance):
    """GET /api/v1/hardware should include default_vlm spec and managed_vlm_command."""
    status, body = api_instance.handle_request("GET", "/api/v1/hardware")
    assert status == 200
    data = json.loads(body)
    assert "default_vlm" in data
    assert "managed_vlm_command" in data
    vlm = data["default_vlm"]
    assert "name" in vlm
    assert "hf_repo" in vlm
    assert "approx_size_mb" in vlm
    cmd = data["managed_vlm_command"]
    assert "--hf-repo" in cmd


def test_api_search_foods_valid(api_instance):
    """GET /api/v1/foods/search should return ranked USDA matches scaled to grams."""
    from src.db import seed_default_usda_foods

    seed_default_usda_foods(api_instance.conn)

    status, body = api_instance.handle_request(
        "GET", "/api/v1/foods/search?q=brown+rice&grams=150&limit=5"
    )
    assert status == 200
    data = json.loads(body)
    assert "results" in data
    results = data["results"]
    assert len(results) >= 1
    top = results[0]
    assert "fdc_id" in top
    assert "brown" in top["description"].lower() or "rice" in top["description"].lower()
    assert "preparation_state" in top
    assert "confidence_score" in top
    assert "nutrients" in top
    nutrients = top["nutrients"]
    assert nutrients["grams"] == 150.0
    assert nutrients["calories"] > 0
    assert isinstance(nutrients["micronutrients"], dict)


def test_api_search_foods_validation_errors(api_instance):
    """GET /api/v1/foods/search must return 400 on invalid or missing query params."""
    # Missing q
    status1, _ = api_instance.handle_request("GET", "/api/v1/foods/search")
    assert status1 == 400

    # Blank q
    status2, _ = api_instance.handle_request("GET", "/api/v1/foods/search?q=%20%20")
    assert status2 == 400

    # Negative grams
    status3, _ = api_instance.handle_request("GET", "/api/v1/foods/search?q=rice&grams=-50")
    assert status3 == 400

    # Zero grams
    status4, _ = api_instance.handle_request("GET", "/api/v1/foods/search?q=rice&grams=0")
    assert status4 == 400

    # Non-numeric grams
    status5, _ = api_instance.handle_request("GET", "/api/v1/foods/search?q=rice&grams=abc")
    assert status5 == 400

    # Limit < 1
    status6, _ = api_instance.handle_request("GET", "/api/v1/foods/search?q=rice&limit=0")
    assert status6 == 400

    # Limit > 50
    status7, _ = api_instance.handle_request("GET", "/api/v1/foods/search?q=rice&limit=51")
    assert status7 == 400

    # Non-integer limit
    status8, _ = api_instance.handle_request("GET", "/api/v1/foods/search?q=rice&limit=xyz")
    assert status8 == 400


def test_api_serves_pwa_html_with_zero_cdn_links(api_instance):
    """GET / must return 200 OK with self-contained HTML and zero external scripts/styles."""
    status, body = api_instance.handle_request("GET", "/")
    assert status == 200
    assert "<!DOCTYPE html>" in body or "<html" in body.lower()
    assert "NutriVault" in body
    # Strict Zero-WAN / Zero-CDN assertion: no external scripts, styles, or fonts
    assert '<script src="http' not in body.lower()
    assert '<link rel="stylesheet" href="http' not in body.lower()


def test_api_serves_pwa_manifest(api_instance):
    """GET /manifest.json must return 200 OK with valid PWA manifest JSON."""
    status, body = api_instance.handle_request("GET", "/manifest.json")
    assert status == 200
    data = json.loads(body)
    assert data["name"] == "NutriVault"
    assert data["start_url"] == "/"
    assert data["display"] == "standalone"


def test_http_handler_content_types(api_instance):
    """NutriVaultHTTPHandler must set correct Content-Type for HTML, manifest, and API."""
    import io
    from unittest.mock import Mock

    handler = NutriVaultHTTPHandler.__new__(NutriVaultHTTPHandler)
    handler.api = api_instance

    recorded_headers = {}

    def mock_send_header(name, val):
        recorded_headers[name] = val

    handler.send_response = Mock()
    handler.send_header = Mock(side_effect=mock_send_header)
    handler.end_headers = Mock()
    handler.headers = {}
    handler.request_version = "HTTP/1.1"

    # 1. GET /
    handler.path = "/"
    handler.wfile = io.BytesIO()
    handler.do_GET()
    assert recorded_headers.get("Content-Type") == "text/html; charset=utf-8"

    # 2. GET /manifest.json
    handler.path = "/manifest.json"
    handler.wfile = io.BytesIO()
    handler.do_GET()
    assert recorded_headers.get("Content-Type") == "application/manifest+json"

    # 3. GET /api/v1/hardware
    handler.path = "/api/v1/hardware"
    handler.wfile = io.BytesIO()
    handler.do_GET()
    assert recorded_headers.get("Content-Type") == "application/json"


def test_cli_vlm_guide_flag(capsys):
    """Running CLI with --vlm-guide must output VLM setup instructions and exit 0."""
    from src.api import main

    with pytest.raises(SystemExit) as exc_info:
        main(["src.api", "--vlm-guide"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "NutriVault Local VLM Setup Guide" in captured.out
    assert "llama-server" in captured.out
    assert "--port 8081" in captured.out


def test_pwa_js_schema_alignment_and_xss_safety(api_instance):
    """PWA JS in GET / must match backend response keys and avoid unsafe inline JSON onclick."""
    status, html = api_instance.handle_request("GET", "/")
    assert status == 200

    # 1. commitBatchMeal uses data.meal_log_ids, not data.meal_logs
    assert "data.meal_log_ids" in html
    assert "data.meal_logs." not in html

    # 2. loadAnalytics uses top-level calories_ema, protein_g_ema, etc., not data.rolling_ema
    assert "data.calories_ema" in html
    assert "data.protein_g_ema" in html
    assert "data.carbs_g_ema" in html
    assert "data.fat_g_ema" in html
    assert "data.fiber_g_ema" in html
    assert "data.rolling_ema" not in html

    # 3. parseMealPhoto uses data.items, not data.candidates / c.resolved_food
    assert "data.items" in html
    assert "data.candidates" not in html
    assert "resolved_food" not in html

    # 4. Athletic AI target tracking uses state.isAiGeneratedDraft
    assert "isAiGeneratedDraft" in html
    assert "is_ai_generated: isAthletic && ack" not in html

    # 5. Search result addition uses index lookup and HTML escaping instead of inline JSON.stringify
    assert "addSearchItemByIndex(" in html
    assert "escapeHtml(" in html
    assert "addSearchItemToDraft(${JSON.stringify" not in html

    # 6. updateDraftGrams scales micronutrients (ing.micros)
    assert "ing.micros" in html


def test_http_handler_non_200_on_root_returns_json_content_type(api_instance):
    """POST / returns 404 JSON error and must have Content-Type: application/json, not text/html."""
    import io
    from unittest.mock import Mock

    from src.api import NutriVaultHTTPHandler

    handler = NutriVaultHTTPHandler.__new__(NutriVaultHTTPHandler)
    handler.api = api_instance

    recorded_headers = {}

    def mock_send_header(name, val):
        recorded_headers[name] = val

    handler.send_response = Mock()
    handler.send_header = Mock(side_effect=mock_send_header)
    handler.end_headers = Mock()
    handler.headers = {"Content-Length": "0"}
    handler.rfile = io.BytesIO()
    handler.wfile = io.BytesIO()
    handler.request_version = "HTTP/1.1"
    handler.path = "/"

    handler.do_POST()
    handler.send_response.assert_called_once_with(404)
    assert recorded_headers.get("Content-Type") == "application/json"

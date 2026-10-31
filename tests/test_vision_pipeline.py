import pytest

from src.vision_pipeline import (
    EphemeralImageBuffer,
    ExtractedCandidateItem,
    ImagePayloadTooLargeError,
    VLMClient,
    VLMInvalidJSONError,
    VLMUnavailableError,
    clean_vlm_json_output,
)


def test_ephemeral_image_buffer_lifecycle():
    """Verify EphemeralImageBuffer holds bytes in memory, converts to base64, and purges."""
    fake_image_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + b"dummy_image_content" * 100

    buffer = EphemeralImageBuffer.from_bytes(fake_image_bytes, max_size_bytes=1024 * 1024)
    assert buffer.size == len(fake_image_bytes)

    # Base64 string generation in RAM
    b64_str = buffer.to_base64()
    assert isinstance(b64_str, str)
    assert len(b64_str) > 0

    # Purge buffer
    buffer.purge()
    assert buffer.is_purged is True
    assert buffer.size == 0

    # Once purged, accessing to_base64 or bytes must raise ValueError
    with pytest.raises(ValueError):
        buffer.to_base64()


def test_ephemeral_image_buffer_context_manager():
    """Verify EphemeralImageBuffer cleans up automatically when used as context manager."""
    fake_image_bytes = b"jpeg_fake_stream_bytes"

    with EphemeralImageBuffer.from_bytes(fake_image_bytes) as buf:
        b64 = buf.to_base64()
        assert len(b64) > 0
        assert buf.is_purged is False

    # After context manager exit, buffer must be purged
    assert buf.is_purged is True


def test_ephemeral_image_buffer_max_size_enforcement():
    """Verify that uploads exceeding max_size_bytes raise ImagePayloadTooLargeError."""
    # 2 MB payload with 1 MB limit
    oversized_bytes = b"x" * (2 * 1024 * 1024)

    with pytest.raises(ImagePayloadTooLargeError) as exc_info:
        EphemeralImageBuffer.from_bytes(oversized_bytes, max_size_bytes=1024 * 1024)

    assert exc_info.value.error_code == "ERR_IMAGE_PAYLOAD_TOO_LARGE"


def test_clean_vlm_json_output():
    """Verify markdown code fences and extraneous text are cleanly stripped before json parsing."""
    raw_with_fences = """```json
[
  {"item_name": "steamed edamame", "estimated_grams": 150.0},
  {"item_name": "cooked brown rice", "estimated_grams": 200.0}
]
```"""
    cleaned = clean_vlm_json_output(raw_with_fences)
    assert cleaned.strip().startswith("[")
    assert cleaned.strip().endswith("]")

    raw_with_text = """Here is the extracted meal information:
[{"item_name": "apple", "estimated_grams": 120.0}]
Hope that helps!"""
    cleaned2 = clean_vlm_json_output(raw_with_text)
    assert cleaned2 == '[{"item_name": "apple", "estimated_grams": 120.0}]'


def test_vlm_client_parse_success(mocker):
    """Assert successful loopback /v1/chat/completions call extracts ExtractedCandidateItem list."""
    client = VLMClient(endpoint_url="http://127.0.0.1:8080/v1/chat/completions")

    mock_response = {
        "choices": [
            {
                "message": {
                    "content": (
                        '[\n  {"item_name": "baked salmon", "estimated_grams": 180.0},\n'
                        '  {"item_name": "steamed asparagus", "estimated_grams": 100.0}\n]'
                    )
                }
            }
        ]
    }

    mocker.patch("src.vision_pipeline._post_loopback_json", return_value=mock_response)

    with EphemeralImageBuffer.from_bytes(b"dummy_bytes") as buf:
        candidates = client.parse_meal_image(buf)

    assert len(candidates) == 2
    assert candidates[0] == ExtractedCandidateItem(item_name="baked salmon", estimated_grams=180.0)
    assert candidates[1] == ExtractedCandidateItem(
        item_name="steamed asparagus", estimated_grams=100.0
    )


def test_vlm_client_invalid_json_retry_failure(mocker):
    """Assert invalid JSON response triggers 1 retry and raises VLMInvalidJSONError if still bad."""
    client = VLMClient(endpoint_url="http://127.0.0.1:8080/v1/chat/completions")

    bad_response = {
        "choices": [{"message": {"content": "This is definitely not a JSON array at all."}}]
    }

    mock_post = mocker.patch("src.vision_pipeline._post_loopback_json", return_value=bad_response)

    with EphemeralImageBuffer.from_bytes(b"dummy_bytes") as buf:
        with pytest.raises(VLMInvalidJSONError) as exc_info:
            client.parse_meal_image(buf)

    assert exc_info.value.error_code == "ERR_VLM_INVALID_JSON"
    # Initial attempt + 1 retry = 2 calls
    assert mock_post.call_count == 2


def test_vlm_client_unavailable_error(mocker):
    """Assert socket connection failure raises VLMUnavailableError."""
    client = VLMClient(endpoint_url="http://127.0.0.1:8080/v1/chat/completions")

    mocker.patch(
        "src.vision_pipeline._post_loopback_json",
        side_effect=ConnectionError("Failed to connect to loopback socket"),
    )

    with EphemeralImageBuffer.from_bytes(b"dummy_bytes") as buf:
        with pytest.raises(VLMUnavailableError) as exc_info:
            client.parse_meal_image(buf)

    assert exc_info.value.error_code == "ERR_VLM_UNAVAILABLE"

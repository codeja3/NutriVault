import pytest

from src.vision_pipeline import (
    EphemeralImageBuffer,
    ImagePayloadTooLargeError,
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

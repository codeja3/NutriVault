"""Ephemeral in-memory vision pipeline: volatile buffer management and zero-disk guarantee."""

import base64
import gc
import io

MAX_IMAGE_SIZE_BYTES = 15 * 1024 * 1024  # 15 MB contract ceiling


class ImagePayloadTooLargeError(ValueError):
    """Raised when uploaded image exceeds the in-memory allocation limit."""

    def __init__(self, size_bytes: int, max_bytes: int):
        self.error_code = "ERR_IMAGE_PAYLOAD_TOO_LARGE"
        super().__init__(
            f"Image payload size ({size_bytes} bytes) exceeds maximum allowable memory "
            f"limit of {max_bytes} bytes."
        )


class EphemeralImageBuffer:
    """Manages raw image bytes strictly in volatile RAM (io.BytesIO) with zero disk writes."""

    def __init__(self, stream: io.BytesIO):
        self._stream: io.BytesIO | None = stream
        self._is_purged: bool = False

    @classmethod
    def from_bytes(
        cls,
        image_bytes: bytes,
        max_size_bytes: int = MAX_IMAGE_SIZE_BYTES,
    ) -> "EphemeralImageBuffer":
        if len(image_bytes) > max_size_bytes:
            raise ImagePayloadTooLargeError(len(image_bytes), max_size_bytes)
        stream = io.BytesIO(image_bytes)
        return cls(stream)

    @property
    def is_purged(self) -> bool:
        return self._is_purged

    @property
    def size(self) -> int:
        if self._is_purged or self._stream is None:
            return 0
        return self._stream.getbuffer().nbytes

    def to_base64(self) -> str:
        """Encode volatile stream to base64 in RAM without touching storage."""
        if self._is_purged or self._stream is None:
            raise ValueError("Cannot read from purged EphemeralImageBuffer.")
        self._stream.seek(0)
        return base64.b64encode(self._stream.read()).decode("utf-8")

    def purge(self) -> None:
        """Zero out, truncate, and close buffer, then trigger garbage collection."""
        if self._is_purged:
            return
        if self._stream is not None:
            self._stream.seek(0)
            self._stream.truncate(0)
            self._stream.close()
            self._stream = None
        self._is_purged = True
        gc.collect()

    def __enter__(self) -> "EphemeralImageBuffer":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.purge()

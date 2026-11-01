"""Ephemeral in-memory vision pipeline: volatile buffer management and llama.cpp client."""

import base64
import gc
import io
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

MAX_IMAGE_SIZE_BYTES = 15 * 1024 * 1024  # 15 MB contract ceiling

VLM_SYSTEM_PROMPT = """You are an ephemeral nutritional extraction engine.
Examine the meal photograph. Identify each distinct edible component and estimate its mass in grams.
Respond ONLY with a valid JSON array adhering strictly to this schema:
[
  {"item_name": "plain descriptive food item", "estimated_grams": float}
]
Never calculate calories, never emit markdown code fences, and never include commentary."""


class ImagePayloadTooLargeError(ValueError):
    """Raised when uploaded image exceeds the in-memory allocation limit."""

    def __init__(self, size_bytes: int, max_bytes: int):
        self.error_code = "ERR_IMAGE_PAYLOAD_TOO_LARGE"
        super().__init__(
            f"Image payload size ({size_bytes} bytes) exceeds maximum allowable memory "
            f"limit of {max_bytes} bytes."
        )


class VLMUnavailableError(RuntimeError):
    """Raised when local loopback inference server is unreachable."""

    def __init__(self, message: str = "Local VLM inference service is unavailable."):
        self.error_code = "ERR_VLM_UNAVAILABLE"
        super().__init__(message)


class VLMInvalidJSONError(ValueError):
    """Raised when VLM emits output that cannot be parsed into the candidate schema."""

    def __init__(self, raw_output: str):
        self.error_code = "ERR_VLM_INVALID_JSON"
        super().__init__(f"Failed to parse VLM output into valid candidate items: {raw_output}")


@dataclass(frozen=True)
class ExtractedCandidateItem:
    item_name: str
    estimated_grams: float


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
            try:
                buf = self._stream.getbuffer()
                buf[:] = b"\x00" * len(buf)
                buf.release()
            except (ValueError, BufferError):
                pass
            self._stream.seek(0)
            try:
                self._stream.truncate(0)
            except BufferError:
                pass
            try:
                self._stream.close()
            except BufferError:
                pass
            self._stream = None
        self._is_purged = True
        gc.collect()

    def __enter__(self) -> "EphemeralImageBuffer":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.purge()


def clean_vlm_json_output(content: str) -> str:
    """Extract and isolate JSON array string, stripping markdown fences or text."""
    # Fallback to stripping markdown fences
    cleaned = re.sub(r"^```(?:json)?", "", content.strip(), flags=re.MULTILINE)
    cleaned = re.sub(r"```$", "", cleaned.strip(), flags=re.MULTILINE).strip()

    # Find matching outermost bracket pair [...]
    start = cleaned.find("[")
    end = cleaned.rfind("]")
    if start != -1 and end != -1 and end > start:
        return cleaned[start : end + 1].strip()

    return cleaned


def _post_loopback_json(
    url: str,
    payload: dict[str, Any],
    timeout_sec: float = 30.0,
) -> dict[str, Any]:
    """Execute raw HTTP POST to loopback llama.cpp instance using standard library."""
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as e:
        raise ConnectionError(f"Failed to connect to local loopback VLM: {e}") from e


class VLMClient:
    """Embedded loopback client communicating with local llama.cpp /v1/chat/completions."""

    def __init__(self, endpoint_url: str = "http://127.0.0.1:8080/v1/chat/completions"):
        parsed = urllib.parse.urlparse(endpoint_url)
        hostname = (parsed.hostname or "").lower()
        if hostname not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError(
                f"VLM endpoint URL '{endpoint_url}' is not a local loopback address. "
                "Must be '127.0.0.1', 'localhost', or '::1' to prevent WAN SSRF."
            )
        self.endpoint_url = endpoint_url

    def parse_meal_image(
        self,
        image_buffer: EphemeralImageBuffer,
        max_retries: int = 1,
    ) -> list[ExtractedCandidateItem]:
        b64_image = image_buffer.to_base64()

        payload = {
            "messages": [
                {"role": "system", "content": VLM_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Analyze meal and estimate grams per item."},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{b64_image}"},
                        },
                    ],
                },
            ],
            "temperature": 0.1,
        }

        attempts = 0
        last_error: Exception | None = None
        last_raw_content = ""

        while attempts <= max_retries:
            attempts += 1
            try:
                response = _post_loopback_json(self.endpoint_url, payload)
                content = response["choices"][0]["message"]["content"]
                last_raw_content = content
                cleaned_json = clean_vlm_json_output(content)
                parsed_data = json.loads(cleaned_json)

                if not isinstance(parsed_data, list):
                    raise ValueError("VLM response must be a JSON array")

                candidates: list[ExtractedCandidateItem] = []
                for item in parsed_data:
                    candidates.append(
                        ExtractedCandidateItem(
                            item_name=str(item["item_name"]).strip(),
                            estimated_grams=float(item["estimated_grams"]),
                        )
                    )
                return candidates

            except (ConnectionError, urllib.error.URLError) as e:
                raise VLMUnavailableError(str(e)) from e
            except Exception as e:
                last_error = e
                continue

        raise VLMInvalidJSONError(raw_output=last_raw_content) from last_error

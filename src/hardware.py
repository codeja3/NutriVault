"""Hardware probing and cascading model tier gating engine."""

import os
import platform
import shutil
import subprocess
from dataclasses import dataclass
from enum import Enum


class AcceleratorType(str, Enum):
    APPLE_SILICON = "apple_silicon"
    CUDA = "cuda"
    CPU = "cpu"


class HardwareTier(str, Enum):
    TIER_1_CPU = "tier_1_cpu"
    TIER_2_MID = "tier_2_mid"
    TIER_3_HIGH = "tier_3_high"


TIER_HIERARCHY = {
    HardwareTier.TIER_1_CPU: 1,
    HardwareTier.TIER_2_MID: 2,
    HardwareTier.TIER_3_HIGH: 3,
}


class HardwareTierExceededError(ValueError):
    """Raised when a requested model tier exceeds the host's hardware capacity."""

    def __init__(self, requested: HardwareTier, ceiling: HardwareTier):
        self.requested = requested
        self.ceiling = ceiling
        self.error_code = "ERR_HARDWARE_TIER_EXCEEDED"
        super().__init__(
            f"Requested model tier '{requested.value}' exceeds host hardware tier ceiling "
            f"'{ceiling.value}'."
        )


@dataclass(frozen=True)
class HardwareProfile:
    os_name: str
    total_ram_gb: float
    accelerator: AcceleratorType
    vram_gb: float
    cpu_cores: int


def _get_system_ram_bytes() -> int:
    """Detect total system RAM in bytes across platforms."""
    os_name = platform.system()
    if os_name == "Darwin":
        try:
            out = subprocess.check_output(["sysctl", "-n", "hw.memsize"], text=True)
            return int(out.strip())
        except Exception:
            pass
    elif os_name == "Linux":
        try:
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        parts = line.split()
                        return int(parts[1]) * 1024
        except Exception:
            pass

    # Windows or fallback using os.sysconf if available
    try:
        if (
            hasattr(os, "sysconf")
            and "SC_PAGE_SIZE" in os.sysconf_names
            and "SC_PHYS_PAGES" in os.sysconf_names
        ):
            return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
    except Exception:
        pass

    # Safe fallback: 8 GB
    return 8 * (1024**3)


def _probe_cuda_vram_gb() -> float | None:
    """Probe for NVIDIA CUDA GPU presence and dedicated VRAM in GB."""
    nvidia_smi = shutil.which("nvidia-smi")
    if not nvidia_smi:
        return None
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
            text=True,
            timeout=3,
        )
        lines = [line.strip() for line in out.strip().splitlines() if line.strip()]
        if lines:
            total_mib = float(lines[0])
            return round(total_mib / 1024.0, 2)
    except Exception:
        return None
    return None


def probe_hardware() -> HardwareProfile:
    """Inspect host compute resources and return a HardwareProfile."""
    os_name = platform.system()
    machine = platform.machine().lower()
    cpu_cores = os.cpu_count() or 1

    ram_bytes = _get_system_ram_bytes()
    ram_gb = round(ram_bytes / (1024**3), 2)

    # 1. Apple Silicon detection
    if os_name == "Darwin" and ("arm" in machine or "aarch64" in machine):
        return HardwareProfile(
            os_name=os_name,
            total_ram_gb=ram_gb,
            accelerator=AcceleratorType.APPLE_SILICON,
            vram_gb=ram_gb,  # Unified memory
            cpu_cores=cpu_cores,
        )

    # 2. CUDA detection
    cuda_vram = _probe_cuda_vram_gb()
    if cuda_vram is not None and cuda_vram > 0:
        return HardwareProfile(
            os_name=os_name,
            total_ram_gb=ram_gb,
            accelerator=AcceleratorType.CUDA,
            vram_gb=cuda_vram,
            cpu_cores=cpu_cores,
        )

    # 3. CPU fallback
    return HardwareProfile(
        os_name=os_name,
        total_ram_gb=ram_gb,
        accelerator=AcceleratorType.CPU,
        vram_gb=0.0,
        cpu_cores=cpu_cores,
    )


def resolve_model_tier(profile: HardwareProfile) -> HardwareTier:
    """Resolve the maximum safe model tier given a HardwareProfile."""
    # Check Tier 3: Dedicated GPU >= 16 GB VRAM OR Apple Silicon >= 32 GB Unified Memory
    if profile.accelerator == AcceleratorType.CUDA and profile.vram_gb >= 16.0:
        return HardwareTier.TIER_3_HIGH
    if profile.accelerator == AcceleratorType.APPLE_SILICON and profile.total_ram_gb >= 32.0:
        return HardwareTier.TIER_3_HIGH

    # Check Tier 2: Dedicated GPU >= 6 GB VRAM OR Apple Silicon >= 16 GB Unified Memory
    if profile.accelerator == AcceleratorType.CUDA and profile.vram_gb >= 6.0:
        return HardwareTier.TIER_2_MID
    if profile.accelerator == AcceleratorType.APPLE_SILICON and profile.total_ram_gb >= 16.0:
        return HardwareTier.TIER_2_MID

    # Tier 1 fallback: CPU-only, or < 6 GB VRAM, or < 16 GB RAM
    return HardwareTier.TIER_1_CPU


def validate_model_selection(
    requested_tier: HardwareTier,
    max_allowed_tier: HardwareTier,
) -> None:
    """Validate that requested model tier does not exceed hardware capacity."""
    requested_level = TIER_HIERARCHY[requested_tier]
    max_level = TIER_HIERARCHY[max_allowed_tier]
    if requested_level > max_level:
        raise HardwareTierExceededError(requested=requested_tier, ceiling=max_allowed_tier)

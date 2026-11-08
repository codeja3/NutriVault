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


TIER_RECOMMENDED_MODELS: dict[HardwareTier, list[str]] = {
    HardwareTier.TIER_1_CPU: [
        "SmolVLM-500M-Instruct-Q8_0.gguf",
        "moondream2-text-model-f16.gguf",
        "MiniCPM-V-2_6-Q4_K_M.gguf",
    ],
    HardwareTier.TIER_2_MID: [
        "Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf",
        "gemma-3-4b-it-Q8_0.gguf",
    ],
    HardwareTier.TIER_3_HIGH: [
        "Qwen2.5-VL-14B-Instruct-Q4_K_M.gguf",
        "Qwen2.5-VL-32B-Instruct-Q4_K_M.gguf",
    ],
}


@dataclass(frozen=True)
class PredefinedVLMModel:
    tier: HardwareTier
    name: str
    hf_repo: str
    model_file: str
    mmproj_file: str
    approx_size_mb: int
    sha256_model: str
    sha256_mmproj: str


PREDEFINED_VLM_CATALOG: dict[HardwareTier, PredefinedVLMModel] = {
    HardwareTier.TIER_1_CPU: PredefinedVLMModel(
        tier=HardwareTier.TIER_1_CPU,
        name="SmolVLM-500M-Instruct-Q8_0",
        hf_repo="ggml-org/SmolVLM-500M-Instruct-GGUF",
        model_file="SmolVLM-500M-Instruct-Q8_0.gguf",
        mmproj_file="mmproj-SmolVLM-500M-Instruct-Q8_0.gguf",
        approx_size_mb=550,
        sha256_model="e29851e944ef30e5d070b4ba79ff578a08d6d6232598380486c8742d8ca19c72",
        sha256_mmproj="c8f828a6e8df81cbca3d6dfb37c4aa22ea8910bba1f6e24db10ce3309a96e14a",
    ),
    HardwareTier.TIER_2_MID: PredefinedVLMModel(
        tier=HardwareTier.TIER_2_MID,
        name="Qwen2.5-VL-3B-Instruct-Q4_K_M",
        hf_repo="ggml-org/Qwen2.5-VL-3B-Instruct-GGUF",
        model_file="Qwen2.5-VL-3B-Instruct-Q4_K_M.gguf",
        mmproj_file="mmproj-Qwen2.5-VL-3B-Instruct-Q8_0.gguf",
        approx_size_mb=2200,
        sha256_model="1c9f8021c33be8b327b7a1e05d04f2f45ec4092b604085465e9d99c75cf7015d",
        sha256_mmproj="55e9668d374f1d4f2bc158b09f2d659ad1254dc59be523277e98d9ba8d42d3c9",
    ),
    HardwareTier.TIER_3_HIGH: PredefinedVLMModel(
        tier=HardwareTier.TIER_3_HIGH,
        name="Qwen2.5-VL-7B-Instruct-Q4_K_M",
        hf_repo="ggml-org/Qwen2.5-VL-7B-Instruct-GGUF",
        model_file="Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf",
        mmproj_file="mmproj-Qwen2.5-VL-7B-Instruct-Q8_0.gguf",
        approx_size_mb=5000,
        sha256_model="78a876a392815e1da74d3fb0b3be373b98c368d19abda4e1cc5187e5cc56c80c",
        sha256_mmproj="7f7e9154a86f2b7b2585f096245fc307c0ef7be7f1bfa98e3b5df51ee8eb419c",
    ),
}


def get_default_vlm_spec(tier: HardwareTier) -> PredefinedVLMModel:
    """Return the pinned default PredefinedVLMModel for the given tier."""
    return PREDEFINED_VLM_CATALOG.get(tier, PREDEFINED_VLM_CATALOG[HardwareTier.TIER_1_CPU])


def build_managed_vlm_command(
    tier: HardwareTier,
    port: int = 8081,
    host: str = "127.0.0.1",
) -> list[str]:
    """Build the zero-manual-download llama-server command argv for the resolved tier."""
    spec = get_default_vlm_spec(tier)
    return [
        "./llama-server",
        "--hf-repo",
        spec.hf_repo,
        "--hf-file",
        spec.model_file,
        "--port",
        str(port),
        "--host",
        host,
    ]


def get_recommended_models(tier: HardwareTier) -> list[str]:
    """Return curated list of GGUF model filenames for given tier."""
    return TIER_RECOMMENDED_MODELS.get(tier, TIER_RECOMMENDED_MODELS[HardwareTier.TIER_1_CPU])


def format_vlm_setup_guide(profile: HardwareProfile | None = None) -> str:
    """Generate a human-readable setup guide for the resolved hardware tier."""
    if profile is None:
        profile = probe_hardware()

    tier = resolve_model_tier(profile)
    spec = get_default_vlm_spec(tier)
    models = get_recommended_models(tier)
    cmd = build_managed_vlm_command(tier, port=8081, host="127.0.0.1")
    cmd_str = " ".join(cmd)

    lines = [
        "===========================================================",
        "               NutriVault Local VLM Setup Guide            ",
        "===========================================================",
        f"Detected Host OS:         {profile.os_name}",
        f"Total System RAM:         {profile.total_ram_gb:.1f} GB",
        f"Accelerator Backend:      {profile.accelerator.value.upper()}",
        f"Dedicated / Unified VRAM: {profile.vram_gb:.1f} GB",
        f"Active Model Tier:        {tier.value}",
        "-----------------------------------------------------------",
        f"Predefined Default VLM:   {spec.name} (~{spec.approx_size_mb} MB)",
        f"HuggingFace Repository:   {spec.hf_repo}",
        "-----------------------------------------------------------",
        "One-Command Automatic Launch (zero file hunting):",
        f"  {cmd_str}",
        "-----------------------------------------------------------",
        "Alternative GGUF Vision Models for this tier:",
    ]
    for m in models:
        lines.append(f"  • {m}")

    lines.extend(
        [
            "===========================================================",
        ]
    )
    return "\n".join(lines)

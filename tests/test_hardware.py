import pytest

from src.hardware import (
    AcceleratorType,
    HardwareProfile,
    HardwareTier,
    HardwareTierExceededError,
    probe_hardware,
    resolve_model_tier,
    validate_model_selection,
)


def test_hardware_profile_dataclass():
    """Verify HardwareProfile dataclass fields and immutability."""
    profile = HardwareProfile(
        os_name="Darwin",
        total_ram_gb=16.0,
        accelerator=AcceleratorType.APPLE_SILICON,
        vram_gb=16.0,
        cpu_cores=8,
    )
    assert profile.os_name == "Darwin"
    assert profile.total_ram_gb == 16.0
    assert profile.accelerator == AcceleratorType.APPLE_SILICON
    assert profile.vram_gb == 16.0
    assert profile.cpu_cores == 8

    with pytest.raises(Exception):
        profile.total_ram_gb = 32.0  # dataclass should be frozen/immutable


def test_probe_hardware_apple_silicon(mocker):
    """Assert Apple Silicon detection on Darwin arm64."""
    mocker.patch("platform.system", return_value="Darwin")
    mocker.patch("platform.machine", return_value="arm64")
    mocker.patch("os.cpu_count", return_value=10)
    # Mock RAM: 16 GB = 16 * 1024**3 bytes
    mocker.patch("src.hardware._get_system_ram_bytes", return_value=16 * (1024**3))

    profile = probe_hardware()
    assert profile.os_name == "Darwin"
    assert profile.accelerator == AcceleratorType.APPLE_SILICON
    assert profile.total_ram_gb == 16.0
    assert profile.vram_gb == 16.0  # Unified memory on Apple Silicon
    assert profile.cpu_cores == 10


def test_probe_hardware_cuda(mocker):
    """Assert CUDA detection on Linux when nvidia GPU is present."""
    mocker.patch("platform.system", return_value="Linux")
    mocker.patch("platform.machine", return_value="x86_64")
    mocker.patch("os.cpu_count", return_value=16)
    mocker.patch("src.hardware._get_system_ram_bytes", return_value=32 * (1024**3))
    mocker.patch("src.hardware._probe_cuda_vram_gb", return_value=8.0)

    profile = probe_hardware()
    assert profile.os_name == "Linux"
    assert profile.accelerator == AcceleratorType.CUDA
    assert profile.total_ram_gb == 32.0
    assert profile.vram_gb == 8.0
    assert profile.cpu_cores == 16


def test_probe_hardware_cpu_fallback(mocker):
    """Assert CPU fallback when no GPU accelerator is available."""
    mocker.patch("platform.system", return_value="Windows")
    mocker.patch("platform.machine", return_value="AMD64")
    mocker.patch("os.cpu_count", return_value=4)
    mocker.patch("src.hardware._get_system_ram_bytes", return_value=8 * (1024**3))
    mocker.patch("src.hardware._probe_cuda_vram_gb", return_value=None)

    profile = probe_hardware()
    assert profile.os_name == "Windows"
    assert profile.accelerator == AcceleratorType.CPU
    assert profile.total_ram_gb == 8.0
    assert profile.vram_gb == 0.0
    assert profile.cpu_cores == 4


def test_resolve_model_tier_tier_1_cpu():
    """Assert CPU or low RAM falls into tier_1_cpu."""
    # CPU only
    p1 = HardwareProfile(
        os_name="Linux",
        total_ram_gb=32.0,
        accelerator=AcceleratorType.CPU,
        vram_gb=0.0,
        cpu_cores=8,
    )
    assert resolve_model_tier(p1) == HardwareTier.TIER_1_CPU

    # GPU but low VRAM (< 6 GB)
    p2 = HardwareProfile(
        os_name="Linux",
        total_ram_gb=16.0,
        accelerator=AcceleratorType.CUDA,
        vram_gb=4.0,
        cpu_cores=8,
    )
    assert resolve_model_tier(p2) == HardwareTier.TIER_1_CPU

    # Apple Silicon but < 16 GB Unified Memory
    p3 = HardwareProfile(
        os_name="Darwin",
        total_ram_gb=8.0,
        accelerator=AcceleratorType.APPLE_SILICON,
        vram_gb=8.0,
        cpu_cores=8,
    )
    assert resolve_model_tier(p3) == HardwareTier.TIER_1_CPU


def test_resolve_model_tier_tier_2_mid():
    """Assert Mid-spec hardware qualifies for tier_2_mid."""
    # CUDA with 8 GB VRAM
    p1 = HardwareProfile(
        os_name="Linux",
        total_ram_gb=32.0,
        accelerator=AcceleratorType.CUDA,
        vram_gb=8.0,
        cpu_cores=8,
    )
    assert resolve_model_tier(p1) == HardwareTier.TIER_2_MID

    # Apple Silicon with 16 GB Unified Memory
    p2 = HardwareProfile(
        os_name="Darwin",
        total_ram_gb=16.0,
        accelerator=AcceleratorType.APPLE_SILICON,
        vram_gb=16.0,
        cpu_cores=10,
    )
    assert resolve_model_tier(p2) == HardwareTier.TIER_2_MID


def test_resolve_model_tier_tier_3_high():
    """Assert High-spec hardware qualifies for tier_3_high."""
    # CUDA with 24 GB VRAM
    p1 = HardwareProfile(
        os_name="Linux",
        total_ram_gb=64.0,
        accelerator=AcceleratorType.CUDA,
        vram_gb=24.0,
        cpu_cores=16,
    )
    assert resolve_model_tier(p1) == HardwareTier.TIER_3_HIGH

    # Apple Silicon with 36 GB Unified Memory
    p2 = HardwareProfile(
        os_name="Darwin",
        total_ram_gb=36.0,
        accelerator=AcceleratorType.APPLE_SILICON,
        vram_gb=36.0,
        cpu_cores=14,
    )
    assert resolve_model_tier(p2) == HardwareTier.TIER_3_HIGH


def test_validate_model_selection():
    """Verify allowable tiers pass and exceeded tiers raise HardwareTierExceededError."""
    # Tier 1 host: only tier_1_cpu allowed
    validate_model_selection(
        requested_tier=HardwareTier.TIER_1_CPU,
        max_allowed_tier=HardwareTier.TIER_1_CPU,
    )

    with pytest.raises(HardwareTierExceededError) as exc_info:
        validate_model_selection(
            requested_tier=HardwareTier.TIER_2_MID,
            max_allowed_tier=HardwareTier.TIER_1_CPU,
        )
    assert exc_info.value.error_code == "ERR_HARDWARE_TIER_EXCEEDED"

    with pytest.raises(HardwareTierExceededError) as exc_info2:
        validate_model_selection(
            requested_tier=HardwareTier.TIER_3_HIGH,
            max_allowed_tier=HardwareTier.TIER_2_MID,
        )
    assert exc_info2.value.error_code == "ERR_HARDWARE_TIER_EXCEEDED"


def test_get_recommended_models():
    """Verify get_recommended_models returns tier-appropriate GGUF models."""
    from src.hardware import get_recommended_models

    t1_models = get_recommended_models(HardwareTier.TIER_1_CPU)
    assert any("SmolVLM" in m for m in t1_models)
    assert any("moondream" in m.lower() for m in t1_models)

    t2_models = get_recommended_models(HardwareTier.TIER_2_MID)
    assert any("Qwen2.5-VL-7B" in m for m in t2_models)

    t3_models = get_recommended_models(HardwareTier.TIER_3_HIGH)
    assert any("Qwen2.5-VL-14B" in m for m in t3_models)


def test_format_vlm_setup_guide():
    """Verify format_vlm_setup_guide generates human-readable hardware-aware CLI instructions."""
    from src.hardware import format_vlm_setup_guide

    guide = format_vlm_setup_guide()
    assert "NutriVault Local VLM Setup Guide" in guide
    assert "llama-server" in guide
    assert "--port 8081" in guide
    assert "--host 127.0.0.1" in guide

    # Test with custom profile
    p_mid = HardwareProfile(
        os_name="Darwin",
        total_ram_gb=16.0,
        accelerator=AcceleratorType.APPLE_SILICON,
        vram_gb=16.0,
        cpu_cores=10,
    )
    mid_guide = format_vlm_setup_guide(p_mid)
    assert "tier_2_mid" in mid_guide
    assert "Qwen2.5-VL-7B" in mid_guide

    # Tier 3 host allows Tier 1, 2, or 3
    validate_model_selection(
        requested_tier=HardwareTier.TIER_1_CPU,
        max_allowed_tier=HardwareTier.TIER_3_HIGH,
    )
    validate_model_selection(
        requested_tier=HardwareTier.TIER_2_MID,
        max_allowed_tier=HardwareTier.TIER_3_HIGH,
    )
    validate_model_selection(
        requested_tier=HardwareTier.TIER_3_HIGH,
        max_allowed_tier=HardwareTier.TIER_3_HIGH,
    )


def test_predefined_vlm_catalog():
    """Verify PREDEFINED_VLM_CATALOG, get_default_vlm_spec, and build_managed_vlm_command."""
    from src.hardware import (
        PREDEFINED_VLM_CATALOG,
        PredefinedVLMModel,
        build_managed_vlm_command,
        get_default_vlm_spec,
    )

    for tier in (HardwareTier.TIER_1_CPU, HardwareTier.TIER_2_MID, HardwareTier.TIER_3_HIGH):
        spec = get_default_vlm_spec(tier)
        assert isinstance(spec, PredefinedVLMModel)
        assert spec.tier == tier
        assert spec.hf_repo.startswith("ggml-org/")
        assert spec.model_file.endswith(".gguf")
        assert spec.mmproj_file.endswith(".gguf")
        assert spec.approx_size_mb > 0
        assert spec.sha256_model
        assert spec.sha256_mmproj

    # Exact tier model checks
    t1 = PREDEFINED_VLM_CATALOG[HardwareTier.TIER_1_CPU]
    assert t1.name == "SmolVLM-500M-Instruct-Q8_0"
    assert t1.approx_size_mb == 550

    t2 = PREDEFINED_VLM_CATALOG[HardwareTier.TIER_2_MID]
    assert t2.name == "Qwen2.5-VL-3B-Instruct-Q4_K_M"
    assert t2.approx_size_mb == 2200

    t3 = PREDEFINED_VLM_CATALOG[HardwareTier.TIER_3_HIGH]
    assert t3.name == "Qwen2.5-VL-7B-Instruct-Q4_K_M"
    assert t3.approx_size_mb == 5000

    cmd = build_managed_vlm_command(HardwareTier.TIER_1_CPU, port=8081, host="127.0.0.1")
    assert any("llama-server" in token for token in cmd)
    assert "--hf-repo" in cmd
    assert t1.hf_repo in cmd
    assert "--hf-file" in cmd
    assert t1.model_file in cmd
    assert "--port" in cmd
    assert "8081" in cmd
    assert "--host" in cmd
    assert "127.0.0.1" in cmd

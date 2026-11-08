import importlib
import sys


def test_python_version():
    """NutriVault requires Python 3.11+ strictly."""
    assert sys.version_info >= (3, 11), f"Expected Python 3.11+, got {sys.version_info}"


def test_core_package_import():
    """Verify src package can be imported and exposes version."""
    src = importlib.import_module("src")
    assert hasattr(src, "__version__"), "src must define __version__"
    assert src.__version__ == "1.0.0"


def test_docker_configuration_and_compose_files():
    """Verify Dockerfile and docker-compose.yml exist with port 8080, volumes, and non-root user."""
    from pathlib import Path

    repo_root = Path(__file__).parent.parent

    dockerfile = repo_root / "Dockerfile"
    assert dockerfile.exists(), "Dockerfile must exist at repo root"
    df_content = dockerfile.read_text()
    assert "8080" in df_content
    assert "/app/data" in df_content
    assert "USER" in df_content

    compose_file = repo_root / "docker-compose.yml"
    assert compose_file.exists(), "docker-compose.yml must exist at repo root"
    compose_content = compose_file.read_text()
    assert "8080:8080" in compose_content
    assert "/app/data" in compose_content

    dockerignore = repo_root / ".dockerignore"
    assert dockerignore.exists(), ".dockerignore must exist at repo root"


def test_docker_compose_turnkey_vlm_sidecar_and_remote_profile():
    """Verify docker-compose.yml defines preconfigured SmolVLM sidecar & remote profile."""
    from pathlib import Path

    repo_root = Path(__file__).parent.parent
    compose_file = repo_root / "docker-compose.yml"
    assert compose_file.exists()
    content = compose_file.read_text()

    # Preconfigured VLM sidecar
    assert "nutrivault-vlm:" in content
    assert "ghcr.io/ggerganov/llama.cpp:server" in content
    assert "SmolVLM-500M-Instruct-GGUF" in content
    assert "SmolVLM-500M-Instruct-Q8_0.gguf" in content
    assert "8081:8081" in content
    assert "./models:/root/.cache/llama.cpp" in content

    # Optional remote P2P access
    assert "nutrivault-remote:" in content
    assert "tailscale/tailscale" in content
    assert "profiles:" in content
    assert "remote" in content

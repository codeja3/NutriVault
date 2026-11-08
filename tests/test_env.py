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


def test_double_click_desktop_launchers_exist():
    """Verify Start_NutriVault.command (macOS) and Start_NutriVault.bat (Windows) exist."""
    import os
    from pathlib import Path

    repo_root = Path(__file__).parent.parent

    mac_launcher = repo_root / "Start_NutriVault.command"
    assert mac_launcher.exists(), "Start_NutriVault.command must exist at repo root"
    assert os.access(mac_launcher, os.X_OK), "Start_NutriVault.command must be executable"
    mac_text = mac_launcher.read_text()
    assert 'cd "$(dirname "$0")"' in mac_text
    assert "--open-browser" in mac_text or "http://localhost:8080" in mac_text

    win_launcher = repo_root / "Start_NutriVault.bat"
    assert win_launcher.exists(), "Start_NutriVault.bat must exist at repo root"
    win_text = win_launcher.read_text()
    assert 'cd /d "%~dp0"' in win_text
    assert "--open-browser" in win_text or "http://localhost:8080" in win_text

    manual_file = repo_root / "MANUAL.md"
    assert manual_file.exists()
    manual_text = manual_file.read_text()
    assert "https://github.com/codeja3/NutriVault/archive/refs/heads/main.zip" in manual_text
    assert "Start_NutriVault.command" in manual_text
    assert "Start_NutriVault.bat" in manual_text
    assert "Phone Wi-Fi Link" in manual_text
    assert "git clone" not in manual_text
    assert "uv venv" not in manual_text

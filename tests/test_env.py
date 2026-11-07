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

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

"""
Tests build dependencies presence.
"""


def test_imports():
    import PIL  # noqa: F401
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        import pytest
        pytest.skip("PyInstaller not installed")

    assert PIL.__version__
    assert PyInstaller.__version__

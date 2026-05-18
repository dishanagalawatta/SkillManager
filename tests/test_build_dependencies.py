"""
Tests build dependencies presence.
"""


def test_imports():
    import PIL
    import PyInstaller

    assert PIL.__version__
    assert PyInstaller.__version__

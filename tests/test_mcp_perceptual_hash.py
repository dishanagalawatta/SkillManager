"""Unit tests for perceptual hash and baseline-name support in screenshot comparison."""

from __future__ import annotations

import base64
import io
from pathlib import Path

import pytest
from PIL import Image

from skill_manager.mcp.bridge import _visual_analysis as va


def _png_b64(image: Image.Image) -> str:
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


# ---------------------------------------------------------------------------
# _phash
# ---------------------------------------------------------------------------
def test_phash_identical_images_distance_zero() -> None:
    """Identical images produce identical perceptual hashes (distance 0)."""
    img = Image.new("RGB", (32, 32), (100, 150, 200))
    # Add some structure so the hash isn't all-zero
    for x in range(32):
        for y in range(32):
            img.putpixel((x, y), ((x * 8) % 256, (y * 8) % 256, 128))
    h1 = va._phash(img)
    h2 = va._phash(img)
    assert va._hamming_distance(h1, h2) == 0


def test_phash_different_images_distance_positive() -> None:
    """Structurally different images produce different perceptual hashes."""
    a = Image.new("RGB", (32, 32), (255, 0, 0))
    a.paste((0, 0, 255), (16, 0, 32, 32))  # right half blue
    b = Image.new("RGB", (32, 32), (0, 0, 255))
    b.paste((255, 0, 0), (16, 0, 32, 32))  # right half red
    ha = va._phash(a)
    hb = va._phash(b)
    assert va._hamming_distance(ha, hb) > 0


def test_phash_similarity_range() -> None:
    """_phash_similarity returns a value in [0, 1]."""
    img = Image.new("RGB", (32, 32), (100, 150, 200))
    h = va._phash(img)
    sim = va._phash_similarity(h, h)
    assert 0.0 <= sim <= 1.0
    assert sim == 1.0


def test_hamming_distance_bounds() -> None:
    """Hamming distance is symmetric and non-negative."""
    a, b = 0b10101010, 0b01010101
    d = va._hamming_distance(a, b)
    assert d == va._hamming_distance(b, a)
    assert d >= 0
    assert d <= 64  # 8x8 = 64 bits


# ---------------------------------------------------------------------------
# compare_screenshot with baseline_name
# ---------------------------------------------------------------------------
def test_compare_screenshot_baseline_name_not_found(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """baseline_name that doesn't resolve to a file returns ok=False."""
    monkeypatch.setattr(va, "_REPO_ROOT", tmp_path)
    result = va.compare_screenshot(baseline_b64="", baseline_name="nonexistent", threshold=0.95)
    assert result["ok"] is False
    assert "nonexistent" in result["error"]


def test_compare_screenshot_no_baseline(monkeypatch: pytest.MonkeyPatch) -> None:
    """No baseline_b64 and no baseline_name returns ok=False."""
    result = va.compare_screenshot(baseline_b64="", baseline_name=None, threshold=0.95)
    assert result["ok"] is False
    assert "required" in result["error"]


def test_compare_screenshot_baseline_name_loaded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """baseline_name loads the PNG from .agents/screenshots/<name>.png."""
    screenshots_dir = tmp_path / ".agents" / "screenshots"
    screenshots_dir.mkdir(parents=True)
    img = Image.new("RGB", (8, 8), (255, 0, 0))
    img.save(screenshots_dir / "mybaseline.png")

    monkeypatch.setattr(va, "_REPO_ROOT", tmp_path)
    # Mock capture_app_window to return a matching image
    current_b64 = _png_b64(Image.new("RGB", (8, 8), (255, 0, 0)))
    monkeypatch.setattr(va, "capture_app_window", lambda: (current_b64, 8, 8))

    result = va.compare_screenshot(
        baseline_b64="", baseline_name="mybaseline", current_b64=None, threshold=0.95
    )
    assert result["ok"] is True
    assert result["error"] is None
    assert result["within_threshold"] is True


# ---------------------------------------------------------------------------
# compare_screenshot returns phash_similarity
# ---------------------------------------------------------------------------
def test_compare_screenshot_returns_phash_similarity() -> None:
    """compare_screenshot includes phash_similarity in the result."""
    img = Image.new("RGB", (16, 16), (100, 150, 200))
    b64 = _png_b64(img)
    result = va.compare_screenshot(b64, current_b64=b64, threshold=0.95)
    assert result["ok"] is True
    assert "phash_similarity" in result
    assert result["phash_similarity"] == 1.0
    assert 0.0 <= result["phash_similarity"] <= 1.0


def test_compare_screenshot_phash_detects_rearrangement() -> None:
    """Perceptual hash detects structural rearrangement even when pixel diff is high."""
    # Two images with same colors but different arrangement
    a = Image.new("RGB", (16, 16), (255, 0, 0))
    a.paste((0, 0, 255), (8, 0, 16, 16))  # right half blue
    b = Image.new("RGB", (16, 16), (0, 0, 255))
    b.paste((255, 0, 0), (8, 0, 16, 16))  # right half red
    result = va.compare_screenshot(_png_b64(a), current_b64=_png_b64(b), threshold=0.95)
    assert result["ok"] is True
    # Structural similarity will be 0 (completely different pixels)
    assert result["similarity"] == 0.0
    # phash_similarity should be low since spatial arrangement differs
    assert result["phash_similarity"] < 1.0

"""Visual analysis bridge functions: screenshot comparison and visual issue detection."""

from __future__ import annotations

import base64
import io
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops  # type: ignore[import-not-found]

from ._capture import capture_app_window
from ._telemetry import _log_call

# Repo root for resolving baseline name -> .agents/screenshots/<name>.png
_REPO_ROOT = Path(__file__).resolve().parents[4]


def _b64_to_image(b64: str) -> Image.Image:
    raw = base64.b64decode(b64)
    return Image.open(io.BytesIO(raw)).convert("RGB")


def _load_baseline_png(baseline_name: str) -> Image.Image | None:
    """Load a baseline PNG from .agents/screenshots/<baseline_name>.png."""
    try:
        path = _REPO_ROOT / ".agents" / "screenshots" / f"{baseline_name}.png"
        if not path.exists():
            return None
        return Image.open(path).convert("RGB")
    except Exception:  # noqa: BLE001
        return None


def _phash(image: Image.Image, hash_size: int = 8) -> int:
    """Compute a perceptual hash (average-hash variant) of *image*.

    Converts to grayscale, resizes to hash_size x hash_size, computes the
    mean pixel value, and builds a bitmask where each bit is 1 if the
    corresponding pixel exceeds the mean. Returns an integer bitmask.
    Two visually similar images produce close hashes (small Hamming distance).
    """
    small = image.convert("L").resize((hash_size, hash_size), Image.Resampling.LANCZOS)
    pixels = list(small.tobytes())
    mean = sum(pixels) / len(pixels) if pixels else 0
    bits = 0
    for i, p in enumerate(pixels):
        if p > mean:
            bits |= 1 << i
    return bits


def _hamming_distance(a: int, b: int) -> int:
    """Return the Hamming distance between two perceptual-hash integers."""
    x = a ^ b
    distance = 0
    while x:
        distance += x & 1
        x >>= 1
    return distance


def _phash_similarity(a: int, b: int, hash_size: int = 8) -> float:
    """Convert Hamming distance between two hashes into a 0-1 similarity score."""
    total_bits = hash_size * hash_size
    distance = _hamming_distance(a, b)
    return max(0.0, 1.0 - (distance / total_bits))


def compare_screenshot(
    baseline_b64: str,
    current_b64: str | None = None,
    threshold: float = 0.95,
    baseline_name: str | None = None,
) -> dict[str, Any]:
    """Compare a baseline screenshot against the current (or supplied) screenshot."""
    _log_call("compare_screenshot")
    try:
        threshold = float(threshold)

        # Resolve baseline image: explicit base64 takes priority; otherwise try
        # baseline_name -> .agents/screenshots/<baseline_name>.png.
        baseline: Image.Image | None = None
        if baseline_b64:
            baseline = _b64_to_image(baseline_b64)
        elif baseline_name:
            baseline = _load_baseline_png(baseline_name)
            if baseline is None:
                return {
                    "ok": False,
                    "similarity": 0.0,
                    "diff_pixels": 0,
                    "total_pixels": 0,
                    "within_threshold": False,
                    "issues": [],
                    "error": f"baseline '{baseline_name}' not found in .agents/screenshots/",
                }
        else:
            return {
                "ok": False,
                "similarity": 0.0,
                "diff_pixels": 0,
                "total_pixels": 0,
                "within_threshold": False,
                "issues": [],
                "error": "baseline_b64 or baseline_name is required",
            }

        if current_b64 is not None:
            current = _b64_to_image(current_b64)
        else:
            b64, _w, _h = capture_app_window()
            if b64 is None:
                return {
                    "ok": False,
                    "similarity": 0.0,
                    "diff_pixels": 0,
                    "total_pixels": 0,
                    "within_threshold": False,
                    "issues": [],
                    "error": "capture_failed",
                }
            current = _b64_to_image(b64)

        if baseline.size != current.size:
            current = current.resize(baseline.size, Image.Resampling.LANCZOS)

        # ── Pixel-exact structural diff (ImageChops) ──────────────────────
        diff = ImageChops.difference(baseline, current)
        diff_bytes = diff.tobytes()
        diff_pixels = sum(1 for i in range(0, len(diff_bytes), 3) if any(diff_bytes[i : i + 3]))
        total_pixels = max(1, baseline.width * baseline.height)
        similarity = 1.0 - (diff_pixels / total_pixels)

        # ── Perceptual hash similarity (robust to anti-aliasing / sub-pixel) ──
        baseline_hash = _phash(baseline)
        current_hash = _phash(current)
        phash_similarity = _phash_similarity(baseline_hash, current_hash)

        # Primary pass/fail uses perceptual similarity; structural similarity is
        # reported alongside for diagnostics.
        within_threshold = phash_similarity >= threshold
        issues: list[str] = []
        if not within_threshold:
            issues.append(
                f"screenshots differ (phash_similarity {phash_similarity:.2f} "
                f"< threshold {threshold:.2f}; structural {similarity:.2f})"
            )
        return {
            "ok": True,
            "similarity": round(float(similarity), 4),
            "phash_similarity": round(float(phash_similarity), 4),
            "diff_pixels": int(diff_pixels),
            "total_pixels": int(total_pixels),
            "within_threshold": bool(within_threshold),
            "issues": issues,
            "error": None,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "similarity": 0.0,
            "diff_pixels": 0,
            "total_pixels": 0,
            "within_threshold": False,
            "issues": [],
            "error": str(exc),
        }


def find_visual_issues(
    image_b64: str,
    check_clipping: bool = True,
    check_contrast: bool = True,
    check_overlap: bool = True,
) -> dict[str, Any]:
    """Scan an image for common visual issues (clipping, contrast, overlap)."""
    _log_call("find_visual_issues")
    try:
        img = _b64_to_image(image_b64).convert("L")
        width, height = img.size
        pixels = list(img.tobytes())
        issues: list[dict[str, Any]] = []

        if check_clipping and width > 2 and height > 2:
            # Content hard against the outermost 1px border suggests clipping.
            border: list[int] = []
            for row in range(height):
                border.append(pixels[row * width])
                border.append(pixels[row * width + width - 1])
            for col in range(width):
                border.append(pixels[col])
                border.append(pixels[(height - 1) * width + col])
            nonwhite = sum(1 for p in border if p < 250)
            if nonwhite > 0:
                issues.append(
                    {
                        "type": "clipping",
                        "severity": "medium",
                        "description": "Content appears clipped at image edges.",
                        "location": {"x": 0, "y": 0, "width": width, "height": height},
                    }
                )

        if check_contrast and pixels:
            lo = min(pixels)
            hi = max(pixels)
            if 0 < (hi - lo) < 40:
                issues.append(
                    {
                        "type": "contrast",
                        "severity": "low",
                        "description": "Insufficient tonal contrast in image.",
                        "location": {"x": 0, "y": 0, "width": width, "height": height},
                    }
                )

        # Overlap cannot be reliably detected on a flattened raster image, so it
        # is intentionally left unchecked here (kept for API completeness).
        _ = check_overlap

        return {
            "ok": True,
            "issue_count": len(issues),
            "issues": issues,
            "error": None,
        }
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "issue_count": 0, "issues": [], "error": str(exc)}

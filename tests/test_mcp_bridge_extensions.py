"""Unit tests for the MCP bridge extension functions (called directly).

These tests exercise the bridge functions in ``skill_manager.mcp.bridge`` with
mocked dependencies (controller, QML engine, screenshot). They never boot Qt or
construct ``AppController``.
"""

from __future__ import annotations

import base64
import io
import os
from types import SimpleNamespace
from typing import Any

import pytest
from PIL import Image

from skill_manager.mcp.bridge import (
    _bug_detection,
    _ui_inspection,
    compare_screenshot,
    detect_qml_errors,
    find_visual_issues,
    get_current_view,
    get_performance_metrics,
    get_pixel_color,
    inspect_qml_tree,
    measure_startup_time,
    run_ui_scenario,
)


def _png_b64(image: Image.Image) -> str:
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


# ---------------------------------------------------------------------------
# get_current_view — mocked controller
# ---------------------------------------------------------------------------
def test_get_current_view_mocked_controller(monkeypatch: pytest.MonkeyPatch) -> None:
    """get_current_view reports the controller's currentView."""
    controller = SimpleNamespace(ui=SimpleNamespace(currentView="Library"))
    monkeypatch.setattr(_ui_inspection, "_controller_or_none", lambda: controller)

    result = get_current_view()

    assert result == {"view": "Library", "ok": True, "error": None}


def test_get_current_view_no_controller(monkeypatch: pytest.MonkeyPatch) -> None:
    """get_current_view degrades when no controller is available."""
    monkeypatch.setattr(_ui_inspection, "_controller_or_none", lambda: None)

    result = get_current_view()

    assert result["view"] == "unknown"
    assert result["ok"] is False
    assert result["error"] is not None


# ---------------------------------------------------------------------------
# inspect_qml_tree — mocked QML engine
# ---------------------------------------------------------------------------
def test_inspect_qml_tree_mocked_engine(monkeypatch: pytest.MonkeyPatch) -> None:
    """inspect_qml_tree builds a tree from a mocked QML engine."""
    root = SimpleNamespace(
        objectName="root",
        isVisible=True,
        isEnabled=True,
        x=0,
        y=0,
        width=800,
        height=600,
        childItems=[],
    )
    engine = SimpleNamespace(rootObjects=lambda: [root])
    controller = SimpleNamespace(qml_engine=engine)
    monkeypatch.setattr(_ui_inspection, "_controller_or_none", lambda: controller)
    monkeypatch.setattr(_ui_inspection, "ensure_qml_engine", lambda: engine)

    result = inspect_qml_tree(max_depth=2)

    assert result["ok"] is True
    assert result["root_count"] == 1
    assert result["error"] is None
    node = result["tree"][0]
    assert node["object_name"] == "root"
    assert node["visible"] is True
    assert node["width"] == 800
    assert node["height"] == 600
    assert node["children"] == []


def test_inspect_qml_tree_no_engine(monkeypatch: pytest.MonkeyPatch) -> None:
    """inspect_qml_tree degrades when there is no QML engine."""
    controller = SimpleNamespace()  # no qml_engine attribute
    monkeypatch.setattr(_ui_inspection, "_controller_or_none", lambda: controller)
    monkeypatch.setattr(_ui_inspection, "ensure_qml_engine", lambda: None)

    result = inspect_qml_tree()

    assert result["ok"] is False
    assert result["root_count"] == 0
    assert result["error"] == "no_qml_engine"


# ---------------------------------------------------------------------------
# get_pixel_color — mocked screenshot
# ---------------------------------------------------------------------------
def test_get_pixel_color_mocked_screenshot(monkeypatch: pytest.MonkeyPatch) -> None:
    """get_pixel_color samples a pixel from a mocked captured screenshot."""
    img = Image.new("RGB", (2, 2), (255, 0, 0))  # red
    b64 = _png_b64(img)
    monkeypatch.setattr(
        _ui_inspection,
        "capture_app_window_info",
        lambda **kw: {
            "image_b64": b64,
            "width": 2,
            "height": 2,
            "source": "headless-qml",
            "error": None,
        },
    )

    result = get_pixel_color(0, 0)

    assert result["ok"] is True
    assert result["color"] == "#ff0000"
    assert result["r"] == 255
    assert result["g"] == 0
    assert result["b"] == 0
    assert result["x"] == 0
    assert result["y"] == 0
    assert result["width"] == 2
    assert result["height"] == 2
    assert result["source"] == "headless-qml"
    assert result["error"] is None


def test_get_pixel_color_capture_failed(monkeypatch: pytest.MonkeyPatch) -> None:
    """get_pixel_color degrades when screenshot capture fails."""
    monkeypatch.setattr(
        _ui_inspection,
        "capture_app_window_info",
        lambda **kw: {
            "image_b64": None,
            "width": 0,
            "height": 0,
            "source": None,
            "error": "SkillManager GUI not running and no headless QML render available",
        },
    )

    result = get_pixel_color(0, 0)

    assert result["ok"] is False
    assert "no headless QML render" in result["error"]


def test_get_pixel_color_out_of_bounds(monkeypatch: pytest.MonkeyPatch) -> None:
    """get_pixel_color degrades for coordinates outside the captured image."""
    img = Image.new("RGB", (2, 2), (255, 0, 0))
    b64 = _png_b64(img)
    monkeypatch.setattr(
        _ui_inspection,
        "capture_app_window_info",
        lambda **kw: {"image_b64": b64, "width": 2, "height": 2, "source": "native"},
    )

    result = get_pixel_color(99, 99)

    assert result["ok"] is False
    assert result["error"] == "coordinate_out_of_bounds"
    assert result["width"] == 2
    assert result["height"] == 2
    assert result["source"] == "native"


# ---------------------------------------------------------------------------
# get_performance_metrics — direct (psutil)
# ---------------------------------------------------------------------------
def test_get_performance_metrics_direct() -> None:
    """get_performance_metrics returns live process metrics via psutil."""
    result = get_performance_metrics()

    assert result["ok"] is True
    assert result["error"] is None
    assert isinstance(result["memory_mb"], float)
    assert result["memory_mb"] >= 0.0
    assert isinstance(result["cpu_percent"], float)
    assert result["cpu_percent"] >= 0.0
    assert isinstance(result["thread_count"], int)
    assert result["thread_count"] >= 1
    assert result["process_id"] == os.getpid()
    assert isinstance(result["uptime_seconds"], float)
    assert result["uptime_seconds"] >= 0.0


# ---------------------------------------------------------------------------
# measure_startup_time — direct
# ---------------------------------------------------------------------------
def test_measure_startup_time_direct() -> None:
    """measure_startup_time returns a non-negative elapsed startup time."""
    result = measure_startup_time()

    assert result["ok"] is True
    assert result["error"] is None
    assert isinstance(result["startup_ms"], float)
    assert result["startup_ms"] >= 0.0
    assert result["timestamp"]


# ---------------------------------------------------------------------------
# compare_screenshot — PIL ImageChops
# ---------------------------------------------------------------------------
def test_compare_screenshot_identical_images() -> None:
    """Identical screenshots yield similarity 1.0 and within_threshold True."""
    img = Image.new("RGB", (8, 8), (100, 150, 200))
    b64 = _png_b64(img)

    result = compare_screenshot(b64, current_b64=b64, threshold=0.95)

    assert result["ok"] is True
    assert result["error"] is None
    assert result["similarity"] == 1.0
    assert result["diff_pixels"] == 0
    assert result["total_pixels"] == 64
    assert result["within_threshold"] is True
    assert result["issues"] == []


def test_compare_screenshot_different_images() -> None:
    """Different screenshots yield low similarity and within_threshold False."""
    # Use images with actual visual structure so perceptual hashes differ.
    left_red = Image.new("RGB", (8, 8), (255, 0, 0))
    left_red.paste((0, 0, 255), (4, 0, 8, 8))  # right half blue
    red_blue = _png_b64(left_red)

    right_red = Image.new("RGB", (8, 8), (0, 0, 255))
    right_red.paste((255, 0, 0), (4, 0, 8, 8))  # right half red
    blue_red = _png_b64(right_red)

    result = compare_screenshot(red_blue, current_b64=blue_red, threshold=0.95)

    assert result["ok"] is True
    assert result["error"] is None
    assert result["similarity"] == 0.0
    assert result["diff_pixels"] == 64
    assert result["total_pixels"] == 64
    assert result["within_threshold"] is False
    assert len(result["issues"]) == 1


# ---------------------------------------------------------------------------
# find_visual_issues — synthetic images
# ---------------------------------------------------------------------------
def test_find_visual_issues_white_image_no_issues() -> None:
    """A solid white image reports no clipping or contrast issues."""
    b64 = _png_b64(Image.new("RGB", (10, 10), (255, 255, 255)))

    result = find_visual_issues(b64)

    assert result["ok"] is True
    assert result["error"] is None
    assert result["issue_count"] == 0
    assert result["issues"] == []


def test_find_visual_issues_border_clipping() -> None:
    """A dark pixel at the border is flagged as clipping."""
    img = Image.new("RGB", (10, 10), (255, 255, 255))
    img.putpixel((0, 0), (0, 0, 0))
    b64 = _png_b64(img)

    result = find_visual_issues(b64, check_clipping=True, check_contrast=False, check_overlap=False)

    assert result["ok"] is True
    assert result["issue_count"] == 1
    assert result["issues"][0]["type"] == "clipping"
    assert result["issues"][0]["severity"] == "medium"


def test_find_visual_issues_low_contrast() -> None:
    """A narrow tonal range is flagged as low contrast."""
    img = Image.new("RGB", (10, 10), (125, 125, 125))
    img.putpixel((5, 5), (135, 135, 135))
    b64 = _png_b64(img)

    result = find_visual_issues(b64, check_clipping=False, check_contrast=True, check_overlap=False)

    assert result["ok"] is True
    assert result["issue_count"] == 1
    assert result["issues"][0]["type"] == "contrast"
    assert result["issues"][0]["severity"] == "low"


# ---------------------------------------------------------------------------
# run_ui_scenario / detect_qml_errors — direct with mocked IPC
# ---------------------------------------------------------------------------
def test_run_ui_scenario_mocked_ipc(monkeypatch: pytest.MonkeyPatch) -> None:
    """run_ui_scenario navigates through views via send_navigation_command."""
    sent: list[dict[str, Any]] = []

    def _fake_send(view: str, wait: bool = False, timeout: float = 2.0) -> dict[str, Any]:
        sent.append({"view": view, "wait": wait, "timeout": timeout})
        return {"ok": True, "cmd_id": 1}

    monkeypatch.setattr(
        "skill_manager.mcp.bridge._bug_detection.send_navigation_command", _fake_send
    )
    monkeypatch.setattr(_bug_detection, "headless_qml_enabled", lambda: False)

    result = run_ui_scenario("navigate_library")

    assert result["ok"] is True
    assert result["scenario"] == "navigate_library"
    assert result["result"] == "passed"
    assert len(result["steps"]) == 1
    assert result["steps"][0]["target"] == "Library"
    assert result["steps"][0]["ok"] is True
    # The acknowledgement is awaited so "passed" means the view really changed.
    assert sent == [{"view": "Library", "wait": True, "timeout": 2.0}]


def test_run_ui_scenario_in_process_when_headless(monkeypatch: pytest.MonkeyPatch) -> None:
    """A headless --mcp process navigates its own offscreen window directly.

    It also owns the CommandChannel that would answer an IPC navigation, so
    waiting for an acknowledgement would deadlock; the view is set in-process
    and verified instead (no IPC call at all).
    """

    class _UI:
        def __init__(self) -> None:
            self.currentView = "Library"

    ui = _UI()
    monkeypatch.setattr(_bug_detection, "headless_qml_enabled", lambda: True)
    monkeypatch.setattr(_bug_detection, "_controller_or_none", lambda: SimpleNamespace(ui=ui))
    monkeypatch.setattr(
        _bug_detection,
        "send_navigation_command",
        lambda *a, **kw: pytest.fail("IPC must not be used in headless mode"),
    )

    result = run_ui_scenario("full_tour")

    assert result["result"] == "passed"
    assert [step["target"] for step in result["steps"]] == [
        "Library",
        "QuickCopy",
        "Updates",
        "Settings",
    ]
    assert all(step["verified"] is True for step in result["steps"])
    assert all(step["in_process"] is True for step in result["steps"])
    assert ui.currentView == "Settings"


def test_run_ui_scenario_reports_failed_navigation(monkeypatch: pytest.MonkeyPatch) -> None:
    """An unacknowledged navigation fails the scenario instead of claiming success."""
    monkeypatch.setattr(_bug_detection, "headless_qml_enabled", lambda: False)
    monkeypatch.setattr(
        _bug_detection,
        "send_navigation_command",
        lambda view, wait=False, timeout=2.0: {"ok": False, "error": "timeout"},
    )

    result = run_ui_scenario("navigate_settings")

    assert result["result"] == "failed"
    assert result["steps"][0]["ok"] is False
    assert result["steps"][0]["error"] == "timeout"


def test_detect_qml_errors_direct() -> None:
    """detect_qml_errors returns the diagnostic error buffer shape."""
    result = detect_qml_errors(limit=10)

    assert result["ok"] is True
    assert "count" in result
    assert isinstance(result["errors"], list)
    assert result["error"] is None

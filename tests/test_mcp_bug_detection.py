"""Unit tests for the bug detection MCP tool handlers.

These tests exercise each handler entry point directly while monkeypatching the
``skill_manager.mcp.bridge`` bug detection functions. They never boot Qt or
construct ``AppController``.
"""

from __future__ import annotations

import base64
import io
from typing import Any

import pytest
from PIL import Image

from skill_manager.mcp.models import ToolResult
from skill_manager.mcp.tools import bug_detection as bug_mod


def _png_b64(image: Image.Image) -> str:
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def test_detect_qml_errors_returns_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    """sm_detect_qml_errors returns the bridge's error list."""
    fake = {
        "ok": True,
        "count": 1,
        "errors": [
            {
                "ts": "t1",
                "level": "error",
                "msg": "qml error",
                "file": "a.qml",
                "line": 3,
                "column": 5,
            }
        ],
        "error": None,
    }
    monkeypatch.setattr(bug_mod, "_bridge_detect_qml_errors", lambda limit=50: fake)

    result = bug_mod._HANDLERS["sm_detect_qml_errors"]({"limit": 10})

    assert isinstance(result, ToolResult)
    assert result.ok is True
    assert result.tool == "sm_detect_qml_errors"
    assert result.data == fake
    assert result.data["count"] == 1


def test_detect_qml_errors_defaults_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    """sm_detect_qml_errors forwards limit (default 50) to the bridge."""
    captured = {}

    def _fake(limit: int = 50) -> dict[str, Any]:
        captured["limit"] = limit
        return {"ok": True, "count": 0, "errors": [], "error": None}

    monkeypatch.setattr(bug_mod, "_bridge_detect_qml_errors", _fake)

    bug_mod._HANDLERS["sm_detect_qml_errors"]({})
    assert captured["limit"] == 50

    bug_mod._HANDLERS["sm_detect_qml_errors"]({"limit": 5})
    assert captured["limit"] == 5


def test_compare_screenshot_returns_similarity(monkeypatch: pytest.MonkeyPatch) -> None:
    """sm_compare_screenshot returns the comparison result."""
    baseline = _png_b64(Image.new("RGB", (4, 4), (255, 0, 0)))
    current = _png_b64(Image.new("RGB", (4, 4), (255, 0, 0)))
    fake = {
        "ok": True,
        "similarity": 1.0,
        "diff_pixels": 0,
        "total_pixels": 16,
        "within_threshold": True,
        "issues": [],
        "error": None,
    }
    monkeypatch.setattr(
        bug_mod,
        "_bridge_compare_screenshot",
        lambda baseline_b64="", baseline_name=None, current_b64=None, threshold=0.95: fake,
    )

    result = bug_mod._HANDLERS["sm_compare_screenshot"](
        {"baseline_b64": baseline, "current_b64": current, "threshold": 0.95}
    )

    assert result.ok is True
    assert result.tool == "sm_compare_screenshot"
    assert result.data == fake
    assert result.data["similarity"] == 1.0


def test_compare_screenshot_forwards_args(monkeypatch: pytest.MonkeyPatch) -> None:
    """sm_compare_screenshot forwards baseline/current/threshold to the bridge."""
    captured: dict[str, Any] = {}

    def _fake(
        baseline_b64: str,
        baseline_name: str | None = None,
        current_b64: str | None = None,
        threshold: float = 0.95,
    ) -> dict[str, Any]:
        captured["baseline_b64"] = baseline_b64
        captured["baseline_name"] = baseline_name
        captured["current_b64"] = current_b64
        captured["threshold"] = threshold
        return {
            "ok": True,
            "similarity": 1.0,
            "diff_pixels": 0,
            "total_pixels": 1,
            "within_threshold": True,
            "issues": [],
            "error": None,
        }

    monkeypatch.setattr(bug_mod, "_bridge_compare_screenshot", _fake)

    baseline = _png_b64(Image.new("RGB", (2, 2), (0, 0, 0)))
    bug_mod._HANDLERS["sm_compare_screenshot"](
        {"baseline_b64": baseline, "current_b64": None, "threshold": 0.5}
    )
    assert captured == {
        "baseline_b64": baseline,
        "baseline_name": None,
        "current_b64": None,
        "threshold": 0.5,
    }


def test_compare_screenshot_degrades_on_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """sm_compare_screenshot returns ok=False when the bridge reports failure."""
    monkeypatch.setattr(
        bug_mod,
        "_bridge_compare_screenshot",
        lambda baseline_b64="", baseline_name=None, current_b64=None, threshold=0.95: {
            "ok": False,
            "similarity": 0.0,
            "diff_pixels": 0,
            "total_pixels": 0,
            "within_threshold": False,
            "issues": [],
            "error": "capture_failed",
        },
    )

    baseline = _png_b64(Image.new("RGB", (2, 2), (0, 0, 0)))
    result = bug_mod._HANDLERS["sm_compare_screenshot"]({"baseline_b64": baseline})

    assert result.ok is False
    assert result.error is not None
    assert "capture_failed" in result.error


def test_find_visual_issues_returns_issues(monkeypatch: pytest.MonkeyPatch) -> None:
    """sm_find_visual_issues returns the detected issues."""
    fake = {
        "ok": True,
        "issue_count": 1,
        "issues": [
            {
                "type": "clipping",
                "severity": "medium",
                "description": "Content appears clipped at image edges.",
                "location": {"x": 0, "y": 0, "width": 10, "height": 10},
            }
        ],
        "error": None,
    }
    monkeypatch.setattr(
        bug_mod,
        "_bridge_find_visual_issues",
        lambda image_b64, check_clipping=True, check_contrast=True, check_overlap=True: fake,
    )

    image_b64 = _png_b64(Image.new("RGB", (10, 10), (255, 255, 255)))
    result = bug_mod._HANDLERS["sm_find_visual_issues"](
        {
            "image_b64": image_b64,
            "check_clipping": True,
            "check_contrast": True,
            "check_overlap": False,
        }
    )

    assert result.ok is True
    assert result.tool == "sm_find_visual_issues"
    assert result.data["issue_count"] == 1
    assert result.data["source"] == "provided"
    assert result.data["issues"] == fake["issues"]


def test_find_visual_issues_captures_when_image_omitted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Omitting image_b64 analyses the current app window (headless or live)."""
    captured: dict[str, Any] = {}

    def _bridge(image_b64: str, **kwargs: Any) -> dict[str, Any]:
        captured["image_b64"] = image_b64
        return {"ok": True, "issue_count": 0, "issues": [], "error": None}

    monkeypatch.setattr(bug_mod, "_bridge_find_visual_issues", _bridge)
    monkeypatch.setattr(
        bug_mod,
        "_bridge_capture_app_window_info",
        lambda **kwargs: {
            "image_b64": "CAPTURED",
            "width": 800,
            "height": 600,
            "source": "headless-qml",
            "error": None,
        },
    )

    result = bug_mod._HANDLERS["sm_find_visual_issues"]({})

    assert result.ok is True
    assert result.data["source"] == "headless-qml"
    assert captured["image_b64"] == "CAPTURED"


def test_find_visual_issues_reports_capture_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failed auto-capture is reported instead of analysing an empty image."""
    monkeypatch.setattr(
        bug_mod,
        "_bridge_capture_app_window_info",
        lambda **kwargs: {
            "image_b64": None,
            "width": 0,
            "height": 0,
            "source": None,
            "error": "not running",
        },
    )

    result = bug_mod._HANDLERS["sm_find_visual_issues"]({})

    assert result.ok is False
    assert result.error is not None
    assert "not running" in result.error


def test_run_ui_scenario_returns_steps(monkeypatch: pytest.MonkeyPatch) -> None:
    """sm_run_ui_scenario returns the scenario steps and result."""
    fake = {
        "ok": True,
        "scenario": "navigate_library",
        "steps": [
            {
                "step": 1,
                "action": "navigate",
                "target": "Library",
                "ok": True,
                "error": None,
                "screenshot": None,
            }
        ],
        "result": "passed",
        "error": None,
    }
    monkeypatch.setattr(
        bug_mod,
        "_bridge_run_ui_scenario",
        lambda scenario, params=None: fake,
    )

    result = bug_mod._HANDLERS["sm_run_ui_scenario"]({"scenario": "navigate_library", "params": {}})

    assert result.ok is True
    assert result.tool == "sm_run_ui_scenario"
    assert result.data == fake
    assert result.data["result"] == "passed"


def test_bug_detection_tool_schemas_present() -> None:
    """All bug detection tools are declared in TOOL_SCHEMAS with valid input schemas."""
    assert set(bug_mod.TOOL_SCHEMAS) == {
        "sm_detect_qml_errors",
        "sm_compare_screenshot",
        "sm_find_visual_issues",
        "sm_run_ui_scenario",
    }

    for name, meta in bug_mod.TOOL_SCHEMAS.items():
        assert meta["description"], f"{name} missing description"
        assert "inputSchema" in meta
        assert meta["inputSchema"]["type"] == "object"
        assert "annotations" in meta

    assert bug_mod.TOOL_SCHEMAS["sm_compare_screenshot"]["inputSchema"]["required"] == []
    props = bug_mod.TOOL_SCHEMAS["sm_compare_screenshot"]["inputSchema"]["properties"]
    assert "baseline_b64" in props
    assert "baseline_name" in props
    assert "current_b64" in props
    assert "threshold" in props
    assert bug_mod.TOOL_SCHEMAS["sm_find_visual_issues"]["inputSchema"]["required"] == []
    assert bug_mod.TOOL_SCHEMAS["sm_run_ui_scenario"]["inputSchema"]["required"] == [
        "scenario",
    ]
    scenarios = bug_mod.TOOL_SCHEMAS["sm_run_ui_scenario"]["inputSchema"]["properties"]["scenario"][
        "enum"
    ]
    assert set(scenarios) == {
        "navigate_library",
        "navigate_quickcopy",
        "navigate_updates",
        "navigate_settings",
        "full_tour",
    }


def test_compare_screenshot_forwards_baseline_name(monkeypatch: pytest.MonkeyPatch) -> None:
    """sm_compare_screenshot forwards baseline_name to the bridge."""
    captured: dict[str, Any] = {}

    def _fake(
        baseline_b64: str = "",
        baseline_name: str | None = None,
        current_b64: str | None = None,
        threshold: float = 0.95,
    ) -> dict[str, Any]:
        captured["baseline_b64"] = baseline_b64
        captured["baseline_name"] = baseline_name
        captured["current_b64"] = current_b64
        captured["threshold"] = threshold
        return {
            "ok": True,
            "similarity": 1.0,
            "phash_similarity": 1.0,
            "diff_pixels": 0,
            "total_pixels": 1,
            "within_threshold": True,
            "issues": [],
            "error": None,
        }

    monkeypatch.setattr(bug_mod, "_bridge_compare_screenshot", _fake)

    bug_mod._HANDLERS["sm_compare_screenshot"]({"baseline_name": "mybaseline", "threshold": 0.9})
    assert captured == {
        "baseline_b64": "",
        "baseline_name": "mybaseline",
        "current_b64": None,
        "threshold": 0.9,
    }

"""Unit tests for the UI inspection MCP tool handlers.

These tests exercise each handler entry point directly while monkeypatching the
``skill_manager.mcp.bridge`` UI inspection functions. They never boot Qt or
construct ``AppController``.
"""

from __future__ import annotations

from typing import Any

import pytest

from skill_manager.mcp.models import ToolResult
from skill_manager.mcp.tools import ui_inspection as ui_mod


def test_get_current_view_returns_view(monkeypatch: pytest.MonkeyPatch) -> None:
    """sm_get_current_view returns the bridge's current view in a ToolResult."""
    fake = {"view": "Library", "ok": True, "error": None}
    monkeypatch.setattr(ui_mod, "_bridge_get_current_view", lambda: fake)

    result = ui_mod._HANDLERS["sm_get_current_view"]({})

    assert isinstance(result, ToolResult)
    assert result.ok is True
    assert result.tool == "sm_get_current_view"
    assert result.data == fake
    assert result.error is None


def test_get_current_view_forwards_to_bridge(monkeypatch: pytest.MonkeyPatch) -> None:
    """sm_get_current_view calls the bridge with no args."""
    called = False

    def _fake() -> dict[str, Any]:
        nonlocal called
        called = True
        return {"view": "QuickCopy", "ok": True, "error": None}

    monkeypatch.setattr(ui_mod, "_bridge_get_current_view", _fake)
    ui_mod._HANDLERS["sm_get_current_view"]({})
    assert called is True


def test_get_current_view_degrades_on_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """sm_get_current_view returns ok=False when the bridge reports failure."""
    monkeypatch.setattr(
        ui_mod,
        "_bridge_get_current_view",
        lambda: {"view": "unknown", "ok": False, "error": "no_controller"},
    )

    result = ui_mod._HANDLERS["sm_get_current_view"]({})

    assert result.ok is False
    assert result.tool == "sm_get_current_view"
    assert result.error is not None
    assert "no_controller" in result.error


def test_get_current_view_exception_becomes_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """A bridge exception degrades to a ToolResult error envelope."""
    monkeypatch.setattr(
        ui_mod,
        "_bridge_get_current_view",
        lambda: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    result = ui_mod._HANDLERS["sm_get_current_view"]({})

    assert result.ok is False
    assert result.error is not None
    assert "boom" in result.error


def test_inspect_qml_tree_returns_tree(monkeypatch: pytest.MonkeyPatch) -> None:
    """sm_inspect_qml_tree returns the bridge's tree snapshot."""
    fake = {
        "ok": True,
        "root_count": 2,
        "tree": [
            {
                "object_name": "root",
                "class_name": "QQuickWindow",
                "visible": True,
                "enabled": True,
                "x": 0,
                "y": 0,
                "width": 800,
                "height": 600,
                "children": [],
            }
        ],
        "error": None,
    }
    monkeypatch.setattr(ui_mod, "_bridge_inspect_qml_tree", lambda max_depth: fake)

    result = ui_mod._HANDLERS["sm_inspect_qml_tree"]({"max_depth": 3})

    assert result.ok is True
    assert result.tool == "sm_inspect_qml_tree"
    assert result.data == fake
    assert result.data["root_count"] == 2


def test_inspect_qml_tree_defaults_max_depth(monkeypatch: pytest.MonkeyPatch) -> None:
    """sm_inspect_qml_tree forwards max_depth (default 5) to the bridge."""
    captured = {}

    def _fake(max_depth: int = 5) -> dict[str, Any]:
        captured["max_depth"] = max_depth
        return {"ok": True, "root_count": 0, "tree": [], "error": None}

    monkeypatch.setattr(ui_mod, "_bridge_inspect_qml_tree", _fake)

    ui_mod._HANDLERS["sm_inspect_qml_tree"]({})
    assert captured["max_depth"] == 5

    ui_mod._HANDLERS["sm_inspect_qml_tree"]({"max_depth": 10})
    assert captured["max_depth"] == 10


def test_get_pixel_color_returns_color(monkeypatch: pytest.MonkeyPatch) -> None:
    """sm_get_pixel_color returns the sampled RGB color."""
    fake = {"ok": True, "color": "#ff0000", "r": 255, "g": 0, "b": 0, "error": None}
    monkeypatch.setattr(ui_mod, "_bridge_get_pixel_color", lambda x, y: fake)

    result = ui_mod._HANDLERS["sm_get_pixel_color"]({"x": 10, "y": 20})

    assert result.ok is True
    assert result.tool == "sm_get_pixel_color"
    assert result.data == fake
    assert result.data["color"] == "#ff0000"


def test_get_pixel_color_forwards_coordinates(monkeypatch: pytest.MonkeyPatch) -> None:
    """sm_get_pixel_color forwards x and y to the bridge."""
    captured: dict[str, Any] = {}

    def _fake(x: int, y: int) -> dict[str, Any]:
        captured["x"] = x
        captured["y"] = y
        return {"ok": True, "color": "#000000", "r": 0, "g": 0, "b": 0, "error": None}

    monkeypatch.setattr(ui_mod, "_bridge_get_pixel_color", _fake)

    ui_mod._HANDLERS["sm_get_pixel_color"]({"x": 3, "y": 7})
    assert captured == {"x": 3, "y": 7}


def test_get_pixel_color_degrades_on_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """sm_get_pixel_color returns ok=False when the bridge reports failure."""
    monkeypatch.setattr(
        ui_mod,
        "_bridge_get_pixel_color",
        lambda x, y: {
            "ok": False,
            "color": "#000000",
            "r": 0,
            "g": 0,
            "b": 0,
            "error": "coordinate_out_of_bounds",
        },
    )

    result = ui_mod._HANDLERS["sm_get_pixel_color"]({"x": 9999, "y": 9999})

    assert result.ok is False
    assert result.error is not None
    assert "coordinate_out_of_bounds" in result.error


def test_ui_inspection_tool_schemas_present() -> None:
    """All UI inspection tools are declared in TOOL_SCHEMAS with valid input schemas."""
    assert set(ui_mod.TOOL_SCHEMAS) == {
        "sm_get_current_view",
        "sm_inspect_qml_tree",
        "sm_get_pixel_color",
    }

    for name, meta in ui_mod.TOOL_SCHEMAS.items():
        assert meta["description"], f"{name} missing description"
        assert "inputSchema" in meta
        assert meta["inputSchema"]["type"] == "object"
        assert "annotations" in meta

    assert ui_mod.TOOL_SCHEMAS["sm_get_pixel_color"]["inputSchema"]["required"] == [
        "x",
        "y",
    ]
    assert (
        ui_mod.TOOL_SCHEMAS["sm_inspect_qml_tree"]["inputSchema"]["properties"]["max_depth"][
            "default"
        ]
        == 5
    )

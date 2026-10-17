"""Unit tests for the ``sm_get_frame_timing`` MCP tool handler and bridge.

These tests exercise the handler entry point directly while monkeypatching the
bridge function. They never boot Qt or construct ``AppController``.
"""

from __future__ import annotations

from typing import Any

import pytest

from skill_manager.mcp.models import ToolResult
from skill_manager.mcp.tools import frame_timing as ft_mod


def test_get_frame_timing_returns_result(monkeypatch: pytest.MonkeyPatch) -> None:
    """sm_get_frame_timing returns the bridge's timing result."""
    fake = {
        "ok": True,
        "duration_s": 2.0,
        "frame_count": 120,
        "fps": 60.0,
        "avg_frame_ms": 16.67,
        "p95_frame_ms": 18.5,
        "max_frame_ms": 45.2,
        "dropped_frames": 3,
        "samples": [],
        "error": None,
    }
    monkeypatch.setattr(
        ft_mod,
        "_bridge_get_frame_timing",
        lambda duration_s=2.0, **kwargs: fake,
    )

    result = ft_mod.get_handlers()["sm_get_frame_timing"]({"duration_s": 2.0})

    assert isinstance(result, ToolResult)
    assert result.ok is True
    assert result.tool == "sm_get_frame_timing"
    assert result.data == fake
    assert result.data["fps"] == 60.0


def test_get_frame_timing_forwards_duration_s(monkeypatch: pytest.MonkeyPatch) -> None:
    """sm_get_frame_timing forwards duration_s to the bridge."""
    captured: dict[str, Any] = {}

    def _fake(duration_s: float = 2.0, force_render: bool = False) -> dict[str, Any]:
        captured["duration_s"] = duration_s
        return {
            "ok": True,
            "duration_s": duration_s,
            "frame_count": 0,
            "fps": 0.0,
            "avg_frame_ms": 0.0,
            "p95_frame_ms": 0.0,
            "max_frame_ms": 0.0,
            "dropped_frames": 0,
            "samples": [],
            "error": None,
        }

    monkeypatch.setattr(ft_mod, "_bridge_get_frame_timing", _fake)

    ft_mod.get_handlers()["sm_get_frame_timing"]({"duration_s": 5.0})
    assert captured["duration_s"] == 5.0


def test_get_frame_timing_defaults_duration_s(monkeypatch: pytest.MonkeyPatch) -> None:
    """sm_get_frame_timing defaults duration_s to 2.0."""
    captured: dict[str, Any] = {}

    def _fake(duration_s: float = 2.0, force_render: bool = False) -> dict[str, Any]:
        captured["duration_s"] = duration_s
        return {
            "ok": True,
            "duration_s": duration_s,
            "frame_count": 0,
            "fps": 0.0,
            "avg_frame_ms": 0.0,
            "p95_frame_ms": 0.0,
            "max_frame_ms": 0.0,
            "dropped_frames": 0,
            "samples": [],
            "error": None,
        }

    monkeypatch.setattr(ft_mod, "_bridge_get_frame_timing", _fake)

    ft_mod.get_handlers()["sm_get_frame_timing"]({})
    assert captured["duration_s"] == 2.0


def test_get_frame_timing_degrades_on_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """sm_get_frame_timing returns ok=False when the bridge reports failure."""
    monkeypatch.setattr(
        ft_mod,
        "_bridge_get_frame_timing",
        lambda duration_s=2.0, **kwargs: {
            "ok": False,
            "duration_s": duration_s,
            "frame_count": 0,
            "fps": 0.0,
            "avg_frame_ms": 0.0,
            "p95_frame_ms": 0.0,
            "max_frame_ms": 0.0,
            "dropped_frames": 0,
            "samples": [],
            "error": "qml_engine_unavailable",
        },
    )

    result = ft_mod.get_handlers()["sm_get_frame_timing"]({"duration_s": 2.0})

    assert result.ok is False
    assert result.error is not None
    assert "qml_engine_unavailable" in result.error


def test_get_frame_timing_exception_becomes_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """A bridge exception degrades to a ToolResult error envelope."""
    monkeypatch.setattr(
        ft_mod,
        "_bridge_get_frame_timing",
        lambda duration_s=2.0, **kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    result = ft_mod.get_handlers()["sm_get_frame_timing"]({"duration_s": 2.0})

    assert result.ok is False
    assert result.error is not None
    assert "boom" in result.error


def test_frame_timing_tool_schema_declared() -> None:
    """sm_get_frame_timing is declared in TOOL_SCHEMAS with valid input schema."""
    assert "sm_get_frame_timing" in ft_mod.TOOL_SCHEMAS
    schema = ft_mod.TOOL_SCHEMAS["sm_get_frame_timing"]
    assert schema["description"]
    assert schema["inputSchema"]["type"] == "object"
    assert "duration_s" in schema["inputSchema"]["properties"]
    assert "force_render" in schema["inputSchema"]["properties"]
    assert schema["inputSchema"]["properties"]["force_render"]["default"] is False
    assert schema["annotations"]["readOnlyHint"] is True


def test_get_frame_timing_forwards_force_render(monkeypatch: pytest.MonkeyPatch) -> None:
    """sm_get_frame_timing forwards force_render to the bridge."""
    captured: dict[str, Any] = {}

    def _fake(duration_s: float = 2.0, force_render: bool = False) -> dict[str, Any]:
        captured["duration_s"] = duration_s
        captured["force_render"] = force_render
        return {"ok": True, "duration_s": duration_s, "mode": "forced_60hz"}

    monkeypatch.setattr(ft_mod, "_bridge_get_frame_timing", _fake)

    result = ft_mod.get_handlers()["sm_get_frame_timing"]({"duration_s": 2.0, "force_render": True})

    assert captured == {"duration_s": 2.0, "force_render": True}
    assert result.ok is True
    assert result.data is not None
    assert result.data["mode"] == "forced_60hz"


def test_get_frame_timing_force_render_defaults_false(monkeypatch: pytest.MonkeyPatch) -> None:
    """force_render defaults to False so natural sampling is the default."""
    captured: dict[str, Any] = {}

    def _fake(duration_s: float = 2.0, force_render: bool = False) -> dict[str, Any]:
        captured["force_render"] = force_render
        return {"ok": True, "duration_s": duration_s}

    monkeypatch.setattr(ft_mod, "_bridge_get_frame_timing", _fake)

    ft_mod.get_handlers()["sm_get_frame_timing"]({})

    assert captured["force_render"] is False

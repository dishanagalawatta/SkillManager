"""Unit tests for the ``sm_get_frame_timing`` MCP tool handler and bridge.

These tests exercise the handler entry point directly while monkeypatching the
bridge function. They never boot Qt or construct ``AppController``.
"""

from __future__ import annotations

import sys
import time
from types import SimpleNamespace
from typing import Any

import pytest

import skill_manager.mcp.bridge._frame_timing as ft_bridge
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


# ---------------------------------------------------------------------------
# bridge.get_frame_timing — validation, the render-loop guard and the sampling
#
# The handler tests above stub the bridge, so they never touch the statistics,
# the live-render-loop guard or the graceful degradation paths. Sampling needs a
# real QQuickWindow (the bridge checks isinstance), so these tests use `qtbot`
# for the QApplication and drive the window's signals from a QTimer.
# ---------------------------------------------------------------------------
def _engine_with(roots: list[Any]) -> Any:
    """Fake QML engine returning *roots*."""
    return SimpleNamespace(rootObjects=lambda: list(roots))


def _explode(*_args: Any, **_kwargs: Any) -> Any:
    """Fail loudly if a guarded code path is reached."""
    raise AssertionError("should not be reached")


# Frame budget taken from the bridge module, used to force "dropped" samples.
_DROP_THRESHOLD_S = ft_bridge._DROP_THRESHOLD_MS / 1000.0


def _patched_window(monkeypatch: pytest.MonkeyPatch) -> Any:
    """A real QQuickWindow wired as the sampling target, render-loop guard bypassed."""
    from PySide6.QtQuick import QQuickWindow

    window = QQuickWindow()
    monkeypatch.setattr(ft_bridge, "_controller_or_none", lambda: SimpleNamespace())
    monkeypatch.setattr(ft_bridge, "ensure_qml_engine", lambda: _engine_with([window]))
    monkeypatch.setattr(ft_bridge, "_window_has_live_render_loop", lambda _window: True)
    return window


@pytest.mark.parametrize(
    ("window", "expected"),
    [
        (SimpleNamespace(isExposed=lambda: True), True),
        (SimpleNamespace(isExposed=lambda: False), False),
        (SimpleNamespace(isExposed=lambda: True, isVisible=lambda: False), True),
        (SimpleNamespace(isExposed=lambda: False, isVisible=lambda: True), False),
        (SimpleNamespace(isVisible=lambda: True), True),
        (SimpleNamespace(isVisible=lambda: False), False),
        (SimpleNamespace(), False),
    ],
)
def test_window_has_live_render_loop(window: Any, expected: bool) -> None:
    """isExposed() is authoritative; isVisible() is the fallback."""
    assert ft_bridge._window_has_live_render_loop(window) is expected


def test_fallback_frame_timing_envelope() -> None:
    """The degraded envelope keeps the result shape and explains itself."""
    result = ft_bridge._fallback_frame_timing(2.0, "no engine")

    assert result["ok"] is True
    assert result["mode"] == "unavailable"
    assert result["frame_count"] == 0
    assert result["samples"] == []
    assert result["error"] == "no engine"
    assert result["duration_s"] == 2.0


@pytest.mark.parametrize("bad_duration", [0.1, 30.5])
def test_get_frame_timing_rejects_out_of_range_duration(
    monkeypatch: pytest.MonkeyPatch, bad_duration: float
) -> None:
    """Duration bounds are checked before any controller/engine access."""
    monkeypatch.setattr(ft_bridge, "_controller_or_none", _explode)

    result = ft_bridge.get_frame_timing(bad_duration)

    assert result["ok"] is False
    assert result["mode"] == "invalid"
    assert "duration_s must be between 0.5 and 30" in result["error"]


def test_get_frame_timing_rejects_non_numeric_duration() -> None:
    """A non-numeric duration degrades instead of raising."""
    result = ft_bridge.get_frame_timing("soon")  # type: ignore[arg-type]

    assert result["ok"] is False
    assert result["mode"] == "invalid"
    assert "invalid duration_s" in result["error"]


@pytest.mark.parametrize(
    ("controller", "engine", "reason"),
    [
        (None, "default", "AppController unavailable"),
        ("default", None, "QML engine not available"),
    ],
)
def test_get_frame_timing_falls_back_without_controller_or_engine(
    monkeypatch: pytest.MonkeyPatch, controller: Any, engine: Any, reason: str
) -> None:
    """Missing controller/engine degrade with an actionable reason."""
    monkeypatch.setattr(
        ft_bridge, "_controller_or_none", lambda: None if controller is None else SimpleNamespace()
    )
    monkeypatch.setattr(
        ft_bridge,
        "ensure_qml_engine",
        (lambda: None) if engine is None else (lambda: _engine_with([])),
    )

    result = ft_bridge.get_frame_timing(1.0)

    assert result["mode"] == "unavailable"
    assert result["frame_count"] == 0
    assert result["error"] == reason


def test_get_frame_timing_falls_back_without_roots(monkeypatch: pytest.MonkeyPatch) -> None:
    """An engine with no root objects degrades rather than raising IndexError."""
    monkeypatch.setattr(ft_bridge, "_controller_or_none", lambda: SimpleNamespace())
    monkeypatch.setattr(ft_bridge, "ensure_qml_engine", lambda: _engine_with([]))

    result = ft_bridge.get_frame_timing(1.0)

    assert result["mode"] == "unavailable"
    assert result["error"] == "no QML root objects"


def test_get_frame_timing_falls_back_when_root_is_not_a_window(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A non-QQuickWindow root cannot provide frame signals."""
    monkeypatch.setattr(ft_bridge, "_controller_or_none", lambda: SimpleNamespace())
    monkeypatch.setattr(ft_bridge, "ensure_qml_engine", lambda: _engine_with([SimpleNamespace()]))

    result = ft_bridge.get_frame_timing(1.0)

    assert result["mode"] == "unavailable"
    assert result["error"] == "root object is not a QQuickWindow"


def test_get_frame_timing_falls_back_when_pyside_import_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A broken PySide6 binding degrades instead of propagating ImportError."""
    monkeypatch.setattr(ft_bridge, "_controller_or_none", lambda: SimpleNamespace())
    monkeypatch.setattr(ft_bridge, "ensure_qml_engine", lambda: _engine_with([object()]))
    monkeypatch.setitem(sys.modules, "PySide6.QtCore", None)

    result = ft_bridge.get_frame_timing(1.0)

    assert result["mode"] == "unavailable"
    assert "PySide6 import failed" in result["error"]


def test_offscreen_qquickwindow_has_no_live_render_loop(qtbot: Any) -> None:
    """An unexposed (offscreen) window renders nothing — the headless case."""
    from PySide6.QtQuick import QQuickWindow

    window = QQuickWindow()

    assert ft_bridge._window_has_live_render_loop(window) is False


def test_get_frame_timing_reports_missing_render_loop(
    qtbot: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A window without a live render loop degrades with the reason spelled out."""
    from PySide6.QtQuick import QQuickWindow

    window = QQuickWindow()
    monkeypatch.setattr(ft_bridge, "_controller_or_none", lambda: SimpleNamespace())
    monkeypatch.setattr(ft_bridge, "ensure_qml_engine", lambda: _engine_with([window]))
    monkeypatch.setattr(ft_bridge, "_window_has_live_render_loop", lambda _window: False)

    result = ft_bridge.get_frame_timing(0.5)

    assert result["mode"] == "unavailable"
    assert "no live render loop" in result["error"]


def test_get_frame_timing_reports_idle_window(qtbot: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    """A live window that renders nothing explains the zero-frame result."""
    _patched_window(monkeypatch)

    result = ft_bridge.get_frame_timing(0.5)

    assert result["ok"] is True
    assert result["mode"] == "natural"
    assert result["frame_count"] == 0
    assert result["fps"] == 0.0
    assert "no frames observed" in result["error"]


def test_get_frame_timing_computes_statistics_from_frames(
    qtbot: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Emitted frames produce fps/avg/p95/max and dropped-frame counts."""
    from PySide6.QtCore import QTimer

    window = _patched_window(monkeypatch)

    def _emit_frames() -> None:
        for _ in range(3):
            window.beforeRendering.emit()
            time.sleep(_DROP_THRESHOLD_S * 1.5)  # each frame misses the 60 Hz budget
            window.afterRendering.emit()

    QTimer.singleShot(20, _emit_frames)

    result = ft_bridge.get_frame_timing(0.5)

    assert result["ok"] is True
    assert result["mode"] == "natural"
    assert result["frame_count"] == 3
    assert [sample["frame_index"] for sample in result["samples"]] == [0, 1, 2]
    assert all(sample["duration_ms"] >= 0 for sample in result["samples"])
    assert result["dropped_frames"] == 3
    assert result["fps"] == 6.0
    assert result["avg_frame_ms"] > 0
    assert result["max_frame_ms"] >= result["avg_frame_ms"]
    assert result["p95_frame_ms"] <= result["max_frame_ms"]


def test_get_frame_timing_force_render_reports_forced_mode(
    qtbot: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """force_render drives the redraw cadence and labels the mode accordingly."""
    from PySide6.QtCore import QTimer

    window = _patched_window(monkeypatch)

    def _emit_one_frame() -> None:
        window.beforeRendering.emit()
        window.afterRendering.emit()

    QTimer.singleShot(20, _emit_one_frame)

    result = ft_bridge.get_frame_timing(0.5, force_render=True)

    assert result["mode"] == "forced_60hz"
    assert result["frame_count"] == 1

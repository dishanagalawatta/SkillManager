"""Unit tests for the performance MCP tool handlers.

These tests exercise each handler entry point directly while monkeypatching the
``skill_manager.mcp.bridge`` performance functions. They never boot Qt or
construct ``AppController``.
"""

from __future__ import annotations

from typing import Any

import pytest

from skill_manager.mcp.models import ToolResult
from skill_manager.mcp.tools import performance as perf_mod


def test_get_performance_metrics_returns_metrics(monkeypatch: pytest.MonkeyPatch) -> None:
    """sm_get_performance_metrics returns the bridge's metrics in a ToolResult."""
    fake = {
        "ok": True,
        "memory_mb": 128.5,
        "cpu_percent": 4.2,
        "thread_count": 7,
        "process_id": 4242,
        "uptime_seconds": 123.4,
        "error": None,
    }
    monkeypatch.setattr(perf_mod, "_bridge_get_performance_metrics", lambda: fake)

    result = perf_mod._HANDLERS["sm_get_performance_metrics"]({})

    assert isinstance(result, ToolResult)
    assert result.ok is True
    assert result.tool == "sm_get_performance_metrics"
    assert result.data == fake
    assert result.error is None


def test_get_performance_metrics_forwards_to_bridge(monkeypatch: pytest.MonkeyPatch) -> None:
    """sm_get_performance_metrics calls the bridge with no args."""
    called = False

    def _fake() -> dict[str, Any]:
        nonlocal called
        called = True
        return {
            "ok": True,
            "memory_mb": 0.0,
            "cpu_percent": 0.0,
            "thread_count": 1,
            "process_id": 1,
            "uptime_seconds": 0.0,
            "error": None,
        }

    monkeypatch.setattr(perf_mod, "_bridge_get_performance_metrics", _fake)
    perf_mod._HANDLERS["sm_get_performance_metrics"]({})
    assert called is True


def test_get_performance_metrics_degrades_on_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """sm_get_performance_metrics returns ok=False when the bridge reports failure."""
    monkeypatch.setattr(
        perf_mod,
        "_bridge_get_performance_metrics",
        lambda: {
            "ok": False,
            "memory_mb": 0.0,
            "cpu_percent": 0.0,
            "thread_count": 0,
            "process_id": 0,
            "uptime_seconds": 0.0,
            "error": "psutil_unavailable",
        },
    )

    result = perf_mod._HANDLERS["sm_get_performance_metrics"]({})

    assert result.ok is False
    assert result.tool == "sm_get_performance_metrics"
    assert result.error is not None
    assert "psutil_unavailable" in result.error


def test_get_performance_metrics_exception_becomes_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """A bridge exception degrades to a ToolResult error envelope."""
    monkeypatch.setattr(
        perf_mod,
        "_bridge_get_performance_metrics",
        lambda: (_ for _ in ()).throw(RuntimeError("metrics_failed")),
    )

    result = perf_mod._HANDLERS["sm_get_performance_metrics"]({})

    assert result.ok is False
    assert result.error is not None
    assert "metrics_failed" in result.error


def test_measure_startup_time_returns_timing(monkeypatch: pytest.MonkeyPatch) -> None:
    """sm_measure_startup_time returns the bridge's startup timing."""
    fake = {
        "ok": True,
        "startup_ms": 450.25,
        "timestamp": "2026-01-01T00:00:00+00:00",
        "error": None,
    }
    monkeypatch.setattr(perf_mod, "_bridge_measure_startup_time", lambda: fake)

    result = perf_mod._HANDLERS["sm_measure_startup_time"]({})

    assert result.ok is True
    assert result.tool == "sm_measure_startup_time"
    assert result.data == fake
    assert result.data["startup_ms"] == 450.25


def test_measure_startup_time_degrades_on_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """sm_measure_startup_time returns ok=False when the bridge reports failure."""
    monkeypatch.setattr(
        perf_mod,
        "_bridge_measure_startup_time",
        lambda: {"ok": False, "startup_ms": 0.0, "timestamp": "", "error": "timer_failed"},
    )

    result = perf_mod._HANDLERS["sm_measure_startup_time"]({})

    assert result.ok is False
    assert result.error is not None
    assert "timer_failed" in result.error


def test_performance_tool_schemas_present() -> None:
    """Both performance tools are declared in TOOL_SCHEMAS with valid input schemas."""
    assert set(perf_mod.TOOL_SCHEMAS) == {
        "sm_get_performance_metrics",
        "sm_measure_startup_time",
    }

    for name, meta in perf_mod.TOOL_SCHEMAS.items():
        assert meta["description"], f"{name} missing description"
        assert meta["inputSchema"] == {"type": "object", "properties": {}}
        assert "annotations" in meta

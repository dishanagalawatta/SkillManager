"""Read-only performance MCP tools: process metrics and startup timing."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from skill_manager.mcp.bridge import (
    get_performance_metrics as _bridge_get_performance_metrics,
    measure_startup_time as _bridge_measure_startup_time,
)
from skill_manager.mcp.models import ToolResult, err, ok

# ---------------------------------------------------------------------------
# Tool schemas with annotations
# ---------------------------------------------------------------------------
TOOL_SCHEMAS: dict[str, dict[str, Any]] = {
    "sm_get_performance_metrics": {
        "description": "Snapshot process-level performance metrics (resident memory, CPU percent, thread count, pid, uptime). Read-only.",
        "annotations": {
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
        "inputSchema": {"type": "object", "properties": {}},
    },
    "sm_measure_startup_time": {
        "description": "Measure application startup time (elapsed since the bridge loaded). Read-only.",
        "annotations": {
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
        "inputSchema": {"type": "object", "properties": {}},
    },
}


# ---------------------------------------------------------------------------
# Tool handlers (return ToolResult)
# ---------------------------------------------------------------------------
def _handle_get_performance_metrics(_args: dict[str, Any]) -> ToolResult:
    try:
        result = _bridge_get_performance_metrics()
        if result.get("ok"):
            return ok("sm_get_performance_metrics", result)
        return err(
            "sm_get_performance_metrics", result.get("error", "failed to read performance metrics")
        )
    except Exception as exc:  # noqa: BLE001
        return err("sm_get_performance_metrics", str(exc))


def _handle_measure_startup_time(_args: dict[str, Any]) -> ToolResult:
    try:
        result = _bridge_measure_startup_time()
        if result.get("ok"):
            return ok("sm_measure_startup_time", result)
        return err("sm_measure_startup_time", result.get("error", "failed to measure startup time"))
    except Exception as exc:  # noqa: BLE001
        return err("sm_measure_startup_time", str(exc))


# ---------------------------------------------------------------------------
# Dispatch table
# ---------------------------------------------------------------------------
_HANDLERS: dict[str, Callable[[dict[str, Any]], ToolResult]] = {
    "sm_get_performance_metrics": _handle_get_performance_metrics,
    "sm_measure_startup_time": _handle_measure_startup_time,
}


def get_handlers(_allow_write: bool = False) -> dict[str, Callable[..., Any]]:
    return dict(_HANDLERS)


__all__ = ["TOOL_SCHEMAS", "get_handlers"]

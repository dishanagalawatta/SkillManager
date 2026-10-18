"""Read-only ``sm_get_frame_timing`` MCP tool for QML render performance profiling.

Captures QML render frame timings over a sampling window and reports FPS,
avg/p95/max frame duration, and dropped frames. Read-only; never mutates app
state. Works in headless ``--mcp`` mode by rendering ``Main.qml`` offscreen on
demand; pass ``force_render`` to measure a forced redraw cadence, since an idle
window renders no frames.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, Field

from skill_manager.core.analytics import capture_mcp_tool_call
from skill_manager.mcp.bridge import get_frame_timing as _bridge_get_frame_timing
from skill_manager.mcp.models import ToolResult, err, ok


# ---------------------------------------------------------------------------
# Request model
# ---------------------------------------------------------------------------
class _GetFrameTimingArgs(BaseModel):
    duration_s: float = Field(
        default=2.0, ge=0.5, le=30.0, description="Sampling window in seconds."
    )
    force_render: bool = Field(
        default=False,
        description="Drive a 60 Hz update() cadence so an idle window still renders.",
    )


# ---------------------------------------------------------------------------
# Tool schema with annotations
# ---------------------------------------------------------------------------
TOOL_SCHEMAS: dict[str, dict[str, Any]] = {
    "sm_get_frame_timing": {
        "description": (
            "Capture QML render frame timings over a sampling window and report "
            "FPS, avg/p95/max frame duration, and dropped frames. Read-only. "
            "Works headless (offscreen render). An idle window renders nothing, "
            "so pass force_render=true to drive a 60 Hz redraw cadence; 'mode' "
            "in the result reports whether frames were forced or natural. When "
            "no render loop exists the result reports ok:true with zero frames "
            "and an explanatory 'error'."
        ),
        "annotations": {
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
        "inputSchema": {
            "type": "object",
            "properties": {
                "duration_s": {
                    "type": "number",
                    "default": 2.0,
                    "minimum": 0.5,
                    "maximum": 30.0,
                    "description": "Sampling window in seconds (0.5-30).",
                },
                "force_render": {
                    "type": "boolean",
                    "default": False,
                    "description": "Drive a 60 Hz update() cadence so an idle window still renders frames.",
                },
            },
            "required": [],
        },
    },
}


# ---------------------------------------------------------------------------
# Tool handler
# ---------------------------------------------------------------------------
def _handle_get_frame_timing(args: dict[str, Any]) -> ToolResult:
    try:
        parsed = _GetFrameTimingArgs(**args)
        capture_mcp_tool_call(
            "mcp_tool_call",
            "sm_get_frame_timing",
            {
                "duration_s": parsed.duration_s,
                "force_render": parsed.force_render,
            },
        )
        result = _bridge_get_frame_timing(
            duration_s=parsed.duration_s, force_render=parsed.force_render
        )
        if result.get("ok"):
            return ok("sm_get_frame_timing", result)
        return err("sm_get_frame_timing", result.get("error", "frame timing failed"))
    except Exception as exc:  # noqa: BLE001
        return err("sm_get_frame_timing", str(exc))


# ---------------------------------------------------------------------------
# Public dispatch surface
# ---------------------------------------------------------------------------
def get_handlers(_allow_write: bool = False) -> dict[str, Callable[..., Any]]:
    def _dispatch(args: dict[str, Any]) -> ToolResult:
        return _handle_get_frame_timing(args)

    return {"sm_get_frame_timing": _dispatch}


__all__ = ["TOOL_SCHEMAS", "get_handlers"]

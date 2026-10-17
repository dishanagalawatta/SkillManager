"""Read-only UI inspection MCP tools: current QML view, QML tree, pixel color.

Wraps the ``skill_manager.mcp.bridge`` UI inspection functions into MCP tool
handlers. All tools are read-only and degrade to ``ok:false`` when the live GUI
is unavailable.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from skill_manager.mcp.bridge import (
    get_current_view as _bridge_get_current_view,
    get_pixel_color as _bridge_get_pixel_color,
    inspect_qml_tree as _bridge_inspect_qml_tree,
)
from skill_manager.mcp.models import ToolResult, err, ok

# ---------------------------------------------------------------------------
# Tool schemas with annotations
# ---------------------------------------------------------------------------
TOOL_SCHEMAS: dict[str, dict[str, Any]] = {
    "sm_get_current_view": {
        "description": "Report the currently active QML view (Library / QuickCopy / Settings / …). Read-only. Returns ok:false when the GUI controller is unavailable.",
        "annotations": {
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
        "inputSchema": {"type": "object", "properties": {}},
    },
    "sm_inspect_qml_tree": {
        "description": (
            "Capture a bounded snapshot of the QML object tree (object names, classes, geometry, "
            "visibility, child counts). Returns root_count and node_count plus the nested tree; "
            "nodes at max_depth set truncated:true. Read-only. Works in headless --mcp mode by "
            "rendering Main.qml offscreen on demand; no running GUI required."
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
                "max_depth": {
                    "type": "integer",
                    "default": 5,
                    "minimum": 1,
                    "maximum": 20,
                    "description": "Maximum recursion depth into children.",
                }
            },
        },
    },
    "sm_get_pixel_color": {
        "description": (
            "Read the color of a pixel in the captured app window, as #RRGGBB plus RGB channels. "
            "Coordinates are relative to the captured image (top-left is 0,0). Works in headless "
            "--mcp mode against the offscreen render; the result's 'source' reports which capture "
            "strategy was used ('live-gui', 'native' or 'headless-qml')."
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
                "x": {
                    "type": "integer",
                    "description": "X coordinate in the captured image (0 = left edge).",
                },
                "y": {
                    "type": "integer",
                    "description": "Y coordinate in the captured image (0 = top edge).",
                },
            },
            "required": ["x", "y"],
        },
    },
}


# ---------------------------------------------------------------------------
# Tool handlers (return ToolResult)
# ---------------------------------------------------------------------------
def _handle_get_current_view(_args: dict[str, Any]) -> ToolResult:
    try:
        result = _bridge_get_current_view()
        if result.get("ok"):
            return ok("sm_get_current_view", result)
        return err("sm_get_current_view", result.get("error", "failed to get current view"))
    except Exception as exc:  # noqa: BLE001
        return err("sm_get_current_view", str(exc))


def _handle_inspect_qml_tree(args: dict[str, Any]) -> ToolResult:
    try:
        max_depth = int(args.get("max_depth", 5))
        result = _bridge_inspect_qml_tree(max_depth=max_depth)
        if result.get("ok"):
            return ok("sm_inspect_qml_tree", result)
        return err("sm_inspect_qml_tree", result.get("error", "failed to inspect QML tree"))
    except Exception as exc:  # noqa: BLE001
        return err("sm_inspect_qml_tree", str(exc))


def _handle_get_pixel_color(args: dict[str, Any]) -> ToolResult:
    try:
        x = int(args["x"])
        y = int(args["y"])
        result = _bridge_get_pixel_color(x=x, y=y)
        if result.get("ok"):
            return ok("sm_get_pixel_color", result)
        return err("sm_get_pixel_color", result.get("error", "failed to read pixel color"))
    except Exception as exc:  # noqa: BLE001
        return err("sm_get_pixel_color", str(exc))


# ---------------------------------------------------------------------------
# Dispatch table
# ---------------------------------------------------------------------------
_HANDLERS: dict[str, Callable[[dict[str, Any]], ToolResult]] = {
    "sm_get_current_view": _handle_get_current_view,
    "sm_inspect_qml_tree": _handle_inspect_qml_tree,
    "sm_get_pixel_color": _handle_get_pixel_color,
}


def get_handlers(_allow_write: bool = False) -> dict[str, Callable[..., Any]]:
    return dict(_HANDLERS)


__all__ = ["TOOL_SCHEMAS", "get_handlers"]

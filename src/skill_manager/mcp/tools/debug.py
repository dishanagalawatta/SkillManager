"""Read-only debugging MCP tools for the SkillManager MCP server.

This module registers the *introspection* MCP tools (``sm_dump_state``,
``sm_inspect_controller``, ``sm_capture_errors``, ``sm_toggle_debug_overlay``).
They are pure read-only accessors over the headless bridge
(``skill_manager.mcp.bridge``) and never mutate app state.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, Field

from skill_manager.core.analytics import capture_event
from skill_manager.mcp.bridge import (
    capture_errors as _bridge_capture_errors,
    dump_state as _bridge_dump_state,
    inspect_controller as _bridge_inspect_controller,
    send_debug_overlay_command as _bridge_send_debug_overlay,
)
from skill_manager.mcp.models import ToolResult, err, ok


# ---------------------------------------------------------------------------
# Request models (pydantic v2)
# ---------------------------------------------------------------------------
class _DumpStateArgs(BaseModel):
    pass


class _InspectControllerArgs(BaseModel):
    name: str = Field(..., description="Name of the sub-controller attribute.")


class _CaptureErrorsArgs(BaseModel):
    limit: int = Field(default=100, ge=1, description="Max number of errors.")


class _ToggleDebugOverlayArgs(BaseModel):
    enabled: bool = Field(True, description="Enable or disable the ribbon debug overlay.")


# ---------------------------------------------------------------------------
# Tool schemas with annotations
# ---------------------------------------------------------------------------
TOOL_SCHEMAS: dict[str, dict[str, Any]] = {
    "sm_dump_state": {
        "description": "Serialize a safe subset of the live AppController state (sources, projects, model counts, config keys).",
        "annotations": {
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
        "inputSchema": {"type": "object", "properties": {}},
    },
    "sm_inspect_controller": {
        "description": "Introspect the public surface (methods and signals) of a named sub-controller attribute on the AppController.",
        "annotations": {
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name of the sub-controller attribute to introspect.",
                }
            },
            "required": ["name"],
        },
    },
    "sm_capture_errors": {
        "description": "Return only error-level diagnostic events from the SkillManager diagnostic ring buffer.",
        "annotations": {
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "default": 100,
                    "minimum": 1,
                    "description": "Maximum number of error events to return.",
                }
            },
        },
    },
    "sm_toggle_debug_overlay": {
        "description": "Toggle the QuickCopyView ribbon debug overlay on the live GUI. Writes an IPC command to enable/disable the green debug text showing threshold values (RCW, HW, RGE, HCE, IM).",
        "annotations": {
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
        "inputSchema": {
            "type": "object",
            "properties": {
                "enabled": {
                    "type": "boolean",
                    "description": "Enable (true) or disable (false) the ribbon debug overlay.",
                    "default": True,
                }
            },
        },
    },
}


# ---------------------------------------------------------------------------
# Tool handlers
# ---------------------------------------------------------------------------
def _handle_dump_state() -> ToolResult:
    try:
        state = _bridge_dump_state()
    except Exception as exc:
        return err("sm_dump_state", str(exc))
    return ok("sm_dump_state", state)


def _handle_inspect_controller(name: str) -> ToolResult:
    try:
        result = _bridge_inspect_controller(name=name)
    except Exception as exc:
        return err("sm_inspect_controller", str(exc))
    return ok("sm_inspect_controller", result)


def _handle_capture_errors(limit: int) -> ToolResult:
    try:
        errors = _bridge_capture_errors(limit=limit)
    except Exception as exc:
        return err("sm_capture_errors", str(exc))
    return ok("sm_capture_errors", {"errors": errors})


def _handle_toggle_debug_overlay(enabled: bool) -> ToolResult:
    try:
        result = _bridge_send_debug_overlay(enabled=enabled)
    except Exception as exc:
        return err("sm_toggle_debug_overlay", str(exc))
    return ok("sm_toggle_debug_overlay", result)


# ---------------------------------------------------------------------------
# Public dispatch surface
# ---------------------------------------------------------------------------
def get_handlers(_allow_write: bool = False) -> dict[str, Callable[..., Any]]:
    def _dispatch_dump_state(_args: dict[str, Any]) -> ToolResult:
        capture_event("mcp_tool_call", {"tool": "sm_dump_state", "args": {}})
        return _handle_dump_state()

    def _dispatch_inspect_controller(args: dict[str, Any]) -> ToolResult:
        parsed = _InspectControllerArgs(**args)
        capture_event(
            "mcp_tool_call", {"tool": "sm_inspect_controller", "args": {"name": parsed.name}}
        )
        return _handle_inspect_controller(parsed.name)

    def _dispatch_capture_errors(args: dict[str, Any]) -> ToolResult:
        parsed = _CaptureErrorsArgs(**args)
        capture_event(
            "mcp_tool_call", {"tool": "sm_capture_errors", "args": {"limit": parsed.limit}}
        )
        return _handle_capture_errors(parsed.limit)

    def _dispatch_toggle_debug_overlay(args: dict[str, Any]) -> ToolResult:
        parsed = _ToggleDebugOverlayArgs(**args)
        capture_event(
            "mcp_tool_call",
            {"tool": "sm_toggle_debug_overlay", "args": {"enabled": parsed.enabled}},
        )
        return _handle_toggle_debug_overlay(parsed.enabled)

    return {
        "sm_dump_state": _dispatch_dump_state,
        "sm_inspect_controller": _dispatch_inspect_controller,
        "sm_capture_errors": _dispatch_capture_errors,
        "sm_toggle_debug_overlay": _dispatch_toggle_debug_overlay,
    }


__all__ = ["TOOL_SCHEMAS", "get_handlers"]

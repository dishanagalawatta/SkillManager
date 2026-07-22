"""Read-only debugging MCP tools for the SkillManager MCP server.

This module registers the *introspection* MCP tools (``sm_dump_state``,
``sm_inspect_controller``, ``sm_capture_errors``). They are pure read-only
accessors over the headless bridge (``skill_manager.mcp.bridge``) and never
mutate app state.

Server API pattern
------------------
Registration is written against the standard ``mcp`` Python SDK low-level
``Server`` object (``from mcp.server import Server``). The registration
function decorates ``@server.list_tools()`` and ``@server.call_tool()``
directly, matching the low-level ``Server`` style used by the MCP server
entrypoint. This is consistent with the project's other tool waves; the
sibling ``write.py`` module instead returns schemas/handlers because it needs
to close over an ``allow_write`` gate, but these debug tools have no such gate
and register directly.

Every tool is safe-wrapped: exceptions are caught and returned as
``ToolResult(ok=False, error=str(e))`` so the MCP server never crashes. Each
call is recorded via ``capture_event("mcp_tool_call", {"tool": ..., "args": ...})``.
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
from skill_manager.mcp.models import ToolResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _ok(tool: str, data: dict[str, Any] | None = None) -> ToolResult:
    """Build a successful ToolResult envelope."""
    return ToolResult(ok=True, tool=tool, data=data)


def _err(tool: str, error: str) -> ToolResult:
    """Build a failed ToolResult envelope."""
    return ToolResult(ok=False, tool=tool, error=error)


# ---------------------------------------------------------------------------
# Request models (pydantic v2) — used only for input validation/clarity
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
# Tool schemas (valid JSON-schema input schemas)
# ---------------------------------------------------------------------------
DUMP_STATE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {},
}

INSPECT_CONTROLLER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "name": {
            "type": "string",
            "description": "Name of the sub-controller attribute to introspect.",
        }
    },
    "required": ["name"],
}

CAPTURE_ERRORS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "limit": {
            "type": "integer",
            "default": 100,
            "minimum": 1,
            "description": "Maximum number of error events to return.",
        }
    },
}

TOGGLE_DEBUG_OVERLAY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "enabled": {
            "type": "boolean",
            "description": "Enable (true) or disable (false) the ribbon debug overlay.",
            "default": True,
        }
    },
}


# ---------------------------------------------------------------------------
# Tool handlers
# ---------------------------------------------------------------------------
def _handle_dump_state() -> ToolResult:
    """Serialize a safe subset of AppController state."""
    try:
        state = _bridge_dump_state()
    except Exception as exc:  # noqa: BLE001 - surface as ToolResult, never crash
        return _err("sm_dump_state", str(exc))
    return _ok("sm_dump_state", state)


def _handle_inspect_controller(name: str) -> ToolResult:
    """Introspect the public surface (methods/signals) of a sub-controller."""
    try:
        result = _bridge_inspect_controller(name=name)
    except Exception as exc:  # noqa: BLE001 - surface as ToolResult, never crash
        return _err("sm_inspect_controller", str(exc))
    return _ok("sm_inspect_controller", result)


def _handle_capture_errors(limit: int) -> ToolResult:
    """Return only error-level diagnostic events."""
    try:
        errors = _bridge_capture_errors(limit=limit)
    except Exception as exc:  # noqa: BLE001 - surface as ToolResult, never crash
        return _err("sm_capture_errors", str(exc))
    return _ok("sm_capture_errors", {"errors": errors})


def _handle_toggle_debug_overlay(enabled: bool) -> ToolResult:
    """Toggle the QuickCopyView ribbon debug overlay on the live GUI.

    Writes an IPC command for the GUI process to pick up.  Returns the
    bridge result dict (including the ack status on success).
    """
    try:
        result = _bridge_send_debug_overlay(enabled=enabled)
    except Exception as exc:  # noqa: BLE001 - surface as ToolResult, never crash
        return _err("sm_toggle_debug_overlay", str(exc))
    return _ok("sm_toggle_debug_overlay", result)


# ---------------------------------------------------------------------------
# Public dispatch surface
# ---------------------------------------------------------------------------
TOOL_SCHEMAS: dict[str, dict[str, Any]] = {
    "sm_dump_state": {
        "description": (
            "Serialize a safe subset of the live AppController state "
            "(sources, projects, model counts, config keys)."
        ),
        "inputSchema": DUMP_STATE_SCHEMA,
    },
    "sm_inspect_controller": {
        "description": (
            "Introspect the public surface (methods and signals) of a "
            "named sub-controller attribute on the AppController."
        ),
        "inputSchema": INSPECT_CONTROLLER_SCHEMA,
    },
    "sm_capture_errors": {
        "description": (
            "Return only error-level diagnostic events from the "
            "SkillManager diagnostic ring buffer."
        ),
        "inputSchema": CAPTURE_ERRORS_SCHEMA,
    },
    "sm_toggle_debug_overlay": {
        "description": (
            "Toggle the QuickCopyView ribbon debug overlay on the live GUI. "
            "Writes an IPC command to enable/disable the green debug text "
            "showing threshold values (RCW, HW, RGE, HCE, IM)."
        ),
        "inputSchema": TOGGLE_DEBUG_OVERLAY_SCHEMA,
    },
}


def get_handlers(_allow_write: bool = False) -> dict[str, Callable[..., Any]]:
    """Return the debug tool dispatch table (name -> handler).

    Each handler is a thunk that parses its args and emits a ``ToolResult``.
    The ``_allow_write`` parameter is accepted for a uniform module interface
    but is unused: debug tools are read-only.
    """

    def _dispatch_dump_state(_args: dict[str, Any]) -> ToolResult:
        capture_event("mcp_tool_call", {"tool": "sm_dump_state", "args": {}})
        return _handle_dump_state()

    def _dispatch_inspect_controller(args: dict[str, Any]) -> ToolResult:
        parsed = _InspectControllerArgs(**args)
        capture_event(
            "mcp_tool_call",
            {"tool": "sm_inspect_controller", "args": {"name": parsed.name}},
        )
        return _handle_inspect_controller(parsed.name)

    def _dispatch_capture_errors(args: dict[str, Any]) -> ToolResult:
        parsed = _CaptureErrorsArgs(**args)
        capture_event(
            "mcp_tool_call",
            {"tool": "sm_capture_errors", "args": {"limit": parsed.limit}},
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


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------
def register_debug_tools(_server: Any) -> None:
    """Register the read-only debugging tools against the MCP ``server``.

    .. deprecated::
        Tool registration now happens centrally in ``server.py`` via a single
        ``list_tools`` / ``call_tool`` pair. This function is retained as a
        no-op so existing importers keep working; it MUST NOT decorate any
        ``call_tool`` handler (the SDK keeps only one such slot).

    The registered tools are:
    * ``sm_dump_state`` — serialize a safe subset of app state (no args).
    * ``sm_inspect_controller`` — introspect a sub-controller (arg ``name``).
    * ``sm_capture_errors`` — return error-level events (arg ``limit``).
    """
    return


__all__ = [
    "register_debug_tools",
    "DUMP_STATE_SCHEMA",
    "INSPECT_CONTROLLER_SCHEMA",
    "CAPTURE_ERRORS_SCHEMA",
    "TOGGLE_DEBUG_OVERLAY_SCHEMA",
    "TOOL_SCHEMAS",
    "get_handlers",
]

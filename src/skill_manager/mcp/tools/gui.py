"""Read-only ``sm_mouse_*`` / ``sm_type_text`` / ``sm_get_window_info`` MCP tools.

Wraps the Win32 GUI interaction functions from ``skill_manager.mcp.bridge`` into
MCP tool handlers. All tools operate on the **live** SkillManager desktop window
cross-process \u2014 they send Windows messages to the running GUI process.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from skill_manager.core.analytics import capture_event
from skill_manager.mcp.bridge import (
    get_window_info as _bridge_get_window_info,
    send_mouse_click as _bridge_send_mouse_click,
    send_mouse_move as _bridge_send_mouse_move,
    send_navigation_command as _bridge_send_navigation_command,
    send_type_text as _bridge_send_type_text,
)
from skill_manager.mcp.models import ToolResult, err, ok

# ---------------------------------------------------------------------------
# Tool schemas with annotations
# ---------------------------------------------------------------------------
TOOL_SCHEMAS: dict[str, dict[str, Any]] = {
    "sm_mouse_move": {
        "description": "Move the system cursor to absolute screen pixel coordinates (x, y). Does not click. Returns ok:false if SetCursorPos fails.",
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
                    "description": "Screen X coordinate to move the cursor to.",
                },
                "y": {
                    "type": "integer",
                    "description": "Screen Y coordinate to move the cursor to.",
                },
            },
            "required": ["x", "y"],
        },
    },
    "sm_mouse_click": {
        "description": "Move the cursor to (x, y) if provided and click a mouse button. Supports left/right/middle buttons and double-click. Use after sm_screenshot to target elements at known screen coordinates.",
        "annotations": {
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": False,
            "openWorldHint": False,
        },
        "inputSchema": {
            "type": "object",
            "properties": {
                "x": {
                    "type": "integer",
                    "description": "Optional: screen X coordinate. Omit to click at current cursor position.",
                },
                "y": {
                    "type": "integer",
                    "description": "Optional: screen Y coordinate. Omit to click at current cursor position.",
                },
                "button": {
                    "type": "string",
                    "enum": ["left", "right", "middle"],
                    "default": "left",
                    "description": "Mouse button to press.",
                },
                "double": {
                    "type": "boolean",
                    "default": False,
                    "description": "Perform a double-click when true.",
                },
            },
        },
    },
    "sm_type_text": {
        "description": "Type text into the currently focused window. Supports alphanumeric characters, common symbols, space, Enter, and Tab. Handles Shift-key modulation for uppercase and shifted symbols. Returns the number of characters successfully sent.",
        "annotations": {
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": False,
            "openWorldHint": False,
        },
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Text to type into the currently focused window.",
                }
            },
            "required": ["text"],
        },
    },
    "sm_get_window_info": {
        "description": "Return the live SkillManager window's geometry (left, top, right, bottom, width, height) and HWND. Useful for calculating click coordinates relative to the window.",
        "annotations": {
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
        "inputSchema": {"type": "object", "properties": {}},
    },
    "sm_navigate": {
        "description": "Navigate the live SkillManager GUI to a different view (QuickCopy, Library, Updates, Settings). Fire-and-forget: writes the command and returns immediately. The GUI processes it asynchronously. Use sm_screenshot afterwards to verify the view changed.",
        "annotations": {
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
        "inputSchema": {
            "type": "object",
            "properties": {
                "view": {
                    "type": "string",
                    "enum": ["QuickCopy", "Library", "Updates", "Settings"],
                    "description": "Target navigation view.",
                },
            },
            "required": ["view"],
        },
    },
}


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------
def _handle_mouse_move(x: int, y: int) -> ToolResult:
    try:
        result = _bridge_send_mouse_move(x=x, y=y)
        if result.get("ok"):
            return ok("sm_mouse_move", result)
        return err("sm_mouse_move", result.get("error", "mouse move failed"))
    except Exception as exc:
        return err("sm_mouse_move", str(exc))


def _handle_mouse_click(
    x: int | None = None,
    y: int | None = None,
    button: str = "left",
    double: bool = False,
) -> ToolResult:
    try:
        result = _bridge_send_mouse_click(x=x, y=y, button=button, double=double)
        if result.get("ok"):
            return ok("sm_mouse_click", result)
        return err("sm_mouse_click", result.get("error", "mouse click failed"))
    except Exception as exc:
        return err("sm_mouse_click", str(exc))


def _handle_type_text(text: str) -> ToolResult:
    try:
        result = _bridge_send_type_text(text=text)
        if result.get("ok"):
            return ok("sm_type_text", result)
        return err("sm_type_text", result.get("error", "type text failed"))
    except Exception as exc:
        return err("sm_type_text", str(exc))


def _handle_get_window_info() -> ToolResult:
    try:
        result = _bridge_get_window_info()
        if result.get("ok"):
            return ok("sm_get_window_info", result)
        return err("sm_get_window_info", result.get("error", "window not found"))
    except Exception as exc:
        return err("sm_get_window_info", str(exc))


def _handle_navigate(view: str) -> ToolResult:
    try:
        result = _bridge_send_navigation_command(view)
        if result.get("ok"):
            return ok("sm_navigate", {"view": view, "cmd_id": result.get("cmd_id")})
        return err("sm_navigate", result.get("error", "navigation failed"))
    except Exception as exc:
        return err("sm_navigate", str(exc))


# ---------------------------------------------------------------------------
# Public dispatch surface
# ---------------------------------------------------------------------------
def get_handlers(_allow_write: bool = False) -> dict[str, Callable[..., Any]]:
    def _dispatch_mouse_move(args: dict[str, Any]) -> ToolResult:
        capture_event("mcp_tool_call", {"tool": "sm_mouse_move", "args": args})
        return _handle_mouse_move(x=int(args["x"]), y=int(args["y"]))

    def _dispatch_mouse_click(args: dict[str, Any]) -> ToolResult:
        capture_event("mcp_tool_call", {"tool": "sm_mouse_click", "args": args})
        return _handle_mouse_click(
            x=int(args["x"]) if args.get("x") is not None else None,
            y=int(args["y"]) if args.get("y") is not None else None,
            button=str(args.get("button", "left")),
            double=bool(args.get("double", False)),
        )

    def _dispatch_type_text(args: dict[str, Any]) -> ToolResult:
        capture_event("mcp_tool_call", {"tool": "sm_type_text", "args": args})
        return _handle_type_text(text=str(args["text"]))

    def _dispatch_get_window_info(_args: dict[str, Any]) -> ToolResult:
        capture_event("mcp_tool_call", {"tool": "sm_get_window_info", "args": {}})
        return _handle_get_window_info()

    def _dispatch_navigate(args: dict[str, Any]) -> ToolResult:
        capture_event("mcp_tool_call", {"tool": "sm_navigate", "args": args})
        return _handle_navigate(view=str(args["view"]))

    return {
        "sm_mouse_move": _dispatch_mouse_move,
        "sm_mouse_click": _dispatch_mouse_click,
        "sm_type_text": _dispatch_type_text,
        "sm_get_window_info": _dispatch_get_window_info,
        "sm_navigate": _dispatch_navigate,
    }


__all__ = ["TOOL_SCHEMAS", "get_handlers"]

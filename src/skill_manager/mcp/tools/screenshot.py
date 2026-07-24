"""Read-only ``sm_screenshot`` MCP tool for the SkillManager MCP server.

Captures the live SkillManager GUI window (title "Skill Manager") cross-process
via Win32 and returns a base64 PNG. Optionally navigates the running GUI to
a section first through the file-based IPC channel in ``skill_manager.mcp.bridge``.
"""

from __future__ import annotations

import base64
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from skill_manager.core.analytics import capture_event
from skill_manager.mcp.bridge import (
    capture_app_window as _bridge_capture_app_window,
    send_navigation_command as _bridge_send_navigation_command,
)
from skill_manager.mcp.models import ToolResult, err, ok

# Valid navigation targets (Sidebar.qml / TopBar.qml view names).
VALID_VIEWS: tuple[str, ...] = ("QuickCopy", "Library", "Updates", "Settings")

# Repo root for the optional PNG save dir (.agents/screenshots).
_REPO_ROOT = Path(__file__).resolve().parents[4]

# Settle delay (seconds) after a fire-and-forget navigation command so the
# GUI's CommandChannel QTimer (200ms interval) picks up the command, switches
# the view, and the UI repaints before we capture.
_SETTLE_DELAY = 0.6


# ---------------------------------------------------------------------------
# Tool schema with annotations
# ---------------------------------------------------------------------------
TOOL_SCHEMAS: dict[str, dict[str, Any]] = {
    "sm_screenshot": {
        "description": "Capture the live SkillManager GUI window (title 'Skill Manager') as a base64 PNG. Optionally navigate the running GUI to a section first. Read-only. Returns ok:false if the GUI is not running or the window cannot be found.",
        "annotations": {
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
        "inputSchema": {
            "type": "object",
            "properties": {
                "navigate": {
                    "type": "string",
                    "enum": ["QuickCopy", "Library", "Updates", "Settings"],
                    "description": "Optional: navigate the live GUI to this section before capture.",
                },
                "save": {
                    "type": "boolean",
                    "default": False,
                    "description": "If true, also write the PNG to .agents/screenshots/ and include its path in the result.",
                },
                "width": {
                    "type": "integer",
                    "default": None,
                    "description": "Optional: resize the window to this width before capture. Window is restored to its original size afterward. Use together with height to test responsive layouts.",
                },
                "height": {
                    "type": "integer",
                    "default": None,
                    "description": "Optional: resize the window to this height before capture. Window is restored to its original size afterward.",
                },
            },
        },
    },
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _current_view() -> str:
    try:
        from skill_manager.mcp.bridge import _controller_or_none

        controller = _controller_or_none()
        if controller is not None:
            return str(getattr(controller.ui, "currentView", "unknown"))
    except Exception:
        pass
    return "unknown"


def _save_png(b64: str) -> str | None:
    try:
        raw = base64.b64decode(b64)
        save_dir = _REPO_ROOT / ".agents" / "screenshots"
        save_dir.mkdir(parents=True, exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        path = save_dir / f"Screenshot_{timestamp}.png"
        path.write_bytes(raw)
        return str(path)
    except Exception:
        return None


def _handle_screenshot(
    navigate: str | None = None,
    save: bool = False,
    width: int | None = None,
    height: int | None = None,
) -> ToolResult:
    try:
        if navigate:
            if navigate not in VALID_VIEWS:
                return err("sm_screenshot", f"invalid navigate view: {navigate!r}")
            _bridge_send_navigation_command(navigate)
            time.sleep(_SETTLE_DELAY)

        b64, captured_w, captured_h = _bridge_capture_app_window(
            resize_width=width,
            resize_height=height,
        )
        if b64 is None:
            return err("sm_screenshot", "SkillManager GUI not running or window not found")

        data: dict[str, Any] = {
            "image_b64": b64,
            "width": captured_w,
            "height": captured_h,
            "resize_requested": width is not None and height is not None,
            "view": navigate if navigate else _current_view(),
        }
        if save:
            save_path = _save_png(b64)
            if save_path:
                data["save_path"] = save_path

        return ok("sm_screenshot", data)
    except Exception as exc:
        return err("sm_screenshot", str(exc))


# ---------------------------------------------------------------------------
# Public dispatch surface
# ---------------------------------------------------------------------------
def get_handlers(_allow_write: bool = False) -> dict[str, Callable[..., Any]]:
    def _dispatch(args: dict[str, Any]) -> ToolResult:
        navigate = args.get("navigate")
        save = bool(args.get("save", False))
        width = args.get("width")
        height = args.get("height")
        capture_event(
            "mcp_tool_call",
            {
                "tool": "sm_screenshot",
                "args": {"navigate": navigate, "save": save, "width": width, "height": height},
            },
        )
        return _handle_screenshot(navigate=navigate, save=save, width=width, height=height)

    return {"sm_screenshot": _dispatch}


__all__ = ["TOOL_SCHEMAS", "get_handlers"]

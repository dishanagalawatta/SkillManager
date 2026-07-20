"""Read-only ``sm_screenshot`` MCP tool for the SkillManager MCP server.

Captures the live SkillManager GUI window (title "Skill Manager") cross-process
via Win32 and returns a base64 PNG. Optionally navigates the running GUI to
a section first through the file-based IPC channel in ``skill_manager.mcp.bridge``.

Mirrors ``monitor.py``: a ``TOOL_SCHEMAS`` dict plus a ``get_handlers()``
dispatcher returning name->handler thunks, with ``_ok``/``_err`` helpers and
``ToolResult`` from ``skill_manager.mcp.models``. The tool is read-only and
never requires ``--mcp-allow-write``.
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
from skill_manager.mcp.models import ToolResult

# Valid navigation targets (Sidebar.qml / TopBar.qml view names).
VALID_VIEWS: tuple[str, ...] = ("QuickCopy", "Library", "Updates", "Settings")

# Repo root for the optional PNG save dir (.agents/screenshots).
# src/skill_manager/mcp/tools/screenshot.py -> parents[4] == repo root.
_REPO_ROOT = Path(__file__).resolve().parents[4]

# Settle delay (seconds) after a navigation command so the UI can repaint.
_SETTLE_DELAY = 0.3


def _ok(tool: str, data: dict[str, Any] | None = None) -> ToolResult:
    """Build a successful ToolResult envelope."""
    return ToolResult(ok=True, tool=tool, data=data)


def _err(tool: str, error: str) -> ToolResult:
    """Build a failed ToolResult envelope."""
    return ToolResult(ok=False, tool=tool, error=error)


# ---------------------------------------------------------------------------
# Tool schema
# ---------------------------------------------------------------------------
SCREENSHOT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "navigate": {
            "type": "string",
            "enum": ["QuickCopy", "Library", "Updates", "Settings"],
            "description": ("Optional: navigate the live GUI to this section before capture."),
        },
        "save": {
            "type": "boolean",
            "default": False,
            "description": (
                "If true, also write the PNG to .agents/screenshots/ and "
                "include its path in the result."
            ),
        },
    },
}

TOOL_SCHEMAS: dict[str, dict[str, Any]] = {
    "sm_screenshot": {
        "description": (
            "Capture the live SkillManager GUI window (title 'Skill Manager') as a "
            "base64 PNG. Optionally navigate the running GUI to a section first. "
            "Read-only. Returns ok:false if the GUI is not running or the window "
            "cannot be found."
        ),
        "inputSchema": SCREENSHOT_SCHEMA,
    },
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _current_view() -> str:
    """Best-effort read of the live GUI's current view (headless-safe)."""
    try:
        from skill_manager.mcp.bridge import _controller_or_none

        controller = _controller_or_none()
        if controller is not None:
            return str(getattr(controller.ui, "currentView", "unknown"))
    except Exception:  # noqa: BLE001
        pass
    return "unknown"


def _save_png(b64: str) -> str | None:
    """Decode base64 PNG and write it under .agents/screenshots/; return path."""
    try:
        raw = base64.b64decode(b64)
        save_dir = _REPO_ROOT / ".agents" / "screenshots"
        save_dir.mkdir(parents=True, exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        path = save_dir / f"Screenshot_{timestamp}.png"
        path.write_bytes(raw)
        return str(path)
    except Exception:  # noqa: BLE001
        return None


def _handle_screenshot(navigate: str | None = None, save: bool = False) -> ToolResult:
    """Capture the live GUI, optionally navigating first."""
    try:
        navigated = False
        if navigate:
            if navigate not in VALID_VIEWS:
                return _err("sm_screenshot", f"invalid navigate view: {navigate!r}")
            ack = _bridge_send_navigation_command(navigate)
            navigated = bool(ack.get("ok")) if isinstance(ack, dict) else False
            time.sleep(_SETTLE_DELAY)

        b64, width, height = _bridge_capture_app_window()
        if b64 is None:
            return _err(
                "sm_screenshot",
                "SkillManager GUI not running or window not found",
            )

        data: dict[str, Any] = {
            "image_b64": b64,
            "width": width,
            "height": height,
            "view": navigate if navigate else _current_view(),
            "navigated": navigated,
        }
        if save:
            save_path = _save_png(b64)
            if save_path:
                data["save_path"] = save_path

        return _ok("sm_screenshot", data)
    except Exception as exc:  # noqa: BLE001 - surface as ToolResult, never crash
        return _err("sm_screenshot", str(exc))


# ---------------------------------------------------------------------------
# Public dispatch surface
# ---------------------------------------------------------------------------
def get_handlers(_allow_write: bool = False) -> dict[str, Callable[..., Any]]:
    """Return the screenshot tool dispatch table (name -> handler).

    The ``_allow_write`` parameter is accepted for a uniform module interface
    but is unused: ``sm_screenshot`` is read-only.
    """

    def _dispatch(args: dict[str, Any]) -> ToolResult:
        navigate = args.get("navigate")
        save = bool(args.get("save", False))
        capture_event(
            "mcp_tool_call",
            {"tool": "sm_screenshot", "args": {"navigate": navigate, "save": save}},
        )
        return _handle_screenshot(navigate=navigate, save=save)

    return {"sm_screenshot": _dispatch}


__all__ = ["TOOL_SCHEMAS", "get_handlers"]

"""Read-only ``sm_screenshot`` MCP tool for the SkillManager MCP server.

Captures the SkillManager window (live GUI, platform-native, or the headless
offscreen QML render) and returns a base64 PNG. Optionally navigates to a
section first — in-process in headless ``--mcp`` mode, over the file-based IPC
channel when a GUI runs in another process.
"""

from __future__ import annotations

import base64
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from skill_manager.core.analytics import capture_mcp_tool_call
from skill_manager.mcp.bridge import (
    capture_app_window_info as _bridge_capture_app_window_info,
    navigate_view as _bridge_navigate_view,
)
from skill_manager.mcp.models import ToolResult, err, ok

# Valid navigation targets (Sidebar.qml / TopBar.qml view names).
VALID_VIEWS: tuple[str, ...] = ("QuickCopy", "Library", "Updates", "Settings")

# Repo root for the optional PNG save dir (.agents/screenshots).
_REPO_ROOT = Path(__file__).resolve().parents[4]

# Settle delay (seconds) after a cross-process navigation command so the GUI's
# CommandChannel QTimer picks up the command, switches the view, and the UI
# repaints before we capture. In-process (headless) navigation needs no delay:
# the view is already set and verified when the bridge call returns.
_SETTLE_DELAY = 0.6


# ---------------------------------------------------------------------------
# Tool schema with annotations
# ---------------------------------------------------------------------------
TOOL_SCHEMAS: dict[str, dict[str, Any]] = {
    "sm_screenshot": {
        "description": "Capture the SkillManager UI as a base64 PNG. Prefers the live GUI window (title 'Skill Manager'), falling back to a headless offscreen render when no GUI is running. Optionally navigate the GUI to a section first. Read-only. The result's 'source' field reports which strategy produced the image ('live-gui', 'native' or 'headless-qml').",
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
                    "description": (
                        "Optional: switch to this section before capture. Applied in-process when "
                        "this process owns the offscreen window (headless --mcp); otherwise the "
                        "live GUI is asked over IPC and must acknowledge."
                    ),
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
            nav = _bridge_navigate_view(navigate)
            if not nav.get("ok"):
                return err(
                    "sm_screenshot",
                    f"navigation to {navigate!r} failed: {nav.get('error') or 'no acknowledgement'}",
                )
            if not nav.get("in_process"):
                time.sleep(_SETTLE_DELAY)

        info = _bridge_capture_app_window_info(
            resize_width=width,
            resize_height=height,
        )
        b64 = info.get("image_b64")
        if b64 is None:
            return err(
                "sm_screenshot",
                "SkillManager GUI not running and no headless QML render available",
            )

        data: dict[str, Any] = {
            "image_b64": b64,
            "width": info.get("width", 0),
            "height": info.get("height", 0),
            "source": info.get("source"),
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
        capture_mcp_tool_call(
            "mcp_tool_call",
            "sm_screenshot",
            {"navigate": navigate, "save": save, "width": width, "height": height},
        )
        return _handle_screenshot(navigate=navigate, save=save, width=width, height=height)

    return {"sm_screenshot": _dispatch}


__all__ = ["TOOL_SCHEMAS", "get_handlers"]

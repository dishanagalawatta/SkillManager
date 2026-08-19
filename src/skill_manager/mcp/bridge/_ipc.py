"""Cross-process file-based IPC for navigation / capture / debug overlay."""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any

from ._telemetry import _log_call

# Cross-process IPC for sm_screenshot: the headless bridge cannot see the GUI
# window, so it writes a navigate command the GUI watches and polls an ack.
_MCP_ROOT = Path(__file__).resolve().parents[4] / "data" / "mcp"
MCP_COMMANDS_DIR = _MCP_ROOT / "commands"
MCP_ACKS_DIR = _MCP_ROOT / "acks"


def _wait_for_ack(cmd_id: str, acks_dir: Path, timeout: float) -> dict[str, Any]:
    ack_path = acks_dir / f"{cmd_id}.json"
    deadline = time.time() + timeout
    while time.time() < deadline:
        if ack_path.exists():
            try:
                return json.loads(ack_path.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001
                return {"ok": False, "error": "invalid ack payload"}
        time.sleep(0.02)
    return {"ok": False}


def _write_command(commands_dir: Path, action: str, **extra: object) -> str:
    """Write a JSON command file and return its ``cmd_id``.

    The GUI's ``CommandChannel`` picks up the file via QTimer polling
    (every 200ms) and processes it asynchronously.
    """
    cmd_id = uuid.uuid4().hex
    command: dict[str, object] = {"action": action, "id": cmd_id, **extra}
    (commands_dir / f"{cmd_id}.json").write_text(json.dumps(command), encoding="utf-8")
    return cmd_id


def send_navigation_command(
    view: str,
    wait: bool = False,
    timeout: float = 2.0,
) -> dict[str, Any]:
    """Send a navigate command to the live GUI via file-based IPC.

    By default (``wait=False``) this is **fire-and-forget**: the command
    is written and the function returns immediately with ``{"ok": True}``
    and the ``cmd_id``. The GUI processes it asynchronously via its
    ``CommandChannel`` (QTimer + QFileSystemWatcher). This means the MCP
    tool never blocks the user's mouse or keyboard.

    When ``wait=True`` the function polls for the acknowledgement file
    for up to *timeout* seconds — useful for callers that need to confirm
    the navigation happened before proceeding.

    Best-effort: returns ``{"ok": False, "error": ...}`` on any failure.
    """
    _log_call("send_navigation_command")
    try:
        commands_dir = MCP_COMMANDS_DIR
        acks_dir = MCP_ACKS_DIR
        commands_dir.mkdir(parents=True, exist_ok=True)
        acks_dir.mkdir(parents=True, exist_ok=True)

        cmd_id = _write_command(commands_dir, "navigate", view=view)

        if wait:
            ack = _wait_for_ack(cmd_id, acks_dir, timeout)
            ack["cmd_id"] = cmd_id
            return ack

        return {"ok": True, "cmd_id": cmd_id, "wait": False}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


def send_capture_command(
    wait: bool = False,
    timeout: float = 5.0,
) -> dict[str, Any]:
    """Send a ``capture_screenshot`` command to the live GUI via file-based IPC.

    The GUI's ``CommandChannel._capture_screenshot`` calls
    ``QQuickWindow::grabWindow()`` (works minimised, no colour cast) and saves
    the result as PNG to ``data/mcp/captures/<cmd_id>.png``.

    By default (``wait=False``) this is fire-and-forget — use ``wait=True`` to
    poll for the acknowledgement which includes the PNG path and capture dimensions.

    Best-effort: returns ``{"ok": False, "error": ...}`` on any failure.
    """
    _log_call("send_capture_command")
    try:
        commands_dir = MCP_COMMANDS_DIR
        acks_dir = MCP_ACKS_DIR
        commands_dir.mkdir(parents=True, exist_ok=True)
        acks_dir.mkdir(parents=True, exist_ok=True)

        cmd_id = _write_command(commands_dir, "capture_screenshot")

        if wait:
            ack = _wait_for_ack(cmd_id, acks_dir, timeout)
            ack["cmd_id"] = cmd_id
            return ack

        return {"ok": True, "cmd_id": cmd_id, "wait": False}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


def send_debug_overlay_command(
    enabled: bool,
    wait: bool = False,
    timeout: float = 2.0,
) -> dict[str, Any]:
    """Toggle the QuickCopyView ribbon debug overlay on the live GUI via IPC.

    By default (``wait=False``) this is **fire-and-forget**: writes the
    command and returns immediately. Use ``wait=True`` to poll for
    confirmation (up to *timeout* seconds).

    Returns ``{"ok": False, "error": ...}`` on any failure.
    """
    _log_call("send_debug_overlay_command")
    try:
        commands_dir = MCP_COMMANDS_DIR
        acks_dir = MCP_ACKS_DIR
        commands_dir.mkdir(parents=True, exist_ok=True)
        acks_dir.mkdir(parents=True, exist_ok=True)

        cmd_id = _write_command(commands_dir, "set_debug_overlay", enabled=enabled)

        if wait:
            ack = _wait_for_ack(cmd_id, acks_dir, timeout)
            ack["cmd_id"] = cmd_id
            return ack

        return {"ok": True, "cmd_id": cmd_id, "wait": False}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}

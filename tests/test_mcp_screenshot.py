"""Tests for the sm_screenshot MCP tool + cross-process navigation IPC.

Mirrors ``test_screenshot_*.py`` style: mock the Win32/PIL capture path
and the file-based IPC so no real GUI window is required.
"""

import base64
import io
import json
from pathlib import Path
from unittest.mock import MagicMock

from PIL import Image

import skill_manager.mcp.bridge as bridge
import skill_manager.mcp.bridge._capture as bridge_capture
import skill_manager.mcp.bridge._ipc as bridge_ipc
import skill_manager.mcp.bridge._win32 as bridge_win32
import skill_manager.mcp.tools.screenshot as tools_screenshot
from skill_manager.mcp.models import ToolResult


# ---------------------------------------------------------------------------
# bridge.capture_app_window()
# ---------------------------------------------------------------------------
def test_capture_app_window_success(monkeypatch):
    img = Image.new("RGB", (100, 50), "red")
    # IPC path: mock send_capture_command to fail fast (no live GUI in test).
    monkeypatch.setattr(
        bridge_capture, "send_capture_command", lambda **kw: {"ok": False, "error": "no GUI"}
    )
    # Win32 fallback path: mock window + capture.
    monkeypatch.setattr(bridge_capture, "_find_skill_manager_window", lambda: 123)
    monkeypatch.setattr(bridge_capture, "_get_window_rect", lambda _h: (0, 0, 100, 50))
    monkeypatch.setattr(bridge_capture, "_capture_window_to_image", lambda *a, **kw: img)
    # Force Windows path for this test (Win32 fallback).
    monkeypatch.setattr("sys.platform", "win32")

    b64, width, height = bridge.capture_app_window()

    assert b64 is not None
    assert width == 100
    assert height == 50
    raw = base64.b64decode(b64)
    assert raw[:8] == b"\x89PNG\r\n\x1a\n"


def test_capture_app_window_no_window(monkeypatch):
    monkeypatch.setattr(bridge_capture, "_find_skill_manager_window", lambda: None)
    monkeypatch.setattr("sys.platform", "win32")

    b64, width, height = bridge.capture_app_window()

    assert b64 is None
    assert width == 0
    assert height == 0


def test_capture_app_window_no_matching_title(monkeypatch):
    monkeypatch.setattr(bridge_win32, "_enum_top_level_windows", lambda: [1, 2, 3])
    monkeypatch.setattr(bridge_win32, "_get_window_title", lambda _h: "Notepad")
    monkeypatch.setattr("sys.platform", "win32")

    b64, width, height = bridge.capture_app_window()

    assert b64 is None
    assert width == 0
    assert height == 0


# ---------------------------------------------------------------------------
# bridge.send_navigation_command()
# ---------------------------------------------------------------------------
class _FakeUUID:
    hex = "testcmdid123"


def test_send_navigation_command_writes_file_and_parses_ack(tmp_path, monkeypatch):
    commands_dir = tmp_path / "commands"
    acks_dir = tmp_path / "acks"
    monkeypatch.setattr(bridge_ipc, "MCP_COMMANDS_DIR", commands_dir)
    monkeypatch.setattr(bridge_ipc, "MCP_ACKS_DIR", acks_dir)
    monkeypatch.setattr(bridge_ipc.uuid, "uuid4", lambda: _FakeUUID())
    acks_dir.mkdir(parents=True, exist_ok=True)
    (acks_dir / f"{_FakeUUID.hex}.json").write_text(
        json.dumps({"ok": True, "view": "Library"}), encoding="utf-8"
    )

    # Use wait=True so send_navigation_command polls for the ack and
    # returns its content (with cmd_id appended).
    result = bridge.send_navigation_command("Library", wait=True)

    assert result["ok"] is True
    assert result["view"] == "Library"
    assert result["cmd_id"] == _FakeUUID.hex
    cmd_files = list(commands_dir.glob("*.json"))
    assert len(cmd_files) == 1
    cmd = json.loads(cmd_files[0].read_text(encoding="utf-8"))
    assert cmd["action"] == "navigate"
    assert cmd["view"] == "Library"
    assert cmd["id"] == _FakeUUID.hex


def test_send_navigation_command_timeout_returns_ok_false(tmp_path, monkeypatch):
    commands_dir = tmp_path / "commands"
    acks_dir = tmp_path / "acks"
    monkeypatch.setattr(bridge_ipc, "MCP_COMMANDS_DIR", commands_dir)
    monkeypatch.setattr(bridge_ipc, "MCP_ACKS_DIR", acks_dir)
    monkeypatch.setattr(bridge_ipc.uuid, "uuid4", lambda: _FakeUUID())

    # wait=True makes it poll for an ack that never arrives.
    result = bridge.send_navigation_command("Library", wait=True, timeout=0.05)

    assert result.get("ok") is False


# ---------------------------------------------------------------------------
# app.CommandChannel (file-based IPC consumer)
# ---------------------------------------------------------------------------
def test_command_channel_handles_navigate(tmp_path):
    from skill_manager.app import CommandChannel

    app = MagicMock()
    app.ui = MagicMock()
    app.ui.currentView = "QuickCopy"

    ch = CommandChannel.__new__(CommandChannel)
    ch.app = app
    ch._acks_dir = tmp_path
    ch._commands_dir = tmp_path
    ch._watcher = None

    # Valid navigation -> ack ok + view switched.
    ch._handle_command({"action": "navigate", "view": "Library", "id": "id1"})
    ack = json.loads((tmp_path / "id1.json").read_text(encoding="utf-8"))
    assert ack == {"ok": True, "view": "Library"}
    assert app.ui.currentView == "Library"

    # Invalid view -> ack ok:false.
    ch._handle_command({"action": "navigate", "view": "Bogus", "id": "id2"})
    ack2 = json.loads((tmp_path / "id2.json").read_text(encoding="utf-8"))
    assert ack2["ok"] is False

    # Unknown action -> ack ok:false.
    ch._handle_command({"action": "explode", "id": "id3"})
    ack3 = json.loads((tmp_path / "id3.json").read_text(encoding="utf-8"))
    assert ack3["ok"] is False


# ---------------------------------------------------------------------------
# tools/screenshot.py — sm_screenshot handler
# ---------------------------------------------------------------------------
def _make_png_b64(size=(10, 10), color="blue"):
    img = Image.new("RGB", size, color)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def test_handler_capture_success(monkeypatch):
    b64 = _make_png_b64()
    monkeypatch.setattr(
        tools_screenshot,
        "_bridge_capture_app_window",
        lambda *a, **kw: (b64, 10, 10),
    )
    monkeypatch.setattr(
        tools_screenshot, "_bridge_send_navigation_command", lambda v: {"ok": True, "view": v}
    )
    handlers = tools_screenshot.get_handlers()
    result = handlers["sm_screenshot"]({"navigate": "Library"})

    assert isinstance(result, ToolResult)
    assert result.ok is True
    assert result.data is not None
    assert result.data["image_b64"] == b64
    assert result.data["width"] == 10
    assert result.data["height"] == 10
    assert result.data["view"] == "Library"


def test_handler_no_gui_returns_ok_false(monkeypatch):
    monkeypatch.setattr(
        tools_screenshot, "_bridge_capture_app_window", lambda *a, **kw: (None, 0, 0)
    )
    handlers = tools_screenshot.get_handlers()
    result = handlers["sm_screenshot"]({})

    assert result.ok is False
    assert "not running" in (result.error or "")


def test_handler_invalid_view(monkeypatch):
    monkeypatch.setattr(tools_screenshot, "_bridge_capture_app_window", lambda: (None, 0, 0))
    handlers = tools_screenshot.get_handlers()
    result = handlers["sm_screenshot"]({"navigate": "Bogus"})

    assert result.ok is False
    assert "invalid navigate view" in (result.error or "")


def test_handler_save_true_writes_png(monkeypatch, tmp_path):
    b64 = _make_png_b64()
    monkeypatch.setattr(
        tools_screenshot,
        "_bridge_capture_app_window",
        lambda *a, **kw: (b64, 10, 10),
    )
    monkeypatch.setattr(
        tools_screenshot, "_bridge_send_navigation_command", lambda v: {"ok": True, "view": v}
    )
    monkeypatch.setattr(tools_screenshot, "_REPO_ROOT", tmp_path)
    handlers = tools_screenshot.get_handlers()
    result = handlers["sm_screenshot"]({"navigate": "Library", "save": True})

    assert result.ok is True
    assert result.data is not None
    save_path = result.data["save_path"]
    assert save_path
    assert Path(save_path).exists()
    assert save_path.endswith(".png")


def test_schema_and_handlers_present():
    assert "sm_screenshot" in tools_screenshot.TOOL_SCHEMAS
    schema = tools_screenshot.TOOL_SCHEMAS["sm_screenshot"]
    assert "navigate" in schema["inputSchema"]["properties"]
    assert schema["inputSchema"]["properties"]["navigate"]["enum"] == [
        "QuickCopy",
        "Library",
        "Updates",
        "Settings",
    ]
    assert "save" in schema["inputSchema"]["properties"]

    handlers = tools_screenshot.get_handlers()
    assert "sm_screenshot" in handlers
    assert callable(handlers["sm_screenshot"])


def test_server_registers_sm_screenshot():
    from skill_manager.mcp import server
    from skill_manager.mcp.tools.screenshot import TOOL_SCHEMAS

    server.create_mcp_server()
    assert "sm_screenshot" in TOOL_SCHEMAS

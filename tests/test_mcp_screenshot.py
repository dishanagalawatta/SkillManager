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
# bridge.ipc_enabled() — kill-switch that keeps tests/CI off a live GUI
# ---------------------------------------------------------------------------
def test_ipc_enabled_by_default(monkeypatch):
    """Cross-process IPC is on unless the environment says otherwise."""
    monkeypatch.delenv("SKILL_MANAGER_MCP_NO_IPC", raising=False)
    assert bridge.ipc_enabled() is True
    monkeypatch.setenv("SKILL_MANAGER_MCP_NO_IPC", "0")
    assert bridge.ipc_enabled() is True


def test_ipc_disabled_refuses_without_writing(tmp_path, monkeypatch):
    """SKILL_MANAGER_MCP_NO_IPC=1 makes every sender refuse and write nothing.

    This is what keeps a test (or CI) run from driving the developer's live GUI
    through the repo-relative drop-dir.
    """
    commands_dir = tmp_path / "commands"
    acks_dir = tmp_path / "acks"
    monkeypatch.setattr(bridge_ipc, "MCP_COMMANDS_DIR", commands_dir)
    monkeypatch.setattr(bridge_ipc, "MCP_ACKS_DIR", acks_dir)
    monkeypatch.setenv("SKILL_MANAGER_MCP_NO_IPC", "1")

    assert bridge.ipc_enabled() is False
    assert bridge.send_navigation_command("Library", wait=True, timeout=0.05) == {
        "ok": False,
        "error": "ipc_disabled",
    }
    assert bridge.send_capture_command(wait=True, timeout=0.05) == {
        "ok": False,
        "error": "ipc_disabled",
    }
    assert bridge.send_debug_overlay_command(True, wait=True, timeout=0.05) == {
        "ok": False,
        "error": "ipc_disabled",
    }
    assert not commands_dir.exists()
    assert not acks_dir.exists()


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
# CommandChannel._normalize_capture_image (window-only grab → PIL-readable PNG)
# ---------------------------------------------------------------------------
def test_normalize_capture_image_produces_pil_readable_png(tmp_path):
    from PySide6.QtGui import QImage

    from skill_manager.controllers.command_channel import _normalize_capture_image

    # A 30-bit BGR image at a fractional DPR mirrors the Wayland
    # grabWindow() state that made Qt's PNG writer emit a corrupt IDAT.
    image = QImage(64, 48, QImage.Format.Format_BGR30)
    image.fill(0x00FF0000)
    image.setDevicePixelRatio(1.3046875)

    normalized = _normalize_capture_image(image)

    assert normalized.format() == QImage.Format.Format_RGBA8888
    assert normalized.devicePixelRatio() == 1.0
    assert (normalized.width(), normalized.height()) == (64, 48)

    out_path = tmp_path / "normalized.png"
    assert normalized.save(str(out_path), "PNG")
    img = Image.open(out_path)
    assert img.size == (64, 48)


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
        "_bridge_capture_app_window_info",
        lambda *a, **kw: {
            "image_b64": b64,
            "width": 10,
            "height": 10,
            "source": "live-gui",
            "error": None,
        },
    )
    monkeypatch.setattr(
        tools_screenshot,
        "_bridge_navigate_view",
        lambda v: {"ok": True, "view": v, "in_process": True, "verified": True},
    )
    handlers = tools_screenshot.get_handlers()
    result = handlers["sm_screenshot"]({"navigate": "Library"})

    assert isinstance(result, ToolResult)
    assert result.ok is True
    assert result.data is not None
    assert result.data["image_b64"] == b64
    assert result.data["width"] == 10
    assert result.data["height"] == 10
    assert result.data["source"] == "live-gui"
    assert result.data["view"] == "Library"


def test_handler_headless_source_reported(monkeypatch):
    """sm_screenshot reports the headless offscreen render as its source."""
    b64 = _make_png_b64()
    monkeypatch.setattr(
        tools_screenshot,
        "_bridge_capture_app_window_info",
        lambda *a, **kw: {
            "image_b64": b64,
            "width": 800,
            "height": 600,
            "source": "headless-qml",
            "error": None,
        },
    )
    handlers = tools_screenshot.get_handlers()
    result = handlers["sm_screenshot"]({})

    assert result.ok is True
    assert result.data is not None
    assert result.data["source"] == "headless-qml"


def test_handler_navigation_failure_prevents_capture(monkeypatch):
    """A failed navigation fails the call instead of capturing the wrong view."""
    captures: list[int] = []
    monkeypatch.setattr(
        tools_screenshot,
        "_bridge_navigate_view",
        lambda v: {"ok": False, "error": "not acknowledged by GUI"},
    )
    monkeypatch.setattr(
        tools_screenshot,
        "_bridge_capture_app_window_info",
        lambda *a, **kw: captures.append(1),
    )

    result = tools_screenshot.get_handlers()["sm_screenshot"]({"navigate": "Settings"})

    assert result.ok is False
    assert result.error is not None
    assert "not acknowledged" in result.error
    assert captures == []


def test_handler_no_gui_returns_ok_false(monkeypatch):
    monkeypatch.setattr(
        tools_screenshot,
        "_bridge_capture_app_window_info",
        lambda *a, **kw: {
            "image_b64": None,
            "width": 0,
            "height": 0,
            "source": None,
            "error": "capture_failed",
        },
    )
    handlers = tools_screenshot.get_handlers()
    result = handlers["sm_screenshot"]({})

    assert result.ok is False
    assert "not running" in (result.error or "")


def test_handler_invalid_view(monkeypatch):
    monkeypatch.setattr(
        tools_screenshot,
        "_bridge_capture_app_window_info",
        lambda **kw: {"image_b64": None, "width": 0, "height": 0, "source": None},
    )
    handlers = tools_screenshot.get_handlers()
    result = handlers["sm_screenshot"]({"navigate": "Bogus"})

    assert result.ok is False
    assert "invalid navigate view" in (result.error or "")


def test_handler_save_true_writes_png(monkeypatch, tmp_path):
    b64 = _make_png_b64()
    monkeypatch.setattr(
        tools_screenshot,
        "_bridge_capture_app_window_info",
        lambda *a, **kw: {
            "image_b64": b64,
            "width": 10,
            "height": 10,
            "source": "native",
            "error": None,
        },
    )
    monkeypatch.setattr(
        tools_screenshot,
        "_bridge_navigate_view",
        lambda v: {"ok": True, "view": v, "in_process": True, "verified": True},
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


# ---------------------------------------------------------------------------
# Capture strategy: background (headless) must win over the live GUI
# ---------------------------------------------------------------------------
def _headless_stub(monkeypatch, *, enabled=True, png=("HEADLESS", 100, 50), render=None):
    """Stub the lazy offscreen renderer so no Qt/display is needed."""
    import skill_manager.mcp.bridge._qml_headless as qml_headless

    monkeypatch.setattr(qml_headless, "headless_qml_enabled", lambda: enabled)
    monkeypatch.setattr(
        qml_headless,
        "capture_headless_window",
        lambda *a, **kw: png,
    )
    monkeypatch.setattr(
        qml_headless,
        "headless_render_info",
        lambda: render or {"engine": "Main.qml", "sha256": "deadbeef", "style": "Basic"},
    )
    return qml_headless


def test_capture_prefers_headless_and_never_contacts_live_gui(monkeypatch):
    """A headless --mcp capture must not send IPC to the running app."""
    _headless_stub(monkeypatch)
    ipc_calls: list[int] = []

    def _ipc(**kwargs):
        ipc_calls.append(1)
        return {"ok": False}

    monkeypatch.setattr(bridge_capture, "send_capture_command", _ipc)

    info = bridge.capture_app_window_info()

    assert info["source"] == "headless-qml"
    assert info["image_b64"] == "HEADLESS"
    assert (info["width"], info["height"]) == (100, 50)
    assert info["render"]["sha256"] == "deadbeef"
    assert ipc_calls == [], "headless capture must not touch the live GUI"


def test_capture_strategy_live_uses_ipc_and_skips_headless(monkeypatch, tmp_path):
    qml_headless = _headless_stub(monkeypatch)
    headless_calls: list[int] = []
    monkeypatch.setattr(
        qml_headless,
        "capture_headless_window",
        lambda *a, **kw: headless_calls.append(1) or (None, 0, 0),
    )

    img = Image.new("RGB", (8, 6), "blue")
    live_png = tmp_path / "live.png"
    img.save(live_png)
    monkeypatch.setattr(
        bridge_capture,
        "send_capture_command",
        lambda **kw: {"ok": True, "capture_path": str(live_png)},
    )

    info = bridge.capture_app_window_info(strategy="live")

    assert info["source"] == "live-gui"
    assert (info["width"], info["height"]) == (8, 6)
    assert headless_calls == []


def test_capture_strategy_headless_never_uses_ipc(monkeypatch):
    _headless_stub(monkeypatch, enabled=False)

    def _ipc(**kwargs):
        raise AssertionError("strategy='headless' must not contact the live GUI")

    monkeypatch.setattr(bridge_capture, "send_capture_command", _ipc)

    info = bridge.capture_app_window_info(strategy="headless")

    assert info["source"] is None
    assert info["error"] == "headless_render_unavailable"


def test_capture_auto_falls_back_to_ipc_when_headless_empty(monkeypatch, tmp_path):
    _headless_stub(monkeypatch, png=(None, 0, 0))
    img = Image.new("RGB", (5, 4), "green")
    live_png = tmp_path / "live.png"
    img.save(live_png)
    monkeypatch.setattr(
        bridge_capture,
        "send_capture_command",
        lambda **kw: {"ok": True, "capture_path": str(live_png)},
    )

    info = bridge.capture_app_window_info(strategy="auto")

    assert info["source"] == "live-gui"


def test_capture_strategy_live_reports_failure_without_headless(monkeypatch):
    _headless_stub(monkeypatch, png=(None, 0, 0))
    monkeypatch.setattr(bridge_capture, "send_capture_command", lambda **kw: {"ok": False})
    monkeypatch.setattr(bridge_capture, "_fallback_capture_linux", lambda: (None, 0, 0))

    info = bridge.capture_app_window_info(strategy="live")

    assert info["source"] is None
    assert info["error"] == "live_capture_unavailable"


def test_screenshot_handler_exposes_render_provenance(monkeypatch):
    _headless_stub(monkeypatch, render={"engine": "Main.qml", "sha256": "cafebabe"})
    monkeypatch.setattr(
        tools_screenshot,
        "_bridge_navigate_view",
        lambda v: {"ok": True, "view": v, "in_process": True, "verified": True},
    )

    handlers = tools_screenshot.get_handlers()
    result = handlers["sm_screenshot"]({"navigate": "Library"})

    assert result.ok is True
    assert result.data["source"] == "headless-qml"
    assert result.data["render"]["sha256"] == "cafebabe"
    assert result.data["view"] == "Library"


def test_screenshot_schema_documents_source():
    props = tools_screenshot.TOOL_SCHEMAS["sm_screenshot"]["inputSchema"]["properties"]
    assert props["source"]["enum"] == ["auto", "headless", "live"]
    assert props["source"]["default"] == "auto"


def test_screenshot_live_source_error_mentions_live(monkeypatch):
    monkeypatch.setattr(
        tools_screenshot,
        "_bridge_capture_app_window_info",
        lambda **kw: {"image_b64": None, "width": 0, "height": 0, "source": None},
    )

    handlers = tools_screenshot.get_handlers()
    result = handlers["sm_screenshot"]({"source": "live"})

    assert result.ok is False
    assert "live capture failed" in result.error

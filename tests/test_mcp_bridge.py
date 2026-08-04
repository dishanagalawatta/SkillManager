"""Lightweight tests for the MCP bridge functions that need no Qt/AppController.

These exercise the parts of ``skill_manager.mcp.bridge`` that are safe to run
headless: the async job buffer (``run_async_job`` / ``get_job``), the
filesystem grep (``static_analyze``), and the input-injection guard on the
cross-process GUI tools (``send_mouse_move`` / ``send_mouse_click`` /
``send_type_text``). They never call ``get_app_controller()``, so no Qt
application is constructed.
"""

from __future__ import annotations

import ctypes
import sys
import time
from typing import Any
from unittest.mock import MagicMock

import pytest

import skill_manager.utils.linux as linux_utils
from skill_manager.mcp import bridge
from skill_manager.mcp.bridge import _input as bridge_input, _static as bridge_static
from skill_manager.utils import input_guard


def test_run_async_job_returns_id_and_buffers() -> None:
    """run_async_job returns a job_id and records a running buffer immediately."""
    job_id = bridge.run_async_job(lambda: 42)

    assert isinstance(job_id, str) and job_id
    job = bridge.get_job(job_id)
    assert job is not None
    assert job["job_id"] == job_id
    assert job["status"] in {"running", "done", "error"}


def test_run_async_job_captures_result() -> None:
    """A completed job buffer carries the return value and done status."""
    job_id = bridge.run_async_job(lambda: {"ok": True})

    # Poll briefly; the fallback daemon thread should finish quickly.
    job: dict[str, Any] | None = None
    for _ in range(50):
        job = bridge.get_job(job_id)
        if job is not None and job["status"] == "done":
            break
        time.sleep(0.02)

    assert job is not None
    assert job["status"] == "done"
    assert job["result"] == {"ok": True}
    assert job["error"] is None


def test_run_async_job_captures_exception() -> None:
    """A failing job records the error and an error status."""
    job_id = bridge.run_async_job(lambda: (_ for _ in ()).throw(RuntimeError("kaboom")))

    job = None
    for _ in range(50):
        job = bridge.get_job(job_id)
        if job is not None and job["status"] == "error":
            break
        time.sleep(0.02)

    assert job is not None
    assert job["status"] == "error"
    assert "kaboom" in (job["error"] or "")


def test_get_job_unknown_returns_none() -> None:
    """get_job returns None for an id that was never dispatched."""
    assert bridge.get_job("does-not-exist") is None


def test_static_analyze_finds_pattern(tmp_path: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    """static_analyze greps a directory tree and returns file/line/text matches."""
    monkeypatch.setattr(bridge_static, "_REPO_ROOT", tmp_path)
    (tmp_path / "a.py").write_text("x = 1\nSECRET_TOKEN = 'abc'\ny = 2\n", encoding="utf-8")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.py").write_text("print('hello')\nSECRET_TOKEN = 9\n", encoding="utf-8")

    matches = bridge.static_analyze(pattern="SECRET_TOKEN", path=".")

    assert len(matches) == 2
    files = {m["file"] for m in matches}
    assert any("a.py" in f for f in files)
    assert any("b.py" in f for f in files)
    assert all(m["text"] for m in matches)


def test_static_analyze_invalid_pattern(tmp_path: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    """An invalid regex yields a structured error entry, not a crash."""
    monkeypatch.setattr(bridge_static, "_REPO_ROOT", tmp_path)

    matches = bridge.static_analyze(pattern="([", path=".")

    assert len(matches) == 1
    assert "error" in matches[0]
    assert "invalid_pattern" in matches[0]["error"]


def test_static_analyze_missing_path(tmp_path: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    """A non-existent search root yields an empty match list."""
    monkeypatch.setattr(bridge_static, "_REPO_ROOT", tmp_path)

    matches = bridge.static_analyze(pattern="x", path="no-such-dir-xyz")

    assert matches == []


def _clear_injection_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Simulate a real desktop session so the guard can reach its target check."""
    """Simulate a real desktop session so the guard can reach its target check."""
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.delenv("QT_QPA_PLATFORM", raising=False)


def test_input_tools_refuse_under_pytest_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Under pytest (PYTEST_CURRENT_TEST set) every input tool refuses."""
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "tests/test_mcp_bridge.py::f")

    for result in (
        bridge.send_mouse_move(10, 10),
        bridge.send_mouse_click(10, 10),
        bridge.send_type_text("hello"),
    ):
        assert result["ok"] is False
        assert "pytest" in (result["error"] or "")


def test_input_tools_refuse_offscreen(monkeypatch: pytest.MonkeyPatch) -> None:
    """With QT_QPA_PLATFORM=offscreen every input tool refuses."""
    _clear_injection_env(monkeypatch)
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    for result in (
        bridge.send_mouse_move(10, 10),
        bridge.send_mouse_click(10, 10),
        bridge.send_type_text("hello"),
    ):
        assert result["ok"] is False
        assert "offscreen" in (result["error"] or "")


def test_input_tools_refuse_without_gui_window(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No SkillManager window present => injection refused (never blind)."""
    _clear_injection_env(monkeypatch)
    monkeypatch.setattr(input_guard, "gui_window_present", lambda: False)

    for result in (
        bridge.send_mouse_move(10, 10),
        bridge.send_mouse_click(10, 10),
        bridge.send_type_text("hello"),
    ):
        assert result["ok"] is False
        assert "window" in (result["error"] or "")


def test_input_tools_run_when_gui_window_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With a live GUI window present, tools delegate to the platform backends."""
    _clear_injection_env(monkeypatch)
    monkeypatch.setattr(input_guard, "gui_window_present", lambda: True)
    if sys.platform == "win32":
        # The bridge dispatches to the Win32 backend on Windows: stub the
        # user32 surface so no real input reaches the runner's desktop.
        fake_user32 = MagicMock()
        fake_user32.SetCursorPos.return_value = 1
        fake_user32.SendInput.return_value = 5
        monkeypatch.setattr(ctypes.windll, "user32", fake_user32)
    else:
        monkeypatch.setattr(linux_utils, "move_mouse", lambda x, y: True)
        monkeypatch.setattr(linux_utils, "click_mouse", lambda x, y, button: True)
        monkeypatch.setattr(linux_utils, "type_text", lambda text: len(text))

    move = bridge.send_mouse_move(10, 10)
    click = bridge.send_mouse_click(10, 10)
    typed = bridge.send_type_text("hello")

    assert move["ok"] is True
    assert click["ok"] is True
    assert typed == {"ok": True, "chars": 5}


def test_send_type_text_win32_handles_lowercase(monkeypatch: pytest.MonkeyPatch) -> None:
    """Win32 typing must emit events for lowercase letters.

    Regression: the vk table only holds uppercase A-Z, and the fallback
    lowered the char again, so ``"hello"`` produced an empty event list and
    returned ``{"ok": True, "chars": 0}`` on Windows.
    """
    fake_user32 = MagicMock()
    fake_user32.SendInput.side_effect = lambda n, inputs, size: n
    loader = MagicMock()
    loader.user32 = fake_user32
    # ctypes.windll does not exist on non-Windows: allow creating it.
    monkeypatch.setattr(ctypes, "windll", loader, raising=False)

    result = bridge_input._send_type_text_win32("hello")

    # 5 chars x (keydown + keyup) = 10 events delivered to SendInput.
    assert result == {"ok": True, "chars": 10}

"""Unit tests for the centralized input-injection guard.

The guard is the single safety boundary for real mouse/keyboard injection:
tests, CI, and headless processes must never trigger real injection, and MCP
input tools must never inject into a window that is not the live SkillManager
GUI.
"""

from __future__ import annotations

import ctypes
import sys
from unittest.mock import MagicMock, patch

from skill_manager.utils import input_guard


def test_injection_allowed_clean_env(monkeypatch) -> None:
    """A real interactive desktop session (no pytest/offscreen) is allowed."""
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.delenv("QT_QPA_PLATFORM", raising=False)

    assert input_guard.injection_allowed() is True


def test_injection_allowed_blocked_under_pytest(monkeypatch) -> None:
    """Running under pytest must never allow real injection."""
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "tests/test_input_guard.py::f")
    monkeypatch.delenv("QT_QPA_PLATFORM", raising=False)

    assert input_guard.injection_allowed() is False


def test_injection_allowed_blocked_offscreen(monkeypatch) -> None:
    """QT_QPA_PLATFORM=offscreen (headless/CI) must never allow injection."""
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    assert input_guard.injection_allowed() is False


def test_gui_window_present_linux_found(monkeypatch) -> None:
    """A real X11 window id counts as present."""
    monkeypatch.setattr(sys, "platform", "linux")
    with patch("skill_manager.utils.linux.find_window_by_title", return_value=123):
        assert input_guard.gui_window_present() is True


def test_gui_window_present_linux_missing(monkeypatch) -> None:
    """No window found => absent (fail closed)."""
    monkeypatch.setattr(sys, "platform", "linux")
    with patch("skill_manager.utils.linux.find_window_by_title", return_value=None):
        assert input_guard.gui_window_present() is False


def test_gui_window_present_win32_found(monkeypatch) -> None:
    """A non-zero HWND counts as present."""
    monkeypatch.setattr(sys, "platform", "win32")
    windll = MagicMock()
    windll.user32.FindWindowW.return_value = 456
    monkeypatch.setattr(ctypes, "windll", windll, raising=False)

    assert input_guard.gui_window_present() is True


def test_gui_window_present_win32_missing(monkeypatch) -> None:
    """HWND 0 means the window is absent (fail closed)."""
    monkeypatch.setattr(sys, "platform", "win32")
    windll = MagicMock()
    windll.user32.FindWindowW.return_value = 0
    monkeypatch.setattr(ctypes, "windll", windll, raising=False)

    assert input_guard.gui_window_present() is False


def test_refused_reason_none_when_allowed(monkeypatch) -> None:
    """All checks pass => no refusal reason."""
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.delenv("QT_QPA_PLATFORM", raising=False)
    with patch("skill_manager.utils.input_guard.gui_window_present", return_value=True):
        assert input_guard.injection_refused_reason() is None


def test_refused_reason_pytest(monkeypatch) -> None:
    """Under pytest the reason names pytest."""
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "tests/test_input_guard.py::f")

    reason = input_guard.injection_refused_reason()

    assert reason is not None
    assert "pytest" in reason


def test_refused_reason_offscreen(monkeypatch) -> None:
    """Offscreen mode yields an offscreen refusal reason."""
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    reason = input_guard.injection_refused_reason()

    assert reason is not None
    assert "offscreen" in reason


def test_refused_reason_window_missing(monkeypatch) -> None:
    """GUI window absent => refusal mentions the window."""
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.delenv("QT_QPA_PLATFORM", raising=False)
    with patch("skill_manager.utils.input_guard.gui_window_present", return_value=False):
        reason = input_guard.injection_refused_reason()

    assert reason is not None
    assert "window" in reason

"""Centralized safety guard for real input injection (mouse/keyboard).

Every code path that sends real keystrokes or mouse events to the user's
live desktop (``ydotool`` uinput, ``pyautogui``, Win32 ``keybd_event`` /
``SendInput``) MUST consult this module before acting.  The injection policy
lives in exactly one place so it can never drift between callers:

* ``injection_allowed()`` — environment check: never from tests, CI, or
  headless (``QT_QPA_PLATFORM=offscreen``) processes.
* ``gui_window_present()`` — the live SkillManager GUI window must actually
  be running before MCP input tools inject anything (otherwise keystrokes
  land in whatever window the user currently has focused).
* ``injection_refused_reason()`` — combined check returning a human-readable
  reason, used by the MCP bridge input tools.
"""

from __future__ import annotations

import ctypes
import os
import sys

# Live GUI window title (Main.qml: title: "Skill Manager").
_WINDOW_TITLE = "Skill Manager"


def injection_allowed() -> bool:
    """Return True only when running in a real interactive desktop session.

    Input injection must never run from tests, CI, or headless processes.
    Those environments set ``PYTEST_CURRENT_TEST`` and/or
    ``QT_QPA_PLATFORM=offscreen``.
    """
    if "PYTEST_CURRENT_TEST" in os.environ:
        return False
    return os.environ.get("QT_QPA_PLATFORM") != "offscreen"


def gui_window_present() -> bool:
    """Return True only when a live SkillManager GUI window can be found.

    Mirrors the ``get_window_info`` presence semantics, but **fails closed**:
    the window has to be positively identified before anything is injected.
    On Windows that means a non-zero HWND from ``FindWindowW``; on Linux a
    real window id from ``find_window_by_title``.

    The Wayland "cannot locate the window" sentinel (``WINDOW_ID_UNKNOWN``)
    counts as *absent*: without ``xdotool``/``wmctrl`` there is no way to
    prove the SkillManager window is the one that would receive the
    keystrokes, so injecting would risk typing into an unrelated window.
    """
    if sys.platform == "win32":
        try:
            return bool(ctypes.windll.user32.FindWindowW(None, _WINDOW_TITLE))
        except Exception:  # noqa: BLE001 - never crash the guard
            return False
    from skill_manager.utils.linux import WINDOW_ID_UNKNOWN, find_window_by_title

    window_id = find_window_by_title(_WINDOW_TITLE)
    return window_id is not None and window_id != WINDOW_ID_UNKNOWN


def injection_refused_reason() -> str | None:
    """Return why input injection must be refused, else ``None``.

    Refusal reasons, in priority order: running under pytest, offscreen
    (headless/CI) mode, or no live SkillManager GUI window.
    """
    if "PYTEST_CURRENT_TEST" in os.environ:
        return "Input injection disabled under pytest"
    if os.environ.get("QT_QPA_PLATFORM") == "offscreen":
        return "Input injection disabled in offscreen mode"
    if not gui_window_present():
        return "SkillManager GUI window not running — refusing input injection"
    return None

"""Cross-process GUI interaction (mouse + keyboard) for the MCP bridge."""

from __future__ import annotations

import ctypes
import sys
from typing import Any

from skill_manager.utils import input_guard

from ._telemetry import _log_call
from ._win32 import _find_skill_manager_window, _get_window_rect


# ---------------------------------------------------------------------------
# Cross-process GUI interaction (mouse + keyboard via Win32)
# ---------------------------------------------------------------------------
def send_mouse_move(x: int, y: int) -> dict[str, Any]:
    """Move the system cursor to screen coordinates (``x``, ``y``).

    Best-effort: returns ``{"ok": True}`` on success, ``{"ok": False, "error": ...}``
    on failure.
    """
    _log_call("send_mouse_move")
    refused = input_guard.injection_refused_reason()
    if refused is not None:
        return {"ok": False, "error": refused}
    if sys.platform == "win32":
        try:
            result = ctypes.windll.user32.SetCursorPos(x, y)  # type: ignore[attr-defined]
            if not result:
                return {"ok": False, "error": "SetCursorPos returned 0"}
            return {"ok": True}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}
    # Linux: try ydotool / pyautogui
    from skill_manager.utils.linux import move_mouse as _linux_move_mouse

    if _linux_move_mouse(x, y):
        return {"ok": True}
    return {"ok": False, "error": "No mouse injection tool available (try ydotool)"}


def send_mouse_click(
    x: int | None = None,
    y: int | None = None,
    button: str = "left",
    double: bool = False,
) -> dict[str, Any]:
    """Move the cursor to (``x``, ``y``) if provided and click.

    ``button`` may be ``"left"``, ``"right"``, or ``"middle"``.
    ``double`` performs a double-click when ``True``.

    Best-effort: returns ``{"ok": True}`` on success, ``{"ok": False, "error": ...}``
    on failure.
    """
    _log_call("send_mouse_click")
    refused = input_guard.injection_refused_reason()
    if refused is not None:
        return {"ok": False, "error": refused}
    if sys.platform == "win32":
        try:
            user32 = ctypes.windll.user32  # type: ignore[attr-defined]

            if x is not None and y is not None and not user32.SetCursorPos(x, y):
                return {"ok": False, "error": "SetCursorPos failed"}

            flags: dict[str, tuple[int, int]] = {
                "left": (0x0002, 0x0004),
                "right": (0x0008, 0x0010),
                "middle": (0x0020, 0x0040),
            }
            down_flag, up_flag = flags.get(button, (0x0002, 0x0004))

            for _ in range(2 if double else 1):
                user32.mouse_event(down_flag, 0, 0, 0, 0)
                user32.mouse_event(up_flag, 0, 0, 0, 0)

            return {"ok": True}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}
    # Linux: try ydotool / pyautogui
    from skill_manager.utils.linux import click_mouse as _linux_click

    if _linux_click(x, y, button):
        return {"ok": True}
    return {"ok": False, "error": "No mouse injection tool available (try ydotool)"}


def send_type_text(text: str) -> dict[str, Any]:
    """Type ``text`` into the currently focused window.

    On Windows uses ``SendInput`` (handles Shift-key modulation etc.).
    On Linux tries ``ydotool`` or ``pyautogui``.

    Best-effort: returns ``{"ok": True, "chars": N}`` on success,
    ``{"ok": False, "error": ...}`` on failure.
    """
    _log_call("send_type_text")
    refused = input_guard.injection_refused_reason()
    if refused is not None:
        return {"ok": False, "error": refused}
    if sys.platform == "win32":
        return _send_type_text_win32(text)
    # Linux: try ydotool / pyautogui
    from skill_manager.utils.linux import type_text as _linux_type

    chars = _linux_type(text)
    if chars > 0:
        return {"ok": True, "chars": chars}
    return {"ok": False, "error": "No keyboard injection tool available (try ydotool)"}


def _send_type_text_win32(text: str) -> dict[str, Any]:
    """Type ``text`` via Win32 ``SendInput``."""
    try:
        user32 = ctypes.windll.user32  # type: ignore[attr-defined]

        input_keyboard = 1
        keyeventf_keyup = 0x0002

        class KEYBDINPUT(ctypes.Structure):
            _fields_ = [
                ("wVk", ctypes.c_uint16),
                ("wScan", ctypes.c_uint16),
                ("dwFlags", ctypes.c_uint32),
                ("time", ctypes.c_uint32),
                ("dwExtraInfo", ctypes.c_void_p),
            ]

        class _InputUnion(ctypes.Union):
            _fields_ = [("ki", KEYBDINPUT)]

        class INPUT(ctypes.Structure):
            _fields_ = [
                ("type", ctypes.c_uint32),
                ("union", _InputUnion),
            ]

        _vk: dict[str, int] = {
            **{chr(0x30 + i): 0x30 + i for i in range(10)},
            **{chr(0x41 + i): 0x41 + i for i in range(26)},
            "`": 0xC0,
            "~": 0xC0,
            "-": 0xBD,
            "_": 0xBD,
            "=": 0xBB,
            "+": 0xBB,
            "[": 0xDB,
            "{": 0xDB,
            "]": 0xDD,
            "}": 0xDD,
            "\\": 0xDC,
            "|": 0xDC,
            ";": 0xBA,
            ":": 0xBA,
            "'": 0xDE,
            '"': 0xDE,
            ",": 0xBC,
            "<": 0xBC,
            ".": 0xBE,
            ">": 0xBE,
            "/": 0xBF,
            "?": 0xBF,
            " ": 0x20,
            "\n": 0x0D,
            "\t": 0x09,
        }

        _shift_chars: set[str] = set('ABCDEFGHIJKLMNOPQRSTUVWXYZ~!@#$%^&*()_+{}|:"<>?')

        vk_shift = 0x10

        def _make_input(vk: int, flags: int = 0) -> INPUT:
            ki = KEYBDINPUT(wVk=vk, wScan=0, dwFlags=flags, time=0, dwExtraInfo=0)
            return INPUT(type=input_keyboard, union=_InputUnion(ki=ki))

        def _key_down(vk: int) -> INPUT:
            return _make_input(vk, 0)

        def _key_up(vk: int) -> INPUT:
            return _make_input(vk, keyeventf_keyup)

        sentinel = []
        for ch in text:
            vk = _vk.get(ch)
            if vk is None:
                lower = ch.lower()
                vk = _vk.get(lower)
                if vk is None:
                    continue

            need_shift = ch in _shift_chars
            if need_shift:
                sentinel.append(_key_down(vk_shift))
            sentinel.append(_key_down(vk))
            sentinel.append(_key_up(vk))
            if need_shift:
                sentinel.append(_key_up(vk_shift))

        if not sentinel:
            return {"ok": True, "chars": 0}

        n = len(sentinel)
        inputs_type = INPUT * n
        inputs = inputs_type(*sentinel)

        sent = user32.SendInput(n, inputs, ctypes.sizeof(INPUT))
        return {"ok": True, "chars": sent}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


def get_window_info() -> dict[str, Any]:
    """Return the live SkillManager window's geometry and DPI.

    On Windows uses Win32 ``GetWindowRect``.  On Linux uses
    ``xdotool`` / ``wmctrl`` if available.

    Returns ``{"ok": True, "window": {left, top, right, bottom, width, height}}``
    or ``{"ok": False, "error": ...}`` if the window is not found.
    """
    _log_call("get_window_info")
    if sys.platform == "win32":
        try:
            hwnd = _find_skill_manager_window()
            if hwnd is None:
                return {"ok": False, "error": "SkillManager window not found"}

            rect = _get_window_rect(hwnd)
            if rect is None:
                return {"ok": False, "error": "GetWindowRect failed"}

            left, top, right, bottom = rect
            return {
                "ok": True,
                "hwnd": hwnd,
                "left": left,
                "top": top,
                "right": right,
                "bottom": bottom,
                "width": right - left,
                "height": bottom - top,
            }
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    # Linux: try xdotool / wmctrl
    from skill_manager.utils.linux import find_window_by_title, get_window_geometry

    wid = find_window_by_title("Skill Manager")
    if wid is None:
        return {"ok": False, "error": "SkillManager window not found (no xdotool/wmctrl)"}

    geo = get_window_geometry(wid)
    if geo is None:
        return {"ok": False, "error": "Could not query window geometry on Linux"}

    left, top, width, height = geo["left"], geo["top"], geo["width"], geo["height"]
    return {
        "ok": True,
        "window_id": wid,
        "left": left,
        "top": top,
        "right": left + width,
        "bottom": top + height,
        "width": width,
        "height": height,
    }

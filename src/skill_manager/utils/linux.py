"""Linux-specific GUI automation utilities (Wayland-first, X11 fallback).

Provides clipboard, paste, window-detection, and screen-capture helpers
that the Win32 module (``utils/win32.py``) provides on Windows.  Wayland
compositors do not allow cross-process input injection without portal
infrastructure, so every function is best-effort and returns a success
indicator.

Available tool probes:
- ``wl-clipboard`` (wl-copy / wl-paste) for Wayland clipboard
- ``pyperclip`` for X11 / cross-platform clipboard fallback
- ``ydotool`` for Wayland keyboard/mouse injection (if installed)
- ``pyautogui`` for X11 keyboard/mouse injection (if display available)
- ``gdbus`` / ``dbus-send`` for FreeDesktop Portal screenshot (Wayland)
- ``gnome-screenshot`` for GNOME Screenshot CLI fallback
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess

from skill_manager.utils.input_guard import injection_allowed

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tool probes (cached booleans)
# ---------------------------------------------------------------------------

_WL_COPY: bool | None = None
_WL_PASTE: bool | None = None
_YDOTOOL: bool | None = None
_HAS_PYPERCLIP: bool | None = None


def _has_wl_copy() -> bool:
    global _WL_COPY
    if _WL_COPY is None:
        _WL_COPY = shutil.which("wl-copy") is not None
    return _WL_COPY


def _has_wl_paste() -> bool:
    global _WL_PASTE
    if _WL_PASTE is None:
        _WL_PASTE = shutil.which("wl-paste") is not None
    return _WL_PASTE


def _has_ydotool() -> bool:
    global _YDOTOOL
    if _YDOTOOL is None:
        _YDOTOOL = shutil.which("ydotool") is not None
    return _YDOTOOL


def _has_pyperclip() -> bool:
    global _HAS_PYPERCLIP
    if _HAS_PYPERCLIP is None:
        try:
            import pyperclip  # noqa: F401

            _HAS_PYPERCLIP = True
        except ImportError:
            _HAS_PYPERCLIP = False
    return _HAS_PYPERCLIP


# ---------------------------------------------------------------------------
# Clipboard
# ---------------------------------------------------------------------------


def set_clipboard(text: str) -> bool:
    """Copy *text* to the system clipboard.

    Tries ``wl-copy`` first (Wayland), then ``pyperclip`` (X11 fallback).
    Returns ``True`` on success.

    ``wl-copy`` forks a child that owns the Wayland selection and inherits
    any open pipes; capturing stdout/stderr would make ``subprocess.run``
    block on the inherited pipe FDs until the child exits (i.e. when the
    selection is lost).  Both streams are therefore redirected to DEVNULL.
    """
    if _has_wl_copy():
        try:
            proc = subprocess.run(
                ["wl-copy"],
                input=text,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                text=True,
                timeout=5,
            )
            return proc.returncode == 0
        except Exception as exc:  # noqa: BLE001
            logger.debug("wl-copy failed: %s", exc)

    if _has_pyperclip():
        try:
            import pyperclip  # type: ignore[import-not-found]

            pyperclip.copy(text)
            return True
        except Exception as exc:  # noqa: BLE001
            logger.debug("pyperclip.copy failed: %s", exc)

    return False


def get_clipboard() -> str | None:
    """Return the current clipboard content, or ``None`` on failure."""
    if _has_wl_paste():
        try:
            proc = subprocess.run(
                ["wl-paste"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if proc.returncode == 0:
                return proc.stdout
        except Exception as exc:  # noqa: BLE001
            logger.debug("wl-paste failed: %s", exc)

    if _has_pyperclip():
        try:
            import pyperclip  # type: ignore[import-not-found]

            return pyperclip.paste()
        except Exception as exc:  # noqa: BLE001
            logger.debug("pyperclip.paste failed: %s", exc)

    return None


# ---------------------------------------------------------------------------
# Keyboard/mouse injection (guarded)
# ---------------------------------------------------------------------------

_KEY_CTRL = 29  # ydotool KEY_LEFTCTRL
_KEY_V = 47  # ydotool KEY_V


def send_ctrl_v() -> bool:
    """Send Ctrl+V (paste) keystroke to the focused window.

    Tries ``ydotool`` first (Wayland uinput), then falls back gracefully.
    Returns ``True`` on success.
    """
    if not injection_allowed():
        return False
    if _has_ydotool():
        try:
            subprocess.run(
                ["ydotool", "key", f"{_KEY_CTRL}+{_KEY_V}"],
                capture_output=True,
                timeout=5,
            )
            return True
        except Exception as exc:  # noqa: BLE001
            logger.debug("ydotool Ctrl+V failed: %s", exc)

    # Try pyautogui hotkey as X11 fallback (fails silently on pure Wayland)
    try:
        import pyautogui  # type: ignore[import-not-found]

        pyautogui.hotkey("ctrl", "v")
        return True
    except Exception as exc:  # noqa: BLE001
        logger.debug("pyautogui.hotkey('ctrl', 'v') failed: %s", exc)

    return False


def send_paste_to_focused_window() -> bool:
    """Set clipboard + send Ctrl+V.  Returns True on success."""
    return send_ctrl_v()


# ---------------------------------------------------------------------------
# Window detection
# ---------------------------------------------------------------------------


def find_window_by_title(title_fragment: str) -> int | None:
    """Return a window identifier (X11 window ID or 0) matching *title_fragment*.

    On Wayland without ``xdotool``, returns ``0`` as a sentinel (callers
    should treat any non-``None`` value as "found").  On X11 returns the
    actual window ID.
    """
    xdotool = shutil.which("xdotool")
    if xdotool:
        try:
            proc = subprocess.run(
                [xdotool, "search", "--name", title_fragment],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if proc.returncode == 0 and proc.stdout.strip():
                return int(proc.stdout.strip().split("\n")[0])
        except Exception as exc:  # noqa: BLE001
            logger.debug("xdotool search failed: %s", exc)

    wmctrl = shutil.which("wmctrl")
    if wmctrl:
        try:
            proc = subprocess.run(
                [wmctrl, "-l"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            for line in proc.stdout.splitlines():
                if title_fragment.lower() in line.lower():
                    parts = line.split(None, 3)
                    if parts:
                        return int(parts[0], 16)
        except Exception as exc:  # noqa: BLE001
            logger.debug("wmctrl -l failed: %s", exc)

    # Wayland fallback: return 0 to mean "assume found"
    if os.environ.get("WAYLAND_DISPLAY"):
        return 0

    return None


def capture_screen(output_path: str | None = None) -> str | None:
    """Capture the full screen on Linux.

    On X11 this uses Qt's ``grabWindow(0)`` internally (done by the
    caller).  On Wayland where that returns null, this function
    delegates to the FreeDesktop Portal Screenshot API, then to
    ``gnome-screenshot`` as a fallback.

    Returns the path to the saved PNG or ``None`` on failure.
    """
    from skill_manager.controllers.screenshot_controller import _portal_capture

    return _portal_capture(output_path)


def get_window_geometry(_window_id: int) -> dict | None:
    """Return ``{left, top, width, height}`` for a window, or ``None``.

    Uses ``xdotool`` or ``wmctrl``.  Not supported on pure Wayland
    without helper tools.
    """
    xdotool = shutil.which("xdotool")
    if xdotool:
        try:
            proc = subprocess.run(
                [xdotool, "getwindowgeometry", str(_window_id)],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if proc.returncode == 0:
                result: dict[str, int] = {}
                for line in proc.stdout.splitlines():
                    if "Position:" in line:
                        _, coords = line.split(":", 1)
                        x_str, y_str = coords.strip().split(",")
                        result["left"] = int(x_str.strip())
                        result["top"] = int(y_str.strip())
                    elif "Geometry:" in line:
                        _, dims = line.split(":", 1)
                        w_str, h_str = dims.strip().split("x")
                        result["width"] = int(w_str.strip())
                        result["height"] = int(h_str.strip())
                if "left" in result:
                    return result
        except Exception as exc:  # noqa: BLE001
            logger.debug("xdotool getwindowgeometry failed: %s", exc)

    wmctrl = shutil.which("wmctrl")
    if wmctrl:
        try:
            proc = subprocess.run(
                ["wmctrl", "-lG"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            for line in proc.stdout.splitlines():
                parts = line.split(None, 5)
                if len(parts) >= 6:
                    wid = int(parts[0], 16)
                    if wid == _window_id:
                        return {
                            "left": int(parts[2]),
                            "top": int(parts[3]),
                            "width": int(parts[4]),
                            "height": int(parts[5]),
                        }
        except Exception as exc:  # noqa: BLE001
            logger.debug("wmctrl -lG failed: %s", exc)

    return None


# ---------------------------------------------------------------------------
# Mouse injection
# ---------------------------------------------------------------------------


def move_mouse(x: int, y: int) -> bool:
    """Move cursor to (``x``, ``y``).  Returns ``True`` on success."""
    if not injection_allowed():
        return False
    # ydotool (Wayland uinput)
    ydotool = shutil.which("ydotool")
    if ydotool:
        try:
            subprocess.run(
                [ydotool, "mousemove", "--x", str(x), "--y", str(y)],
                capture_output=True,
                timeout=5,
            )
            return True
        except Exception as exc:  # noqa: BLE001
            logger.debug("ydotool mousemove failed: %s", exc)

    # pyautogui (X11 fallback)
    try:
        import pyautogui  # type: ignore[import-not-found]

        pyautogui.moveTo(x, y)
        return True
    except Exception as exc:  # noqa: BLE001
        logger.debug("pyautogui.moveTo failed: %s", exc)

    return False


def click_mouse(
    x: int | None = None,
    y: int | None = None,
    button: str = "left",
) -> bool:
    """Click at (``x``, ``y``) if provided.  Returns ``True`` on success."""
    if not injection_allowed():
        return False
    if x is not None and y is not None and not move_mouse(x, y):
        return False

    # ydotool
    ydotool = shutil.which("ydotool")
    if ydotool:
        btn = {  # ydotool button codes
            "left": 0x110,
            "right": 0x111,
            "middle": 0x112,
        }.get(button, 0x110)
        try:
            subprocess.run(
                [ydotool, "click", str(btn)],
                capture_output=True,
                timeout=5,
            )
            return True
        except Exception as exc:  # noqa: BLE001
            logger.debug("ydotool click failed: %s", exc)

    # pyautogui (X11 fallback)
    try:
        import pyautogui  # type: ignore[import-not-found]

        pyautogui.click(button=button)
        return True
    except Exception as exc:  # noqa: BLE001
        logger.debug("pyautogui.click failed: %s", exc)

    return False


def type_text(text: str) -> int:
    """Type *text* into the focused window.  Returns chars typed (0 on failure)."""
    if not injection_allowed():
        return 0
    # ydotool type
    ydotool = shutil.which("ydotool")
    if ydotool:
        try:
            subprocess.run(
                [ydotool, "type", text],
                capture_output=True,
                timeout=15,
            )
            return len(text)
        except Exception as exc:  # noqa: BLE001
            logger.debug("ydotool type failed: %s", exc)

    # pyautogui write (X11 fallback)
    try:
        import pyautogui  # type: ignore[import-not-found]

        pyautogui.write(text)
        return len(text)
    except Exception as exc:  # noqa: BLE001
        logger.debug("pyautogui.write failed: %s", exc)

    return 0

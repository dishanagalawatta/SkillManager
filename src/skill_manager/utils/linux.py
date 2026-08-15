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
- ``gdbus`` / ``dbus-send`` for FreeDesktop Portal snap (Wayland)
- ``gnome-screenshot`` for GNOME screenshot CLI fallback
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess

from skill_manager.utils.input_guard import injection_allowed

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tool probes & Environment Sanitization
# ---------------------------------------------------------------------------

_WL_COPY: bool | None = None
_WL_PASTE: bool | None = None
_YDOTOOL: bool | None = None
_HAS_PYPERCLIP: bool | None = None
_XCLIP: bool | None = None
_XSEL: bool | None = None

_FALLBACK_BIN_DIRS = (
    "/usr/bin",
    "/usr/local/bin",
    "/bin",
    "/snap/bin",
    os.path.expanduser("~/.local/bin"),
)


def get_clean_env() -> dict[str, str]:
    """Return an os.environ dictionary suitable for invoking host system binaries.

    When running in a PyInstaller frozen binary or AppImage on Linux, the process
    inherits an altered LD_LIBRARY_PATH (pointing to _internal or $APPDIR/usr/lib).
    System binaries (such as wl-copy, wl-paste, xclip, xsel, ydotool, xdotool,
    wmctrl, gdbus, xdg-open) compiled against host system libraries can crash or
    fail to resolve symbols when executed under the bundled LD_LIBRARY_PATH.

    This helper restores LD_LIBRARY_PATH to LD_LIBRARY_PATH_ORIG (if present) or
    removes it, ensuring system binaries load their expected system libraries.
    """
    env = dict(os.environ)
    if "LD_LIBRARY_PATH_ORIG" in env:
        env["LD_LIBRARY_PATH"] = env["LD_LIBRARY_PATH_ORIG"]
    else:
        env.pop("LD_LIBRARY_PATH", None)
    return env


def find_system_binary(name: str) -> str | None:
    """Locate a system executable, checking PATH and common Linux binary locations."""
    found = shutil.which(name)
    if found:
        return found

    for prefix in _FALLBACK_BIN_DIRS:
        candidate = os.path.join(prefix, name)
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate

    return None


def is_wayland_active() -> bool:
    """Return True if running under an active Wayland session."""
    if os.environ.get("XDG_SESSION_TYPE") == "wayland":
        return True
    wayland_display = os.environ.get("WAYLAND_DISPLAY")
    if wayland_display:
        runtime_dir = os.environ.get("XDG_RUNTIME_DIR")
        if runtime_dir and os.path.exists(os.path.join(runtime_dir, wayland_display)):
            return True
        return True
    runtime_dir = os.environ.get("XDG_RUNTIME_DIR")
    if runtime_dir and os.path.isdir(runtime_dir):
        try:
            for item in os.listdir(runtime_dir):
                if item.startswith("wayland-"):
                    return True
        except OSError:
            pass
    return False


def _has_wl_copy() -> bool:
    global _WL_COPY
    if _WL_COPY is None:
        _WL_COPY = find_system_binary("wl-copy") is not None
    return _WL_COPY


def _has_wl_paste() -> bool:
    global _WL_PASTE
    if _WL_PASTE is None:
        _WL_PASTE = find_system_binary("wl-paste") is not None
    return _WL_PASTE


def _has_xclip() -> bool:
    global _XCLIP
    if _XCLIP is None:
        _XCLIP = find_system_binary("xclip") is not None
    return _XCLIP


def _has_xsel() -> bool:
    global _XSEL
    if _XSEL is None:
        _XSEL = find_system_binary("xsel") is not None
    return _XSEL


def _has_ydotool() -> bool:
    global _YDOTOOL
    if _YDOTOOL is None:
        _YDOTOOL = find_system_binary("ydotool") is not None
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

    Tries ``wl-copy`` first if Wayland is active or wl-copy is present, then
    ``xclip``, ``xsel``, and ``pyperclip`` (X11 fallbacks). Returns ``True`` on success.

    ``wl-copy`` forks a child that owns the Wayland selection and inherits
    any open pipes; capturing stdout/stderr would make ``subprocess.run``
    block on the inherited pipe FDs until the child exits (i.e. when the
    selection is lost).  Both streams are therefore redirected to DEVNULL.
    """
    clean_env = get_clean_env()

    # 1. Wayland / wl-copy
    wl_copy_bin = find_system_binary("wl-copy")
    if wl_copy_bin and (_has_wl_copy() or is_wayland_active()):
        try:
            proc = subprocess.run(
                [wl_copy_bin],
                input=text,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                text=True,
                timeout=5,
                env=clean_env,
            )
            if proc.returncode == 0:
                return True
        except Exception as exc:  # noqa: BLE001
            logger.debug("wl-copy failed: %s", exc)

    # 2. X11 xclip
    xclip_bin = find_system_binary("xclip")
    if xclip_bin:
        try:
            proc = subprocess.run(
                [xclip_bin, "-selection", "clipboard"],
                input=text,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                text=True,
                timeout=5,
                env=clean_env,
            )
            if proc.returncode == 0:
                return True
        except Exception as exc:  # noqa: BLE001
            logger.debug("xclip failed: %s", exc)

    # 3. X11 xsel
    xsel_bin = find_system_binary("xsel")
    if xsel_bin:
        try:
            proc = subprocess.run(
                [xsel_bin, "--clipboard", "--input"],
                input=text,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                text=True,
                timeout=5,
                env=clean_env,
            )
            if proc.returncode == 0:
                return True
        except Exception as exc:  # noqa: BLE001
            logger.debug("xsel failed: %s", exc)

    # 4. pyperclip
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
    clean_env = get_clean_env()

    # 1. Wayland / wl-paste
    wl_paste_bin = find_system_binary("wl-paste")
    if wl_paste_bin and (_has_wl_paste() or is_wayland_active()):
        try:
            proc = subprocess.run(
                [wl_paste_bin],
                capture_output=True,
                text=True,
                timeout=5,
                env=clean_env,
            )
            if proc.returncode == 0:
                return proc.stdout
        except Exception as exc:  # noqa: BLE001
            logger.debug("wl-paste failed: %s", exc)

    # 2. X11 xclip
    xclip_bin = find_system_binary("xclip")
    if xclip_bin:
        try:
            proc = subprocess.run(
                [xclip_bin, "-selection", "clipboard", "-o"],
                capture_output=True,
                text=True,
                timeout=5,
                env=clean_env,
            )
            if proc.returncode == 0:
                return proc.stdout
        except Exception as exc:  # noqa: BLE001
            logger.debug("xclip -o failed: %s", exc)

    # 3. X11 xsel
    xsel_bin = find_system_binary("xsel")
    if xsel_bin:
        try:
            proc = subprocess.run(
                [xsel_bin, "--clipboard", "--output"],
                capture_output=True,
                text=True,
                timeout=5,
                env=clean_env,
            )
            if proc.returncode == 0:
                return proc.stdout
        except Exception as exc:  # noqa: BLE001
            logger.debug("xsel --output failed: %s", exc)

    # 4. pyperclip
    if _has_pyperclip():
        try:
            import pyperclip  # type: ignore[import-not-found]

            return pyperclip.paste()
        except Exception as exc:  # noqa: BLE001
            logger.debug("pyperclip.paste failed: %s", exc)

    return None


def set_clipboard_image(image_path: str) -> bool:
    """Copy an image file at *image_path* to the system clipboard (PNG format)."""
    if not os.path.isfile(image_path):
        return False

    clean_env = get_clean_env()

    wl_copy_bin = find_system_binary("wl-copy")
    if wl_copy_bin and (_has_wl_copy() or is_wayland_active()):
        try:
            with open(image_path, "rb") as f:
                proc = subprocess.run(
                    [wl_copy_bin, "--type", "image/png"],
                    stdin=f,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=5,
                    env=clean_env,
                )
            if proc.returncode == 0:
                return True
        except Exception as exc:  # noqa: BLE001
            logger.debug("wl-copy image failed: %s", exc)

    xclip_bin = find_system_binary("xclip")
    if xclip_bin:
        try:
            with open(image_path, "rb") as f:
                proc = subprocess.run(
                    [xclip_bin, "-selection", "clipboard", "-t", "image/png"],
                    stdin=f,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=5,
                    env=clean_env,
                )
            if proc.returncode == 0:
                return True
        except Exception as exc:  # noqa: BLE001
            logger.debug("xclip image failed: %s", exc)

    return False


# ---------------------------------------------------------------------------
# Keyboard/mouse injection (guarded)
# ---------------------------------------------------------------------------

_KEY_CTRL = 29  # ydotool KEY_LEFTCTRL
_KEY_V = 47  # ydotool KEY_V

# ydotool's "+" combos (e.g. "29+47") can leave modifiers stuck; use an
# explicit press/release sequence instead.
_CTRL_V_SEQUENCE = (
    f"{_KEY_CTRL}:1",
    f"{_KEY_V}:1",
    f"{_KEY_V}:0",
    f"{_KEY_CTRL}:0",
)


def _ydotool_daemon_socket() -> str:
    """Return the ydotool daemon socket path (matches ydotool's lookup)."""
    socket_path = os.environ.get("YDOTOOL_SOCKET")
    if socket_path:
        return socket_path
    runtime_dir = os.environ.get("XDG_RUNTIME_DIR")
    if runtime_dir:
        return os.path.join(runtime_dir, ".ydotool_socket")
    return "/tmp/.ydotool_socket"


def _ydotool_daemon_alive() -> bool:
    """Return True when the ydotool daemon socket exists on disk."""
    return os.path.exists(_ydotool_daemon_socket())


def ydotool_daemon_health() -> str:
    """Describe ydotool daemon state for actionable error messages.

    Returns ``"not-installed"`` when the binary is missing, ``"daemon-down"``
    when the binary exists but ``ydotoold`` is unreachable, else ``"ok"``.
    """
    ydotool_bin = find_system_binary("ydotool")
    if not ydotool_bin:
        return "not-installed"
    try:
        proc = subprocess.run(
            [ydotool_bin, "debug"],
            capture_output=True,
            text=True,
            timeout=5,
            env=get_clean_env(),
        )
        return "ok" if proc.returncode == 0 else "daemon-down"
    except Exception as exc:  # noqa: BLE001
        logger.debug("ydotool debug probe failed: %s", exc)
        return "daemon-down"


def send_ctrl_v() -> bool:
    """Send Ctrl+V (paste) keystroke to the focused window.

    Tries ``ydotool`` first (Wayland uinput) with an explicit
    press/release sequence, then ``pyautogui`` on X11 only.
    Returns ``True`` on success.
    """
    if not injection_allowed():
        return False
    ydotool_bin = find_system_binary("ydotool")
    if ydotool_bin and _ydotool_daemon_alive():
        try:
            proc = subprocess.run(
                [ydotool_bin, "key", *_CTRL_V_SEQUENCE],
                capture_output=True,
                text=True,
                timeout=5,
                env=get_clean_env(),
            )
            if proc.returncode == 0:
                return True
            logger.warning(
                "ydotool Ctrl+V failed (rc=%d): %s",
                proc.returncode,
                proc.stderr.strip(),
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug("ydotool Ctrl+V failed: %s", exc)

    # pyautogui is an X11-only fallback (fails silently on pure Wayland)
    if os.environ.get("XDG_SESSION_TYPE") == "x11":
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
    clean_env = get_clean_env()
    xdotool_bin = find_system_binary("xdotool")
    if xdotool_bin:
        try:
            proc = subprocess.run(
                [xdotool_bin, "search", "--name", title_fragment],
                capture_output=True,
                text=True,
                timeout=5,
                env=clean_env,
            )
            if proc.returncode == 0 and proc.stdout.strip():
                return int(proc.stdout.strip().split("\n")[0])
        except Exception as exc:  # noqa: BLE001
            logger.debug("xdotool search failed: %s", exc)

    wmctrl_bin = find_system_binary("wmctrl")
    if wmctrl_bin:
        try:
            proc = subprocess.run(
                [wmctrl_bin, "-l"],
                capture_output=True,
                text=True,
                timeout=5,
                env=clean_env,
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
    from skill_manager.controllers.snap_controller import _portal_capture

    return _portal_capture(output_path)


def get_window_geometry(_window_id: int) -> dict | None:
    """Return ``{left, top, width, height}`` for a window, or ``None``.

    Uses ``xdotool`` or ``wmctrl``.  Not supported on pure Wayland
    without helper tools.
    """
    clean_env = get_clean_env()
    xdotool_bin = find_system_binary("xdotool")
    if xdotool_bin:
        try:
            proc = subprocess.run(
                [xdotool_bin, "getwindowgeometry", str(_window_id)],
                capture_output=True,
                text=True,
                timeout=5,
                env=clean_env,
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

    wmctrl_bin = find_system_binary("wmctrl")
    if wmctrl_bin:
        try:
            proc = subprocess.run(
                [wmctrl_bin, "-lG"],
                capture_output=True,
                text=True,
                timeout=5,
                env=clean_env,
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
    ydotool_bin = find_system_binary("ydotool")
    if ydotool_bin:
        try:
            subprocess.run(
                [ydotool_bin, "mousemove", "--x", str(x), "--y", str(y)],
                capture_output=True,
                timeout=5,
                env=get_clean_env(),
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
    ydotool_bin = find_system_binary("ydotool")
    if ydotool_bin:
        btn = {  # ydotool button codes
            "left": 0x110,
            "right": 0x111,
            "middle": 0x112,
        }.get(button, 0x110)
        try:
            subprocess.run(
                [ydotool_bin, "click", str(btn)],
                capture_output=True,
                timeout=5,
                env=get_clean_env(),
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
    ydotool_bin = find_system_binary("ydotool")
    if ydotool_bin:
        try:
            subprocess.run(
                [ydotool_bin, "type", text],
                capture_output=True,
                timeout=15,
                env=get_clean_env(),
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

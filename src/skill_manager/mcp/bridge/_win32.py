"""Win32 window-management helpers for capture and input (Windows only)."""

from __future__ import annotations

import ctypes

# Live GUI window title prefix (Main.qml: title: "Skill Manager").
_WINDOW_TITLE_PREFIX = "skill manager"


# ---------------------------------------------------------------------------
# Cross-process window capture + navigation (sm_screenshot)
# ---------------------------------------------------------------------------
class _BITMAPINFOHEADER(ctypes.Structure):  # noqa: N801 - Win32 struct name
    """Minimal BITMAPINFOHEADER for GetDIBits capture."""

    _fields_ = [
        ("biSize", ctypes.c_uint32),
        ("biWidth", ctypes.c_int32),
        ("biHeight", ctypes.c_int32),
        ("biPlanes", ctypes.c_uint16),
        ("biBitCount", ctypes.c_uint16),
        ("biCompression", ctypes.c_uint32),
        ("biSizeImage", ctypes.c_uint32),
        ("biXPelsPerMeter", ctypes.c_int32),
        ("biYPelsPerMeter", ctypes.c_int32),
        ("biClrUsed", ctypes.c_uint32),
        ("biClrImportant", ctypes.c_uint32),
    ]


def _enum_top_level_windows() -> list[int]:
    hwnds: list[int] = []
    try:
        user32 = ctypes.windll.user32  # type: ignore[attr-defined]
        enum_proc = ctypes.WINFUNCTYPE(  # type: ignore[attr-defined]
            ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p
        )

        def _callback(hwnd: int, _lparam: int) -> bool:
            hwnds.append(hwnd)
            return True

        user32.EnumWindows(enum_proc(_callback), 0)
    except Exception:  # noqa: BLE001 - never crash the bridge
        return []
    return hwnds


def _get_window_title(hwnd: int) -> str:
    try:
        user32 = ctypes.windll.user32  # type: ignore[attr-defined]
        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return ""
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        return buf.value or ""
    except Exception:  # noqa: BLE001
        return ""


def _get_window_rect(hwnd: int) -> tuple[int, int, int, int] | None:
    try:
        from skill_manager.utils.win32 import RECT

        rect = RECT()
        user32 = ctypes.windll.user32  # type: ignore[attr-defined]
        if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            return None
        return (rect.left, rect.top, rect.right, rect.bottom)
    except Exception:  # noqa: BLE001
        return None


def _find_skill_manager_window() -> int | None:
    try:
        for hwnd in _enum_top_level_windows():
            title = _get_window_title(hwnd)
            if title and title.lower().startswith(_WINDOW_TITLE_PREFIX):
                return hwnd
    except Exception:  # noqa: BLE001
        return None
    return None


class _WINDOWPLACEMENT(ctypes.Structure):  # noqa: N801
    """Minimal WINDOWPLACEMENT for GetWindowPlacement."""

    _fields_ = [
        ("length", ctypes.c_uint),
        ("flags", ctypes.c_uint),
        ("showCmd", ctypes.c_uint),
        ("ptMinPosition_x", ctypes.c_long),
        ("ptMinPosition_y", ctypes.c_long),
        ("ptMaxPosition_x", ctypes.c_long),
        ("ptMaxPosition_y", ctypes.c_long),
        ("rcNormalLeft", ctypes.c_long),
        ("rcNormalTop", ctypes.c_long),
        ("rcNormalRight", ctypes.c_long),
        ("rcNormalBottom", ctypes.c_long),
    ]


def _get_window_placement(hwnd: int) -> int | None:
    """Return the current show state (SW_*) of the window, or ``None``."""
    try:
        user32 = ctypes.windll.user32  # type: ignore[attr-defined]
        wp = _WINDOWPLACEMENT()
        wp.length = ctypes.sizeof(wp)
        if user32.GetWindowPlacement(hwnd, ctypes.byref(wp)):
            return wp.showCmd
    except Exception:  # noqa: BLE001
        pass
    return None


def _get_normal_rect(hwnd: int) -> tuple[int, int, int, int] | None:
    """Return the window's restored (normal) position from ``WINDOWPLACEMENT``.

    For a minimised window ``GetWindowRect`` returns ``(-32000, -32000)``
    with a tiny size. Use ``GetWindowPlacement.rcNormalPosition`` instead
    to get the dimensions the window will have when restored.
    Returns ``(left, top, right, bottom)`` or ``None``.
    """
    try:
        user32 = ctypes.windll.user32  # type: ignore[attr-defined]
        wp = _WINDOWPLACEMENT()
        wp.length = ctypes.sizeof(wp)
        if user32.GetWindowPlacement(hwnd, ctypes.byref(wp)):
            return (
                wp.rcNormalLeft,
                wp.rcNormalTop,
                wp.rcNormalRight,
                wp.rcNormalBottom,
            )
    except Exception:  # noqa: BLE001
        pass
    return None


def _is_minimized(hwnd: int) -> bool:
    """Check whether the window is currently minimised."""
    show = _get_window_placement(hwnd)
    return show == 2  # SW_SHOWMINIMIZED


def _show_window_force(hwnd: int) -> None:
    """Temporarily restore a minimised window so capture works.

    Uses ``SW_RESTORE`` to restore the window — the caller should follow
    up with PrintWindow (which captures the window's own content regardless
    of overlapping windows) and then minimise again.
    """
    user32 = ctypes.windll.user32  # type: ignore[attr-defined]
    user32.ShowWindow(hwnd, 9)  # SW_RESTORE

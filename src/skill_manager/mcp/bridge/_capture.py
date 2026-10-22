"""Cross-process window capture (IPC-first, Win32 fallback) for the MCP bridge."""

from __future__ import annotations

import base64
import ctypes
import io
import sys
import time
from typing import Any

from ._ipc import send_capture_command
from ._telemetry import _log_call, get_diagnostic_logger
from ._win32 import (
    _BITMAPINFOHEADER,
    _find_skill_manager_window,
    _get_normal_rect,
    _get_window_rect,
    _is_minimized,
    _show_window_force,
)


def _buffer_has_content(buf) -> bool:
    """True when a captured bitmap contains more than empty black pixels.

    A window that refused to paint leaves an all-zero buffer; that is the
    only case where the desktop-DC fallback is used.
    """
    try:
        raw = bytes(buf)
    except Exception:  # noqa: BLE001
        return True
    return any(raw)


def _capture_window_to_image(
    hwnd: int,
    width: int,
    height: int,
    window_left: int = 0,
    window_top: int = 0,
) -> Any | None:
    """Capture the window identified by *hwnd* into a PIL ``Image``.

    Capture strategy:
    1. If minimised — restore the window, sleep 200ms for Qt to paint, then
       call PrintWindow (own-content, unaffected by overlapping windows).
    2. If visible — call PrintWindow directly.
    3. Always emit WM_PRINT message as a secondary capture attempt.
    4. Desktop DC ``BitBlt`` **only as a fallback**, when the window painted
       nothing into the memory DC.  Running it unconditionally used to
       overwrite a good ``PrintWindow`` result with the on-screen pixels at
       those coordinates, so an overlapping window (or a different Z-order)
       bled into the capture.
    5. If the window was minimised, re-minimise after capture.

    Returns ``None`` on failure.
    """
    try:
        user32 = ctypes.windll.user32  # type: ignore[attr-defined]
        gdi32 = ctypes.windll.gdi32  # type: ignore[attr-defined]

        hwnd_dc = user32.GetWindowDC(hwnd)
        if not hwnd_dc:
            return None
        mem_dc = gdi32.CreateCompatibleDC(hwnd_dc)
        if not mem_dc:
            user32.ReleaseDC(hwnd, hwnd_dc)
            return None
        bitmap = gdi32.CreateCompatibleBitmap(hwnd_dc, width, height)
        if not bitmap:
            gdi32.DeleteDC(mem_dc)
            user32.ReleaseDC(hwnd, hwnd_dc)
            return None
        gdi32.SelectObject(mem_dc, bitmap)

        was_minimized = _is_minimized(hwnd)
        if was_minimized:
            # Qt skips content rendering when minimised — PrintWindow only
            # captures the title bar. Restore first so Qt paints the full UI,
            # then use PrintWindow (which captures own content regardless of
            # overlapping windows).
            _show_window_force(hwnd)
            ctypes.windll.kernel32.Sleep(200)  # wait for Qt paint cycle
            user32.PrintWindow(hwnd, mem_dc, 0x00000002)  # PW_RENDERFULLCONTENT
            user32.PrintWindow(hwnd, mem_dc, 0)
        else:
            # Window is visible — PrintWindow works directly
            user32.PrintWindow(hwnd, mem_dc, 0x00000002)  # PW_RENDERFULLCONTENT
            user32.PrintWindow(hwnd, mem_dc, 0)

        # WM_PRINT — asks the window to paint itself into our DC
        _prf = 0x00000002 | 0x00000004 | 0x00000010 | 0x00000020  # NONCLIENT|CLIENT|CHILDREN|OWNED
        user32.SendMessageTimeoutW(
            hwnd,
            0x0317,
            mem_dc,
            _prf,
            0,
            2000,
            None,
        )

        if was_minimized:
            user32.ShowWindow(hwnd, 6)  # SW_MINIMIZE

        # ── Read the bitmap data via GetDIBits ────────────────────────────
        bmi = _BITMAPINFOHEADER()
        bmi.biSize = ctypes.sizeof(_BITMAPINFOHEADER)
        bmi.biWidth = width
        bmi.biHeight = -height  # top-down
        bmi.biPlanes = 1
        bmi.biBitCount = 32
        bmi.biCompression = 0  # BI_RGB

        buf_size = width * height * 4
        buf = ctypes.create_string_buffer(buf_size)
        success = gdi32.GetDIBits(mem_dc, bitmap, 0, height, buf, ctypes.byref(bmi), 0)

        # The desktop BitBlt is a *fallback*: it is only used when the
        # window painted nothing at all.  Running it unconditionally
        # replaced the PrintWindow result with whatever was on screen at
        # those coordinates.
        if success and not _buffer_has_content(buf):
            desk_dc = user32.GetDC(0)
            if desk_dc:
                gdi32.BitBlt(
                    mem_dc,
                    0,
                    0,
                    width,
                    height,
                    desk_dc,
                    window_left,
                    window_top,
                    0x00CC0020,
                )
                user32.ReleaseDC(0, desk_dc)
                success = gdi32.GetDIBits(mem_dc, bitmap, 0, height, buf, ctypes.byref(bmi), 0)

        gdi32.DeleteObject(bitmap)
        gdi32.DeleteDC(mem_dc)
        user32.ReleaseDC(hwnd, hwnd_dc)

        if not success:
            return None

        from PIL import Image  # type: ignore[import-not-found]

        # GetDIBits with BI_RGB / 32bpp returns pixels in BGRX byte order
        # (Blue, Green, Red, Reserved) on little-endian Windows. Using
        # "RGBA" would swap R↔B, making blue accent appear orange.
        image = Image.frombytes("BGRA", (width, height), buf.raw)
        return image.convert("RGB")
    except Exception:  # noqa: BLE001
        return None


def _pil_image_to_base64(image: Any) -> str | None:
    try:
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode("ascii")
    except Exception:  # noqa: BLE001
        return None


def _resize_window(hwnd: int, new_width: int, new_height: int) -> tuple[int, int, int, int] | None:
    """Resize a window via ``SetWindowPos`` and return the previous rect.

    Returns ``(left, top, width, height)`` of the old geometry, or ``None``
    on failure. The caller should restore the original geometry after capture.
    """
    try:
        old_rect = _get_window_rect(hwnd)
        if old_rect is None:
            return None
        left, top, right, bottom = old_rect
        old_w = right - left
        old_h = bottom - top
        user32 = ctypes.windll.user32  # type: ignore[attr-defined]
        swp_nozorder = 0x0004
        swp_noactivate = 0x0010
        user32.SetWindowPos(
            hwnd,
            0,
            left,
            top,
            new_width,
            new_height,
            swp_nozorder | swp_noactivate,
        )
        # Small settle delay for the UI to repaint
        time.sleep(0.15)
        return (left, top, old_w, old_h)
    except Exception:  # noqa: BLE001
        return None


def _restore_window(hwnd: int, left: int, top: int, width: int, height: int) -> None:
    """Restore a window to its previous position and size."""
    try:
        user32 = ctypes.windll.user32  # type: ignore[attr-defined]
        swp_nozorder = 0x0004
        swp_noactivate = 0x0010
        user32.SetWindowPos(
            hwnd,
            0,
            left,
            top,
            width,
            height,
            swp_nozorder | swp_noactivate,
        )
        time.sleep(0.15)
    except Exception:  # noqa: BLE001
        pass


def capture_app_window(
    resize_width: int | None = None,
    resize_height: int | None = None,
    strategy: str = "auto",
) -> tuple[str | None, int, int]:
    """Capture the SkillManager UI and return ``(base64_png, width, height)``.

    Tries, in order: the in-process offscreen render (``--mcp`` mode), file-based
    IPC to the live GUI, the platform-native window capture, and finally the
    offscreen render again as a last resort. ``strategy`` selects the order —
    see ``capture_app_window_info``.

    Returns ``(None, 0, 0)`` when every strategy fails.
    """
    _log_call("capture_app_window")

    info = capture_app_window_info(
        resize_width=resize_width,
        resize_height=resize_height,
        strategy=strategy,
    )
    return (info["image_b64"], info["width"], info["height"])


def _capture_result(
    b64: str,
    width: int,
    height: int,
    source: str,
    render: dict[str, Any] | None = None,
    view: str | None = None,
) -> dict[str, Any]:
    """Build the capture result envelope for *source*.

    ``view`` is only set when the producing process reports it (the live GUI
    returns its real ``currentView``); otherwise the caller falls back to this
    process's view.
    """
    result: dict[str, Any] = {
        "image_b64": b64,
        "width": int(width),
        "height": int(height),
        "source": source,
        "error": None,
    }
    if render:
        result["render"] = render
    if view:
        result["view"] = view
    return result


def capture_app_window_info(
    resize_width: int | None = None,
    resize_height: int | None = None,
    strategy: str = "auto",
) -> dict[str, Any]:
    """Capture the SkillManager UI and report which strategy produced the image.

    Strategies, in order for ``strategy="auto"``:

    1. ``"headless-qml"`` — offscreen render of ``Main.qml`` inside this
       process (``--mcp`` mode). Runs first so visual checks never touch a
       running GUI: no view switch, no activation, no resize, no restore from
       the taskbar. It is the same QML, style and controller the app ships, so
       the pixels stay authoritative — ``render`` in the result carries the
       `Main.qml` path and SHA-256 as evidence.
    2. ``"live-gui"`` — file-based IPC to the running Qt GUI, whose
       ``CommandChannel._capture_screenshot`` handler calls
       ``QQuickWindow::grabWindow()`` (works minimised, no colour cast). Used
       when headless rendering is unavailable (``--mcp-light``) or when the
       caller explicitly asks for ``strategy="live"``.
    3. ``"native"`` — Win32 PrintWindow + CreateDIBSection (Windows only; the
       Linux implementation is a no-op because Wayland forbids cross-process
       grabs without a portal).
    4. ``"headless-qml"`` again as a last resort when the live/native paths
       failed.

    ``strategy="headless"`` skips the live GUI entirely; ``strategy="live"``
    only tries the live/native paths and never falls back to an offscreen
    render. Returns a dict with ``image_b64``, ``width``, ``height``,
    ``source``, ``error`` (``render`` for offscreen captures, ``view`` when the
    producing process reported it); ``source`` is ``None`` when every strategy
    failed.
    """
    _log_call("capture_app_window_info")

    strategy = (strategy or "auto").strip().lower()
    if strategy not in {"auto", "headless", "live"}:
        strategy = "auto"

    from ._qml_headless import (
        capture_headless_window,
        headless_qml_enabled,
        headless_render_info,
    )

    headless_first = strategy == "headless" or (strategy == "auto" and headless_qml_enabled())

    def _headless() -> dict[str, Any] | None:
        if not headless_qml_enabled():
            return None
        b64, width, height = capture_headless_window(resize_width, resize_height)
        if not b64:
            return None
        return _capture_result(b64, width, height, "headless-qml", render=headless_render_info())

    def _failure(error: str) -> dict[str, Any]:
        return {"image_b64": None, "width": 0, "height": 0, "source": None, "error": error}

    if headless_first:
        headless = _headless()
        if headless is not None:
            return headless
        if strategy == "headless":
            return _failure("headless_render_unavailable")

    # ── Live GUI: IPC capture via the running CommandChannel ───────────
    # IPC writes a JSON command file that the Qt GUI picks up via QTimer
    # polling.  On Linux we always try it since _find_skill_manager_window()
    # uses Win32 and returns None.  On Windows the hwnd check avoids sending
    # commands when no window is present.
    hwnd_for_ipc = _find_skill_manager_window()
    should_try_ipc = (
        resize_width is None
        and resize_height is None
        and (hwnd_for_ipc is not None or sys.platform != "win32")
    )
    if should_try_ipc:
        ack = send_capture_command(wait=True, timeout=3.0)
        if ack.get("ok"):
            capture_path: str | None = ack.get("capture_path")
            if capture_path:
                try:
                    from PIL import Image  # type: ignore[import-not-found]

                    img = Image.open(capture_path)
                    b64 = _pil_image_to_base64(img)
                    if b64:
                        return _capture_result(
                            b64,
                            img.width,
                            img.height,
                            "live-gui",
                            view=ack.get("view") or None,
                        )
                except Exception as exc:  # noqa: BLE001 — bad PNG, fall through
                    get_diagnostic_logger().log_event(
                        "WARN",
                        "capture_ipc",
                        f"IPC PNG unreadable ({capture_path}): {exc}",
                    )
                    pass

    # ── Platform-native capture ────────────────────────────────────────
    if sys.platform == "win32":
        b64, width, height = _fallback_capture_win32(resize_width, resize_height)
    else:
        b64, width, height = _fallback_capture_linux()
    if b64:
        return _capture_result(b64, width, height, "native")

    # ── Headless in-process render as the last resort ──────────────────
    if strategy == "live":
        return _failure("live_capture_unavailable")
    if not headless_first:
        headless = _headless()
        if headless is not None:
            return headless

    return _failure("capture_failed")


def _fallback_capture_win32(
    resize_width: int | None = None,
    resize_height: int | None = None,
) -> tuple[str | None, int, int]:
    """Win32 PrintWindow + CreateDIBSection fallback for Windows only."""
    try:
        hwnd = _find_skill_manager_window()
        if hwnd is None:
            return (None, 0, 0)

        restore_rect: tuple[int, int, int, int] | None = None
        if resize_width is not None and resize_height is not None:
            restore_rect = _resize_window(hwnd, resize_width, resize_height)

        try:
            rect = _get_window_rect(hwnd)
            if rect is None:
                return (None, 0, 0)
            left, top, right, bottom = rect
            width = max(1, right - left)
            height = max(1, bottom - top)

            # When minimised, GetWindowRect returns (-32000, -32000) →
            # use the restored (normal) position from GetWindowPlacement.
            if _is_minimized(hwnd):
                normal = _get_normal_rect(hwnd)
                if normal is not None:
                    left, top, right, bottom = normal
                    width = max(1, right - left)
                    height = max(1, bottom - top)

            image = _capture_window_to_image(hwnd, width, height, window_left=left, window_top=top)
            if image is None:
                return (None, 0, 0)
            b64 = _pil_image_to_base64(image)
            if b64 is None:
                return (None, 0, 0)
            return (b64, width, height)
        finally:
            if restore_rect is not None:
                _restore_window(hwnd, *restore_rect)
    except Exception:  # noqa: BLE001
        return (None, 0, 0)


def _fallback_capture_linux() -> tuple[str | None, int, int]:
    """Linux fallback — the IPC path is the primary capture method.

    On Wayland, cross-process window capture without portal infrastructure
    is not possible from a headless process.  The IPC path
    (``send_capture_command``) will already have been tried in
    ``capture_app_window`` and succeeds when the Qt GUI is running.
    """
    get_diagnostic_logger().log_event(
        "INFO", "capture_linux", "No native capture; IPC is primary path"
    )
    return (None, 0, 0)

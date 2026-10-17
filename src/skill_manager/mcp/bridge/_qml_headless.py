"""Lazy headless QML engine for the MCP bridge.

``skill-manager --mcp`` runs without a GUI, so ``controller._qml_engine`` is
normally empty and every in-process QML tool (``sm_inspect_qml_tree``,
``sm_accessibility_audit``, ``sm_get_frame_timing``, and in-process screenshots
when no live GUI is running) would degrade to ``ok:false``.

This module loads ``Main.qml`` on demand into the shared ``AppController`` using
Qt's ``offscreen`` platform plugin, so those tools work in a genuinely headless
process. Loading is:

* **opt-in** — enabled by the MCP launcher (``enable_headless_qml``), so tests
  and embedded uses keep the original "no engine" behaviour;
* **lazy** — Main.qml costs roughly 1.5-3 s to construct, so the cost is paid
  only by tools that actually need the QML tree;
* **non-intrusive** — the window is ``show()``-n under the ``offscreen`` platform
  plugin, so Qt paints the scene without mapping anything on the user's desktop;* **idempotent** — a loaded engine (from any mode) is always reused, and a
  failed load is remembered instead of retried;
* **never fatal** — QML failures are recorded (``qml_engine_status``) and turned
  into a graceful ``ok:false`` / degraded result by the callers.
"""

from __future__ import annotations

import base64
import contextlib
from typing import Any

from ._controller import _controller_or_none, get_qml_engine
from ._telemetry import _log_call, get_diagnostic_logger

# Set by the MCP launcher; without it this module is a no-op.
_HEADLESS_ENABLED = False
# A load was attempted (success is detected via the controller's engine).
_LOAD_ATTEMPTED = False
_LOAD_ERROR: str | None = None
# Singleton QML types can only be registered once per process.
_SINGLETONS_REGISTERED = False
# Strong reference to the FontDB singleton (qmlRegisterSingletonInstance keeps
# no Python ownership; dropping this would destroy a QObject QML still uses).
_FONT_BRIDGE: Any | None = None


def enable_headless_qml(enabled: bool = True) -> None:
    """Enable (or disable) lazy headless QML loading for this process."""
    global _HEADLESS_ENABLED  # noqa: PLW0603

    _HEADLESS_ENABLED = bool(enabled)


def headless_qml_enabled() -> bool:
    """Return whether lazy headless QML loading is enabled."""
    return _HEADLESS_ENABLED


def reset_headless_qml() -> None:
    """Forget load state, singleton registration and the enable flag (tests only)."""
    global _HEADLESS_ENABLED, _LOAD_ATTEMPTED, _LOAD_ERROR, _SINGLETONS_REGISTERED  # noqa: PLW0603
    global _FONT_BRIDGE  # noqa: PLW0603

    _HEADLESS_ENABLED = False
    _LOAD_ATTEMPTED = False
    _LOAD_ERROR = None
    _SINGLETONS_REGISTERED = False
    _FONT_BRIDGE = None


def qml_engine_status() -> dict[str, Any]:
    """Report headless-QML availability for diagnostics without loading anything.

    Returns a dict with ``enabled``, ``loaded``, ``attempted``, ``error`` and
    ``root_count``.
    """
    engine = get_qml_engine()
    root_count = 0
    if engine is not None:
        with contextlib.suppress(Exception):
            root_count = len(engine.rootObjects() or [])
    return {
        "enabled": _HEADLESS_ENABLED,
        "loaded": engine is not None and root_count > 0,
        "attempted": _LOAD_ATTEMPTED,
        "error": _LOAD_ERROR,
        "root_count": root_count,
    }


def ensure_qml_engine() -> Any | None:
    """Return the controller's QML engine, loading Main.qml headlessly on first use.

    Returns the existing engine when one is already attached (e.g. the real GUI
    process), otherwise loads Main.qml offscreen if ``enable_headless_qml`` was
    called. Returns ``None`` when no engine is available; the failure reason is
    cached and exposed through ``qml_engine_status``.
    """
    global _LOAD_ATTEMPTED, _LOAD_ERROR, _SINGLETONS_REGISTERED  # noqa: PLW0603

    _log_call("ensure_qml_engine")

    engine = get_qml_engine()
    if engine is not None:
        return engine
    if not _HEADLESS_ENABLED or _LOAD_ATTEMPTED:
        return None

    controller = _controller_or_none()
    if controller is None:
        _LOAD_ERROR = "AppController unavailable"
        return None

    # Remember the attempt first so a failure is never retried per call.
    _LOAD_ATTEMPTED = True
    try:
        font_bridge = _register_qml_singletons(controller)
    except (SystemExit, Exception) as exc:  # noqa: BLE001 - never let a load kill the server
        _LOAD_ERROR = f"{type(exc).__name__}: {exc}"
        return None
    if font_bridge is None:
        return None

    try:
        from skill_manager.bootstrap import _load_qml_engine

        engine = _load_qml_engine(
            controller,
            font_bridge,
            event_name="mcp_headless_qml_loaded",
            exit_on_failure=False,
        )
    except (SystemExit, Exception) as exc:  # noqa: BLE001 - never let a load kill the server
        _LOAD_ERROR = f"{type(exc).__name__}: {exc}"
        get_diagnostic_logger().log_event(
            "WARN", "mcp_headless_qml", f"Headless QML load failed: {_LOAD_ERROR}"
        )
        return None

    if not engine.rootObjects():
        _LOAD_ERROR = "QML load produced no root objects"
        return None

    _show_offscreen_window(engine)
    get_diagnostic_logger().log_event(
        "INFO", "mcp_headless_qml", "Headless QML engine loaded (offscreen)"
    )
    return engine


def _show_offscreen_window(engine: Any, settle_s: float = 0.4) -> None:
    """Expose the offscreen window so the scene graph actually paints.

    A ``QQuickWindow`` that was never shown stays un-exposed: ``grabWindow()``
    then returns an all-black image and ``beforeRendering`` never fires. Calling
    ``show()`` under the ``offscreen`` platform plugin maps nothing on the real
    desktop but makes Qt polish, lay out and render the scene.

    Waits up to *settle_s* for the first rendered frame, then returns.
    """
    import time

    from PySide6.QtCore import QCoreApplication

    try:
        from PySide6.QtQuick import QQuickWindow

        windows = [root for root in (engine.rootObjects() or []) if isinstance(root, QQuickWindow)]
    except Exception:  # noqa: BLE001
        return

    for window in windows:
        try:
            window.show()
        except Exception:  # noqa: BLE001
            continue
        deadline = time.perf_counter() + settle_s
        while time.perf_counter() < deadline:
            QCoreApplication.processEvents()
            if window.isExposed():
                break
            time.sleep(0.01)
        # One extra pass so the first frame lands before the caller grabs it.
        QCoreApplication.processEvents()


def _register_qml_singletons(controller: Any) -> Any | None:
    """Register the ``AppController`` / ``FontDB`` QML singletons.

    Must run *before* the ``QQmlApplicationEngine`` is constructed (matching the
    GUI startup order in ``bootstrap.run_gui``). The font bridge instance is kept
    in a module global because ``qmlRegisterSingletonInstance`` does not take
    ownership — dropping the Python reference would tear the QObject down while
    QML still uses it.

    Returns the font bridge, or ``None`` (recording the error) when registration
    fails.
    """
    global _SINGLETONS_REGISTERED, _FONT_BRIDGE, _LOAD_ERROR  # noqa: PLW0603

    if _SINGLETONS_REGISTERED and _FONT_BRIDGE is not None:
        return _FONT_BRIDGE

    try:
        from PySide6.QtQml import qmlRegisterSingletonInstance

        from skill_manager.app import AppController
        from skill_manager.controllers.font_database_bridge import FontDatabaseBridge

        qmlRegisterSingletonInstance(  # type: ignore[arg-type]
            AppController, "App", 1, 0, "AppController", controller
        )
        _FONT_BRIDGE = FontDatabaseBridge()
        qmlRegisterSingletonInstance(  # type: ignore[arg-type]
            FontDatabaseBridge, "App", 1, 0, "FontDB", _FONT_BRIDGE
        )
        _SINGLETONS_REGISTERED = True
        return _FONT_BRIDGE
    except (SystemExit, Exception) as exc:  # noqa: BLE001 - degrade, never crash
        _LOAD_ERROR = f"{type(exc).__name__}: {exc}"
        get_diagnostic_logger().log_event(
            "WARN", "mcp_headless_qml", f"QML singleton registration failed: {_LOAD_ERROR}"
        )
        return None


def get_qml_window() -> Any | None:
    """Return the root ``QQuickWindow`` of the QML engine, if one exists."""
    try:
        engine = ensure_qml_engine()
        if engine is None:
            return None
        from PySide6.QtQuick import QQuickWindow

        for root in engine.rootObjects() or []:
            if isinstance(root, QQuickWindow):
                return root
    except Exception:  # noqa: BLE001 - pure lookup
        return None
    return None


def _image_to_base64_png(image: Any) -> str | None:
    """Encode a ``QImage`` as base64 PNG, using the same normalisation as the GUI."""
    try:
        from PySide6.QtCore import QBuffer, QIODevice

        from skill_manager.controllers.command_channel import _normalize_capture_image

        buffer = QBuffer()
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        if not _normalize_capture_image(image).save(buffer, "PNG"):
            return None
        raw = bytes(buffer.data())
        buffer.close()
        return base64.b64encode(raw).decode("ascii") if raw else None
    except Exception:  # noqa: BLE001
        return None


def capture_headless_window(
    resize_width: int | None = None,
    resize_height: int | None = None,
) -> tuple[str | None, int, int]:
    """Render the headless QML window to a base64 PNG (no live GUI required).

    Uses ``QQuickWindow::grabWindow()``, which renders the scene graph even when
    the window is not shown — the same technique the GUI's ``CommandChannel``
    uses for IPC captures.

    Args:
        resize_width: Optional temporary window width, applied before the grab
            and restored afterwards (for responsive-layout inspection).
        resize_height: Optional temporary window height.

    Returns:
        ``(base64_png, width, height)`` or ``(None, 0, 0)`` when no window is
        available or the render fails.
    """
    _log_call("capture_headless_window")

    window = get_qml_window()
    if window is None:
        return (None, 0, 0)

    from PySide6.QtCore import QCoreApplication

    restore: tuple[int, int] | None = None
    try:
        want_resize = (
            resize_width is not None
            and resize_height is not None
            and int(resize_width) > 0
            and int(resize_height) > 0
        )
        if want_resize:
            QCoreApplication.processEvents()
            restore = (int(window.width()), int(window.height()))
            window.setWidth(int(resize_width))
            window.setHeight(int(resize_height))
            QCoreApplication.processEvents()

        image = window.grabWindow()
        if image is None or image.isNull():
            return (None, 0, 0)

        b64 = _image_to_base64_png(image)
        if b64 is None:
            return (None, 0, 0)
        return (b64, int(image.width()), int(image.height()))
    except Exception:  # noqa: BLE001
        return (None, 0, 0)
    finally:
        if restore is not None:
            with contextlib.suppress(Exception):
                window.setWidth(restore[0])
                window.setHeight(restore[1])
                QCoreApplication.processEvents()


__all__ = [
    "enable_headless_qml",
    "headless_qml_enabled",
    "reset_headless_qml",
    "qml_engine_status",
    "ensure_qml_engine",
    "get_qml_window",
    "capture_headless_window",
]

"""GUI startup and shutdown orchestration for SkillManager.

Extracted from ``app.py`` during Phase 1 of the codebase refactor: ``run_gui()``
is the former ``app.main()``, split into module-level helpers so the startup
sequence stays readable and testable. ``_handle_qml_warning`` is re-exported
from ``skill_manager.app`` so the public surface is unchanged.
"""

import contextlib
import ctypes
import logging
import os
import sys
from typing import Any

import sentry_sdk
from PySide6.QtCore import QTimer
from PySide6.QtGui import QGuiApplication, QIcon, QSurfaceFormat
from PySide6.QtQml import QQmlApplicationEngine, qmlRegisterSingletonInstance
from PySide6.QtQuickControls2 import QQuickStyle

import skill_manager
import skill_manager.utils.single_instance as single_instance
from skill_manager.controllers.font_database_bridge import FontDatabaseBridge
from skill_manager.core.analytics import capture_event
from skill_manager.core.diagnostics import get_diagnostic_logger
from skill_manager.core.resources import (
    invalidate_qml_disk_cache_if_stale,
    qml_components_dir,
    resource_path as resolve_resource_path,
)
from skill_manager.utils.native_styling import (
    HAS_PYWINSTYLES,
    _apply_immersive_dark,
    pywinstyles,
)
from skill_manager.utils.shutdown import dump_diagnostics, watchdog_exit

logger = logging.getLogger(__name__)


def _handle_qml_warning(msg):
    """Log every QML warning at WARNING level.

    We deliberately do *not* suppress any warnings — including the
    benign-looking "Object or context destroyed during incubation"
    message. The incubation-warning has historically hidden real
    regressions (e.g. signal ordering bugs, late state mutations);
    logging it makes those regressions surface in the test output
    and in user logs.
    """
    msg_str = msg.toString() if hasattr(msg, "toString") else str(msg)
    logger.warning(f"QML Warning: {msg_str}")


def _setup_sentry() -> None:  # pragma: no cover
    """Initialize Sentry as early as possible."""
    sentry_sdk.init(
        dsn=os.environ.get("SENTRY_DSN", ""),  # Placeholder for user's DSN
        traces_sample_rate=0.1,
        profiles_sample_rate=0.1,
        environment="production" if getattr(sys, "frozen", False) else "development",
        release=f"skill-manager@{skill_manager.__version__}",
        default_integrations=False,
    )


def _set_app_user_model_id() -> None:
    """Set the Windows AppUserModelID (stable across runs — taskbar grouping).

    Uses a fixed string plus ``.dev`` in development; never appends a
    timestamp, which would break Windows taskbar icon grouping.
    """
    # Use a standard AppUserModelID format
    myappid = "Antigravity.SkillManager.App.1.0"
    if not getattr(sys, "frozen", False):
        # Development mode: Append .dev to distinguish from release builds.
        # Do NOT append a timestamp, as it breaks Windows taskbar icon grouping.
        myappid += ".dev"

    try:
        res = ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        logger.info(
            f"Windows: Pre-init SetCurrentProcessExplicitAppUserModelID('{myappid}') returned {res}"
        )
    except Exception as e:
        logger.error(f"Failed to set AppUserModelID: {e}")


def _setup_single_instance() -> None:  # pragma: no cover
    """Acquire mutex (Windows) / PID lock (Linux); exit if another instance runs.

    The guard is opt-in: it only blocks a duplicate when
    ``SKILL_MANAGER_SINGLE_INSTANCE=1`` is set or ``--single-instance`` is
    passed. Without these the mutex is still created (for Inno Setup installer
    compatibility) but duplicate-instance detection is skipped.
    """
    single_instance_requested = (
        os.environ.get("SKILL_MANAGER_SINGLE_INSTANCE") == "1" or "--single-instance" in sys.argv
    )

    if sys.platform == "win32":
        single_instance._app_mutex = ctypes.windll.kernel32.CreateMutexW(
            None, False, "SkillManagerAppMutex"
        )
        ERROR_ALREADY_EXISTS = 183  # noqa: N806 (Win32 API constant)

        if (
            ctypes.windll.kernel32.GetLastError() == ERROR_ALREADY_EXISTS
            and single_instance_requested
        ):
            single_instance._bring_existing_window_to_front()
            sys.exit(0)
    elif single_instance_requested and sys.platform == "linux":
        single_instance._app_mutex = single_instance._acquire_linux_lock()
        if single_instance._app_mutex is None:
            single_instance._bring_existing_window_to_front()
            sys.exit(0)

        # Use a standard AppUserModelID format
        _set_app_user_model_id()


def _create_qapp() -> QGuiApplication:  # pragma: no cover
    """Build the QGuiApplication with style, surface format and identity set."""
    # Safety net: drop any stale Qt QML disk cache before loading QML.
    # Runs even when QML_DISABLE_DISK_CACHE=1 is honored (defense in depth).
    invalidate_qml_disk_cache_if_stale(skill_manager.__version__)

    QQuickStyle.setStyle("Basic")
    # Enable per-pixel alpha for all windows (required for transparent overlay
    # on Wayland where Window.FullScreen disables compositor transparency).
    fmt = QSurfaceFormat()
    fmt.setAlphaBufferSize(8)
    QSurfaceFormat.setDefaultFormat(fmt)
    app = QGuiApplication(sys.argv)
    # Prevent Qt from shutting down when secondary overlay windows (e.g., SnapOverlay) close
    # while the main window is minimized or hidden.
    app.setQuitOnLastWindowClosed(False)

    # Set desktop file name immediately after creation so Wayland and X11 compositors map to .desktop file
    if sys.platform == "linux":
        app.setDesktopFileName("skill-manager")
        _ensure_linux_desktop_integration()

    # Set application name and version for better shell integration
    app.setApplicationName("SkillManager")
    app.setApplicationVersion(skill_manager.__version__)
    app.setOrganizationName("Antigravity")
    app.setOrganizationDomain("antigravity.io")
    return app


def _ensure_linux_desktop_integration() -> None:  # pragma: no cover
    """Ensure user-level desktop entries and multi-resolution icons exist for dock/taskbar."""
    if sys.platform != "linux":
        return
    try:
        import shutil

        home = os.path.expanduser("~")
        apps_dir = os.path.join(home, ".local", "share", "applications")
        icons_base = os.path.join(home, ".local", "share", "icons", "hicolor")
        bin_dir = os.path.join(home, ".local", "bin")

        os.makedirs(apps_dir, exist_ok=True)
        os.makedirs(bin_dir, exist_ok=True)

        # 1. Ensure a working executable shim in ~/.local/bin if not globally installed
        local_bin = os.path.join(bin_dir, "skill-manager")
        if not os.path.exists("/usr/bin/skill-manager") and not os.path.exists(local_bin):
            venv_bin = os.path.join(sys.prefix, "bin", "skill-manager")
            if os.path.exists(venv_bin):
                with contextlib.suppress(OSError):
                    os.symlink(venv_bin, local_bin)

        # 2. Ensure icon directories exist and populate multi-resolution icons under all stems
        stems = ("skill-manager", "SkillManager", "org.dishanagalawatta.SkillManager")
        for size, name in (
            ("scalable", "logo.svg"),
            ("256x256", "logo.png"),
            ("128x128", "logo-128.png"),
            ("64x64", "logo-64.png"),
            ("48x48", "logo-64.png"),
            ("32x32", "logo-64.png"),
        ):
            dest_dir = os.path.join(icons_base, size, "apps")
            os.makedirs(dest_dir, exist_ok=True)
            src_path = resolve_resource_path(f"assets/brand/{name}")
            ext = ".svg" if name.endswith(".svg") else ".png"
            for stem in stems:
                dest_file = os.path.join(dest_dir, f"{stem}{ext}")
                if os.path.exists(src_path) and not os.path.exists(dest_file):
                    shutil.copy2(src_path, dest_file)

        # 3. Ensure single canonical desktop file exists with absolute executable path and 0755 permissions
        desktop_src = resolve_resource_path("packaging/linux/skill-manager.desktop")
        primary_desktop = os.path.join(apps_dir, "skill-manager.desktop")
        exec_target = (
            "/usr/bin/skill-manager" if os.path.exists("/usr/bin/skill-manager") else local_bin
        )

        if os.path.exists(desktop_src):
            with open(desktop_src, encoding="utf-8") as f:
                content = f.read()
            # If Exec is a bare command name, replace with absolute path for systemd / GNOME Shell validation
            if "Exec=skill-manager" in content and os.path.exists(exec_target):
                content = content.replace("Exec=skill-manager", f"Exec={exec_target}")
            with open(primary_desktop, "w", encoding="utf-8") as f:
                f.write(content)
            with contextlib.suppress(OSError):
                os.chmod(primary_desktop, 0o755)

        # 4. Clean up any stale desktop aliases to keep only the single official launcher
        for stale_alias in ("SkillManager.desktop", "org.dishanagalawatta.SkillManager.desktop"):
            stale_path = os.path.join(apps_dir, stale_alias)
            if os.path.exists(stale_path) or os.path.islink(stale_path):
                with contextlib.suppress(OSError):
                    os.remove(stale_path)
    except Exception as e:
        logger.debug(f"Desktop integration check skipped: {e}")


def load_app_icon(app: QGuiApplication) -> tuple[QIcon, str]:  # pragma: no cover
    """Load the application icon (PNG/SVG on Linux, ICO+PNG elsewhere).

    Returns ``(app_icon, loaded_icon_path)``; ``loaded_icon_path`` is empty
    when no icon could be loaded.
    """
    from PySide6.QtGui import QPixmap

    app_icon = QIcon()
    loaded_icon = False
    loaded_icon_path = ""
    if sys.platform == "linux":
        # Check system icon theme first
        theme_icon = QIcon.fromTheme("skill-manager")
        if not theme_icon.isNull():
            app_icon = theme_icon
            loaded_icon = True
            loaded_icon_path = "theme:skill-manager"

        # Add bundled multi-resolution pixmaps as fallback/direct icons
        for candidate in (
            resolve_resource_path("assets/brand/logo.svg"),
            resolve_resource_path("assets/brand/logo.png"),
            resolve_resource_path("assets/brand/logo-128.png"),
            resolve_resource_path("assets/brand/logo-64.png"),
        ):
            if os.path.exists(candidate):
                pix = QPixmap(candidate)
                if not pix.isNull():
                    app_icon.addPixmap(pix)
                    loaded_icon = True
                    if not loaded_icon_path:
                        loaded_icon_path = candidate
        if loaded_icon:
            app.setWindowIcon(app_icon)
            logger.info(f"Set application icon from: {loaded_icon_path}")
        # Wayland/GNOME derives dock icon from .desktop file matched via
        # setDesktopFileName, not from setWindowIcon.
        app.setDesktopFileName("skill-manager")
    else:
        icon_candidates = [
            resolve_resource_path("assets/brand/logo.ico"),
            os.path.join(os.path.dirname(__file__), "assets", "brand", "logo.ico"),
            os.path.join(os.path.abspath("."), "assets", "brand", "logo.ico"),
            resolve_resource_path("assets/brand/logo.png"),
            os.path.join(os.path.dirname(__file__), "assets", "brand", "logo.png"),
            os.path.join(os.path.abspath("."), "assets", "brand", "logo.png"),
        ]
        loaded_icon_path = ""
        for icon_path in icon_candidates:
            if os.path.exists(icon_path):
                app_icon = QIcon(icon_path)
                if not app_icon.isNull():
                    app.setWindowIcon(app_icon)
                    logger.info(f"Successfully loaded and set application icon from: {icon_path}")
                    loaded_icon = True
                    loaded_icon_path = icon_path
                    break
                logger.warning(f"QIcon failed to load existing file: {icon_path}")
            else:
                logger.debug(f"Icon candidate not found: {icon_path}")

    if not loaded_icon:
        logger.error("CRITICAL: All icon candidates failed to load.")
        from PySide6.QtGui import QImageReader

        formats = [f.data().decode() for f in QImageReader.supportedImageFormats()]  # type: ignore[attr-defined]
        logger.info(f"Supported image formats: {formats}")
        if "png" not in formats:
            logger.error("PNG format is NOT supported by this PySide6 installation!")
    return app_icon, loaded_icon_path


def _load_qml_engine(controller, font_bridge) -> QQmlApplicationEngine:  # pragma: no cover
    """Create the QML engine, register the image provider and load Main.qml."""
    engine = QQmlApplicationEngine()
    controller._qml_engine = engine
    engine.addImageProvider("snap", controller.snap_provider)
    engine.rootContext().setContextProperty("appController", controller)
    engine.rootContext().setContextProperty("fontDB", font_bridge)
    engine.warnings.connect(_handle_qml_warning)

    qml_dir = qml_components_dir(package_file=__file__)
    engine.addImportPath(str(qml_dir.parent))
    qml_file = qml_dir / "Main.qml"
    engine.load(str(qml_file))
    if not engine.rootObjects():
        logger.error("CRITICAL: Failed to load QML root objects!")
        sys.exit(-1)
    diag = get_diagnostic_logger()
    diag.log_event(
        "INFO", "window_state", f"QML loaded, {len(engine.rootObjects())} root object(s)"
    )
    capture_event("app_opened")
    return engine


def _clamp_window_geometry(app, engine, controller) -> None:  # pragma: no cover
    """Clamp window geometry to visible screen area to prevent off-screen windows.

    Saved coordinates from a previous multi-monitor setup may be invalid if
    the monitor was disconnected.
    """
    diag = get_diagnostic_logger()
    screens = app.screens()
    if screens:
        for root in engine.rootObjects():
            r: Any = root
            win_x, win_y = r.x(), r.y()
            win_w, win_h = r.width(), r.height()

            # Find matching screen where window titlebar/top area is located
            target_screen = None
            for s in screens:
                s_geo = s.availableGeometry()
                if (
                    s_geo.x() <= win_x + win_w - 100
                    and win_x <= s_geo.x() + s_geo.width() - 100
                    and s_geo.y() <= win_y + win_h - 100
                    and win_y <= s_geo.y() + s_geo.height() - 100
                ):
                    target_screen = s
                    break

            if not target_screen:
                target_screen = app.primaryScreen() or screens[0]

            geo = target_screen.availableGeometry()
            screen_x, screen_y = geo.x(), geo.y()
            screen_w, screen_h = geo.width(), geo.height()
            diag.log_event(
                "INFO",
                "window_state",
                f"Screen geometry: ({screen_x}, {screen_y}, {screen_w}, {screen_h}) for window ({win_x}, {win_y}, {win_w}, {win_h})",
            )
            # Clamp so the window is at least partially visible on target screen
            new_x = max(screen_x, min(win_x, screen_x + screen_w - max(win_w, 100)))
            new_y = max(screen_y, min(win_y, screen_y + screen_h - max(win_h, 100)))
            if new_x != win_x or new_y != win_y:
                diag.log_event(
                    "WARN",
                    "window_state",
                    f"Window off-screen at ({win_x}, {win_y}) — clamping to ({new_x}, {new_y})",
                )
                r.setX(new_x)
                r.setY(new_y)
                # Update controller state directly because the QML
                # _isInitialized guard is still false during startup,
                # so the signal-based path (onXChanged) is blocked.
                # Without this the QML position-restore timer would
                # re-apply the original off-screen position.
                controller.ui.state.window_x = new_x
                controller.ui.state.window_y = new_y
                controller.ui.saveUiState()


def _show_windows(engine, controller, app_icon) -> None:  # pragma: no cover
    """Explicitly set icon and position on each QML window, then show it."""
    diag = get_diagnostic_logger()
    # Explicitly set icon on each QML window — QGuiApplication.setWindowIcon()
    # doesn't reliably propagate to QML Window elements with FramelessWindowHint.
    for i, root in enumerate(engine.rootObjects()):
        root_any: Any = root
        if not app_icon.isNull():
            root_any.setIcon(app_icon)
        if hasattr(root, "setTitle") and not root_any.title():
            root_any.setTitle("SkillManager")
        if hasattr(root, "show"):
            # Set position explicitly on native QWindow handle before/during show
            root_any.setX(controller.ui.windowX)
            root_any.setY(controller.ui.windowY)
            root_any.setWidth(controller.ui.windowWidth)
            root_any.setHeight(controller.ui.windowHeight)
            root_any.show()
            if hasattr(root, "raise_"):
                root_any.raise_()
            if hasattr(root, "requestActivate"):
                root_any.requestActivate()
            diag.log_event(
                "INFO",
                "window_state",
                f"Called root.show() on root {i} at ({root_any.x()}, {root_any.y()}) size={root_any.width()}x{root_any.height()}",
            )


def apply_native_styles(engine, controller, loaded_icon_path) -> None:  # pragma: no cover
    """Apply Mica / DWM immersive dark / taskbar icons to each QML window."""
    diag = get_diagnostic_logger()
    diag.log_event(
        "INFO",
        "window_state",
        f"apply_native_styles: processing {len(engine.rootObjects())} root object(s)",
    )
    dark = bool(controller.ui.darkMode)
    for root in engine.rootObjects():
        try:
            hwnd = int(root.winId())  # type: ignore[attr-defined]
            if HAS_PYWINSTYLES and pywinstyles is not None:
                pywinstyles.apply_style(hwnd, "mica")
                _apply_immersive_dark(hwnd, dark)
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, 33, ctypes.byref(ctypes.c_int(2)), 4
                )

            if sys.platform == "win32" and loaded_icon_path:
                WM_SETICON = 0x0080  # noqa: N806 (Win32 API constant)
                ICON_SMALL = 0  # noqa: N806 (Win32 API constant)
                ICON_BIG = 1  # noqa: N806 (Win32 API constant)
                LR_LOADFROMFILE = 0x0010  # noqa: N806 (Win32 API constant)
                IMAGE_ICON = 1  # noqa: N806 (Win32 API constant)

                hIconSm = ctypes.windll.user32.LoadImageW(  # noqa: N806 (Win32 API variable)
                    None, loaded_icon_path, IMAGE_ICON, 16, 16, LR_LOADFROMFILE
                )
                if hIconSm:
                    ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, hIconSm)

                hIconLg = ctypes.windll.user32.LoadImageW(  # noqa: N806 (Win32 API variable)
                    None, loaded_icon_path, IMAGE_ICON, 32, 32, LR_LOADFROMFILE
                )
                if hIconLg:
                    ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, hIconLg)
        except Exception as e:
            logger.error(f"Failed to apply native style/icon: {e}")


def _reapply_immersive_dark_from_dark_mode(engine, controller) -> None:  # pragma: no cover
    """Re-apply the DWM immersive-dark attribute when darkMode changes."""
    diag = get_diagnostic_logger()
    dark = bool(controller.ui.darkMode)
    for root in engine.rootObjects():
        try:
            hwnd = int(root.winId())  # type: ignore[attr-defined]
            _apply_immersive_dark(hwnd, dark)
        except Exception as e:
            diag.log_event(
                "WARN",
                "window_state",
                f"Immersive-dark re-apply skipped for root: {e}",
            )


def _check_window_visible(engine) -> None:  # pragma: no cover
    """Watchdog: force-show any root not visible 5s after startup."""
    diag = get_diagnostic_logger()
    for i, root in enumerate(engine.rootObjects()):
        try:
            r: Any = root
            vis = r.isVisible()
            x, y, w, h = r.x(), r.y(), r.width(), r.height()
            diag.log_event(
                "INFO",
                "window_state",
                f"Watchdog: root {i} visible={vis}, geometry=({x}, {y}, {w}, {h})",
            )
            if not vis:
                diag.log_event(
                    "WARN",
                    "window_state",
                    f"Watchdog: root {i} NOT VISIBLE after 5s — forcing show",
                )
                r.show()
                r.raise_()
                r.requestActivate()
        except Exception as e:
            diag.log_event("ERROR", "window_state", f"Watchdog error: {e}")


def _shutdown_sequence(app, engine, controller, ret) -> None:  # pragma: no cover
    """Post-``app.exec()`` teardown: watchdog, event drain, telemetry flush, exit."""
    # Arm the watchdog — if shutdown takes >5s, force-exit
    dump_diagnostics("app.exec finished")
    watchdog_exit(ret, timeout=5.0)

    # Drain pending Qt events so QML releases GPU resources cleanly.
    app.processEvents()
    app.processEvents()

    # Explicitly clear QML components to cleanly stop timers
    dump_diagnostics("clearing component cache")
    engine.clearComponentCache()

    # Post-Qt cleanup: flush telemetry, join background threads (bounded < 0.5s)
    dump_diagnostics("calling controller.cleanup")
    controller.cleanup()
    # We bypass sys.exit and del app to avoid hangs caused by Qt C++ teardown
    # or buggy atexit hooks (like loky on Windows).
    # We suppress stderr immediately before exit to hide unavoidable Qt
    # DllMain detach warnings (QThreadStorage, QDxgiVSyncService).
    try:
        # Kill all descendant processes (children, grandchildren) using psutil.
        # We do NOT query cmdline() or other slow/blocking properties to avoid hangs.
        # We reverse the children list to kill bottom-up (grandchildren first, then children)
        # to ensure intermediate parents are not terminated before their descendants.
        import psutil

        dump_diagnostics("executing psutil kill")
        parent = psutil.Process(os.getpid())
        for child in reversed(parent.children(recursive=True)):
            with contextlib.suppress(Exception):
                child.kill()
    except Exception as e:
        dump_diagnostics(f"psutil kill failed: {e}")

    dump_diagnostics("final process termination")
    try:
        null_fd = os.open(os.devnull, os.O_WRONLY)
        os.dup2(null_fd, 2)
    except Exception:
        pass

    # We call os.kill(pid, 9) (which translates to TerminateProcess on Windows)
    # to bypass ExitProcess loader-lock deadlocks and terminate instantly.
    # If running under pytest, we bypass this to prevent killing the test runner.
    if "pytest" in sys.modules:
        sys.exit(ret)

    try:
        os.kill(os.getpid(), 9)
    except Exception:
        os._exit(ret)


def run_gui() -> None:  # pragma: no cover
    """Main GUI entry point (formerly ``app.main()``)."""
    import multiprocessing

    multiprocessing.freeze_support()

    # ----------------------------------------------------------------------
    # MCP stdio mode (headless). Runs the MCP server instead of the GUI.
    # Uses its OWN mutex name so it never conflicts with a running GUI
    # instance. The GUI launch path below is left completely untouched.
    # ----------------------------------------------------------------------
    if "--mcp-light" in sys.argv:
        from skill_manager.mcp import run_mcp_server_light

        run_mcp_server_light()
        return

    if "--mcp" in sys.argv:
        from skill_manager.mcp.launcher import _run_mcp_mode

        _run_mcp_mode()
    if "--version" in sys.argv or "-v" in sys.argv:
        print(f"SkillManager {skill_manager.__version__}")
        return

    _setup_sentry()

    # Acquire mutex so Inno Setup installer can cleanly close the app.
    # Windows-only: guarded by sys.platform so Linux startup doesn't crash.
    _setup_single_instance()

    app = _create_qapp()
    app_icon, loaded_icon_path = load_app_icon(app)

    from skill_manager.app import AppController

    controller = AppController()
    # PySide6 6.11.0's type stub claims ``qml_name`` is ``bytes | bytearray |
    # memoryview[int]`` but the runtime actually requires ``str`` (which it
    # auto-encodes internally) and raises ``TypeError`` on ``bytes``. The
    # stub-vs-runtime mismatch is a known PySide6 limitation; suppress it
    # per-call so the running app keeps working.
    qmlRegisterSingletonInstance(
        AppController,
        "App",
        1,
        0,
        "AppController",  # type: ignore[arg-type]
        controller,
    )
    app.aboutToQuit.connect(controller.on_quit)

    # Register FontDatabaseBridge BEFORE the QQmlApplicationEngine is created.
    # Registering singleton QObject types after `engine = QQmlApplicationEngine()`
    # but before `engine.load()` interacts badly with the engine's type cache for
    # locally-registered QML components, surfacing as
    # "Cannot assign object of type X to list property 'data'; expected 'QObject'"
    # during Main.qml load.
    font_bridge = FontDatabaseBridge()
    qmlRegisterSingletonInstance(FontDatabaseBridge, "App", 1, 0, "FontDB", font_bridge)  # type: ignore[arg-type]

    engine = _load_qml_engine(controller, font_bridge)

    _clamp_window_geometry(app, engine, controller)
    _show_windows(engine, controller, app_icon)

    QTimer.singleShot(0, lambda: apply_native_styles(engine, controller, loaded_icon_path))

    controller.ui.darkModeChanged.connect(
        lambda: _reapply_immersive_dark_from_dark_mode(engine, controller)
    )

    QTimer.singleShot(5000, lambda: _check_window_visible(engine))

    # Configure SIGINT (Ctrl+C) and SIGTERM handlers with a QTimer heartbeat
    # so Python interpreter regularly processes OS signals during the Qt event loop.
    import signal

    def _sigint_handler(*_args):
        logger.info("Received interrupt signal (Ctrl+C) — initiating clean shutdown...")
        app.quit()

    try:
        signal.signal(signal.SIGINT, _sigint_handler)
        signal.signal(signal.SIGTERM, _sigint_handler)
    except (ValueError, AttributeError):
        pass

    sig_timer = QTimer()
    sig_timer.start(250)
    sig_timer.timeout.connect(lambda: None)

    ret = app.exec()

    # Stop signal timer upon event loop exit
    sig_timer.stop()

    _shutdown_sequence(app, engine, controller, ret)


if __name__ == "__main__":
    run_gui()

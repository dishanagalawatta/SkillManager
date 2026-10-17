"""Headless MCP stdio launcher.

Extracted from ``app.py`` during Phase 1 of the codebase refactor:
``_run_mcp_mode`` runs the MCP server in headless mode (no visible GUI). Called
lazily from ``bootstrap.run_gui`` when ``--mcp`` is passed.

The process runs on Qt's ``offscreen`` platform plugin so it never maps a
window — even when a display is available — and loads ``Main.qml`` lazily on
demand (see ``skill_manager.mcp.bridge._qml_headless``) so that UI-introspection
tools (QML tree, accessibility audit, frame timing, in-process screenshots) work
with no GUI running.
"""

import ctypes
import os
import sys

# Platform plugin used when the caller has not pinned one. Overridable for
# debugging (e.g. SKILL_MANAGER_MCP_PLATFORM=xcb to inspect the window).
_PLATFORM_ENV = "SKILL_MANAGER_MCP_PLATFORM"


def _force_offscreen_platform() -> None:
    """Pin Qt to the ``offscreen`` platform plugin for headless MCP use.

    Unlike the GUI path this does not fall back to the caller's platform: MCP
    mode must never open a window. ``SKILL_MANAGER_MCP_PLATFORM`` overrides it
    for debugging.
    """
    os.environ["QT_QPA_PLATFORM"] = os.environ.get(_PLATFORM_ENV) or "offscreen"


def _configure_qt_style() -> None:
    """Apply the GUI's QML style/surface format before the QGuiApplication exists.

    ``QQuickStyle.setStyle`` and the default ``QSurfaceFormat`` must be set
    before the application object is created, exactly as ``bootstrap._create_qapp``
    does for the GUI, otherwise ``Main.qml`` renders with the wrong control style.
    """
    from PySide6.QtGui import QSurfaceFormat
    from PySide6.QtQuickControls2 import QQuickStyle

    QQuickStyle.setStyle("Basic")
    fmt = QSurfaceFormat()
    fmt.setAlphaBufferSize(8)
    QSurfaceFormat.setDefaultFormat(fmt)


def _run_mcp_mode() -> None:  # pragma: no cover
    """Launch the MCP stdio server in headless mode.

    Uses a dedicated mutex (``SkillManagerMcpMutex``) so it never collides with
    a running GUI instance. Constructs a headless ``QGuiApplication`` (offscreen
    platform), a ``skip_initial_load`` ``AppController`` — registered as the
    bridge's shared controller so tools never build a second one — and then runs
    the MCP server over stdio. On exit it cleans up the controller and
    terminates the process.
    """
    allow_write = "--mcp-allow-write" in sys.argv

    # Dedicated mutex — distinct from the GUI's SkillManagerAppMutex so a GUI
    # instance and an MCP instance can run side by side.
    # Windows-only; skipped on Linux (no Inno Setup installer to coordinate with).
    if sys.platform == "win32":
        import skill_manager.utils.single_instance as single_instance

        single_instance._app_mutex = ctypes.windll.kernel32.CreateMutexW(
            None, False, "SkillManagerMcpMutex"
        )

    # Headless by construction: pin the offscreen plugin, then the QML style.
    _force_offscreen_platform()
    _configure_qt_style()

    from PySide6.QtGui import QGuiApplication

    app = QGuiApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName("SkillManagerMCP")

    from skill_manager.app import AppController
    from skill_manager.mcp import run_mcp_server
    from skill_manager.mcp.bridge import enable_headless_qml, set_app_controller

    controller = AppController(skip_initial_load=True)
    app.aboutToQuit.connect(controller.on_quit)

    # Share this controller with the bridge and allow on-demand offscreen QML
    # loading, so sm_inspect_qml_tree / sm_accessibility_audit /
    # sm_get_frame_timing / sm_screenshot work without a running GUI.
    # State persistence is disabled first so the offscreen window can never
    # overwrite the user's saved window geometry / current view.
    controller.ui.disable_state_persistence()
    set_app_controller(controller)
    enable_headless_qml(True)

    try:
        run_mcp_server(allow_write=allow_write)
    finally:
        controller.cleanup()
        sys.exit(0)

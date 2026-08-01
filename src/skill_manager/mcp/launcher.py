"""Headless MCP stdio launcher.

Extracted from ``app.py`` during Phase 1 of the codebase refactor:
``_run_mcp_mode`` runs the MCP server in headless mode (no GUI, no QML
engine). Called lazily from ``bootstrap.run_gui`` when ``--mcp`` is passed.
"""

import ctypes
import os
import sys


def _run_mcp_mode() -> None:  # pragma: no cover
    """Launch the MCP stdio server in headless mode (no GUI, no QML engine).

    Uses a dedicated mutex (``SkillManagerMcpMutex``) so it never collides with
    a running GUI instance. Constructs a headless ``QGuiApplication`` (offscreen
    platform when no display is available) and a ``skip_initial_load``
    ``AppController``, then runs the MCP server over stdio. On exit it cleans up
    the controller and terminates the process.
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

    # Force a headless platform when no display is present so construction
    # works in CI / SSH / service contexts. Set BEFORE QGuiApplication exists.
    if not os.environ.get("DISPLAY") and not os.environ.get("QT_QPA_PLATFORM"):
        os.environ["QT_QPA_PLATFORM"] = "offscreen"

    from PySide6.QtGui import QGuiApplication

    app = QGuiApplication(sys.argv)
    app.setApplicationName("SkillManagerMCP")

    from skill_manager.app import AppController

    controller = AppController(skip_initial_load=True)
    app.aboutToQuit.connect(controller.on_quit)

    from skill_manager.mcp import run_mcp_server

    try:
        run_mcp_server(allow_write=allow_write)
    finally:
        controller.cleanup()
        sys.exit(0)

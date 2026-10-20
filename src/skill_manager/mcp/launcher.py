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

import contextlib
import ctypes
import logging
import os
import sys
from typing import Any

logger = logging.getLogger(__name__)

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
    # Tell QML this is the offscreen renderer so layer effects (MultiEffect /
    # DropShadow) are skipped: the software scenegraph backend cannot execute
    # them, and a layered item with an unusable effect draws nothing at all.
    os.environ["SKILL_MANAGER_HEADLESS_RENDER"] = "1"


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


def _disable_command_consumer(controller: Any) -> None:
    """Stop the controller's ``CommandChannel`` in the MCP process.

    ``AppController`` always builds a ``CommandChannel`` that polls
    ``data/mcp/commands``. Inside the MCP server that channel would race the real
    GUI for every capture/navigate command and answer it itself with "no QML
    engine", so live screenshots fail or come from the wrong process. The MCP
    side is a sender only.
    """
    channel = getattr(controller, "command_channel", None)
    if channel is None:
        return
    with contextlib.suppress(Exception):
        channel.stop()


def _wait_for_initial_load(controller: Any, timeout_s: float = 25.0) -> None:
    """Populate the offscreen controller's models before the server answers.

    ``skip_initial_load=True`` keeps the GUI's background jobs (file watchers,
    package scheduler) out of the MCP process, but it also skips the discovery
    that fills the Library/QuickCopy models. Rendering ``Main.qml`` against
    empty models produced a visibly different app — no project filters, no
    toolbar state, a partial skill list — which defeats the point of a visual
    check.

    So the models are filled here from the **on-disk cache** (``skip_discovery``)
    and drained by pumping Qt events until the final commit lands. Cache-only
    keeps the MCP process read-only: it never scans the filesystem or rewrites
    the index while a GUI is running. A missing cache still falls back to a
    scan, so the render is never an empty shell. Bounded: a slow or broken load
    never blocks server startup forever.
    """
    import time

    from PySide6.QtCore import QCoreApplication

    started = time.monotonic()
    discovery = getattr(controller, "discovery", None)
    try:
        if discovery is not None:
            # Cache-only: paint the models from the index the GUI (or the last
            # run) already wrote. No filesystem scan, no cache writes, so an
            # MCP process can never race a running GUI's discovery or its index.
            discovery.loadInitialData(skip_discovery=True, silent=True)
        else:
            controller.loadInitialData()
    except Exception as exc:  # noqa: BLE001 - a screenshot must still work
        logger.warning("MCP initial load failed to start: %s", exc)
        return

    deadline = started + timeout_s
    while time.monotonic() < deadline:
        QCoreApplication.processEvents()
        if getattr(discovery, "_final_committed_generation", None) is not None:
            break
        time.sleep(0.02)

    # Let model resets, delegates and bindings settle before the first grab.
    for _ in range(10):
        QCoreApplication.processEvents()
        time.sleep(0.01)

    logger.info(
        "MCP initial load finished in %.2fs (final=%s)",
        time.monotonic() - started,
        getattr(discovery, "_final_committed_generation", None) is not None,
    )


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

    # Read-only discovery: this controller is built without the GUI's package
    # scan and watchers, so its result is a subset. Persisting it would replace
    # the complete index the GUI wrote (seen in the wild: 3240 skills -> 620).
    from skill_manager.core.discovery import set_cache_persistence

    set_cache_persistence(False)

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
    _disable_command_consumer(controller)

    # Load skills/projects/sources so the offscreen window renders the same app
    # the user sees, not an empty shell. One-shot discovery only: no watchers,
    # no package scheduler, no auto-update inside the MCP process.
    _wait_for_initial_load(controller)

    try:
        run_mcp_server(allow_write=allow_write)
    finally:
        controller.cleanup()
        sys.exit(0)

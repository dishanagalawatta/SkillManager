# ruff: noqa: E402, ARG001
"""Real-app visual verification for the Packages view and the curated catalog.

Runs the REAL ``AppController`` and the REAL ``Main.qml`` in one process and
captures the live window with ``QWindow.grabWindow()``.

Captures:

1. ``packages_installed.png``    — the Installed tab.
2. ``packages_discover.png``     — the Discover tab (the curated catalog).
3. ``packages_discover_light.png`` — the same tab in light theme.
4. ``packages_sync.png``         — the Project Sync tab.
5. ``packages_catalog_dialog.png`` — the package dialog pre-filled from a
   catalog entry.

Run: uv run python scripts/verify_packages_catalog_real.py
"""

import os
import shutil
import signal
import sys
import tempfile
import time
from pathlib import Path

CAPTURES_DIR = Path("data/mcp/captures")
START_TIME = time.monotonic()

SCRATCH = Path(tempfile.mkdtemp(prefix="skillmanager-packages-verify-"))
os.environ["SKILL_MANAGER_DATA_DIR"] = str(SCRATCH / "data")
os.environ.setdefault("QML_DISABLE_DISK_CACHE", "1")
os.environ["SKILL_MANAGER_DEV_MODE"] = "1"
os.environ["SKILL_MANAGER_MCP_NO_IPC"] = "1"


def watchdog(signum, frame):
    print(f"WATCHDOG: {time.monotonic() - START_TIME:.1f}s — forcing exit", flush=True)
    os._exit(1)


signal.signal(signal.SIGALRM, watchdog)
signal.alarm(240)

if CAPTURES_DIR.exists():
    for stale in CAPTURES_DIR.glob("*.png"):
        stale.unlink()
CAPTURES_DIR.mkdir(parents=True, exist_ok=True)

import sentry_sdk

import skill_manager

sentry_sdk.init(
    dsn="",
    traces_sample_rate=0.1,
    profiles_sample_rate=0.1,
    environment="development",
    release=f"skill-manager@{skill_manager.__version__}",
    default_integrations=False,
)

from PySide6.QtCore import QObject, QTimer
from PySide6.QtGui import QGuiApplication, QSurfaceFormat
from PySide6.QtQml import QQmlApplicationEngine, qmlRegisterSingletonInstance
from PySide6.QtQuickControls2 import QQuickStyle

QQuickStyle.setStyle("Basic")
fmt = QSurfaceFormat()
fmt.setAlphaBufferSize(8)
QSurfaceFormat.setDefaultFormat(fmt)
app = QGuiApplication(sys.argv)
app.setApplicationName("SkillManager")

from skill_manager.app import AppController

controller = AppController()
controller.ui_controller.darkMode = True

qmlRegisterSingletonInstance(AppController, "App", 1, 0, "AppController", controller)
from skill_manager.controllers.font_database_bridge import FontDatabaseBridge

font_bridge = FontDatabaseBridge()
qmlRegisterSingletonInstance(FontDatabaseBridge, "App", 1, 0, "FontDB", font_bridge)

engine = QQmlApplicationEngine()
controller._qml_engine = engine

from skill_manager.core.resources import qml_components_dir

qml_dir = qml_components_dir(package_file="src/skill_manager/app.py")
engine.addImportPath(str(qml_dir.parent))
engine.load(str(qml_dir / "Main.qml"))

window = next((o for o in engine.rootObjects() if hasattr(o, "show")), None)
if window is None or not engine.rootObjects():
    print("FATAL: No QML root objects!", flush=True)
    sys.exit(1)
window.show()
window.raise_()


def _log(step, message):
    print(f"[+{time.monotonic() - START_TIME:.1f}s] {step}: {message}", flush=True)


def _capture(name):
    path = str(CAPTURES_DIR / name)
    pixmap = window.grabWindow()
    if pixmap.isNull():
        print(f"CAPTURE FAILED: {name}", flush=True)
        return
    pixmap.save(path)
    _log("CAPTURE", f"{path} ({pixmap.width()}x{pixmap.height()})")


def _make_project():
    project = SCRATCH / "projectA"
    skill = project / ".agents" / "skills" / "local-helper"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        "---\nname: Local Helper\ndescription: A skill in the project.\n---\n\n# Local\n",
        encoding="utf-8",
    )
    return project


def step1_setup():
    project = _make_project()
    from skill_manager.core.copier import get_skills_dir

    proj = str(get_skills_dir(project))
    controller._sources = []
    controller._projects = [proj]
    controller._config.set("projects", [proj])
    controller.config_mgr._invalidate_project_cache()
    controller._set_current_project(controller.config_mgr.getProjectLabel(proj))

    _log("SETUP", f"project={proj}")
    controller.refreshSkills("verify", True)
    QTimer.singleShot(6000, step2_navigate)


def step2_navigate():
    _log("NAV", "opening the Packages view")
    window.navigateTo("Updates")
    QTimer.singleShot(4000, step3_capture_installed)


def step3_capture_installed():
    _capture("packages_installed.png")
    _log("NAV", "switching to the Discover tab")
    _select_tab(1)
    QTimer.singleShot(2500, step4_capture_discover)


def _select_tab(index):
    """Activate a tab of the Packages page switcher."""
    from PySide6.QtCore import QMetaObject

    for obj in window.findChildren(QObject):
        if obj.objectName() == "uv_pages":
            obj.setProperty("currentIndex", index)
            return True
    return False


def step4_capture_discover():
    _capture("packages_discover.png")
    _log("THEME", "switching to light mode")
    controller.ui_controller.darkMode = False
    QTimer.singleShot(2500, step5_capture_light)


def step5_capture_light():
    _capture("packages_discover_light.png")
    _log("THEME", "restoring dark mode")
    controller.ui_controller.darkMode = True
    QTimer.singleShot(2000, step6_open_dialog)


def step6_open_dialog():
    """Open the package dialog pre-filled from a catalog entry."""
    template = controller.update_controller.catalogPackage("vercel-skills")
    _log("DIALOG", f"catalog entry: {template.get('display_name', '?')}")

    dialog = window.findChild(QObject, "uv_packageEditDialog")
    if dialog is None:
        print("DIALOG WARNING: uv_packageEditDialog not found", flush=True)
        finish()
        return

    from PySide6.QtCore import Q_ARG, QMetaObject

    dialog.setProperty("editIndex", -1)
    loaded = dialog.metaObject().invokeMethod(
        dialog, "openWithTemplate", Q_ARG("QVariant", template)
    )
    _log("DIALOG", f"openWithTemplate invoked={loaded}")
    QTimer.singleShot(2500, step7_capture_dialog)


def step7_capture_dialog():
    _capture("packages_catalog_dialog.png")
    QTimer.singleShot(500, step7b_close_dialog)


def step7b_close_dialog():
    dialog = window.findChild(QObject, "uv_packageEditDialog")
    if dialog is not None:
        dialog.metaObject().invokeMethod(dialog, "close")
    QTimer.singleShot(1200, step8_sync_tab)


def step8_sync_tab():
    _log("NAV", "switching to the Project Sync tab")
    _select_tab(2)
    QTimer.singleShot(2500, step9_capture_sync)


def step9_capture_sync():
    _capture("packages_sync.png")
    QTimer.singleShot(300, finish)


def finish():
    print("=== CAPTURES ===", flush=True)
    for p in sorted(CAPTURES_DIR.glob("*.png")):
        print(f"  {p} ({p.stat().st_size} bytes)", flush=True)
    shutil.rmtree(SCRATCH, ignore_errors=True)
    os._exit(0)


QTimer.singleShot(1500, step1_setup)
app.exec()

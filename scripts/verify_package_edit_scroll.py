"""
Verification script for PackageEditDialog ("Edit Skill Package").
Opens PackageEditDialog in the real app and captures screenshot via QWindow.grabWindow().
"""

import os
import shutil
import signal
import sys
import time
import uuid
from pathlib import Path

START_TIME = time.monotonic()


def watchdog_timeout(signum, frame):
    print(f"WATCHDOG: {time.monotonic() - START_TIME:.1f}s — forcing exit")
    os._exit(1)


signal.signal(signal.SIGALRM, watchdog_timeout)
signal.alarm(40)

# Mandatory Rule #6: Clean all captures from data/mcp/captures/ BEFORE run
CAPTURES_DIR = Path("data/mcp/captures")
if CAPTURES_DIR.exists():
    shutil.rmtree(CAPTURES_DIR)
CAPTURES_DIR.mkdir(parents=True, exist_ok=True)

os.environ.setdefault("QML_DISABLE_DISK_CACHE", "1")
os.environ["SKILL_MANAGER_DEV_MODE"] = "1"
os.environ["SKILL_MANAGER_TESTING"] = "1"
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["XDG_DATA_HOME"] = str(Path("data/test_xdg_data").resolve())
os.environ["XDG_CONFIG_HOME"] = str(Path("data/test_xdg_config").resolve())

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

from PySide6.QtCore import QTimer
from PySide6.QtGui import QGuiApplication, QSurfaceFormat
from PySide6.QtQml import QQmlApplicationEngine, qmlRegisterSingletonInstance
from PySide6.QtQuickControls2 import QQuickStyle

QQuickStyle.setStyle("Basic")
fmt = QSurfaceFormat()
fmt.setAlphaBufferSize(8)
QSurfaceFormat.setDefaultFormat(fmt)

app = QGuiApplication(sys.argv)
app.setApplicationName("SkillManager")
app.setApplicationVersion(skill_manager.__version__)

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
if window:
    window.show()
    window.raise_()

if not engine.rootObjects():
    print("FATAL: No QML root objects!")
    sys.exit(1)


def step1_wait():
    print(f"[+{time.monotonic() - START_TIME:.1f}s] Waiting for main app to settle...")
    QTimer.singleShot(2500, step2_open_package_edit_dialog)


def step2_open_package_edit_dialog():
    print(f"[+{time.monotonic() - START_TIME:.1f}s] Switching view to Updates & Opening Edit Skill Package dialog...")
    controller.ui_controller.currentView = "Updates"

    test_pkg = {
        "name": "agentic-awesome-skills",
        "source_type": "git",
        "package_name": "agentic-awesome-skills",
        "repository_url": "https://github.com/sickn33/agentic-awesome-skills",
        "github_token": "ghp_xxxxxxxxxxxx",
        "package_path": "/tmp/packages/agentic-awesome-skills",
        "package_args": "",
        "update_command": "git pull",
        "current_version_command": "npx list -g @org/skills --json",
        "latest_version_command": "npx show @org/skills version",
    }

    def find_dialog(obj):
        if not obj:
            return None
        if hasattr(obj, "objectName") and obj.objectName() == "uv_packageEditDialog":
            return obj
        if "PackageEditDialog" in str(obj.metaObject().className()):
            return obj
        for child in obj.children():
            res = find_dialog(child)
            if res:
                return res
        return None

    dlg = find_dialog(window)
    if dlg and hasattr(dlg, "loadPackage") and hasattr(dlg, "open"):
        dlg.editIndex = 0
        dlg.loadPackage(test_pkg)
        dlg.open()
        print("Opened PackageEditDialog via QML hierarchy.")
    else:
        print("ERR: Could not locate PackageEditDialog in QML tree!")

    QTimer.singleShot(3500, step3_take_shot)


def step3_take_shot():
    print(f"[+{time.monotonic() - START_TIME:.1f}s] Capturing real app screenshot...")

    shot_path = CAPTURES_DIR / "verify_package_edit_scroll.png"
    img = window.grabWindow()
    img.save(str(shot_path))
    print(f"SAVED SCREENSHOT TO: {shot_path.resolve()}")

    signal.alarm(0)
    QTimer.singleShot(100, app.quit)


QTimer.singleShot(1000, step1_wait)
app.exec()
print(f"[+{time.monotonic() - START_TIME:.1f}s] Script complete.")

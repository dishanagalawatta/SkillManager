"""
Verification script for CommandCreateDialog ("Edit Custom Command").
Starts the REAL application via AppController, opens CommandCreateDialog in edit mode,
captures the window screenshot via QWindow.grabWindow(), and saves it to data/mcp/captures/.

Usage: uv run python scripts/verify_edit_command_dialog.py
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
    print(f"WATCHDOG: {time.monotonic() - START_TIME:.1f}s elapsed — forcing exit")
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
    QTimer.singleShot(2500, step2_open_edit_command_dialog)


def step2_open_edit_command_dialog():
    print(f"[+{time.monotonic() - START_TIME:.1f}s] Opening Edit Custom Command dialog...")

    proj1 = Path("data/test_xdg_data/proj1").resolve()
    proj2 = Path("data/test_xdg_data/proj2").resolve()
    (proj1 / ".agents" / "commands").mkdir(parents=True, exist_ok=True)
    (proj2 / ".agents" / "commands").mkdir(parents=True, exist_ok=True)

    cmd_file1 = proj1 / ".agents" / "commands" / "Debug.md"
    cmd_file1.write_text("---\nname: Debug\ncategory: Custom Commands\ntype: command\n---\nBody text")

    controller._projects = [str(proj1), str(proj2)]

    test_cmd = {
        "name": "Debug",
        "description": "Senior System Architect & Expert Debugger command.",
        "local_path": str(cmd_file1),
        "category": "Custom Commands",
        "author": "Antigravity",
        "version": "1.0.0",
        "tags": ["debug"],
        "source_id": "test",
        "is_command": True,
        "is_package": False,
        "body_content": (
            "You are a Senior System Architect and Expert Debugger. An issue description and "
            "technical context have been provided adjacent to this prompt.\n\n"
            "**Core Directives:**\nDo not apply temporary patches. Your primary goal is to resolve the issue "
            "while refactoring the codebase to be clean, professional, and maintainable for the long term."
        ),
        "raw_content": "",
        "project_label": "proj1",
    }

    # Find the dialog in QML root objects or overlay
    # CommandCreateDialog is instantiated inside CommandInspectorPanel
    inspector = window.findChild(object, "_commandDialog")
    if not inspector:
        # Search all children recursively
        for child in window.findChildren(object):
            if child.metaObject().className().startswith("CommandCreateDialog"):
                inspector = child
                break

    if inspector and hasattr(inspector, "openForEdit"):
        print("Found CommandCreateDialog via QML hierarchy, calling openForEdit...")
        inspector.openForEdit(test_cmd)
    else:
        print(
            "Calling QML via AppController or fallback root search for CommandCreateDialog..."
        )
        # Try finding by objectName or QML engine root
        def find_dialog(obj):
            if not obj:
                return None
            if "CommandCreateDialog" in str(obj.metaObject().className()):
                return obj
            for child in obj.children():
                res = find_dialog(child)
                if res:
                    return res
            return None

        dlg = find_dialog(window)
        if dlg and hasattr(dlg, "openForEdit"):
            dlg.openForEdit(test_cmd)
        else:
            print("ERR: Could not locate CommandCreateDialog in QML tree!")

    QTimer.singleShot(3500, step3_take_shot)


def step3_take_shot():
    print(f"[+{time.monotonic() - START_TIME:.1f}s] Capturing real app screenshot...")

    cmd_id = uuid.uuid4().hex
    shot_path = CAPTURES_DIR / "verify_edit_command_dialog.png"

    img = window.grabWindow()
    img.save(str(shot_path))
    print(f"SAVED SCREENSHOT TO: {shot_path.resolve()}")

    signal.alarm(0)
    QTimer.singleShot(100, app.quit)


QTimer.singleShot(1000, step1_wait)
app.exec()
print(f"[+{time.monotonic() - START_TIME:.1f}s] Script complete.")

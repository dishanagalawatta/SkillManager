"""
Verify QuickCopy view: switch to QuickCopy, select test skill,
check inspector renders content correctly.
Run: uv run python scripts/verify_qc.py
"""

import os
import signal
import sys
import time
import uuid
from pathlib import Path

CAPTURES_DIR = Path("data/mcp/captures")
CAPTURES_DIR.mkdir(parents=True, exist_ok=True)

START_TIME = time.monotonic()


def watchdog(signum, frame):
    print(f"WATCHDOG: {time.monotonic() - START_TIME:.1f}s — forcing exit")
    os._exit(1)


signal.signal(signal.SIGALRM, watchdog)
signal.alarm(40)

os.makedirs("/tmp/test-qc-injected", exist_ok=True)
with open("/tmp/test-qc-injected/skill.md", "w") as f:
    f.write("# QC Test Inspector\n\nContent for QuickCopy verification.\n")

os.environ.setdefault("QML_DISABLE_DISK_CACHE", "1")
os.environ["SKILL_MANAGER_DEV_MODE"] = "1"
os.environ["SKILL_MANAGER_TESTING"] = "1"

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
    print(f"[+{time.monotonic() - START_TIME:.1f}s] Waiting for app to settle...")
    QTimer.singleShot(2500, step2_setup_qc)


def step2_setup_qc():
    lm = controller.libraryModel
    lm.categoryFilter = None
    lm.projectFilter = None
    lm.filterText = ""
    lm.showArchived = True
    lm.isPackageOnly = False

    body_content = (
        "# Test QuickCopy Inspector\n\n"
        "## Overview\n"
        "This is a test skill to verify the QuickCopy view inspector renders content correctly. "
        "The inspector panel should display this body content after the skill is selected.\n"
    )

    test_skill = {
        "name": "QC-Test-Inspector-Skill",
        "description": "Test skill for QuickCopy view inspector verification.",
        "local_path": "/tmp/test-qc-injected/skill.md",
        "category": "testing",
        "author": "verification",
        "version": "1.0.0",
        "tags": ["test", "verification"],
        "source_id": "test",
        "is_command": False,
        "is_package": False,
        "commands": [],
        "body_content": body_content,
        "raw_content": body_content,
        "project_label": "QC Verification",
    }

    lm.setSkills([test_skill])
    if hasattr(controller, "quickCopyModel") and controller.quickCopyModel:
        controller.quickCopyModel.categoryFilter = None
        controller.quickCopyModel.projectFilter = None
        controller.quickCopyModel.filterText = ""
        controller.quickCopyModel.showArchived = True
        controller.quickCopyModel.isPackageOnly = False
        controller.quickCopyModel.setSkills([test_skill])

    window.navigateTo("Quick Copy")
    controller.ui_controller.currentView = "Quick Copy"

    def do_select():
        controller.ui_controller.selectSkill(0)
        sel = controller.selectedSkill
        name = sel.name if sel else "NONE"
        print(f"[+{time.monotonic() - START_TIME:.1f}s] Model skills: {lm.rowCount()}")
        print(f"[+{time.monotonic() - START_TIME:.1f}s] Selected: {name}")

    QTimer.singleShot(500, do_select)
    QTimer.singleShot(3500, step3_capture)


def step3_capture():
    sel = controller.selectedSkill
    name = sel.name if sel else "NONE"
    print(f"[+{time.monotonic() - START_TIME:.1f}s] Capturing QuickCopy screenshot...")

    cmd_id = uuid.uuid4().hex
    shot_path = str(CAPTURES_DIR / f"verify_qc_{cmd_id}.png")

    img = window.grabWindow()
    img.save(shot_path)
    print(f"SAVED: {shot_path}")

    print(f"\nRESULT: screenshot={shot_path}")
    print(f"RESULT: selected={name}")

    signal.alarm(0)
    QTimer.singleShot(100, app.quit)


QTimer.singleShot(1000, step1_wait)
app.exec()
print(f"[+{time.monotonic() - START_TIME:.1f}s] Done.")

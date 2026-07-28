"""
Helper: inject a skill with LONG description, select it, screenshot.
Run via: uv run python scripts/verify_fix.py
"""

import json
import os
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

os.makedirs("/tmp/test-pkg-skill", exist_ok=True)
with open("/tmp/test-pkg-skill/skill.md", "w") as f:
    f.write("# Test Skill\n\nContent.\n")

LONG_DESC = (
    "Senior System Architect responsible for designing "
    "large-scale distributed systems, microservices architectures, "
    "event-driven patterns, and cloud-native solutions. "
    * 30
)

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
    QTimer.singleShot(2500, step2_inject_and_select)


def step2_inject_and_select():
    lm = controller.libraryModel
    lm.categoryFilter = None
    lm.projectFilter = None
    lm.filterText = ""
    lm.showArchived = True
    lm.isPackageOnly = False

    test_skill = {
        "name": "ZZ_Test_Long_Description",
        "description": LONG_DESC,
        "local_path": "/tmp/test-pkg-skill/skill.md",
        "category": "architecture",
        "author": "team",
        "version": "1.0.0",
        "tags": ["test"],
        "source_id": "test",
        "is_command": False,
        "is_package": False,
        "commands": [],
        "body_content": "# Test\n\nBody content for verification.\n",
        "raw_content": "",
        "project_label": "Test",
        "date": "2026-01-15",
        "source": "built-in",
        "risk": "Low",
        "client": "Antigravity",
    }
    lm.setSkills([test_skill])
    controller.ui_controller.currentView = "Library"
    controller.ui_controller.selectSkill(0)

    sel = controller.selectedSkill
    print(f"[+{time.monotonic() - START_TIME:.1f}s] Model skills: {lm.rowCount()}")
    print(f"[+{time.monotonic() - START_TIME:.1f}s] Selected: {sel.name if sel else 'NONE'}")

    QTimer.singleShot(3000, step3_capture)


def step3_capture():
    print(f"[+{time.monotonic() - START_TIME:.1f}s] Capturing screenshot...")
    captures_dir = Path("data/mcp/captures")
    captures_dir.mkdir(parents=True, exist_ok=True)

    cmd_id = uuid.uuid4().hex
    shot_path = captures_dir / f"verify_fix_{cmd_id}.png"

    img = window.grabWindow()
    img.save(str(shot_path))
    print(f"SAVED: {shot_path}")

    sel = controller.selectedSkill
    print(f"RESULT: screenshot={shot_path}")
    print(f"RESULT: selected={sel.name if sel else 'NONE'}")
    if sel:
        print(f"RESULT: desc_length={len(sel.description or '')}")

    signal.alarm(0)
    QTimer.singleShot(100, app.quit)


QTimer.singleShot(1000, step1_wait)
app.exec()
print(f"[+{time.monotonic() - START_TIME:.1f}s] Done.")

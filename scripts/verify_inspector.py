"""
Helper script: starts the REAL SkillManager app, ensures Library view,
selects a skill, takes a screenshot, and exits.
Must be run from the project root via: uv run python scripts/verify_inspector.py
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
    print(f"WATCHDOG: {time.monotonic() - START_TIME:.1f}s elapsed — forcing exit")
    os._exit(1)


signal.signal(signal.SIGALRM, watchdog_timeout)
signal.alarm(40)

CAPTURES_DIR = Path("data/mcp/captures")
CAPTURES_DIR.mkdir(parents=True, exist_ok=True)

os.makedirs("/tmp/test-pkg-skill", exist_ok=True)
with open("/tmp/test-pkg-skill/skill.md", "w") as f:
    f.write("# Senior Software Architect\n\nPackage skill content for verification.\n")

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
    print(f"[+{time.monotonic() - START_TIME:.1f}s] Waiting for app to settle...")
    QTimer.singleShot(2500, step2_inject_and_select)


def step2_inject_and_select():
    lm = controller.libraryModel
    lm.categoryFilter = None
    lm.projectFilter = None
    lm.filterText = ""
    lm.showArchived = True
    lm.isPackageOnly = False

    raw = "# Senior Software Architect\n\nPackage skill content for verification.\n"
    body = "Package skill content for verification."
    test_skill = {
        "name": "Senior Software Architect",
        "description": "System Architect responsible for large-scale distributed systems.",
        "local_path": "/tmp/test-pkg-skill/skill.md",
        "category": "architecture",
        "author": "team",
        "version": "1.0.0",
        "tags": ["architecture"],
        "source_id": "test",
        "is_command": False,
        "is_package": False,
        "commands": [],
        "body_content": body,
        "raw_content": raw,
        "project_label": "Test Injection",
        "client": "Antigravity",
    }

    lm.setSkills([test_skill])
    controller.ui_controller.currentView = "Library"
    controller.ui_controller.selectSkill(0)

    sel = controller.selectedSkill
    print(f"[+{time.monotonic() - START_TIME:.1f}s] Model skills: {lm.rowCount()}")
    print(f"[+{time.monotonic() - START_TIME:.1f}s] Selected: {sel.name if sel else 'NONE'}")

    QTimer.singleShot(3000, step3_take_shot)


def step3_take_shot():
    sel = controller.selectedSkill
    name = sel.name if sel else "NONE"
    print(f"[+{time.monotonic() - START_TIME:.1f}s] Capturing inspector screenshot...")

    cmd_id = uuid.uuid4().hex
    shot_path = CAPTURES_DIR / f"verify_inspector_{cmd_id}.png"

    img = window.grabWindow()
    img.save(str(shot_path))
    print(f"SAVED: {shot_path}")

    print(f"\nRESULT: screenshot={shot_path}")
    print(f"RESULT: selected={name}")

    signal.alarm(0)
    QTimer.singleShot(100, app.quit)


QTimer.singleShot(1000, step1_wait)
app.exec()
print(f"[+{time.monotonic() - START_TIME:.1f}s] Done.")

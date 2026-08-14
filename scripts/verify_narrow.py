"""
Resize window to narrow width (600x700), select skill with long description,
screenshot, verify no clipping.
Run via: uv run python scripts/verify_narrow.py
"""

import os
import signal
import sys
import time
import uuid
from pathlib import Path

START_TIME = time.monotonic()


def watchdog(signum, frame):
    print(f"WATCHDOG: {time.monotonic() - START_TIME:.1f}s — forcing exit")
    os._exit(1)


signal.signal(signal.SIGALRM, watchdog)
signal.alarm(40)

LONG_DESC = "Senior System Architect. " * 200

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
    window.resize(600, 700)
    print("[+0.1s] Window resized to 600x700")
else:
    print("FATAL: No window!")
    sys.exit(1)


def step1_wait():
    print(f"[+{time.monotonic() - START_TIME:.1f}s] Waiting for app to settle...")
    QTimer.singleShot(2500, step2_select_long_desc)


def step2_select_long_desc():
    lm = controller.libraryModel
    lm.categoryFilter = None
    lm.projectFilter = None
    lm.filterText = ""
    lm.showArchived = True
    lm.isPackageOnly = False

    test_skill = {
        "name": "ZZ_Test_Long_Desc",
        "description": LONG_DESC,
        "local_path": "/tmp/test-long-desc/skill.md",
        "category": "test",
        "author": "test",
        "version": "1.0.0",
        "tags": ["test"],
        "source_id": "test_local",
        "is_command": False,
        "is_package": False,
        "commands": [],
        "body_content": "# Test\n\nContent for narrow width verification.\n",
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
    name = sel.name if sel else "NONE"
    print(f"[+{time.monotonic() - START_TIME:.1f}s] Selected: {name}, desc_len={len(LONG_DESC)}")
    QTimer.singleShot(3000, step3_capture)


def step3_capture():
    print(f"[+{time.monotonic() - START_TIME:.1f}s] Capturing narrow screenshot...")
    captures_dir = Path("data/mcp/captures")
    captures_dir.mkdir(parents=True, exist_ok=True)

    cmd_id = uuid.uuid4().hex
    shot_path = str(captures_dir / f"verify_narrow_{cmd_id}.png")

    img = window.grabWindow()
    img.save(shot_path)
    print(f"SAVED: {shot_path}")

    sel = controller.selectedSkill
    print(f"\nRESULT: screenshot={shot_path}")
    print(f"RESULT: selected={sel.name if sel else 'NONE'}")
    print("RESULT: window_size=600x700")

    signal.alarm(0)
    QTimer.singleShot(100, app.quit)


QTimer.singleShot(1000, step1_wait)
app.exec()
print(f"[+{time.monotonic() - START_TIME:.1f}s] Done.")

"""Visual verification script for real running SkillManager app.

Captures screenshots of both Library and QuickCopy views after full discovery.
Run: uv run python scripts/verify_ui_real.py
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
signal.alarm(45)

os.environ.setdefault("QML_DISABLE_DISK_CACHE", "1")
os.environ["SKILL_MANAGER_DEV_MODE"] = "1"

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


def step1_capture_library():
    print(f"[+{time.monotonic() - START_TIME:.1f}s] Capturing Library view screenshot...")
    shot_path = str(CAPTURES_DIR / "library_view.png")
    img = window.grabWindow()
    img.save(shot_path)
    print(f"SAVED: {shot_path}")

    # Now navigate to Quick Copy
    print(f"[+{time.monotonic() - START_TIME:.1f}s] Navigating to Quick Copy...")
    window.navigateTo("Quick Copy")

    QTimer.singleShot(1500, step2_select_qc_skill)


def step2_select_qc_skill():
    print(f"[+{time.monotonic() - START_TIME:.1f}s] Selecting first skill in Quick Copy...")
    controller.ui_controller.selectSkill(0)
    sel = controller.selectedSkill
    name = sel.name if sel else "NONE"
    print(f"[+{time.monotonic() - START_TIME:.1f}s] Selected skill: {name}")

    QTimer.singleShot(3500, step3_capture_quickcopy)


def step3_capture_quickcopy():
    print(f"[+{time.monotonic() - START_TIME:.1f}s] Capturing QuickCopy view screenshot...")
    shot_path = str(CAPTURES_DIR / "quickcopy_view.png")
    img = window.grabWindow()
    img.save(shot_path)
    print(f"SAVED: {shot_path}")

    signal.alarm(0)
    QTimer.singleShot(100, app.quit)


# Allow discovery and rendering to settle before capture
QTimer.singleShot(4000, step1_capture_library)
app.exec()
print(f"[+{time.monotonic() - START_TIME:.1f}s] Verification completed cleanly.")

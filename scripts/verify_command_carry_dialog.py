"""
Verification script for CommandCarrySkillsDialog ("Carry Skills to Project").
Starts the REAL application via AppController loaded through Main.qml, opens CommandCarrySkillsDialog,
captures the window screenshot via QWindow.grabWindow(), and saves it to data/mcp/captures/.

Usage: uv run python scripts/verify_command_carry_dialog.py
"""

import os
import shutil
import signal
import sys
import time
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
    QTimer.singleShot(2500, step2_open_dialog)


def step2_open_dialog():
    print(f"[+{time.monotonic() - START_TIME:.1f}s] Opening Carry Skills to Project dialog...")

    test_skills = [
        {"name": "concise-planning", "folder_name": "concise-planning"},
        {"name": "conductor-implement", "folder_name": "conductor-implement"},
        {"name": "systematic-debugging", "folder_name": "systematic-debugging"},
    ]

    # Emit signal on AppController so LibraryView / QuickCopyView opens lv_carrySkillsDialog
    import json

    controller.commandSkillsCarryPrompt.emit(
        '["/path/to/cmd.md"]', "/target/project", json.dumps(test_skills)
    )

    QTimer.singleShot(3500, step3_take_shot)


def step3_take_shot():
    print(f"[+{time.monotonic() - START_TIME:.1f}s] Capturing real app screenshot...")

    shot_path = CAPTURES_DIR / "verify_command_carry_dialog.png"

    img = window.grabWindow()
    img.save(str(shot_path))
    print(f"SAVED SCREENSHOT TO: {shot_path.resolve()}")

    signal.alarm(0)
    QTimer.singleShot(100, app.quit)


QTimer.singleShot(1000, step1_wait)
app.exec()
print(f"[+{time.monotonic() - START_TIME:.1f}s] Script complete.")

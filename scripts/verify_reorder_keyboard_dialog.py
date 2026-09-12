"""
Verification script for keyboard-operable ProjectReorderDialog.
Starts the REAL application via AppController loaded through Main.qml,
seeds test projects, opens the reorder dialog from Settings, focuses the
first row, invokes the keyboard move path, and captures screenshots via
QWindow.grabWindow() into data/mcp/captures/.

Usage: uv run python scripts/verify_reorder_keyboard_dialog.py
"""

import os
import shutil
import signal
import sys
import tempfile
import time
from pathlib import Path

START_TIME = time.monotonic()


def watchdog_timeout(signum, frame):
    print(f"WATCHDOG: {time.monotonic() - START_TIME:.1f}s elapsed — forcing exit")
    os._exit(1)


signal.signal(signal.SIGALRM, watchdog_timeout)
signal.alarm(90)

# Mandatory Rule #6: Clean all captures from data/mcp/captures/ BEFORE run
CAPTURES_DIR = Path("data/mcp/captures")
if CAPTURES_DIR.exists():
    shutil.rmtree(CAPTURES_DIR)
CAPTURES_DIR.mkdir(parents=True, exist_ok=True)

# Hermetic run: drop persisted test config/data from previous runs
for _d in ("data/test_xdg_data", "data/test_xdg_config"):
    shutil.rmtree(_d, ignore_errors=True)

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

from PySide6.QtCore import QMetaObject, QObject, QTimer
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

seed_dir = Path(tempfile.mkdtemp(prefix="reorder_verify_"))
for name in ["alpha-proj", "beta-proj", "gamma-proj"]:
    (seed_dir / name).mkdir(parents=True, exist_ok=True)

dialog = None


def find_reorder_dialog():
    for obj in engine.rootObjects():
        for child in obj.findChildren(QObject):
            try:
                if child.property("projectLabels") is not None and child.property("pendingFocusIndex") is not None:
                    return child
            except Exception:
                continue
    return None


def grab(name):
    shot_path = CAPTURES_DIR / name
    img = window.grabWindow()
    img.save(str(shot_path))
    print(f"SAVED SCREENSHOT TO: {shot_path.resolve()}")


def step1_seed_and_navigate():
    print(f"[+{time.monotonic() - START_TIME:.1f}s] Seeding projects + opening Settings...")
    for name in ["alpha-proj", "beta-proj", "gamma-proj"]:
        controller.config_mgr.addProject(f"file://{(seed_dir / name).as_posix()}")
    print(f"[VERIFY] projects: {controller._projects}")
    controller.ui.currentView = "Settings"
    QTimer.singleShot(2500, step2_open_dialog)


def step2_open_dialog():
    global dialog
    print(f"[+{time.monotonic() - START_TIME:.1f}s] Opening ProjectReorderDialog...")
    dialog = find_reorder_dialog()
    if dialog is None:
        print("FATAL: reorder dialog object not found")
        sys.exit(1)
    QMetaObject.invokeMethod(dialog, "open")
    QTimer.singleShot(3500, step3_focus_first_row)


def focus_row(idx):
    from PySide6.QtCore import Q_ARG

    ok = QMetaObject.invokeMethod(dialog, "focusRow", Q_ARG(int, idx))
    print(f"[VERIFY] focusRow({idx}) returned: {ok}")
    try:
        return bool(ok)
    except Exception:
        return False


def step3_focus_first_row():
    print(f"[+{time.monotonic() - START_TIME:.1f}s] Focusing row 0 + capturing...")
    ok = focus_row(0)
    print(f"[VERIFY] focus row 0: {ok}")
    QTimer.singleShot(1200, step4_shot_focused)


def step4_shot_focused():
    grab("verify_reorder_focused.png")
    print(f"[+{time.monotonic() - START_TIME:.1f}s] Invoking keyboard move path (row 0 down)...")
    # moveProject(fromIdx, delta) exercises the same slot the Alt+Down key
    # handler calls (physical keypresses cannot be injected per input policy).
    from PySide6.QtCore import Q_ARG

    QMetaObject.invokeMethod(dialog, "moveProject", Q_ARG(int, 0), Q_ARG(int, 1))
    QTimer.singleShot(3500, step5_shot_moved)


def step5_shot_moved():
    grab("verify_reorder_moved.png")
    print(f"[VERIFY] labels after move: {list(controller.config_mgr.projectLabels)}")
    print(f"[VERIFY] pendingFocusIndex: {dialog.property('pendingFocusIndex')}")
    signal.alarm(0)
    shutil.rmtree(seed_dir, ignore_errors=True)
    QTimer.singleShot(100, app.quit)


QTimer.singleShot(1000, step1_seed_and_navigate)
app.exec()
print(f"[+{time.monotonic() - START_TIME:.1f}s] Script complete.")

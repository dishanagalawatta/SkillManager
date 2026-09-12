"""
Verification script for GlassMultiSelect single-tab-stop rows.
Starts the REAL application via AppController loaded through Main.qml,
seeds test projects, enters QuickCopy collection editing, opens the
project GlassMultiSelect popup, focuses the first row, and captures via
QWindow.grabWindow() into data/mcp/captures/.

Usage: uv run python scripts/verify_multiselect_row_focus.py
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

# Hermetic run: clean captures and persisted test config/data BEFORE run
CAPTURES_DIR = Path("data/mcp/captures")
if CAPTURES_DIR.exists():
    shutil.rmtree(CAPTURES_DIR)
CAPTURES_DIR.mkdir(parents=True, exist_ok=True)
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

from PySide6.QtCore import Q_ARG, QMetaObject, QObject, QTimer
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

seed_dir = Path(tempfile.mkdtemp(prefix="multiselect_verify_"))
for name in ["alpha-proj", "beta-proj", "gamma-proj"]:
    (seed_dir / name).mkdir(parents=True, exist_ok=True)


def find_qcv_root():
    for obj in engine.rootObjects():
        for child in obj.findChildren(QObject):
            try:
                if child.property("isEditingCollection") is not None and child.property("editingCollectionProjects") is not None:
                    return child
            except Exception:
                continue
    return None


def step1_seed_and_navigate():
    print(f"[+{time.monotonic() - START_TIME:.1f}s] Seeding projects + opening QuickCopy...")
    for name in ["alpha-proj", "beta-proj", "gamma-proj"]:
        controller.config_mgr.addProject(f"file://{(seed_dir / name).as_posix()}")
    print(f"[VERIFY] projects: {controller._projects}")
    controller.ui.currentView = "QuickCopy"
    QTimer.singleShot(2500, step2_enter_editing)


def step2_enter_editing():
    qcv = find_qcv_root()
    if qcv is None:
        print("FATAL: QuickCopy root not found")
        sys.exit(1)
    print(f"[+{time.monotonic() - START_TIME:.1f}s] Entering collection editing...")
    qcv.setProperty("isEditingCollection", True)
    QTimer.singleShot(2000, step3_open_popup)


def step3_open_popup():
    qcv = find_qcv_root()
    ms = None
    for child in qcv.findChildren(QObject):
        try:
            if child.property("allLabel") == "All Projects":
                ms = child
                break
        except Exception:
            continue
    if ms is None:
        print("FATAL: GlassMultiSelect control not found")
        sys.exit(1)
    print(f"[+{time.monotonic() - START_TIME:.1f}s] Opening popup + focusing row 0...")
    QMetaObject.invokeMethod(ms, "openPopup")
    QTimer.singleShot(1200, lambda: step4_focus_row(ms))


def step4_focus_row(ms):
    ok = QMetaObject.invokeMethod(ms, "focusRow", Q_ARG(int, 0))
    print(f"[VERIFY] focusRow(0) returned: {ok}")
    QTimer.singleShot(3000, step5_shot)


def step5_shot():
    shot_path = CAPTURES_DIR / "verify_multiselect_row_focus.png"
    img = window.grabWindow()
    img.save(str(shot_path))
    print(f"SAVED SCREENSHOT TO: {shot_path.resolve()}")
    signal.alarm(0)
    shutil.rmtree(seed_dir, ignore_errors=True)
    QTimer.singleShot(100, app.quit)


QTimer.singleShot(1000, step1_seed_and_navigate)
app.exec()
print(f"[+{time.monotonic() - START_TIME:.1f}s] Script complete.")

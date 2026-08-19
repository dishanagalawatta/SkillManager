"""
Helper script: starts the REAL SkillManager app (real Main.qml + AppController),
injects a STARRED skill, and captures the starred-icon rendering across all
affected views (Library, SkillInspector, QuickCopy) to verify the Theme.accent
token substitution (PR #245 consolidation).

Must be run from the project root via: uv run python scripts/verify_star_theme_accent.py
"""

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
signal.alarm(60)

CAPTURES_DIR = Path("data/mcp/captures")
CAPTURES_DIR.mkdir(parents=True, exist_ok=True)

os.makedirs("/tmp/test-pkg-skill-star", exist_ok=True)
with open("/tmp/test-pkg-skill-star/skill.md", "w") as f:
    f.write("# Starred Verification Skill\n\nContent for star theme-accent verification.\n")

os.environ.setdefault("QML_DISABLE_DISK_CACHE", "1")
os.environ["SKILL_MANAGER_DEV_MODE"] = "1"
os.environ["SKILL_MANAGER_TESTING"] = "1"
if "QT_QPA_PLATFORM" not in os.environ:
    os.environ["QT_QPA_PLATFORM"] = "offscreen"

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
controller.ui_controller.darkMode = True  # accent = #3B82F6 blue; legacy gold would be #FFD700

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

SHOTS = []


def shoot(tag):
    cmd_id = uuid.uuid4().hex
    shot_path = CAPTURES_DIR / f"star_accent_{tag}_{cmd_id}.png"
    img = window.grabWindow()
    img.save(str(shot_path))
    SHOTS.append(shot_path)
    print(f"SAVED: {shot_path}")


def step1_wait():
    print(f"[+{time.monotonic() - START_TIME:.1f}s] Waiting for app to settle...")
    QTimer.singleShot(2500, step2_inject_and_select)


def step2_inject_and_select():
    lm = controller.libraryModel
    qm = controller.quickCopyModel

    raw = "# Starred Verification Skill\n\nContent for star theme-accent verification.\n"
    body = "Content for star theme-accent verification."
    test_skill = {
        "name": "Starred Verification Skill",
        "description": "Verifies Theme.accent starred icon rendering.",
        "local_path": "/tmp/test-pkg-skill-star/skill.md",
        "category": "architecture",
        "author": "team",
        "version": "1.0.0",
        "tags": ["architecture"],
        "source_id": "test",
        "is_command": False,
        "is_package": False,
        "is_starred": True,
        "commands": [],
        "body_content": body,
        "raw_content": raw,
        "project_label": "Test Injection",
        "client": "Antigravity",
    }

    # Order matters: setSkills(reset=True) re-reads filter state from config,
    # so filter overrides must be applied AFTER the injection.
    lm.setSkills([test_skill])
    lm.categoryFilter = None
    lm.projectFilter = None
    lm.filterText = ""
    lm.showArchived = True
    lm.isPackageOnly = False
    lm.clientFilter = ""  # config defaults to client_format=OpenCode, which would filter the test skill out

    qm.setSkills([test_skill])
    qm.categoryFilter = None
    qm.projectFilter = None
    qm.filterText = ""
    qm.showArchived = True
    qm.isPackageOnly = False
    qm.clientFilter = ""

    controller.ui_controller.currentView = "Library"
    controller.ui_controller.selectSkill(0)

    sel = controller.selectedSkill
    print(f"[+{time.monotonic() - START_TIME:.1f}s] Model skills: {lm.rowCount()} (quickcopy: {qm.rowCount()})")
    print(f"[+{time.monotonic() - START_TIME:.1f}s] Selected: {sel.name if sel else 'NONE'} "
          f"starred={getattr(sel, 'is_starred', 'N/A')}")

    QTimer.singleShot(3000, step3_library_shot)


def step3_library_shot():
    print(f"[+{time.monotonic() - START_TIME:.1f}s] Capturing LIBRARY view (SkillItem star overlay)...")
    shoot("library")
    QTimer.singleShot(300, step4_inspector_shot)


def step4_inspector_shot():
    controller.ui_controller.currentView = "Library"  # inspector overlay opens over library
    QTimer.singleShot(2000, step5_capture_inspector)


def step5_capture_inspector():
    print(f"[+{time.monotonic() - START_TIME:.1f}s] Capturing SKILL INSPECTOR (star button)...")
    shoot("inspector")
    QTimer.singleShot(300, step6_quickcopy_shot)


def step6_quickcopy_shot():
    controller.ui_controller.currentView = "QuickCopy"
    QTimer.singleShot(2500, step7_capture_quickcopy)


def step7_capture_quickcopy():
    print(f"[+{time.monotonic() - START_TIME:.1f}s] Capturing QUICKCOPY view (SkillItem star overlay)...")
    shoot("quickcopy")

    print("\nRESULT shots:")
    for s in SHOTS:
        print(f"RESULT: {s}")

    signal.alarm(0)
    QTimer.singleShot(100, app.quit)


QTimer.singleShot(1000, step1_wait)
app.exec()
print(f"[+{time.monotonic() - START_TIME:.1f}s] Done.")

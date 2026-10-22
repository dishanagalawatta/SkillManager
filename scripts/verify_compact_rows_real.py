# ruff: noqa: E402, ARG001
"""Real-app visual verification for the permanent compact list-row design.

Runs the REAL ``AppController`` and the REAL ``Main.qml`` in one process and
captures the live window with ``QWindow.grabWindow()`` (never the IPC
CommandChannel capture, which grabs the wrong region headless).

Captures:

1. ``compact_rows_library.png``   — Library view with skill rows.
2. ``compact_rows_quickcopy.png`` — Quick Copy view with command rows.
3. ``compact_rows_settings.png``  — Settings view, proving the "Compact List
   Rows" toggle is gone and the surrounding layout has no orphaned gap.

The app's own data directory is redirected to a scratch dir, so the user's
``config.json`` is never touched. A throwaway skill source is injected
in-memory so the row delegate actually renders.

Run: uv run python scripts/verify_compact_rows_real.py
"""

import json
import os
import shutil
import signal
import sys
import tempfile
import time
from pathlib import Path

CAPTURES_DIR = Path("data/mcp/captures")
START_TIME = time.monotonic()

# The app writes its own artifacts here; keep them out of the user's real dir.
SCRATCH = Path(tempfile.mkdtemp(prefix="skillmanager-compact-verify-"))
os.environ["SKILL_MANAGER_DATA_DIR"] = str(SCRATCH / "data")
os.environ.setdefault("QML_DISABLE_DISK_CACHE", "1")
os.environ["SKILL_MANAGER_DEV_MODE"] = "1"
# Do not let the MCP bridge contend for the same source tree.
os.environ["SKILL_MANAGER_MCP_NO_IPC"] = "1"


def watchdog(signum, frame):
    print(f"WATCHDOG: {time.monotonic() - START_TIME:.1f}s — forcing exit")
    os._exit(1)


signal.signal(signal.SIGALRM, watchdog)
signal.alarm(180)

# Clean stale captures BEFORE the run so no old screenshot can be misread.
if CAPTURES_DIR.exists():
    for stale in CAPTURES_DIR.glob("*.png"):
        stale.unlink()
CAPTURES_DIR.mkdir(parents=True, exist_ok=True)

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

from PySide6.QtCore import QObject, QTimer
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
if window is None or not engine.rootObjects():
    print("FATAL: No QML root objects!")
    sys.exit(1)
window.show()
window.raise_()


def _log(step, message):
    print(f"[+{time.monotonic() - START_TIME:.1f}s] {step}: {message}", flush=True)


def _capture(name):
    path = str(CAPTURES_DIR / name)
    pixmap = window.grabWindow()
    if pixmap.isNull():
        print(f"CAPTURE FAILED: {name}")
        return
    pixmap.save(path)
    _log("CAPTURE", f"{path} ({pixmap.width()}x{pixmap.height()})")


def _make_source():
    """Build a throwaway skill source so the row delegate renders."""
    src = SCRATCH / "source"
    specs = [
        ("code-review", "Code Review", "Reviews a diff for correctness, naming and test gaps."),
        ("release-notes", "Release Notes", "Turns a git log into a formatted changelog."),
        ("refactor-plan", "Refactor Plan", "Drafts a staged refactor plan for a module."),
    ]
    for folder, name, description in specs:
        d = src / folder
        d.mkdir(parents=True, exist_ok=True)
        (d / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: {description}\n---\n\n# {name}\n\nBody.\n",
            encoding="utf-8",
        )
    return src


def _make_project():
    """Build a throwaway project so the Quick Copy rows render.

    Quick Copy lists *project* skills (``<project>/.agents/skills``), while
    the Library lists *package* skills — both delegates are SkillItem, so both
    need a populated list to verify the compact row metrics.
    """
    proj = SCRATCH / "project"
    skills = proj / ".agents" / "skills"
    specs = [
        ("code-review", "Code Review", "Reviews a diff for correctness, naming and test gaps."),
        ("release-notes", "Release Notes", "Turns a git log into a formatted changelog."),
    ]
    for folder, name, description in specs:
        d = skills / folder
        d.mkdir(parents=True, exist_ok=True)
        (d / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: {description}\n---\n\n# {name}\n\nBody.\n",
            encoding="utf-8",
        )
    return proj


def step1_setup():
    src = _make_source()
    proj = _make_project()
    # The discovery controller reads the controller's in-memory source list,
    # so it has to be updated alongside the persisted config.
    controller._sources = [str(src)]
    controller._projects = [str(proj)]
    controller._config.set("sources", [str(src)])
    controller._config.set("projects", [str(proj)])
    _log("SETUP", f"injected source {src} and project {proj}")
    controller.refreshSkills("verify", True)
    QTimer.singleShot(6000, step2_select_skill)


def step2_select_skill():
    model = controller.libraryModel
    _log("SETUP", f"library rows={model.rowCount()}")

    if model.rowCount() > 0:
        # The real user path: clicking a row selects it by model index.
        controller.ui_controller.selectSkill(0)
        _log("SETUP", "selected row 0")
    QTimer.singleShot(3500, step3_capture_library)


def step3_capture_library():
    _capture("compact_rows_library.png")
    _log("NAV", "navigating to QuickCopy")
    window.navigateTo("QuickCopy")
    QTimer.singleShot(3500, step4_capture_quickcopy)


def step4_capture_quickcopy():
    _log("SETUP", f"quickcopy rows={controller.quickCopyModel.rowCount()}")
    _capture("compact_rows_quickcopy.png")
    _log("NAV", "navigating to Settings")
    window.navigateTo("Settings")
    QTimer.singleShot(3500, step5_capture_settings)


def step5_capture_settings():
    _capture("compact_rows_settings.png")
    QTimer.singleShot(300, finish)


def finish():
    qml_log = Path(os.environ["SKILL_MANAGER_DATA_DIR"]) / "qml_console.log"
    errors = []
    if qml_log.exists():
        for line in qml_log.read_text(encoding="utf-8", errors="ignore").splitlines():
            low = line.lower()
            if "referenceerror" in low or "typeerror" in low or "unable to assign" in low:
                errors.append(line)
    print("=== QML CONSOLE ERRORS ===")
    print(json.dumps(errors, indent=2) if errors else "none")
    print("=== CAPTURES ===")
    for p in sorted(CAPTURES_DIR.glob("*.png")):
        print(f"  {p} ({p.stat().st_size} bytes)")
    shutil.rmtree(SCRATCH, ignore_errors=True)
    os._exit(0)


QTimer.singleShot(1500, step1_setup)
app.exec()

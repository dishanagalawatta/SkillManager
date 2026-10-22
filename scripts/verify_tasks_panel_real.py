# ruff: noqa: E402, ARG001
"""Real-app visual verification for the per-project task list.

Runs the REAL ``AppController`` and the REAL ``Main.qml`` in one process and
captures the live window with ``QWindow.grabWindow()``.

Captures:

1. ``tasks_quickcopy_dark.png``   — Quick Copy with the task panel open,
   several tasks in different priorities and completion states, dark theme.
2. ``tasks_quickcopy_light.png``  — the same view in light theme.
3. ``tasks_panel_open.png``       — the panel's empty state (a project
   without any task yet).
4. ``tasks_no_project.png``       — the "select a project" empty state.

Run: uv run python scripts/verify_tasks_panel_real.py
"""

import os
import shutil
import signal
import sys
import tempfile
import time
from pathlib import Path

CAPTURES_DIR = Path("data/mcp/captures")
START_TIME = time.monotonic()

SCRATCH = Path(tempfile.mkdtemp(prefix="skillmanager-tasks-verify-"))
os.environ["SKILL_MANAGER_DATA_DIR"] = str(SCRATCH / "data")
os.environ.setdefault("QML_DISABLE_DISK_CACHE", "1")
os.environ["SKILL_MANAGER_DEV_MODE"] = "1"
os.environ["SKILL_MANAGER_MCP_NO_IPC"] = "1"


def watchdog(signum, frame):
    print(f"WATCHDOG: {time.monotonic() - START_TIME:.1f}s — forcing exit", flush=True)
    os._exit(1)


signal.signal(signal.SIGALRM, watchdog)
signal.alarm(240)

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
    print("FATAL: No QML root objects!", flush=True)
    sys.exit(1)
window.show()
window.raise_()


def _log(step, message):
    print(f"[+{time.monotonic() - START_TIME:.1f}s] {step}: {message}", flush=True)


def _capture(name):
    path = str(CAPTURES_DIR / name)
    pixmap = window.grabWindow()
    if pixmap.isNull():
        print(f"CAPTURE FAILED: {name}", flush=True)
        return
    pixmap.save(path)
    _log("CAPTURE", f"{path} ({pixmap.width()}x{pixmap.height()})")


def _make_fixture():
    """A project with one skill, plus a second empty project."""
    project = SCRATCH / "projectA"
    skill = project / ".agents" / "skills" / "local-helper"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        "---\nname: Local Helper\ndescription: A skill in the project.\n---\n\n# Local\n",
        encoding="utf-8",
    )
    empty = SCRATCH / "projectB"
    (empty / ".agents" / "skills" / "other-helper").mkdir(parents=True)
    (empty / ".agents" / "skills" / "other-helper" / "SKILL.md").write_text(
        "---\nname: Other Helper\ndescription: Another skill.\n---\n\n# Other\n",
        encoding="utf-8",
    )
    return project, empty


def step1_setup():
    project, empty = _make_fixture()
    controller._sources = []
    # The app normalises project paths to their skills dir at boot, so the
    # fixture mirrors that: the labels then read "projectA" / "projectB".
    from skill_manager.core.copier import get_skills_dir

    proj_a = str(get_skills_dir(project))
    proj_b = str(get_skills_dir(empty))
    controller._projects = [proj_a, proj_b]
    controller._config.set("projects", [proj_a, proj_b])
    # The app invalidates the project cache when a project is added.
    controller.config_mgr._invalidate_project_cache()

    label_a = controller.config_mgr.getProjectLabel(proj_a)
    label_b = controller.config_mgr.getProjectLabel(proj_b)
    _log("SETUP", f"labels={[label_a, label_b]}")
    controller._set_current_project(label_a)
    _log("SETUP", f"projects={[proj_a, proj_b]}")

    controller.refreshSkills("verify", True)
    QTimer.singleShot(7000, step2_open_panel)


def step2_open_panel():
    _log("NAV", "opening Quick Copy")
    window.navigateTo("QuickCopy")
    QTimer.singleShot(3500, step3_enable_panel)


def step3_enable_panel():
    controller.ui_controller.setTasksPanelOpen(True)
    _log("SETUP", f"tasksPanelOpen={controller.ui_controller.tasksPanelOpen}")
    QTimer.singleShot(1500, step4_add_tasks)


def step4_add_tasks():
    """Add tasks with different priorities and completion states."""
    from skill_manager.core.copier import get_skills_dir

    project = str(get_skills_dir(SCRATCH / "projectA"))

    controller.tasks.addProjectTask(project, "Write the release notes", "high", "")
    controller.tasks.addProjectTask(
        project, "Review the migration plan", "medium", "Check the rollback steps."
    )
    controller.tasks.addProjectTask(project, "Tidy the backlog", "low", "")

    tasks = controller.tasks.currentProjectTasks
    _log("SETUP", f"{len(tasks)} task(s) created: {[t['title'] for t in tasks]}")

    if tasks:
        controller.tasks.toggleProjectTask(project, tasks[-1]["id"])

    _log("SETUP", f"active={controller.tasks.activeTaskCount} done={controller.tasks.completedTaskCount}")
    QTimer.singleShot(2500, step5_capture_dark)


def step5_capture_dark():
    _capture("tasks_quickcopy_dark.png")
    _log("THEME", "switching to light mode")
    controller.ui_controller.darkMode = False
    QTimer.singleShot(2500, step6_capture_light)


def step6_capture_light():
    _capture("tasks_quickcopy_light.png")
    _log("THEME", "restoring dark mode")
    controller.ui_controller.darkMode = True
    QTimer.singleShot(2000, step7_other_project)


def step7_other_project():
    """A project without any task renders the "no tasks yet" empty state."""
    from skill_manager.core.copier import get_skills_dir

    empty = str(get_skills_dir(SCRATCH / "projectB"))
    other = controller.config_mgr.getProjectLabel(empty)
    controller._set_current_project(other)
    _log("NAV", f"switched to {other} (no tasks)")
    QTimer.singleShot(3000, step8_capture_empty)


def step8_capture_empty():
    _capture("tasks_panel_open.png")
    QTimer.singleShot(500, step9_no_project)


def step9_no_project():
    """No project selected renders the "select a project" empty state."""
    controller._set_current_project("")
    _log("NAV", "cleared the project selection")
    QTimer.singleShot(3000, step10_capture_no_project)


def step10_capture_no_project():
    _capture("tasks_no_project.png")
    QTimer.singleShot(300, finish)


def finish():
    print("=== CAPTURES ===", flush=True)
    for p in sorted(CAPTURES_DIR.glob("*.png")):
        print(f"  {p} ({p.stat().st_size} bytes)", flush=True)
    shutil.rmtree(SCRATCH, ignore_errors=True)
    os._exit(0)


QTimer.singleShot(1500, step1_setup)
app.exec()

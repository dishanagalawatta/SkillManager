# ruff: noqa: E402, ARG001
"""Real-app visual verification for the 2026-10-28 TODO batch.

Runs the REAL ``AppController`` and the REAL ``Main.qml`` in one process and
captures the live window with ``QWindow.grabWindow()`` (never the IPC
CommandChannel capture, which grabs the wrong region headless).

Captures:

1. ``todo_topbar_workbench.png`` — top bar after Snap moved next to Refresh
   and the nav renamed to Workbench / Hub.
2. ``todo_hub_installed.png``   — Hub bar, Installed tab (page actions).
3. ``todo_hub_discover.png``    — Hub bar, Discover tab (catalog search).
4. ``todo_hub_sync.png``        — Hub bar, Project Sync tab (Add Project).
5. ``todo_settings_clients.png``— Settings, Top Bar Clients (2 selectors + add).
6. ``todo_tasks_composer.png``  — Workbench task panel with the inline composer.

The app's own data directory is redirected to a scratch dir, so the user's
``config.json`` is never touched. Throwaway skills/projects are injected so
the rows render.

Run: uv run python scripts/verify_todo_ui_batch.py
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
SCRATCH = Path(tempfile.mkdtemp(prefix="skillmanager-todo-verify-"))
os.environ["SKILL_MANAGER_DATA_DIR"] = str(SCRATCH / "data")
os.environ.setdefault("QML_DISABLE_DISK_CACHE", "1")
os.environ["SKILL_MANAGER_DEV_MODE"] = "1"
os.environ["SKILL_MANAGER_MCP_NO_IPC"] = "1"


def watchdog(signum, frame):
    print(f"WATCHDOG: {time.monotonic() - START_TIME:.1f}s — forcing exit")
    os._exit(1)


signal.signal(signal.SIGALRM, watchdog)
signal.alarm(240)

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


def _make_project():
    """Build a throwaway project with skills and a couple of tasks."""
    proj = SCRATCH / "project"
    skills = proj / ".agents" / "skills"
    specs = [
        ("code-review", "Code Review", "Reviews a diff for correctness, naming and test gaps."),
        ("release-notes", "Release Notes", "Turns a git log into a formatted changelog."),
        ("refactor-plan", "Refactor Plan", "Drafts a staged refactor plan for a module."),
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
    proj = _make_project()
    controller._sources = [str(proj)]
    controller._projects = [str(proj)]
    controller._config.set("sources", [str(proj)])
    controller._config.set("projects", [str(proj)])
    controller.setCurrentProject(proj.name)
    controller.addProjectTask(str(proj), "Verify the new Hub bar", "high", "Tabs and actions.")
    controller.addProjectTask(str(proj), "Check the composer", "medium", "")
    _log("SETUP", f"injected project {proj}")
    controller.refreshSkills("verify", True)
    QTimer.singleShot(6000, step2_workbench)


def step2_workbench():
    window.navigateTo("QuickCopy")
    label = controller.config_controller.getProjectLabel(controller._projects[0])
    controller.setCurrentProject(label)
    _log(
        "PROJECT",
        f"current={controller.currentProject!r} "
        f"path={controller.config_controller.getProjectPath(label)!r}",
    )
    QTimer.singleShot(3500, step3_capture_workbench)


def step3_capture_workbench():
    _capture("todo_topbar_workbench.png")
    _log("PANEL", "opening the tasks panel")
    controller.ui_controller.setTasksPanelOpen(True)
    QTimer.singleShot(2000, step3b_draft_composer)


def step3b_draft_composer():
    """Type a multi-line draft and attach an image, then capture the composer."""
    proof = SCRATCH / "attachments"
    proof.mkdir(parents=True, exist_ok=True)
    shot = proof / "composer-proof.png"
    from PySide6.QtGui import QColor, QImage

    image = QImage(240, 160, QImage.Format.Format_RGB32)
    image.fill(QColor("#3B82F6"))
    image.save(str(shot))

    stored = controller.tasks.attachTaskImage(str(controller._projects[0]), str(shot))
    if stored:
        # Also attach one to a stored task so the row thumbnails are exercised.
        from skill_manager.core import tasks as task_store

        records = task_store.get_tasks(str(controller._projects[0]))
        if records:
            task_store.update_task(
                str(controller._projects[0]), records[0].id, attachments=[stored]
            )
            controller.tasks.refresh()

    editor = window.findChild(QObject, "taskComposerEditor")
    composer = window.findChild(QObject, "taskComposer")
    if editor is None or composer is None:
        _log("COMPOSER", f"not found (editor={editor}, composer={composer})")
    else:
        editor.setProperty(
            "text",
            "Make the task panel feel fast\n"
            "Notes on what to check:\n"
            "- panel opens without a hitch\n"
            "- attachments render as thumbnails\n",
        )
        if stored:
            composer.setProperty("attachments", [stored])
        _log("COMPOSER", f"draft set, attachments={[stored] if stored else []}")
    QTimer.singleShot(1500, step3c_capture_tasks)


def step3c_capture_tasks():
    _capture("todo_tasks_composer.png")
    _log("NAV", "navigating to Hub")
    controller.ui_controller.setTasksPanelOpen(False)
    window.navigateTo("Updates")
    QTimer.singleShot(3500, step4_capture_hub)


def _set_page(index):
    pages = window.findChild(QObject, "uv_pages")
    if pages is None:
        print("FIND FAILED: uv_pages")
        return False
    pages.setProperty("currentIndex", index)
    return True


def step4_capture_hub():
    _capture("todo_hub_installed.png")
    _log("TAB", f"discover -> {_set_page(1)}")
    QTimer.singleShot(1500, step5_capture_discover)


def step5_capture_discover():
    _capture("todo_hub_discover.png")
    _log("TAB", f"sync -> {_set_page(2)}")
    QTimer.singleShot(1500, step6_capture_sync)


def step6_capture_sync():
    _capture("todo_hub_sync.png")
    _log("NAV", "navigating to Settings")
    window.navigateTo("Settings")
    QTimer.singleShot(3500, step7_scroll_settings)


def _scroll_settings_to_clients():
    """Scroll the settings body so the Top Bar Clients block is on screen."""
    scroll = window.findChild(QObject, "settingsScroll")
    if scroll is None:
        _log("SCROLL", "settingsScroll not found")
        return False
    content = scroll.property("contentItem")
    if content is None:
        _log("SCROLL", "settingsScroll has no contentItem")
        return False
    content.setProperty("contentY", 330)
    _log("SCROLL", f"contentY={content.property('contentY')}")
    return True


def step7_scroll_settings():
    scrolled = _scroll_settings_to_clients()
    _log("SCROLL", f"scrolled={scrolled}")
    QTimer.singleShot(1500, step8_capture_settings)


def step8_capture_settings():
    _capture("todo_settings_clients.png")
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

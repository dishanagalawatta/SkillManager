# ruff: noqa: E402, ARG001
"""Real-app visual verification for the unified command workflow.

Runs the REAL ``AppController`` and the REAL ``Main.qml`` in one process and
captures the live window with ``QWindow.grabWindow()``.

Captures:

1. ``command_library.png``      — Library view with the project's command.
2. ``command_create_dialog.png``— the simplified Create/Edit Command dialog
   (the project selector must be gone and the layout must be clean).
3. ``command_update_confirm.png``— the copy-confirmation dialog shown when a
   selected command already exists in the target project.
4. ``command_carry_skills.png`` — the skill-carry prompt for the deployed
   command that references a skill the target project does not have.

Run: uv run python scripts/verify_command_workflow_real.py
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

# Keep the app's own artifacts out of the user's real data directory.
SCRATCH = Path(tempfile.mkdtemp(prefix="skillmanager-command-verify-"))
os.environ["SKILL_MANAGER_DATA_DIR"] = str(SCRATCH / "data")
os.environ.setdefault("QML_DISABLE_DISK_CACHE", "1")
os.environ["SKILL_MANAGER_DEV_MODE"] = "1"
os.environ["SKILL_MANAGER_MCP_NO_IPC"] = "1"


def watchdog(signum, frame):
    print(f"WATCHDOG: {time.monotonic() - START_TIME:.1f}s — forcing exit", flush=True)
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
    """Build a library skill, a project command, and a second project.

    The command references ``/helper-skill``; the skill lives in the library
    source but in NEITHER project, so the carry prompt must fire.
    """
    source = SCRATCH / "source"
    helper = source / "helper-skill"
    helper.mkdir(parents=True)
    (helper / "SKILL.md").write_text(
        "---\nname: Helper Skill\ndescription: A helper the command depends on.\n---\n\n# Helper\n",
        encoding="utf-8",
    )

    project_a = SCRATCH / "projectA"
    # A project is only discovered when it holds at least one skill, so the
    # fixture gives it a local skill next to the command.
    local_skill = project_a / ".agents" / "skills" / "local-helper"
    local_skill.mkdir(parents=True)
    (local_skill / "SKILL.md").write_text(
        "---\nname: Local Helper\ndescription: A skill that already lives in the project.\n---\n\n"
        "# Local\n",
        encoding="utf-8",
    )
    commands = project_a / ".agents" / "commands"
    commands.mkdir(parents=True)
    (commands / "deploy.md").write_text(
        "---\nname: deploy\ncategory: Commands\ntype: command\n---\n\n"
        "Run the release with /helper-skill first.\n",
        encoding="utf-8",
    )

    # A second project that already holds a command with the same name, so
    # the Library copy flow hits the conflict path.
    project_b = SCRATCH / "projectB"
    local_skill_b = project_b / ".agents" / "skills" / "local-helper"
    local_skill_b.mkdir(parents=True)
    (local_skill_b / "SKILL.md").write_text(
        "---\nname: Local Helper\ndescription: A skill that already lives in the project.\n---\n\n"
        "# Local\n",
        encoding="utf-8",
    )
    commands_b = project_b / ".agents" / "commands"
    commands_b.mkdir(parents=True)
    (commands_b / "deploy.md").write_text(
        "---\nname: deploy\ncategory: Commands\ntype: command\n---\n\n"
        "Older project version — still references /helper-skill.\n",
        encoding="utf-8",
    )
    return source, project_a, project_b


def step1_setup():
    source, project_a, project_b = _make_fixture()
    controller._sources = [str(source)]
    controller._projects = [str(project_a), str(project_b)]
    controller._config.set("sources", [str(source)])
    controller._config.set("projects", [str(project_a), str(project_b)])

    from skill_manager.core.quick_copy import project_label

    controller._current_project_label = project_label(project_a)
    controller._set_current_project(project_label(project_a))

    _log("SETUP", f"source={source} projects={[str(project_a), str(project_b)]}")
    controller.refreshSkills("verify", True)
    QTimer.singleShot(7000, step2_show_commands)


def step2_show_commands():
    """The Library lists package skills by default; show project commands."""
    controller._library_model.isPackageOnly = False
    controller._library_model.showCommands = True
    _log("SETUP", f"library rows={controller.libraryModel.rowCount()}")
    QTimer.singleShot(3000, step3_capture_library)


def step3_capture_library():
    _capture("command_library.png")
    _log("NAV", "opening the Create Command dialog")
    dialog = window.findChild(QObject, "commandCreateDialog")
    if dialog is None:
        print("DIALOG WARNING: commandCreateDialog not found", flush=True)
        finish()
        return
    dialog.metaObject().invokeMethod(dialog, "openWithContext")
    QTimer.singleShot(2500, step4_capture_create_dialog)


def step4_capture_create_dialog():
    _capture("command_create_dialog.png")
    QTimer.singleShot(300, step5_close_dialog)


def step5_close_dialog():
    dialog = window.findChild(QObject, "commandCreateDialog")
    if dialog is not None:
        dialog.metaObject().invokeMethod(dialog, "close")
    QTimer.singleShot(1200, step6_select_command)


def step6_select_command():
    """Select the project command in the Library."""
    model = controller.libraryModel
    target = None
    target_row = -1
    for row in range(model.rowCount()):
        entry = model.get_skill_at(row)
        if entry.get("is_command"):
            target = entry.get("local_path")
            target_row = row
            break
    _log("SETUP", f"selecting command {target} (row {target_row})")
    if target_row >= 0:
        model.toggleSelection(target_row)
    _log("SETUP", f"selected paths={model.getSelectedPaths()}")
    QTimer.singleShot(1500, step7_trigger_copy)


def step7_trigger_copy():
    """Copy the selection into project B, where the command already exists."""
    from skill_manager.core.quick_copy import project_label

    project_b = SCRATCH / "projectB"
    controller._set_current_project(project_label(project_b))
    _log("COPY", f"copying selection to {project_b}")
    controller.ops_controller.copySelectedSkillsToProject(str(project_b))
    QTimer.singleShot(3000, step8_capture_update_confirm)


def step8_capture_update_confirm():
    _capture("command_update_confirm.png")
    QTimer.singleShot(500, step9_confirm_overwrite)


def step9_confirm_overwrite():
    """Choose "Update Existing & Copy New" and let the copy run.

    The deployed command references /helper-skill, which project B does not
    have, so the skill-carry prompt must appear.
    """
    import json

    project_a = SCRATCH / "projectA"
    project_b = SCRATCH / "projectB"
    # The Library's canonical command is the one in project A; it is the
    # source that replaces project B's older copy.
    cmd_path = str(project_a / ".agents" / "commands" / "deploy.md")
    _log("COPY", "confirming 'Update Existing & Copy New'")
    controller.ops_controller.confirmCommandCopyWithOverwrite(
        str(project_b), json.dumps([cmd_path]), True
    )
    QTimer.singleShot(3500, step10_capture_carry)


def step10_capture_carry():
    _capture("command_carry_skills.png")
    QTimer.singleShot(300, finish)


def finish():
    print("=== CAPTURES ===", flush=True)
    for p in sorted(CAPTURES_DIR.glob("*.png")):
        print(f"  {p} ({p.stat().st_size} bytes)", flush=True)
    shutil.rmtree(SCRATCH, ignore_errors=True)
    os._exit(0)


QTimer.singleShot(1500, step1_setup)
app.exec()

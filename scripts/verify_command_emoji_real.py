"""Real-app visual verification for the 📜 default command icon.

Captures from the REAL app process (the same ``AppController`` and QML the app
runs), never from ad-hoc QML:

1. ``command_emoji_library.png`` — Library rows for a project command, which
   must show 📜 in the row glyph.
2. ``command_emoji_library_light.png`` — the same rows in light mode.
3. ``command_emoji_dialog.png`` — the Create Command dialog, whose emoji button
   starts on the default 📜 and hides "Reset Emoji".
4. ``command_emoji_picker.png`` — the emoji picker opened from that dialog:
   "Default: 📜" in the footer and 📜 as the first catalog tile.

Run:
    uv run python scripts/verify_command_emoji_real.py
"""

import os
import signal
import sys
import tempfile
import time
from pathlib import Path

CAPTURES_DIR = Path("data/mcp/captures")
START_TIME = time.monotonic()

# Keep the app's own artifacts out of the user's real data directory.
SCRATCH = Path(tempfile.mkdtemp(prefix="skillmanager-command-emoji-"))
os.environ["SKILL_MANAGER_DATA_DIR"] = str(SCRATCH / "data")
os.environ.setdefault("QML_DISABLE_DISK_CACHE", "1")
os.environ["SKILL_MANAGER_DEV_MODE"] = "1"
os.environ["SKILL_MANAGER_MCP_NO_IPC"] = "1"


def watchdog(signum, frame):
    print(f"WATCHDOG: {time.monotonic() - START_TIME:.1f}s — forcing exit", flush=True)
    os._exit(1)


signal.signal(signal.SIGALRM, watchdog)
signal.alarm(180)

# Clean stale captures BEFORE the run so no old screenshot can be misread.
CAPTURES_DIR.mkdir(parents=True, exist_ok=True)
for stale in CAPTURES_DIR.glob("command_emoji_*.png"):
    stale.unlink()

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


def _find_command_dialog():
    return window.findChild(QObject, "commandCreateDialog")


def _find_emoji_picker(scope):
    for child in scope.findChildren(QObject):
        if "EmojiPicker" in child.metaObject().className():
            return child
    return None


def step1_setup():
    source = SCRATCH / "source"
    helper = source / "helper-skill"
    helper.mkdir(parents=True)
    (helper / "SKILL.md").write_text(
        "---\nname: Helper Skill\ndescription: A library skill.\n---\n\n# Helper\n",
        encoding="utf-8",
    )

    project = SCRATCH / "project"
    local_skill = project / ".agents" / "skills" / "local-helper"
    local_skill.mkdir(parents=True)
    (local_skill / "SKILL.md").write_text(
        "---\nname: Local Helper\ndescription: A project skill.\n---\n\n# Local\n",
        encoding="utf-8",
    )
    commands = project / ".agents" / "commands"
    commands.mkdir(parents=True)
    (commands / "deploy.md").write_text(
        "---\nname: deploy\ncategory: Commands\ntype: command\n---\n\n"
        "Run the release with /helper-skill first.\n",
        encoding="utf-8",
    )

    controller._sources = [str(source)]
    controller._projects = [str(project)]
    controller._config.set("sources", [str(source)])
    controller._config.set("projects", [str(project)])

    from skill_manager.core.quick_copy import project_label

    controller._current_project_label = project_label(project)
    controller._set_current_project(project_label(project))

    _log("SETUP", f"source={source} project={project}")
    controller.refreshSkills("verify", True)
    QTimer.singleShot(7000, step2_show_commands)


def step2_show_commands():
    controller._library_model.isPackageOnly = False
    controller._library_model.showCommands = True
    rows = controller.libraryModel.rowCount()
    _log("SETUP", f"library rows={rows}")
    QTimer.singleShot(3000, step3_capture_library)


def step3_capture_library():
    _capture("command_emoji_library.png")
    QTimer.singleShot(500, step4_capture_light)


def step4_capture_light():
    controller.ui_controller.darkMode = False
    QTimer.singleShot(2500, step5_capture_light)


def step5_capture_light():
    _capture("command_emoji_library_light.png")
    controller.ui_controller.darkMode = True
    QTimer.singleShot(1500, step6_open_dialog)


def step6_open_dialog():
    dialog = _find_command_dialog()
    if dialog is None:
        print("DIALOG WARNING: commandCreateDialog not found", flush=True)
        finish()
        return
    dialog.metaObject().invokeMethod(dialog, "openWithContext")
    QTimer.singleShot(2500, step7_capture_dialog)


def step7_capture_dialog():
    _capture("command_emoji_dialog.png")
    picker = _find_emoji_picker(_find_command_dialog() or window)
    if picker is None:
        print("PICKER WARNING: EmojiPicker not found", flush=True)
        QTimer.singleShot(300, finish)
        return
    _log("PICKER", f"className={picker.metaObject().className()}")
    picker.metaObject().invokeMethod(picker, "open")
    _log("PICKER", f"after open: visible={picker.property('visible')!r}")
    QTimer.singleShot(2500, step8_capture_picker)


def step8_capture_picker():
    picker = _find_emoji_picker(_find_command_dialog() or window)
    if picker is not None:
        _log("PICKER", f"before capture: visible={picker.property('visible')!r}")
        picker.setProperty("visible", True)
    QTimer.singleShot(600, step8b_capture_picker)


def step8b_capture_picker():
    _capture("command_emoji_picker.png")
    QTimer.singleShot(300, finish)


def finish():
    dialog = _find_command_dialog()
    if dialog is not None:
        dialog.metaObject().invokeMethod(dialog, "close")
    _log("DONE", f"captures in {CAPTURES_DIR}")
    controller.on_quit()
    app.quit()


QTimer.singleShot(0, step1_setup)
app.exec()

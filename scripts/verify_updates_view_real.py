# ruff: noqa: E402, ARG001
"""Real-app visual verification for the Skill Packages workflow (Sync & Updates).

Captures, from the REAL app process (same AppController the app runs):

1. ``updates_view.png``       — Updates view, dark mode, with a package whose
   version check failed: the "· could not check" caption, the warning retry
   button, and the header's "N unchecked" count must all render un-clipped.
2. ``updates_view_light.png`` — same view in light mode (Theme.warning is a
   different colour there, so contrast must be re-checked).
3. ``updates_dialog.png``     — PackageEditDialog with a repo URL typed in, so
   the asynchronous Verify button renders in its enabled state.

Run: uv run python scripts/verify_updates_view_real.py
"""

import os
import signal
import sys
import time
from pathlib import Path

CAPTURES_DIR = Path("data/mcp/captures")
CAPTURES_DIR.mkdir(parents=True, exist_ok=True)

START_TIME = time.monotonic()


def watchdog(signum, frame):
    print(f"WATCHDOG: {time.monotonic() - START_TIME:.1f}s — forcing exit")
    os._exit(1)


signal.signal(signal.SIGALRM, watchdog)
signal.alarm(90)

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
if window:
    window.show()
    window.raise_()

if not engine.rootObjects():
    print("FATAL: No QML root objects!")
    sys.exit(1)


def _log(step, message):
    print(f"[+{time.monotonic() - START_TIME:.1f}s] {step}: {message}")


def _capture(name):
    path = str(CAPTURES_DIR / name)
    _log(
        "CAPTURE-DIAG",
        f"{name} opacity={window.property('opacity')} active={window.property('active')} "
        f"visibility={window.property('visibility')}",
    )
    window.grabWindow().save(path)
    _log("CAPTURE", path)


def _mark_failed_checks():
    """Put a package into the "could not check" state, in memory only.

    Deliberately does not touch the on-disk config: the app's own data must
    not be rewritten just to take a screenshot.
    """
    packages = controller._update_packages
    _log("SETUP", f"{len(packages)} package(s) in config")
    if not packages:
        print("SETUP WARNING: no packages configured — badge/banner will not render")
        return

    first = packages[0]
    first["check_status"] = "failed"
    first["check_error"] = "could not resolve host: git.invalid"
    if not first.get("current_version"):
        first["current_version"] = "1.0.0"
    if len(packages) > 1:
        packages[1]["check_status"] = "failed"
        packages[1]["check_error"] = "network unreachable"

    controller.updatePackagesChanged.emit()
    controller.update_controller.recalculateStats()
    _log("SETUP", f"statsUnchecked={controller.statsUnchecked}")


def step1_show_updates():
    _mark_failed_checks()
    _log("NAV", "navigating to Sync & Updates")
    window.navigateTo("Updates")
    QTimer.singleShot(3000, step2_capture_dark)


def step2_capture_dark():
    _capture("updates_view.png")
    _log("THEME", "switching to light mode")
    controller.ui_controller.darkMode = False
    QTimer.singleShot(2500, step3_capture_light)


def step3_capture_light():
    _capture("updates_view_light.png")
    _log("THEME", "restoring dark mode")
    controller.ui_controller.darkMode = True
    QTimer.singleShot(1500, step4_open_dialog)


def step4_open_dialog():
    from PySide6.QtCore import Q_ARG

    dialog = window.findChild(QObject, "uv_packageEditDialog")
    if dialog is None:
        print("DIALOG WARNING: uv_packageEditDialog not found")
        finish()
        return

    dialog.setProperty("editIndex", -1)
    dialog.metaObject().invokeMethod(dialog, "open")

    # Load a git package exactly the way the row's Edit button does, so the
    # repository field is populated and the (now asynchronous) Verify button
    # renders in its enabled state.
    package = {
        "name": "Example Skills",
        "source_type": "git",
        "repository_url": "https://github.com/example/skills.git",
        "current_version": "1.0.0",
        "latest_version": "1.0.0",
    }
    loaded = dialog.metaObject().invokeMethod(dialog, "loadPackage", Q_ARG("QVariant", package))
    _log("DIALOG", f"loadPackage invoked={loaded}")

    QTimer.singleShot(2500, step5_capture_dialog)


def step5_capture_dialog():
    _capture("updates_dialog.png")
    QTimer.singleShot(500, step6_run_verify)


def step6_run_verify():
    """Exercise the asynchronous Verify path against an unreachable repo.

    This drives the controller's real probe and the dialog's Connections
    handler; the result must arrive as an inline message with the dialog
    still open (it used to block the GUI thread and report nothing).
    """
    dialog = window.findChild(QObject, "uv_packageEditDialog")
    if dialog is None:
        finish()
        return

    url = "https://github.com/opencode-does-not-exist/nope-nope.git"
    results = []

    def on_finished(finished_url, tag, error):
        results.append((finished_url, tag, error))
        _log("VERIFY", f"signal url={finished_url!r} tag={tag!r} error={error!r}")

    controller.config_controller.gitVerificationFinished.connect(on_finished)

    # Same state the Verify button sets before calling the controller.
    dialog.setProperty("verifyingField", "repo")
    dialog.setProperty("verifyingUrl", url)
    status = dialog.findChild(QObject, "pkgVerifyStatus")
    if status is not None:
        status.setProperty("text", "Validating...")

    _log("VERIFY", "starting asynchronous verify")
    controller.config_controller.verifyGitPackage(url, "")

    QTimer.singleShot(12000, lambda: step7_capture_verify(status, results))


def step7_capture_verify(status, results):
    if status is not None:
        _log("VERIFY", f"inline status text={status.property('text')!r}")
    _log("VERIFY", f"received {len(results)} result(s)")
    _capture("updates_dialog_verify.png")
    # grabWindow can catch a mid-fade composited frame; take a settled one too.
    QTimer.singleShot(2500, step8_capture_verify_settled)


def step8_capture_verify_settled():
    _capture("updates_dialog_verify_settled.png")
    QTimer.singleShot(1500, step9_control_capture)


def step9_control_capture():
    """Control: close the dialog and grab the plain view at the same offset.

    If this frame is dimmed too, the dimming is an environment/compositor
    artefact rather than something the dialog introduced.
    """
    dialog = window.findChild(QObject, "uv_packageEditDialog")
    if dialog is not None:
        dialog.setProperty("visible", False)
    _log("CONTROL", f"isLoading={controller.isLoading}")
    QTimer.singleShot(1500, step10_control_shot)


def step10_control_shot():
    _capture("updates_view_late_control.png")
    finish()


def finish():
    signal.alarm(0)
    _log("DONE", "verification completed cleanly")
    QTimer.singleShot(100, app.quit)


QTimer.singleShot(5000, step1_show_updates)
app.exec()
_log("EXIT", "verification process finished")

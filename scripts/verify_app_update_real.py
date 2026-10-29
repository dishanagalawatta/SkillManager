# ruff: noqa: E402, ARG001
"""Real-app visual verification for the in-app SkillManager self-update UI.

Captures from the REAL app process (the same ``AppController``/QML the app
runs), never from ad-hoc QML:

1. ``app_update_settings.png``        — Settings → About with a release
   available. Shows the AppUpdateCard (version delta, View Release, primary
   action) and the platform reason when self-install is unavailable.
2. ``app_update_settings_progress.png`` — the same card with a download in
   flight (ASCII-only capture when the forced kind supports installs).
3. ``app_update_settings_error.png``  — checksum/install failure text.
4. ``app_update_toast.png``           — the release toast with View Release +
   Update Now.
5. ``app_update_hub.png``             — Updates hub banner above the package
   workflow.

``APP_UPDATE_FORCE_KIND=appimage`` forces the AppImage install context *before*
the QML loads (the controller's install-kind properties are constant), so the
supported branch renders. Without it, the real dev/source context renders,
which must explain why self-install is unavailable.

Run:
    APP_UPDATE_FORCE_KIND=appimage uv run python scripts/verify_app_update_real.py
    uv run python scripts/verify_app_update_real.py
"""

import os
import signal
import sys
import time
from pathlib import Path

CAPTURES_DIR = Path("data/mcp/captures")
CAPTURES_DIR.mkdir(parents=True, exist_ok=True)
for stale in CAPTURES_DIR.glob("app_update_*.png"):
    stale.unlink()

START_TIME = time.monotonic()
FORCE_KIND = os.environ.get("APP_UPDATE_FORCE_KIND", "").strip().lower()


def watchdog(signum, frame):
    print(f"WATCHDOG: {time.monotonic() - START_TIME:.1f}s — forcing exit")
    os._exit(1)


signal.signal(signal.SIGALRM, watchdog)
signal.alarm(120)

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

if FORCE_KIND == "appimage":
    from skill_manager.core.app_update_service import InstallContext, InstallKind

    target = Path.home() / ".local" / "bin" / "skill-manager"
    controller.app_update_controller._context = InstallContext(
        InstallKind.APPIMAGE,
        target=target,
        executable=target,
        supported=True,
    )
    print(f"[SETUP] forced install context: AppImage -> {target}")

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
    window.grabWindow().save(path)
    _log("CAPTURE", path)


def _controller():
    return controller.app_update_controller


def _mark_update_available():
    c = _controller()
    c.state.update_available = True
    c.state.latest_version = "9.9.9"
    c.state.has_checked = True
    c.updateAvailableChanged.emit()
    c.latestVersionChanged.emit()
    c.updateStateChanged.emit()
    _log(
        "SETUP",
        f"update_available=True latest=9.9.9 kind={c.installKind} supported={c.selfUpdateSupported}",
    )


def _find_settings_root():
    """Locate the SettingsView root after the Loader has materialised it."""
    card = window.findChild(QObject, "settingsAppUpdateCard")
    if card is None:
        return None, None
    obj = card
    for _ in range(12):
        obj = obj.parent()
        if obj is None:
            break
        if obj.property("settingsTab") is not None:
            return obj, card
    return None, card


def step1_navigate_settings():
    _log("NAV", "navigating to Settings")
    window.navigateTo("Settings")
    _mark_update_available()
    QTimer.singleShot(2500, step2_show_about)


def step2_show_about():
    root, card = _find_settings_root()
    if root is None:
        print("SETUP WARNING: SettingsView root not found")
        step3_capture_settings()
        return
    root.setProperty("settingsTab", 2)
    _log("NAV", "Settings → About selected")
    QTimer.singleShot(3000, step3_capture_settings)


def step3_capture_settings():
    _capture("app_update_settings.png")
    if FORCE_KIND == "appimage":
        QTimer.singleShot(1200, step4_show_progress)
    else:
        QTimer.singleShot(1200, step5_show_error)


def step4_show_progress():
    c = _controller()
    c.state.is_downloading = True
    c.state.download_progress = 42
    c.state.downloaded_bytes = 35 * 1024 * 1024
    c.state.download_total_bytes = 83 * 1024 * 1024
    c.downloadStateChanged.emit()
    c.updateStateChanged.emit()
    _log("SETUP", "simulated download 42%")
    QTimer.singleShot(2500, step4b_capture_progress)


def step4b_capture_progress():
    _capture("app_update_settings_progress.png")
    c = _controller()
    c.state.is_downloading = False
    c.state.download_progress = 0
    c.state.downloaded_bytes = 0
    c.state.download_total_bytes = 0
    c.downloadStateChanged.emit()
    QTimer.singleShot(1000, step5_show_error)


def step5_show_error():
    c = _controller()
    c.state.install_error = (
        "Checksum mismatch — the downloaded update is corrupt or was tampered with. "
        "Refusing to install."
    )
    c.installStateChanged.emit()
    c.updateStateChanged.emit()
    _log("SETUP", "simulated checksum failure")
    QTimer.singleShot(2000, step6_capture_error)


def step6_capture_error():
    _capture("app_update_settings_error.png")
    _controller().state.install_error = None
    _controller().installStateChanged.emit()
    QTimer.singleShot(1000, step7_show_toast)


def step7_show_toast():
    toast = window.findChild(QObject, "updateToast")
    if toast is None:
        print("SETUP WARNING: updateToast not found")
        QTimer.singleShot(500, step8_show_hub)
        return
    toast.setProperty("toastTitle", "App update available")
    toast.setProperty(
        "toastMessage",
        "SkillManager v9.9.9 is available.",
    )
    toast.setProperty("showAction", True)
    toast.setProperty("actionMode", "release")
    toast.setProperty("visible", True)
    _log("SETUP", "release toast shown")
    QTimer.singleShot(2000, step7b_capture_toast)


def step7b_capture_toast():
    _capture("app_update_toast.png")
    toast = window.findChild(QObject, "updateToast")
    if toast is not None:
        btn = toast.findChild(QObject, "updateToastActionBtn")
        _log(
            "TOAST",
            f"actionMode={toast.property('actionMode')!r} "
            f"showAction={toast.property('showAction')!r} "
            f"btnVisible={btn.property('visible') if btn is not None else None!r} "
            f"supported={_controller().selfUpdateSupported!r}",
        )
        toast.setProperty("visible", False)
    QTimer.singleShot(800, step8_show_hub)


def step8_show_hub():
    _log("NAV", "navigating to Updates")
    window.navigateTo("Updates")
    QTimer.singleShot(3000, step9_capture_hub)


def step9_capture_hub():
    _capture("app_update_hub.png")
    _log("THEME", "switching to light mode for contrast")
    controller.ui_controller.darkMode = False
    QTimer.singleShot(2500, step10_capture_hub_light)


def step10_capture_hub_light():
    _capture("app_update_hub_light.png")
    controller.ui_controller.darkMode = True
    QTimer.singleShot(800, finish)


def finish():
    signal.alarm(0)
    _log("DONE", "verification completed cleanly")
    QTimer.singleShot(100, app.quit)


QTimer.singleShot(5000, step1_navigate_settings)
app.exec()
_log("EXIT", "verification process finished")

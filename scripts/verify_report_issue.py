"""
Verification for Report Issue UI (DiagnosticsPane + SettingsView About card).

REAL-APP ONLY procedure (per AGENTS.md rule #6):
  - Boots the real AppController + real Main.qml in-process (no inline QML,
    no /tmp/*.qml, no ad-hoc QQmlApplicationEngine content).
  - Navigates to Settings > About, enables diagnostic logging, expands the
    Diagnostics pane, fills the Report Issue fields, waits for QML to settle.
  - Captures via QWindow.grabWindow (internal scene-graph render).
  - Also captures Library + QuickCopy to prove they are unaffected.
  - Cleans data/mcp/captures/ BEFORE the run so no stale shots are analyzed.

Run: uv run python scripts/verify_report_issue.py
"""

import os
import signal
import sys
import time
from pathlib import Path

START_TIME = time.monotonic()


def log(msg):
    print(f"[+{time.monotonic() - START_TIME:.1f}s] {msg}", flush=True)


def watchdog(signum, frame):
    log(f"WATCHDOG: {time.monotonic() - START_TIME:.1f}s — forcing exit")
    os._exit(1)


signal.signal(signal.SIGALRM, watchdog)
signal.alarm(120)

CAPTURES_DIR = Path("data/mcp/captures")
CAPTURES_DIR.mkdir(parents=True, exist_ok=True)

# Clean stale captures BEFORE the run (rule 6e).
for f in CAPTURES_DIR.glob("*.png"):
    try:
        f.unlink()
    except Exception:
        pass
log("Cleaned data/mcp/captures/")

os.environ.setdefault("QML_DISABLE_DISK_CACHE", "1")
os.environ["SKILL_MANAGER_DEV_MODE"] = "1"
os.environ["SKILL_MANAGER_TESTING"] = "1"

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

if not engine.rootObjects():
    log("FATAL: No QML root objects — Main.qml failed to load (check QML errors above)")
    sys.exit(1)

window = next((o for o in engine.rootObjects() if hasattr(o, "show")), None)
if window:
    window.setProperty("width", 1280)
    window.setProperty("height", 900)
    window.show()
    window.raise_()


def find_settings_root():
    for child in window.findChildren(QObject):
        if child.metaObject().indexOfProperty("settingsTab") >= 0:
            return child
    return None


def find_diagnostics_pane():
    pill = window.findChild(QObject, "diagnosticsGlassPill")
    if pill is None:
        return None
    # DiagnosticsPane is the direct QML child of the pill; it owns "expanded".
    for child in pill.children():
        if isinstance(child, QObject) and child.metaObject().indexOfProperty("expanded") >= 0:
            return child
    for desc in pill.findChildren(QObject):
        if (
            desc.metaObject().indexOfProperty("expanded") >= 0
            and desc.metaObject().indexOfProperty("reportSummary") >= 0
        ):
            return desc
    return None


def scroll_about_down():
    count = 0
    for child in window.findChildren(QObject):
        try:
            if (
                child.metaObject().indexOfProperty("contentY") >= 0
                and child.metaObject().indexOfProperty("contentHeight") >= 0
            ):
                try:
                    ch = float(child.property("contentHeight") or 0)
                    h = float(child.property("height") or 0)
                    if ch > h:
                        child.setProperty("contentY", max(0.0, ch - h))
                        count += 1
                except Exception:
                    pass
        except Exception:
            pass
    log(f"Scrolled {count} flickable(s) to bottom")


def grab(tag):
    path = str(CAPTURES_DIR / f"{tag}.png")
    img = window.grabWindow()
    if img.isNull():
        log(f"GRAB[{tag}]: null image!")
        return
    img.save(path)
    log(f"SAVED: {path} ({img.width()}x{img.height()})")


def step1_settings_about():
    log("Navigating to Settings > About, enabling diagnostic logging...")
    try:
        window.navigateTo("Settings")
    except Exception as e:
        log(f"navigateTo failed: {e}")
    controller.ui_controller.currentView = "Settings"
    try:
        controller.config_controller.diagnosticLogging = True
    except Exception as e:
        log(f"diagnosticLogging enable failed: {e}")
    QTimer.singleShot(1500, step2_expand_diagnostics)


def step2_expand_diagnostics():
    sv = find_settings_root()
    if sv is not None:
        sv.setProperty("settingsTab", 2)
        log("settingsTab -> About(2)")
    else:
        log("WARN: SettingsView root (settingsTab) not found")
    QTimer.singleShot(1200, step3_fill_report)


def step3_fill_report():
    pane = find_diagnostics_pane()
    if pane is None:
        log("WARN: diagnosticsPane not found (pill hidden?)")
    else:
        pane.setProperty("expanded", True)
        pane.setProperty("reportSummary", "Sync fails on large library")
        pane.setProperty(
            "reportDescription", "Steps: open Library, press Sync All, counts look stale."
        )
        log(
            "Diagnostics expanded; report fields filled; "
            f"implicitHeight={pane.property('implicitHeight')}"
        )
    # Wait >=3s for QML to settle (rule 6c), then scroll + capture.
    QTimer.singleShot(3500, step4_capture_diagnostics)


def step4_capture_diagnostics():
    grab("verify_report_issue_about_top")
    scroll_about_down()
    QTimer.singleShot(800, step5_shoot_diagnostics)


def step5_shoot_diagnostics():
    grab("verify_report_issue_diagnostics")
    log("Capturing Library (unaffected check)...")
    try:
        window.navigateTo("Library")
    except Exception as e:
        log(f"navigateTo Library failed: {e}")
    controller.ui_controller.currentView = "Library"
    QTimer.singleShot(2500, step6_shoot_library)


def step6_shoot_library():
    grab("verify_report_issue_library")
    log("Capturing QuickCopy (unaffected check)...")
    try:
        window.navigateTo("QuickCopy")
    except Exception as e:
        log(f"navigateTo QuickCopy failed: {e}")
    controller.ui_controller.currentView = "QuickCopy"
    QTimer.singleShot(2500, step7_shoot_quickcopy)


def step7_shoot_quickcopy():
    grab("verify_report_issue_quickcopy")
    signal.alarm(0)
    QTimer.singleShot(100, app.quit)


QTimer.singleShot(1000, step1_settings_about)
app.exec()
log("Done.")

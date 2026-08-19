"""
Verification script for PackageEditDialog ("Edit Skill Package").
Opens PackageEditDialog in the real app and captures screenshot via QWindow.grabWindow().
"""

import os
import shutil
import signal
import sys
import time
from pathlib import Path

START_TIME = time.monotonic()


def watchdog_timeout(signum, frame):
    print(f"WATCHDOG: {time.monotonic() - START_TIME:.1f}s — forcing exit")
    os._exit(1)


signal.signal(signal.SIGALRM, watchdog_timeout)
signal.alarm(40)

# Mandatory Rule #6: Clean all captures from data/mcp/captures/ BEFORE run
CAPTURES_DIR = Path("data/mcp/captures")
if CAPTURES_DIR.exists():
    shutil.rmtree(CAPTURES_DIR)
CAPTURES_DIR.mkdir(parents=True, exist_ok=True)

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


def step1_wait():
    print(f"[+{time.monotonic() - START_TIME:.1f}s] Waiting for main app to settle...")
    QTimer.singleShot(2500, step2_open_package_edit_dialog)


def step2_open_package_edit_dialog():
    print(f"[+{time.monotonic() - START_TIME:.1f}s] Switching view to Updates & Opening Add Skill Package dialog to test auto-detection...")
    controller.ui_controller.currentView = "Updates"

    def find_dialog(obj):
        if not obj:
            return None
        if hasattr(obj, "objectName") and obj.objectName() == "uv_packageEditDialog":
            return obj
        if "PackageEditDialog" in str(obj.metaObject().className()):
            return obj
        for child in obj.children():
            res = find_dialog(child)
            if res:
                return res
        return None

    global dlg
    dlg = find_dialog(window)
    if dlg and hasattr(dlg, "handlePackageInputChanged") and hasattr(dlg, "open"):
        dlg.editIndex = -1
        dlg.open()
        # Test real-time auto-detection by passing typed package input
        dlg.handlePackageInputChanged("npx skills add vercel-labs/find-skills")
        print("Tested live auto-detection with 'npx skills add vercel-labs/find-skills'.")
    else:
        print("ERR: Could not locate PackageEditDialog in QML tree!")

    QTimer.singleShot(2500, step2b_test_git_autodetect)


def step2b_test_git_autodetect():
    print(f"[+{time.monotonic() - START_TIME:.1f}s] Capturing NPX Auto-detection screenshot...")
    shot_path = CAPTURES_DIR / "verify_package_autodetect_npx.png"
    img = window.grabWindow()
    img.save(str(shot_path))
    print(f"SAVED SCREENSHOT TO: {shot_path.resolve()}")

    # Test auto-detecting GitHub repo from URL pasted into package input
    dlg.open()
    dlg.handlePackageInputChanged("https://github.com/sickn33/agentic-awesome-skills.git")
    print("Tested live auto-detection with Git URL.")
    QTimer.singleShot(2500, step3_take_shot_npx)


def step3_take_shot_npx():
    print(f"[+{time.monotonic() - START_TIME:.1f}s] Capturing Git Auto-detection screenshot...")
    shot_path = CAPTURES_DIR / "verify_package_autodetect_git.png"
    img = window.grabWindow()
    img.save(str(shot_path))
    print(f"SAVED SCREENSHOT TO: {shot_path.resolve()}")

    test_npx_pkg = {
        "name": "Find-Skills",
        "source_type": "npx",
        "package_name": "vercel-labs/find-skills",
        "repository_url": "",
        "github_token": "",
        "package_path": "/home/user/.agent/skills",
        "package_args": "",
        "update_command": "npx --yes -- vercel-labs/find-skills",
        "current_version_command": "",
        "latest_version_command": "",
    }
    if dlg and hasattr(dlg, "loadPackage"):
        dlg.loadPackage(test_npx_pkg)

    shot_path = CAPTURES_DIR / "verify_package_edit_npx.png"
    img = window.grabWindow()
    img.save(str(shot_path))
    print(f"SAVED SCREENSHOT TO: {shot_path.resolve()}")

    # Load NPX package with upstream override (automatically expands advanced overrides)
    test_npx_override_pkg = {
        "name": "Find-Skills",
        "source_type": "npx",
        "package_name": "vercel-labs/find-skills",
        "repository_url": "https://github.com/vercel-labs/skills",
        "github_token": "",
        "package_path": "/home/user/.agent/skills",
        "package_args": "--force --no-cache",
        "update_command": "npx --yes -- vercel-labs/find-skills --force --no-cache",
        "current_version_command": "",
        "latest_version_command": "",
    }
    if dlg and hasattr(dlg, "loadPackage"):
        dlg.loadPackage(test_npx_override_pkg)
    QTimer.singleShot(1500, step4_take_shot_npx_advanced)


def step4_take_shot_npx_advanced():
    print(f"[+{time.monotonic() - START_TIME:.1f}s] Capturing NPX Advanced dialog screenshot (scrolled)...")
    if dlg and hasattr(dlg, "scrollDown"):
        dlg.scrollDown(250)
        print("Called dlg.scrollDown(250).")

    shot_path = CAPTURES_DIR / "verify_package_edit_npx_advanced.png"
    img = window.grabWindow()
    img.save(str(shot_path))
    print(f"SAVED SCREENSHOT TO: {shot_path.resolve()}")



    # Switch to Git mode
    test_git_pkg = {
        "name": "agentic-awesome-skills",
        "source_type": "git",
        "package_name": "",
        "repository_url": "https://github.com/sickn33/agentic-awesome-skills",
        "github_token": "",
        "package_path": "/tmp/packages/agentic-awesome-skills",
        "package_args": "",
        "update_command": "",
        "current_version_command": "",
        "latest_version_command": "",
    }
    if dlg and hasattr(dlg, "loadPackage"):
        dlg.loadPackage(test_git_pkg)
    QTimer.singleShot(1500, step5_take_shot_git)



def step5_take_shot_git():
    print(f"[+{time.monotonic() - START_TIME:.1f}s] Capturing Git dialog screenshot (default auto-detected)...")
    if dlg and hasattr(dlg, "scrollDown"):
        dlg.scrollDown(0)

    shot_path = CAPTURES_DIR / "verify_package_edit_git.png"
    img = window.grabWindow()
    img.save(str(shot_path))
    print(f"SAVED SCREENSHOT TO: {shot_path.resolve()}")

    # Expand Git advanced
    if dlg and hasattr(dlg, "setAdvancedOverrides"):
        dlg.setAdvancedOverrides(True)
    QTimer.singleShot(1500, step6_take_shot_git_advanced)


def step6_take_shot_git_advanced():
    print(f"[+{time.monotonic() - START_TIME:.1f}s] Capturing Git dialog screenshot (advanced overrides)...")
    if dlg and hasattr(dlg, "scrollDown"):
        dlg.scrollDown(250)

    shot_path = CAPTURES_DIR / "verify_package_edit_git_advanced.png"
    img = window.grabWindow()
    img.save(str(shot_path))
    print(f"SAVED SCREENSHOT TO: {shot_path.resolve()}")

    # Switch to Custom mode
    test_custom_pkg = {
        "name": "Local-Custom-Script",
        "source_type": "custom",
        "package_name": "",
        "repository_url": "",
        "github_token": "",
        "package_path": "/tmp/packages/custom",
        "package_args": "",
        "update_command": "./build-skills.sh",
        "current_version_command": "./build-skills.sh --version",
        "latest_version_command": "./build-skills.sh --latest",
    }
    if dlg and hasattr(dlg, "loadPackage"):
        dlg.loadPackage(test_custom_pkg)
    QTimer.singleShot(1500, step7_take_shot_custom)


def step7_take_shot_custom():
    print(f"[+{time.monotonic() - START_TIME:.1f}s] Capturing Custom dialog screenshot...")
    if dlg and hasattr(dlg, "scrollDown"):
        dlg.scrollDown(0)

    shot_path = CAPTURES_DIR / "verify_package_edit_custom.png"
    img = window.grabWindow()
    img.save(str(shot_path))
    print(f"SAVED SCREENSHOT TO: {shot_path.resolve()}")

    signal.alarm(0)
    QTimer.singleShot(100, app.quit)


QTimer.singleShot(1000, step1_wait)
app.exec()

print(f"[+{time.monotonic() - START_TIME:.1f}s] Script complete.")


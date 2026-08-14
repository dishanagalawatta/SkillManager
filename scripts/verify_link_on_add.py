"""
Verification script for exact-match project-skill linking on project add.

Loads the REAL Main.qml through the REAL AppController in-process (same
pattern as verify_window_persistence.py). The environment must be pre-seeded
with an update-package record whose package source contains a skill with
content identical to a pre-existing skill in the added project. The script:
  1. asserts the skill is discovered without a manual refresh,
  2. asserts the background link task writes project_skill_ownership.json
     mapping the project folder to the package id,
  3. navigates to the Updates view and captures the rendered window.

Usage:
    uv run python scripts/verify_link_on_add.py --project <path>
    uv run python scripts/verify_link_on_add.py --project <path> --real-platform
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

captures_dir = Path("data/mcp/captures")
captures_dir.mkdir(parents=True, exist_ok=True)
for f in captures_dir.glob("*.png"):
    try:
        f.unlink()
    except Exception:
        pass

os.environ.setdefault("QML_DISABLE_DISK_CACHE", "1")
os.environ["SKILL_MANAGER_DEV_MODE"] = "1"
os.environ["SKILL_MANAGER_TESTING"] = "1"
os.environ["SKILL_MANAGER_DATA_DIR"] = str(Path.cwd() / "data")
if "--real-platform" not in sys.argv:
    os.environ["QT_QPA_PLATFORM"] = "offscreen"

import sentry_sdk

import skill_manager

sentry_sdk.init(
    dsn="",
    environment="development",
    release=f"skill-manager@{skill_manager.__version__}",
    default_integrations=False,
)

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtGui import QGuiApplication, QSurfaceFormat
from PySide6.QtQml import QQmlApplicationEngine, qmlRegisterSingletonInstance
from PySide6.QtQuickControls2 import QQuickStyle

from skill_manager.app import AppController
from skill_manager.controllers.font_database_bridge import FontDatabaseBridge
from skill_manager.core.resources import qml_components_dir

OWNERSHIP_FILE = Path("data/project_skill_ownership.json")
PACKAGE_ID = "test-pkg-v1"
EXPECTED_SKILL = "alpha"


def _pump(ms: int) -> None:
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def _capture(win, tag: str):
    """INTERNAL capture — grabWindow + normalize, same code as the fixed
    sm_screenshot tool. Renders the scene graph regardless of visibility."""
    from skill_manager.controllers.command_channel import _normalize_capture_image

    img = win.grabWindow()
    if img.isNull():
        print(f"[VERIFY] capture '{tag}': grabWindow returned null image")
        return None
    out = captures_dir / f"{tag}.png"
    if not _normalize_capture_image(img).save(str(out)):
        print(f"[VERIFY] capture '{tag}': save failed")
        return None
    print(f"[VERIFY] capture: {out} ({img.width()}x{img.height()})")
    return str(out)


def _skill_names(controller) -> list[str]:
    all_skills = getattr(controller.libraryModel, "_all_skills", None) or []
    return [getattr(s, "name", "") for s in all_skills]


def _wait_for_skill(controller, name: str, timeout_s: float = 90) -> bool:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if name in _skill_names(controller):
            return True
        _pump(200)
    return False


def _ownership_mapping() -> dict:
    if not OWNERSHIP_FILE.is_file():
        return {}
    try:
        return json.loads(OWNERSHIP_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def _wait_for_ownership(project_key: str, timeout_s: float = 30) -> bool:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        mapping = _ownership_mapping()
        if mapping.get(project_key, {}).get(EXPECTED_SKILL) == PACKAGE_ID:
            return True
        _pump(300)
    return False


def _run_verify(controller, win, args) -> None:
    try:
        controller.libraryModel.isPackageOnly = False
        _pump(300)
    except Exception as exc:  # noqa: BLE001
        print(f"[VERIFY] filter flip skipped: {exc}")

    before = _skill_names(controller)
    print(f"[VERIFY] pre-add skill count={len(before)}; '{EXPECTED_SKILL}' present: {EXPECTED_SKILL in before}")
    print(f"[VERIFY] pre-add ownership: {_ownership_mapping()}")

    controller.config_mgr.addProject(args.project)
    print(f"[VERIFY] addProject({args.project}) called — NO manual refresh issued")

    if not _wait_for_skill(controller, EXPECTED_SKILL):
        print(f"[VERIFY] FAIL: '{EXPECTED_SKILL}' NOT discovered within timeout")
        _pump(1500)
        _capture(win, "link_on_add_FAIL")
        win.close()
        sys.exit(1)
    print(f"[VERIFY] PASS: '{EXPECTED_SKILL}' discovered automatically after add")

    _pump(3000)
    _capture(win, "link_on_add_library_a")

    added_projects = [p for p in getattr(controller, "_projects", []) if "sm-validation" in p]
    if not added_projects:
        print(f"[VERIFY] FAIL: added project not in controller._projects: {controller._projects}")
        win.close()
        sys.exit(1)
    project_key = str(Path(added_projects[0]).resolve()).casefold()

    if not _wait_for_ownership(project_key):
        print(f"[VERIFY] FAIL: ownership not written for {project_key}; file={_ownership_mapping()}")
        _pump(1500)
        _capture(win, "link_on_add_FAIL")
        win.close()
        sys.exit(1)
    print(f"[VERIFY] PASS: ownership linked {project_key} -> '{EXPECTED_SKILL}' -> {PACKAGE_ID}")
    print(f"[VERIFY] ownership file: {_ownership_mapping()}")

    controller.ui.currentView = "Updates"
    _pump(4000)
    try:
        for p in list(controller.config_mgr.updateProjects or []):
            print(
                f"[VERIFY] updateProjects row: name={p.get('name')} "
                f"skills={p.get('skill_count')} path={p.get('path')}"
            )
    except Exception as exc:  # noqa: BLE001
        print(f"[VERIFY] updateProjects diagnostic skipped: {exc}")
    _capture(win, "link_on_add_updates_a")
    _pump(3000)
    _capture(win, "link_on_add_updates_b")

    win.close()
    print("[VERIFY] RESULT: PASS")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, help="Project folder to add")
    parser.add_argument("--real-platform", action="store_true", help="Run on the real windowing platform (default: offscreen)")
    args = parser.parse_args()

    QQuickStyle.setStyle("Basic")
    fmt = QSurfaceFormat()
    fmt.setAlphaBufferSize(8)
    QSurfaceFormat.setDefaultFormat(fmt)
    app = QGuiApplication(sys.argv)
    app.setApplicationName("SkillManager")

    controller = AppController()
    qmlRegisterSingletonInstance(AppController, "App", 1, 0, "AppController", controller)

    font_bridge = FontDatabaseBridge()
    qmlRegisterSingletonInstance(FontDatabaseBridge, "App", 1, 0, "FontDB", font_bridge)

    engine = QQmlApplicationEngine()
    controller._qml_engine = engine
    engine.addImageProvider("screenshot", controller.screenshot_provider)
    engine.rootContext().setContextProperty("appController", controller)
    engine.rootContext().setContextProperty("fontDB", font_bridge)

    qml_dir = qml_components_dir(package_file="src/skill_manager/app.py")
    engine.addImportPath(str(qml_dir.parent))
    qml_file = qml_dir / "Main.qml"
    engine.load(str(qml_file))

    if not engine.rootObjects():
        print("[VERIFY] ERROR: QML load failed!")
        sys.exit(1)

    win = engine.rootObjects()[0]
    win.show()  # required for the scene graph to render under offscreen

    def step():
        try:
            controller.ui.currentView = "Library"
        except Exception as exc:  # noqa: BLE001
            print(f"[VERIFY] view set skipped: {exc}")
        try:
            print(f"[VERIFY] current view: {controller.ui.currentView}")
        except Exception:  # noqa: BLE001
            pass

        _run_verify(controller, win, args)
        app.quit()

    QTimer.singleShot(5000, step)
    app.exec()


if __name__ == "__main__":
    main()

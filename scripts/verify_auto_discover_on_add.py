"""
Verification script for auto-discovery of pre-existing skills when a project
folder is added via the UI code path (no manual refresh / restart).

Loads the REAL Main.qml through the REAL AppController in-process (same
pattern as verify_window_persistence.py), calls config_mgr.addProject() on a
folder that already contains a skill, then verifies the skill appears in the
library model WITHOUT issuing a refresh, and captures the rendered window.

Usage:
    uv run python scripts/verify_auto_discover_on_add.py --project <path> [--expected-skill alpha]
    uv run python scripts/verify_auto_discover_on_add.py --cleanup --project <path>
"""

import argparse
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


def _run_verify(controller, win, args) -> None:
    # Open the Library filters so non-package (project) skills are visible.
    # Must be set in-process AFTER startup: the QML toggles re-save their
    # default value over any pre-run config flip during startup.
    try:
        controller.libraryModel.isPackageOnly = False
        _pump(300)
    except Exception as exc:  # noqa: BLE001
        print(f"[VERIFY] filter flip skipped: {exc}")

    before = _skill_names(controller)
    print(f"[VERIFY] pre-add skill count={len(before)}; 'alpha' present: {'alpha' in before}")
    print(
        f"[VERIFY] filter state: isPackageOnly={controller.libraryModel.isPackageOnly} "
        f"rowCount={controller.libraryModel.rowCount()}"
    )

    controller.config_mgr.addProject(args.project)
    print(f"[VERIFY] addProject({args.project}) called — NO manual refresh issued")

    if not _wait_for_skill(controller, args.expected_skill):
        print(f"[VERIFY] FAIL: '{args.expected_skill}' NOT discovered within timeout")
        _pump(1500)
        _capture(win, "auto_discover_on_add_FAIL")
        win.close()
        sys.exit(1)

    print(f"[VERIFY] PASS: '{args.expected_skill}' discovered automatically after add")
    print(
        f"[VERIFY] post-add: rowCount={controller.libraryModel.rowCount()} "
        f"filtered={len(controller.libraryModel._filtered_skills or [])} "
        f"incubating={controller.libraryModel.incubating}"
    )

    # Let QML settle and render the updated model — capture twice so a slow
    # ListView rebind cannot be mistaken for an empty library
    _pump(5000)
    _capture(win, "auto_discover_on_add_a")
    _pump(5000)
    _capture(win, "auto_discover_on_add_b")

    for s in getattr(controller.libraryModel, "_all_skills", None) or []:
        if getattr(s, "name", "") == args.expected_skill:
            print(
                f"[VERIFY] matched skill: name={s.name} folder={getattr(s, 'folder_name', None)} "
                f"is_package={getattr(s, 'is_package', None)} "
                f"local_path={getattr(s, 'local_path', None)}"
            )

    win.close()
    print("[VERIFY] RESULT: PASS")


def _run_cleanup(controller, win, args) -> None:
    from skill_manager.core.copier import normalize_project_skills_path

    clean_path = controller.config_mgr.normalize_path(args.project)
    resolved, _ = normalize_project_skills_path(clean_path)
    resolved_str = str(resolved) if resolved else clean_path

    if resolved_str in getattr(controller, "_projects", []):
        controller.config_mgr.removeProject(resolved_str)
        print(f"[VERIFY] cleanup: removed project {resolved_str}")
    else:
        print(f"[VERIFY] cleanup: project not present ({resolved_str}) — nothing to remove")
    win.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, help="Project folder to add")
    parser.add_argument("--expected-skill", default="alpha")
    parser.add_argument("--cleanup", action="store_true", help="Remove the project from config instead")
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
        # Ensure the Library view is active for the capture
        try:
            controller.ui.currentView = "Library"
        except Exception as exc:  # noqa: BLE001
            print(f"[VERIFY] view set skipped: {exc}")
        try:
            print(f"[VERIFY] current view: {controller.ui.currentView}")
        except Exception:  # noqa: BLE001
            pass

        if args.cleanup:
            _run_cleanup(controller, win, args)
        else:
            _run_verify(controller, win, args)
        app.quit()

    # Give initial load + discovery time to settle before addProject
    QTimer.singleShot(5000, step)
    app.exec()


if __name__ == "__main__":
    main()

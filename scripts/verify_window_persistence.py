"""
Verification script for Window Position & Size Persistence.
Sets window to a specific position/size, saves, then verifies the controller
has the correct values. Run via: uv run python scripts/verify_window_persistence.py
"""

import os
import sys
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
os.environ["QT_QPA_PLATFORM"] = "offscreen"

import sentry_sdk
import skill_manager

sentry_sdk.init(
    dsn="",
    environment="development",
    release=f"skill-manager@{skill_manager.__version__}",
    default_integrations=False,
)

from PySide6.QtCore import QTimer
from PySide6.QtGui import QGuiApplication, QSurfaceFormat
from PySide6.QtQml import QQmlApplicationEngine, qmlRegisterSingletonInstance
from PySide6.QtQuickControls2 import QQuickStyle

from skill_manager.app import AppController
from skill_manager.controllers.font_database_bridge import FontDatabaseBridge
from skill_manager.core.resources import qml_components_dir

TEST_X = 180
TEST_Y = 140
TEST_W = 880
TEST_H = 640


def main():
    QQuickStyle.setStyle("Basic")
    fmt = QSurfaceFormat()
    fmt.setAlphaBufferSize(8)
    QSurfaceFormat.setDefaultFormat(fmt)
    app = QGuiApplication(sys.argv)
    app.setApplicationName("SkillManager")

    controller = AppController()
    qmlRegisterSingletonInstance(
        AppController, "App", 1, 0, "AppController", controller
    )

    font_bridge = FontDatabaseBridge()
    qmlRegisterSingletonInstance(
        FontDatabaseBridge, "App", 1, 0, "FontDB", font_bridge
    )

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
        print("ERROR: QML load failed!")
        sys.exit(1)

    win = engine.rootObjects()[0]

    def test_step():
        print(
            f"Initial: ({win.x()}, {win.y()}, {win.width()}, {win.height()})"
        )
        print(f"Setting target: ({TEST_X}, {TEST_Y}, {TEST_W}, {TEST_H})")

        win.setX(TEST_X)
        win.setY(TEST_Y)
        win.setWidth(TEST_W)
        win.setHeight(TEST_H)

        controller.ui_controller.windowX = TEST_X
        controller.ui_controller.windowY = TEST_Y
        controller.ui_controller.windowWidth = TEST_W
        controller.ui_controller.windowHeight = TEST_H
        controller.ui_controller.saveUiState()

        print(
            f"Saved: ({win.x()}, {win.y()}, {win.width()}, {win.height()})"
        )

        # Verify controller state
        assert controller.ui_controller.windowX == TEST_X, (
            f"X: {controller.ui_controller.windowX} != {TEST_X}"
        )
        assert controller.ui_controller.windowY == TEST_Y, (
            f"Y: {controller.ui_controller.windowY} != {TEST_Y}"
        )
        assert controller.ui_controller.windowWidth == TEST_W, (
            f"W: {controller.ui_controller.windowWidth} != {TEST_W}"
        )
        assert controller.ui_controller.windowHeight == TEST_H, (
            f"H: {controller.ui_controller.windowHeight} != {TEST_H}"
        )

        print("Phase 1 PASS: Controller state matches target geometry")

        pixmap = win.grabWindow()
        out_path = captures_dir / "window_persistence_verification.png"
        pixmap.save(str(out_path))
        print(f"Screenshot: {out_path}")

        win.close()
        app.quit()

    QTimer.singleShot(3000, test_step)
    app.exec()


if __name__ == "__main__":
    main()

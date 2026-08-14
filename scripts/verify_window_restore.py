"""
Verification Part 2: Restore.
Launches a fresh app and verifies that saved window position AND size are
restored on startup. Run after verify_window_persistence.py.
"""

import os
import sys
from pathlib import Path

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

EXPECTED_X = 180
EXPECTED_Y = 140
EXPECTED_W = 880
EXPECTED_H = 640


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

    def verify_step():
        # Check controller state (saved values, before WM override)
        ctrl_x = controller.ui_controller.windowX
        ctrl_y = controller.ui_controller.windowY
        ctrl_w = controller.ui_controller.windowWidth
        ctrl_h = controller.ui_controller.windowHeight

        print(f"Controller state: ({ctrl_x}, {ctrl_y}, {ctrl_w}, {ctrl_h})")
        print(f"Window actual:    ({win.x()}, {win.y()}, {win.width()}, {win.height()})")

        assert ctrl_x == EXPECTED_X, f"Expected X={EXPECTED_X}, got {ctrl_x}"
        assert ctrl_y == EXPECTED_Y, f"Expected Y={EXPECTED_Y}, got {ctrl_y}"
        assert ctrl_w == EXPECTED_W, f"Expected W={EXPECTED_W}, got {ctrl_w}"
        assert ctrl_h == EXPECTED_H, f"Expected H={EXPECTED_H}, got {ctrl_h}"

        print("SUCCESS: Window geometry fully restored from saved state!")
        win.close()
        app.quit()

    # Wait 500ms — enough for both QML Component.onCompleted AND the
    # 200ms _positionRestoreTimer to fire.
    QTimer.singleShot(3000, verify_step)
    app.exec()


if __name__ == "__main__":
    main()

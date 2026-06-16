from pathlib import Path

import pytest
from PySide6.QtCore import QRect
from PySide6.QtGui import QGuiApplication, QPixmap


@pytest.mark.usefixtures("setup_qml_style")
class TestUIScreenshotFlow:
    def test_full_screenshot_capture_and_save_flow(self, qml_engine, app_controller, qtbot, temp_dir):
        # 1. Setup the environment
        app_controller.config_controller.autoMinimizeOnScreenshot = False
        app_controller.config_controller.temporaryScreenshots = False
        app_controller._projects = [str(temp_dir)]

        # Ensure we have a valid screen to capture from
        screen = QGuiApplication.primaryScreen()
        assert screen is not None, "A primary screen is required for this test."

        # 2. Trigger capture
        with qtbot.waitSignal(app_controller.screenshot_controller.showOverlay, timeout=2000):
            app_controller.screenshot_controller.takeScreenshot()

        assert app_controller.screenshot_controller._current_full_pixmap is not None
        assert not app_controller.screenshot_controller._current_full_pixmap.isNull()

        # 3. Simulate User action from QML: Saving a cropped area with a redaction
        crop_rect = QRect(0, 0, 100, 100)
        redactions = [{"x": 10, "y": 10, "width": 20, "height": 20}]

        # Save screenshot should emit captureFinished with the saved path
        with qtbot.waitSignal(app_controller.screenshot_controller.captureFinished, timeout=2000) as blocker:
            app_controller.screenshot_controller.saveScreenshot(crop_rect, redactions)

        saved_path = blocker.args[0]

        # 4. Verify file exists
        p = Path(saved_path)
        assert p.exists()
        assert p.is_file()
        assert p.suffix == ".png"

        # Verify the saved image has the expected dimensions
        saved_pixmap = QPixmap(str(p))
        assert saved_pixmap.width() == 100
        assert saved_pixmap.height() == 100

        # 5. Verify Model Integration
        # The new screenshot should be added as a virtual skill to the models
        # It's a "Special" main category, "Screenshots" category

        def check_model_for_screenshot():
            model = app_controller.skillModel
            for i in range(model._all_skills.__len__()):
                skill = model._all_skills[i]
                if skill.get("is_screenshot", False) and skill.get("local_path") == saved_path:
                    return True
            return False

        qtbot.waitUntil(check_model_for_screenshot, timeout=2000)

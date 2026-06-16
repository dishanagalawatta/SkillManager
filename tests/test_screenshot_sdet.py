from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import QRect
from PySide6.QtGui import QColor, QPixmap

from skill_manager.controllers.screenshot_controller import ScreenshotController
from skill_manager.core.image_processing import ImageProcessor
from skill_manager.core.schemas import Redaction


@pytest.fixture
def mock_app():
    app = MagicMock()
    app.config_controller = MagicMock()
    app.quickCopyModel = MagicMock()
    app.projects = ["/fake/project"]
    app.config_controller.project_aliases = {}
    app._categories = []

    app._library_model = MagicMock()
    app._quick_copy_model = MagicMock()

    # Needs to simulate a QClipboard interface
    clipboard_mock = MagicMock()

    with patch("skill_manager.controllers.screenshot_controller.QGuiApplication") as mock_gui:
        mock_gui.clipboard.return_value = clipboard_mock
        yield app

@pytest.fixture
def controller(mock_app):
    ctrl = ScreenshotController(mock_app)
    # Provide a dummy pixmap
    pixmap = QPixmap(100, 100)
    pixmap.fill(QColor("white"))
    ctrl._current_full_pixmap = pixmap
    return ctrl

class TestImageProcessor:
    def test_crop_and_redact_success(self):
        pixmap = QPixmap(100, 100)
        pixmap.fill(QColor("white"))

        crop_rect = QRect(10, 10, 50, 50)
        redactions = [Redaction(x=5, y=5, width=10, height=10)]

        result = ImageProcessor.crop_and_redact(pixmap, crop_rect, redactions)

        # Result should match crop size
        assert result.width() == 50
        assert result.height() == 50

        # Verify redaction is drawn (black pixel at 5,5)
        img = result.toImage()
        color = QColor(img.pixel(5, 5))
        assert color.name() == "#000000"

    def test_crop_and_redact_null_pixmap(self):
        pixmap = QPixmap()
        crop_rect = QRect(0, 0, 10, 10)

        with pytest.raises(ValueError, match="Cannot process a null QPixmap"):
            ImageProcessor.crop_and_redact(pixmap, crop_rect, [])

    def test_crop_and_redact_empty_crop(self):
        pixmap = QPixmap(100, 100)
        crop_rect = QRect(0, 0, 0, 0)

        with pytest.raises(ValueError, match="Crop rectangle cannot be empty"):
            ImageProcessor.crop_and_redact(pixmap, crop_rect, [])


class TestScreenshotControllerSDET:
    def test_save_screenshot_invalid_params(self, controller, mock_app):
        crop_rect = QRect(-10, -10, 0, 0) # Invalid

        controller.saveScreenshot(crop_rect, [])

        # Should set status to error and not proceed
        mock_app._set_status.assert_called_with("Failed to save: invalid crop or redaction parameters.")

    def test_save_screenshot_null_pixmap(self, controller, mock_app):
        controller._current_full_pixmap = None

        controller.saveScreenshot(QRect(0, 0, 10, 10), [])

        # Method should return early, not crashing
        mock_app._set_status.assert_not_called()

    @patch("skill_manager.core.image_processing.ImageProcessor.crop_and_redact")
    def test_save_screenshot_image_processor_fails(self, mock_process, controller, mock_app):
        mock_process.side_effect = ValueError("Test error")

        controller.saveScreenshot(QRect(0, 0, 10, 10), [])

        # Should catch error and return
        mock_app._set_status.assert_not_called()

    def test_save_screenshot_success(self, controller, mock_app, tmp_path):
        mock_app.projects = [str(tmp_path)]
        mock_app.clientFormat = "Standard"

        crop_rect = QRect(0, 0, 50, 50)
        raw_redactions = [{"x": 0, "y": 0, "width": 10, "height": 10}]

        controller.saveScreenshot(crop_rect, raw_redactions)

        # Check files were created
        screenshots_dir = tmp_path / ".agents" / "screenshots"
        assert screenshots_dir.exists()

        files = list(screenshots_dir.glob("Screenshot_*.png"))
        assert len(files) == 1

        # Check model updates
        mock_app._library_model.addOrUpdateSkills.assert_called_once()
        args = mock_app._library_model.addOrUpdateSkills.call_args[0][0]
        assert len(args) == 1
        assert args[0]["is_screenshot"] is True

        # Check categories update
        assert "Screenshots" in mock_app._categories
        mock_app.categoriesChanged.emit.assert_called_once()

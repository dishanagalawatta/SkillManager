import os
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import QRect
from PySide6.QtGui import QPixmap

from skill_manager.controllers.screenshot_controller import ScreenshotController
from skill_manager.core.image_provider import ScreenshotImageProvider
from skill_manager.core.quick_copy import discover_single_project


@pytest.fixture
def mock_app():
    app = MagicMock()
    app.screenshot_provider = MagicMock()
    app.skillModel = MagicMock()
    app.quickCopyModel = MagicMock()
    app._library_model = MagicMock()
    app._quick_copy_model = MagicMock()
    app._categories = []
    app.projects = ["/mock/project"]
    app._config = {}
    app.config_controller = MagicMock()
    app.config_controller.autoMinimizeOnScreenshot = False
    return app


@pytest.fixture
def controller(mock_app):
    return ScreenshotController(mock_app)


def test_screenshot_image_provider_initial():
    provider = ScreenshotImageProvider()
    pixmap = provider.requestPixmap("any", None, None)
    assert not pixmap.isNull()
    assert pixmap.width() == 1
    assert pixmap.height() == 1


def test_screenshot_image_provider_set_pixmap():
    provider = ScreenshotImageProvider()
    test_pix = QPixmap(100, 100)
    test_pix.fill("red")
    provider.set_pixmap(test_pix)
    pixmap = provider.requestPixmap("any", None, None)
    assert pixmap is test_pix
    assert pixmap.width() == 100


def test_take_screenshot(controller, mock_app):
    with patch("PySide6.QtGui.QGuiApplication.primaryScreen") as mock_screen:
        screen = MagicMock()
        mock_screen.return_value = screen
        pixmap = QPixmap(10, 10)
        screen.grabWindow.return_value = pixmap

        # Connect signal to verify emission
        overlay_shown = False

        def on_show():
            nonlocal overlay_shown
            overlay_shown = True

        controller.showOverlay.connect(on_show)

        controller.takeScreenshot()

        assert overlay_shown
        mock_app.screenshot_provider.set_pixmap.assert_called_with(pixmap)


def test_save_screenshot_gemini_cli(controller, mock_app, tmp_path):
    # Setup
    project_path = str(tmp_path)
    mock_app.quickCopyModel.projectFilter = "MockProject"
    mock_app.projects = [project_path]
    mock_app.clientFormat = "Gemini CLI"

    # Mock project_label to return "MockProject"
    with patch("skill_manager.core.quick_copy.project_label", return_value="MockProject"):
        full_pixmap = QPixmap(100, 100)
        full_pixmap.fill("white")
        controller.current_full_pixmap = full_pixmap

        crop_rect = QRect(10, 10, 50, 50)

        with patch("PySide6.QtGui.QGuiApplication.clipboard") as mock_clipboard:
            controller.saveScreenshot(crop_rect, [])

            # Verify text was copied instead of pixmap
            mock_clipboard().setText.assert_called()
            # check that it contains @.agents/screenshots/
            args, _ = mock_clipboard().setText.call_args
            assert args[0].startswith("@.agents/screenshots/Screenshot_")

            # Verify direct injection into models
            mock_app._library_model.addOrUpdateSkills.assert_called()
            mock_app._quick_copy_model.addOrUpdateSkills.assert_called()


def test_save_screenshot_standard(controller, mock_app, tmp_path):
    # Setup
    project_path = str(tmp_path)
    mock_app.quickCopyModel.projectFilter = project_path
    mock_app.projects = [project_path]
    mock_app.clientFormat = "Antigravity"

    full_pixmap = QPixmap(100, 100)
    full_pixmap.fill("white")
    controller.current_full_pixmap = full_pixmap

    crop_rect = QRect(10, 10, 50, 50)

    with patch("PySide6.QtGui.QGuiApplication.clipboard") as mock_clipboard:
        controller.saveScreenshot(crop_rect, [])

        # Check if file exists
        save_dir = os.path.join(project_path, ".agents", "screenshots")
        assert os.path.exists(save_dir)

        # Check clipboard
        mock_clipboard().setPixmap.assert_called()
        # Verify direct injection into models
        mock_app._library_model.addOrUpdateSkills.assert_called()
        mock_app._quick_copy_model.addOrUpdateSkills.assert_called()


def test_screenshot_discovery(tmp_path):
    # Create a mock project with a screenshot
    project_dir = tmp_path / "project"
    screenshot_dir = project_dir / ".agents" / "screenshots"
    screenshot_dir.mkdir(parents=True)

    img_file = screenshot_dir / "Screenshot_20230101_120000.png"
    img_file.write_text("fake image data")

    # Discovery call
    res = discover_single_project(
        project=str(project_dir),
        parse_skill_md=lambda p: {},
        categorize_skill=lambda n, d, m: {"main_category": "Dev", "sub_category": "Tool"},
        build_search_text=lambda s: "search",
    )

    assert res is not None
    skills = res["skills"]
    screenshot_skills = [s for s in skills if s.get("is_screenshot")]

    assert len(screenshot_skills) == 1
    assert screenshot_skills[0]["name"] == img_file.name
    assert screenshot_skills[0]["is_screenshot"] is True
    assert screenshot_skills[0]["skill_md_path"] == str(img_file)


def test_take_screenshot_no_screen(controller, mock_app):
    with patch("PySide6.QtGui.QGuiApplication.primaryScreen", return_value=None):
        controller.takeScreenshot()
        mock_app.screenshot_provider.set_pixmap.assert_not_called()


def test_save_screenshot_no_pixmap(controller, mock_app):
    controller.current_full_pixmap = None
    controller.saveScreenshot(QRect(0, 0, 10, 10), [])
    mock_app._set_status.assert_not_called()


def test_save_screenshot_emits_categories_changed(controller, mock_app, tmp_path):
    project_path = str(tmp_path)
    mock_app.quickCopyModel.projectFilter = "MockProject"
    mock_app.projects = [project_path]
    mock_app.clientFormat = "PlainText"
    mock_app._categories = ["Dev"]

    with patch("skill_manager.core.quick_copy.project_label", return_value="MockProject"):
        full_pixmap = QPixmap(100, 100)
        controller.current_full_pixmap = full_pixmap

        controller.saveScreenshot(QRect(0, 0, 10, 10), [])

    assert "Screenshots" in mock_app._categories
    mock_app.categoriesChanged.emit.assert_called_once()


def test_save_screenshot_skips_categories_changed_when_already_present(
    controller, mock_app, tmp_path
):
    project_path = str(tmp_path)
    mock_app.quickCopyModel.projectFilter = "MockProject"
    mock_app.projects = [project_path]
    mock_app.clientFormat = "PlainText"
    mock_app._categories = ["Screenshots", "Dev"]

    with patch("skill_manager.core.quick_copy.project_label", return_value="MockProject"):
        full_pixmap = QPixmap(100, 100)
        controller.current_full_pixmap = full_pixmap

        controller.saveScreenshot(QRect(0, 0, 10, 10), [])

    mock_app.categoriesChanged.emit.assert_not_called()


def test_save_screenshot_no_project(controller, mock_app):
    mock_app.quickCopyModel.projectFilter = ""
    mock_app.projects = []
    full_pixmap = QPixmap(100, 100)
    controller.current_full_pixmap = full_pixmap

    controller.saveScreenshot(QRect(0, 0, 10, 10), [])
    mock_app._set_status.assert_called_with("No project selected to save screenshot.")


def test_clear_selection_default_shortcut():
    """Clear Selection is the shared ESC shortcut (covers both clearing selection and canceling screenshot)."""
    from skill_manager.core.config import DEFAULT_SHORTCUTS

    assert "clear_selection" in DEFAULT_SHORTCUTS
    assert DEFAULT_SHORTCUTS["clear_selection"] == "Esc"
    assert "screenshot_cancel" not in DEFAULT_SHORTCUTS


def test_screenshot_default_shortcut():
    """Screenshot shortcut is in DEFAULT_SHORTCUTS with Ctrl+Shift+S."""
    from skill_manager.core.config import DEFAULT_SHORTCUTS

    assert "screenshot" in DEFAULT_SHORTCUTS
    assert DEFAULT_SHORTCUTS["screenshot"] == "Ctrl+Shift+S"


def test_auto_minimize_on_screenshot_default():
    from skill_manager.core.schemas import AppConfig

    config = AppConfig()
    assert config.auto_minimize_on_screenshot is False


def test_auto_minimize_on_screenshot_config_controller():
    from skill_manager.controllers.config_controller import ConfigController

    mock_app = MagicMock()
    mock_config = MagicMock()
    mock_config.get.return_value = False
    mock_app._config = mock_config
    controller = ConfigController(mock_app)

    assert controller.autoMinimizeOnScreenshot is False

    controller.autoMinimizeOnScreenshot = True
    mock_config.set.assert_called_with("auto_minimize_on_screenshot", True)


def test_take_screenshot_emits_minimize_requested_when_enabled(controller, mock_app):
    mock_app.config_controller = MagicMock()
    mock_app.config_controller.autoMinimizeOnScreenshot = True

    minimize_requested = False

    def on_minimize():
        nonlocal minimize_requested
        minimize_requested = True

    controller.minimizeRequested.connect(on_minimize)

    controller.takeScreenshot()

    assert minimize_requested
    mock_app.screenshot_provider.set_pixmap.assert_not_called()


def test_take_screenshot_no_minimize_when_disabled(controller, mock_app):
    mock_app.config_controller = MagicMock()
    mock_app.config_controller.autoMinimizeOnScreenshot = False

    minimize_requested = False

    def on_minimize():
        nonlocal minimize_requested
        minimize_requested = True

    controller.minimizeRequested.connect(on_minimize)

    with patch("PySide6.QtGui.QGuiApplication.primaryScreen") as mock_screen:
        screen = MagicMock()
        mock_screen.return_value = screen
        pixmap = QPixmap(10, 10)
        screen.grabWindow.return_value = pixmap

        controller.takeScreenshot()

        assert not minimize_requested
        mock_app.screenshot_provider.set_pixmap.assert_called_with(pixmap)


def test_capture_screen(controller, mock_app):
    with patch("PySide6.QtGui.QGuiApplication.primaryScreen") as mock_screen:
        screen = MagicMock()
        mock_screen.return_value = screen
        pixmap = QPixmap(10, 10)
        screen.grabWindow.return_value = pixmap

        overlay_shown = False

        def on_show():
            nonlocal overlay_shown
            overlay_shown = True

        controller.showOverlay.connect(on_show)

        controller.captureScreen()

        assert overlay_shown
        mock_app.screenshot_provider.set_pixmap.assert_called_with(pixmap)


def test_capture_screen_no_screen(controller, mock_app):
    with patch("PySide6.QtGui.QGuiApplication.primaryScreen", return_value=None):
        controller.captureScreen()
        mock_app.screenshot_provider.set_pixmap.assert_not_called()


def test_cancel_capture_emits_signal(controller):
    """cancelCapture() should emit captureCancelled and clear the current pixmap."""
    called = False

    def on_cancel():
        nonlocal called
        called = True

    controller.captureCancelled.connect(on_cancel)
    controller.current_full_pixmap = QPixmap(50, 50)
    assert not controller.current_full_pixmap.isNull()

    controller.cancelCapture()

    assert called
    assert controller.current_full_pixmap is None


def test_cancel_capture_no_pixmap(controller):
    """cancelCapture() should not fail if called with no current pixmap."""
    called = False

    def on_cancel():
        nonlocal called
        called = True

    controller.captureCancelled.connect(on_cancel)
    controller.current_full_pixmap = None

    controller.cancelCapture()

    assert called
    assert controller.current_full_pixmap is None

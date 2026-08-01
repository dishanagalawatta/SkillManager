import os
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import QRect
from PySide6.QtGui import QColor, QPixmap

from skill_manager.controllers.screenshot_controller import ScreenshotController
from skill_manager.core.image_processing import ImageProcessor
from skill_manager.core.image_provider import ScreenshotImageProvider
from skill_manager.core.quick_copy import discover_single_project
from skill_manager.core.schemas import Redaction


@pytest.fixture
def mock_app(tmp_path):
    app = MagicMock()
    app.screenshot_provider = MagicMock()
    app.skillModel = MagicMock()
    app.quickCopyModel = MagicMock()
    app._library_model = MagicMock()
    app._quick_copy_model = MagicMock()
    app._categories = []
    fake_proj = tmp_path / "mock_project"
    fake_proj.mkdir(parents=True, exist_ok=True)
    app.projects = [str(fake_proj)]
    app._config = {}
    app.config_controller = MagicMock()
    app.config_controller.autoMinimizeOnScreenshot = False
    app.config_controller.autoCopyScreenshotClientFormat = False
    app.config_controller.autoSelectScreenshotInQuickCopy = False
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


def test_save_screenshot_no_project_fallback_to_cwd(controller, mock_app, tmp_path):
    """When no project is configured, save to CWD/.agents/screenshots/ instead of failing."""
    mock_app.quickCopyModel.projectFilter = ""
    mock_app.projects = []
    mock_app.clientFormat = "Antigravity"
    full_pixmap = QPixmap(100, 100)
    full_pixmap.fill("white")
    controller.current_full_pixmap = full_pixmap

    original_cwd = os.getcwd()
    os.chdir(str(tmp_path))
    try:
        with patch("PySide6.QtGui.QGuiApplication.clipboard"):
            controller.saveScreenshot(QRect(0, 0, 10, 10), [])
            save_dir = tmp_path / ".agents" / "screenshots"
            assert save_dir.is_dir(), "save dir should have been created"
            # Verify a file was saved there
            png_files = list(save_dir.glob("Screenshot_*.png"))
            assert len(png_files) >= 1
    finally:
        os.chdir(original_cwd)


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


def test_auto_minimize_full_flow_captures_after_minimize(controller, mock_app):
    """Full auto-minimize flow: takeScreenshot emits minimize, then
    captureScreen (called by QML timer) performs the actual capture."""
    mock_app.config_controller = MagicMock()
    mock_app.config_controller.autoMinimizeOnScreenshot = True

    minimize_requested = False

    def on_minimize():
        nonlocal minimize_requested
        minimize_requested = True

    controller.minimizeRequested.connect(on_minimize)

    # Step 1: takeScreenshot — only emits minimize, does NOT capture
    with patch("PySide6.QtGui.QGuiApplication.primaryScreen") as mock_screen:
        controller.takeScreenshot()

    assert minimize_requested, "minimizeRequested must be emitted"
    mock_app.screenshot_provider.set_pixmap.assert_not_called()
    assert controller.current_full_pixmap is None

    # Step 2: captureScreen — called by the QML timer after window is hidden
    overlay_shown = False

    def on_show():
        nonlocal overlay_shown
        overlay_shown = True

    controller.showOverlay.connect(on_show)

    with patch("PySide6.QtGui.QGuiApplication.primaryScreen") as mock_screen:
        screen = MagicMock()
        mock_screen.return_value = screen
        pixmap = QPixmap(10, 10)
        screen.grabWindow.return_value = pixmap

        controller.captureScreen()

    assert overlay_shown, "Overlay must be shown after deferred capture"
    mock_app.screenshot_provider.set_pixmap.assert_called_with(pixmap)
    assert controller.current_full_pixmap is not None
    assert not controller.current_full_pixmap.isNull()


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


def test_pre_authorize_portal_sets_permission():
    """_pre_authorize_portal calls SetPermission with correct args."""
    from unittest.mock import MagicMock, patch

    from PySide6.QtDBus import QDBus

    from skill_manager.controllers.screenshot_controller import _pre_authorize_portal

    mock_bus = MagicMock()
    mock_bus.isConnected.return_value = True

    mock_interface = MagicMock()
    mock_interface.isValid.return_value = True

    with patch(
        "skill_manager.controllers.screenshot_controller.QDBusInterface",
        return_value=mock_interface,
    ):
        _pre_authorize_portal(mock_bus)

        mock_interface.callWithArgumentList.assert_called_once_with(
            QDBus.AutoDetect,
            "SetPermission",
            ["screenshot", True, "skill-manager", "skill-manager", ["yes"]],
        )


def test_pre_authorize_portal_skips_if_bus_not_connected():
    """_pre_authorize_portal does nothing if D-Bus is not connected."""
    from unittest.mock import MagicMock, patch

    from skill_manager.controllers.screenshot_controller import _pre_authorize_portal

    mock_bus = MagicMock()
    mock_bus.isConnected.return_value = False

    with patch(
        "skill_manager.controllers.screenshot_controller.QDBusInterface",
    ) as mock_iface_cls:
        _pre_authorize_portal(mock_bus)
        mock_iface_cls.assert_not_called()


def test_find_portal_python_uses_system_python():
    """_find_portal_python prefers /usr/bin/python3 when it has dbus."""
    from unittest.mock import patch

    from skill_manager.controllers.screenshot_controller import _find_portal_python

    with (
        patch("os.path.isfile", return_value=True),
        patch(
            "skill_manager.controllers.screenshot_controller.subprocess.run",
        ) as mock_run,
    ):
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "ok"
        mock_run.return_value = mock_proc

        result = _find_portal_python()

        assert result == "/usr/bin/python3"
        # Must verify the system Python has dbus
        args = mock_run.call_args[0][0]
        assert args[0] == "/usr/bin/python3"
        assert "import dbus" in args[2]


def test_find_portal_python_falls_back_to_venv():
    """_find_portal_python falls back to sys.executable when /usr/bin/python3 lacks dbus."""
    import sys
    from unittest.mock import MagicMock, patch

    from skill_manager.controllers.screenshot_controller import _find_portal_python

    # First call: /usr/bin/python3 fails. Second call: sys.executable succeeds.
    results = iter(
        [
            MagicMock(returncode=1, stdout=""),
            MagicMock(returncode=0, stdout="ok"),
        ]
    )

    with (
        patch("os.path.isfile", return_value=True),
        patch(
            "skill_manager.controllers.screenshot_controller.subprocess.run",
        ) as mock_run,
    ):
        mock_run.side_effect = lambda *a, **kw: next(results)

        result = _find_portal_python()

        assert result == sys.executable
        assert mock_run.call_count == 2


def test_find_portal_python_returns_none_when_no_python_has_dbus():
    """_find_portal_python returns None when no candidate has dbus."""
    from unittest.mock import MagicMock, patch

    from skill_manager.controllers.screenshot_controller import _find_portal_python

    with (
        patch("os.path.isfile", return_value=True),
        patch(
            "skill_manager.controllers.screenshot_controller.subprocess.run",
        ) as mock_run,
    ):
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stdout = ""
        mock_run.return_value = mock_proc

        result = _find_portal_python()

        assert result is None


def test_find_portal_python_skips_nonexistent_files():
    """_find_portal_python skips candidates that don't exist on disk."""
    import sys
    from unittest.mock import MagicMock, patch

    from skill_manager.controllers.screenshot_controller import _find_portal_python

    with (
        patch("os.path.isfile", side_effect=lambda p: p == sys.executable),
        patch(
            "skill_manager.controllers.screenshot_controller.subprocess.run",
        ) as mock_run,
    ):
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "ok"
        mock_run.return_value = mock_proc

        result = _find_portal_python()

        assert result == sys.executable
        # Only sys.executable was tested (skipped /usr/bin/python3)
        assert mock_run.call_count == 1


def test_find_portal_python_skips_duplicates():
    """_find_portal_python does not test the same candidate twice."""
    from unittest.mock import MagicMock, patch

    from skill_manager.controllers.screenshot_controller import _find_portal_python

    with (
        patch("os.path.isfile", return_value=True),
        patch(
            "skill_manager.controllers.screenshot_controller.subprocess.run",
        ) as mock_run,
    ):
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stdout = ""
        mock_run.return_value = mock_proc

        result = _find_portal_python()

        assert result is None
        # Should only test unique candidates
        assert mock_run.call_count <= 3


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


def test_take_screenshot_null_pixmap_on_linux_shows_overlay_immediately(controller, mock_app):
    """Wayland: grabWindow returns null, overlay shown immediately without pre-capturing."""
    mock_app._set_status = MagicMock()
    with (
        patch("PySide6.QtGui.QGuiApplication.primaryScreen") as mock_screen,
        patch("sys.platform", "linux"),
    ):
        screen = MagicMock()
        mock_screen.return_value = screen
        screen.grabWindow.return_value = MagicMock(isNull=lambda: True)

        overlay_shown = False
        cancelled = False

        def on_show():
            nonlocal overlay_shown
            overlay_shown = True

        def on_cancel():
            nonlocal cancelled
            cancelled = True

        controller.showOverlay.connect(on_show)
        controller.captureCancelled.connect(on_cancel)

        controller.takeScreenshot()

        assert overlay_shown, "Overlay should show immediately on Wayland"
        assert not cancelled, "Should not cancel - capture deferred to save"
        assert controller._wayland_deferred, "Wayland deferred flag should be set"
        mock_app.screenshot_provider.set_pixmap.assert_not_called()
        assert not controller.screenshotValid


def test_save_screenshot_deferred_portal_succeeds(controller, mock_app, tmp_path):
    """Wayland deferred: saveScreenshot triggers portal capture, crops, saves."""
    project_path = str(tmp_path)
    mock_app.quickCopyModel.projectFilter = project_path
    mock_app.projects = [project_path]
    mock_app.clientFormat = "Antigravity"
    mock_app.ops = MagicMock()
    mock_app._set_status = MagicMock()

    controller._wayland_deferred = True

    full_pixmap = MagicMock(spec=QPixmap)
    full_pixmap.isNull.return_value = False
    full_pixmap.width.return_value = 200
    full_pixmap.height.return_value = 100

    with (
        patch(
            "skill_manager.controllers.screenshot_controller._portal_capture",
            return_value="/tmp/screen.png",
        ),
        patch(
            "skill_manager.controllers.screenshot_controller.QPixmap",
            return_value=full_pixmap,
        ),
        patch("PySide6.QtGui.QGuiApplication.clipboard"),
    ):
        controller.saveScreenshot(QRect(10, 10, 50, 50), [])

    assert not controller._wayland_deferred
    assert controller.current_full_pixmap is full_pixmap


def test_save_screenshot_deferred_all_strategies_fail(controller, mock_app):
    """Wayland deferred: all capture strategies fail, captureCancelled emitted."""
    mock_app._set_status = MagicMock()
    controller._wayland_deferred = True
    controller.current_full_pixmap = None

    with (
        patch(
            "skill_manager.controllers.screenshot_controller._portal_capture",
            return_value=None,
        ),
        patch(
            "skill_manager.controllers.screenshot_controller._gnome_screenshot_capture",
            return_value=None,
        ),
    ):
        cancelled = False

        def on_cancel():
            nonlocal cancelled
            cancelled = True

        controller.captureCancelled.connect(on_cancel)

        controller.saveScreenshot(QRect(0, 0, 10, 10), [])

    assert not controller._wayland_deferred
    assert cancelled, "captureCancelled must be emitted on deferred capture failure"
    assert mock_app._set_status.call_count >= 1


def test_take_screenshot_null_pixmap_non_linux(controller, mock_app):
    """On non-Linux, null pixmap skips overlay (no fallback attempted)."""
    mock_app._set_status = MagicMock()
    with (
        patch("PySide6.QtGui.QGuiApplication.primaryScreen") as mock_screen,
        patch("sys.platform", "win32"),
    ):
        screen = MagicMock()
        mock_screen.return_value = screen
        screen.grabWindow.return_value = MagicMock(isNull=lambda: True)

        overlay_shown = False
        cancelled = False

        def on_show():
            nonlocal overlay_shown
            overlay_shown = True

        def on_cancel():
            nonlocal cancelled
            cancelled = True

        controller.showOverlay.connect(on_show)
        controller.captureCancelled.connect(on_cancel)

        controller.takeScreenshot()

        assert not overlay_shown
        assert cancelled, "captureCancelled must be emitted so QML restores the hidden window"
        mock_app._set_status.assert_called_once()


def test_save_screenshot_refreshes_selection(controller, mock_app, tmp_path):
    """saveScreenshot calls _refresh_selected_skill after model update."""
    project_path = str(tmp_path)
    mock_app.quickCopyModel.projectFilter = project_path
    mock_app.projects = [project_path]
    mock_app.clientFormat = "Antigravity"

    full_pixmap = QPixmap(100, 100)
    full_pixmap.fill("white")
    controller.current_full_pixmap = full_pixmap

    crop_rect = QRect(10, 10, 50, 50)
    mock_app.ops = MagicMock()

    with patch("PySide6.QtGui.QGuiApplication.clipboard"):
        controller.saveScreenshot(crop_rect, [])

        mock_app.ops._refresh_selected_skill.assert_called_once()
        # The filepath is passed to _refresh_selected_skill
        call_args = mock_app.ops._refresh_selected_skill.call_args
        assert call_args[0][0].endswith(".png") or "Screenshot_" in str(call_args)


def test_save_screenshot_auto_copy_client_format(controller, mock_app, tmp_path):
    project_path = str(tmp_path)
    mock_app.quickCopyModel.projectFilter = project_path
    mock_app.projects = [project_path]
    mock_app.clientFormat = "Antigravity"
    mock_app.config_controller.autoCopyScreenshotClientFormat = True
    mock_app.config_controller.autoSelectScreenshotInQuickCopy = False

    full_pixmap = QPixmap(100, 100)
    full_pixmap.fill("white")
    controller.current_full_pixmap = full_pixmap

    crop_rect = QRect(10, 10, 50, 50)
    mock_app.ops = MagicMock()

    with patch("PySide6.QtGui.QGuiApplication.clipboard") as mock_clipboard:
        controller.saveScreenshot(crop_rect, [])

        mock_clipboard().setText.assert_called_once()
        copied_text = mock_clipboard().setText.call_args[0][0]
        assert copied_text.startswith(".agents/screenshots/Screenshot_")


def test_save_screenshot_auto_select_quick_copy(controller, mock_app, tmp_path):
    project_path = str(tmp_path)
    mock_app.quickCopyModel.projectFilter = project_path
    mock_app.projects = [project_path]
    mock_app.clientFormat = "Antigravity"
    mock_app.config_controller.autoCopyScreenshotClientFormat = False
    mock_app.config_controller.autoSelectScreenshotInQuickCopy = True
    mock_app.ui_controller = MagicMock()
    mock_app._quick_copy_model = MagicMock()

    full_pixmap = QPixmap(100, 100)
    full_pixmap.fill("white")
    controller.current_full_pixmap = full_pixmap

    crop_rect = QRect(10, 10, 50, 50)
    mock_app.ops = MagicMock()

    with patch("PySide6.QtGui.QGuiApplication.clipboard"):
        controller.saveScreenshot(crop_rect, [])

        assert mock_app.ui_controller.currentView == "QuickCopy"
        mock_app._quick_copy_model.selectByPaths.assert_called_once()
        mock_app.set_selected_skill.assert_called_once()


# ── SDET contract (merged from test_screenshot_sdet.py; duplicates pruned) ──


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


def test_save_screenshot_invalid_params(controller, mock_app):
    crop_rect = QRect(-10, -10, 0, 0)  # Invalid

    full_pixmap = QPixmap(100, 100)
    full_pixmap.fill("white")
    controller.current_full_pixmap = full_pixmap

    controller.saveScreenshot(crop_rect, [])

    # Should set status to error and not proceed
    mock_app._set_status.assert_called_with("Failed to save: invalid crop or redaction parameters.")


@patch("skill_manager.core.image_processing.ImageProcessor.crop_and_redact")
def test_save_screenshot_image_processor_fails(mock_process, controller, mock_app):
    mock_process.side_effect = ValueError("Test error")

    full_pixmap = QPixmap(100, 100)
    full_pixmap.fill("white")
    controller.current_full_pixmap = full_pixmap

    controller.saveScreenshot(QRect(0, 0, 10, 10), [])

    # Should catch error and return
    mock_app._set_status.assert_not_called()


def test_save_screenshot_success(controller, mock_app, tmp_path):
    mock_app.projects = [str(tmp_path)]
    mock_app.clientFormat = "Standard"

    crop_rect = QRect(0, 0, 50, 50)
    raw_redactions = [{"x": 0, "y": 0, "width": 10, "height": 10}]

    full_pixmap = QPixmap(100, 100)
    full_pixmap.fill("white")
    controller.current_full_pixmap = full_pixmap

    with patch("PySide6.QtGui.QGuiApplication.clipboard"):
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

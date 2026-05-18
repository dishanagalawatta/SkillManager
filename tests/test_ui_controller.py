from unittest.mock import MagicMock, patch

import pytest

from skill_manager.controllers.ui_controller import UIController


@pytest.fixture
def ui_controller(mock_app):
    mock_app._config.get.return_value = {}
    return UIController(mock_app)


def test_ui_controller_init(ui_controller):
    assert ui_controller._current_view == "Library"
    assert ui_controller._window_width == 1300
    assert ui_controller._window_height == 650
    assert ui_controller._compact_list_rows is False


def test_ui_controller_init_normalization(mock_app):
    mock_app._config.get.return_value = {"current_view": "library"}
    ctrl = UIController(mock_app)
    assert ctrl._current_view == "Library"

    mock_app._config.get.return_value = {"current_view": "quick-copy"}
    ctrl = UIController(mock_app)
    assert ctrl._current_view == "QuickCopy"


def test_ui_controller_save_state(ui_controller, mock_app):
    ui_controller._current_view = "QuickCopy"
    ui_controller._window_width = 1400
    ui_controller.save_ui_state()

    mock_app._config.set.assert_called_once()
    args = mock_app._config.set.call_args[0]
    assert args[0] == "ui_state"
    assert args[1]["current_view"] == "QuickCopy"
    assert args[1]["window_width"] == 1400
    assert args[1]["compact_list_rows"] is False


@patch("PySide6.QtCore.QTimer.start")
def test_ui_controller_trigger_save(mock_timer_start, ui_controller):
    ui_controller.trigger_save()
    mock_timer_start.assert_called_with(2000)


def test_ui_controller_get_asset_uri_fallback(ui_controller):
    # Use a dummy base path to avoid relative path resolution issues during mock
    with (
        patch("pathlib.Path.exists", side_effect=[False, True]),
        patch("pathlib.Path.as_uri", return_value="file:///assets/brand/logo.png"),
    ):
        uri = ui_controller.get_asset_uri("brand/missing.png")
        assert uri == "file:///assets/brand/logo.png"


def test_ui_controller_get_asset_uri_frozen(ui_controller):
    # Mock Path to return controlled objects
    mock_path = MagicMock()
    mock_path.__truediv__.return_value = mock_path
    mock_path.exists.return_value = True
    mock_path.as_uri.return_value = "file:///mock/meipass/assets/icons/icon.png"

    with (
        patch("sys.frozen", True, create=True),
        patch("sys._MEIPASS", "/mock/meipass", create=True),
        patch("skill_manager.controllers.ui_controller.Path", return_value=mock_path),
    ):
        uri = ui_controller.get_asset_uri("icons/icon.png")
        assert uri == "file:///mock/meipass/assets/icons/icon.png"


def test_ui_controller_open_path_windows(ui_controller, mock_app):
    with (
        patch("skill_manager.controllers.ui_controller.sys.platform", "win32"),
        patch("os.startfile", create=True) as mock_startfile,
    ):
        ui_controller.open_path("C:/test.txt")
        mock_startfile.assert_called_with("C:/test.txt")
        mock_app._set_status.assert_called_with("Opened: test.txt")


def test_ui_controller_open_path_linux(ui_controller, mock_app):
    with (
        patch("skill_manager.controllers.ui_controller.sys.platform", "linux"),
        patch("subprocess.run") as mock_run,
    ):
        ui_controller.open_path("/path/to/file")
        mock_run.assert_called_with(["xdg-open", "/path/to/file"])


def test_ui_controller_open_path_darwin(ui_controller, mock_app):
    with (
        patch("skill_manager.controllers.ui_controller.sys.platform", "darwin"),
        patch("subprocess.run") as mock_run,
    ):
        ui_controller.open_path("/path/to/file")
        mock_run.assert_called_with(["open", "/path/to/file"])


def test_ui_controller_open_path_failure(ui_controller, mock_app):
    with (
        patch("skill_manager.controllers.ui_controller.sys.platform", "win32"),
        patch("os.startfile", side_effect=OSError("Access Denied"), create=True),
    ):
        ui_controller.open_path("C:/restricted.txt")
        mock_app._set_status.assert_any_call("Failed to open C:/restricted.txt: Access Denied")


def test_ui_controller_launch_skill(ui_controller, mock_app):
    with (
        patch.object(ui_controller, "open_path") as mock_open,
        patch("skill_manager.controllers.ui_controller.capture_event") as mock_event,
    ):
        ui_controller.launch_skill("/path/to/skill")
        mock_app._set_status.assert_called_with("Launching skill: /path/to/skill")
        mock_event.assert_called_with("skill_launched")
        mock_open.assert_called_with("/path/to/skill")

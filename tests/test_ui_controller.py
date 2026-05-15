import pytest
import os
import sys
from unittest.mock import MagicMock, patch
from pathlib import Path
from PySide6.QtCore import QTimer
from skill_manager.controllers.ui_controller import UIController

@pytest.fixture
def mock_app():
    app = MagicMock()
    app._config = MagicMock()
    app._config.get.return_value = {}
    return app

@pytest.fixture
def ui_controller(mock_app):
    return UIController(mock_app)

def test_ui_controller_init(ui_controller):
    assert ui_controller._current_view == "Library"
    assert ui_controller._window_width == 1300
    assert ui_controller._window_height == 650

def test_ui_controller_save_state(ui_controller, mock_app):
    ui_controller._current_view = "QuickCopy"
    ui_controller._window_width = 1400
    ui_controller.save_ui_state()
    
    mock_app._config.set.assert_called_once()
    args = mock_app._config.set.call_args[0]
    assert args[0] == "ui_state"
    assert args[1]["current_view"] == "QuickCopy"
    assert args[1]["window_width"] == 1400

@patch("PySide6.QtCore.QTimer.start")
def test_ui_controller_trigger_save(mock_timer_start, ui_controller):
    ui_controller.trigger_save()
    mock_timer_start.assert_called_with(2000)

def test_ui_controller_get_asset_uri(ui_controller):
    # Test with logo fallback
    uri = ui_controller.get_asset_uri("logo/missing.png")
    assert uri.startswith("file://")
    assert uri.endswith("logo.png")

def test_ui_controller_open_path(ui_controller, mock_app):
    with patch("os.startfile") as mock_startfile, \
         patch("sys.platform", "win32"):
        ui_controller.open_path("C:\\test.txt")
        mock_startfile.assert_called_with("C:\\test.txt")
        mock_app._set_status.assert_called_with("Opened: test.txt")

def test_ui_controller_launch_skill(ui_controller, mock_app):
    with patch.object(ui_controller, "open_path") as mock_open:
        ui_controller.launch_skill("/path/to/skill")
        mock_app._set_status.assert_called_with("Launching skill: /path/to/skill")
        mock_open.assert_called_with("/path/to/skill")

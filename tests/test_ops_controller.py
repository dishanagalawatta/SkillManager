import pytest
import threading
from unittest.mock import MagicMock, patch
from skill_manager.controllers.ops_controller import OpsController

@pytest.fixture
def mock_app():
    app = MagicMock()
    app._selected_skill = {}
    app._archive_paths = []
    app._essential_paths = []
    app._library_model = MagicMock()
    app._quick_copy_model = MagicMock()
    app.skillModel = MagicMock()
    app._config = MagicMock()
    return app

@pytest.fixture
def ops_controller(mock_app):
    return OpsController(mock_app)

def test_ops_controller_toggle_archive(ops_controller, mock_app):
    mock_app._selected_skill = {"local_path": "/path/s", "is_archived": False}
    ops_controller.toggle_archive()
    
    assert "/path/s" in mock_app._archive_paths
    assert mock_app._selected_skill["is_archived"] is True
    mock_app._library_model._apply_filter.assert_called()
    mock_app.selectedSkillChanged.emit.assert_called()

def test_ops_controller_toggle_archive_no_path(ops_controller, mock_app):
    mock_app._selected_skill = {"name": "NoPath"}
    ops_controller.toggle_archive()
    mock_app._set_status.assert_not_called()

def test_ops_controller_toggle_essential_no_path(ops_controller, mock_app):
    mock_app._selected_skill = {"name": "NoPath"}
    ops_controller.toggle_essential()
    mock_app._set_status.assert_not_called()

@patch("skill_manager.controllers.ops_controller.delete_project_skill_folders")
@patch("skill_manager.controllers.ops_controller.QTimer.singleShot")
@patch("threading.Thread")
def test_ops_controller_delete_commands(mock_thread, mock_timer, mock_del, ops_controller, mock_app, tmp_path):
    def side_effect(target, daemon=True):
        target()
        return MagicMock()
    mock_thread.side_effect = side_effect
    
    cmd_file = tmp_path / "test.md"
    cmd_file.write_text("content")
    
    items = [{"local_path": str(cmd_file), "is_command": True}]
    ops_controller.delete_skills(items)
    
    assert not cmd_file.exists()
    mock_app._library_model.removeSkillsByPath.assert_called()

@patch("skill_manager.controllers.ops_controller.delete_project_skill_folders")
@patch("skill_manager.controllers.ops_controller.QTimer.singleShot")
@patch("threading.Thread")
def test_ops_controller_delete_skills(mock_thread, mock_timer, mock_del, ops_controller, mock_app):
    # Mock thread to run immediately and return a mock object for .start()
    def side_effect(target, daemon=True):
        target()
        return MagicMock()
    mock_thread.side_effect = side_effect
    mock_del.return_value = {"deleted": 1, "failed": 0}
    
    items = [{"local_path": "/p1", "is_command": False}]
    ops_controller.delete_skills(items)
    
    mock_app._library_model.removeSkillsByPath.assert_called_with(["/p1"])
    mock_app._quick_copy_model.removeSkillsByPath.assert_called_with(["/p1"])
    mock_del.assert_called_once()
    mock_timer.assert_called()

@patch("skill_manager.core.copier.copy_skill_folders_to_targets")
@patch("skill_manager.controllers.ops_controller.QTimer.singleShot")
@patch("threading.Thread")
def test_ops_controller_copy_selected(mock_thread, mock_timer, mock_copy, ops_controller, mock_app):
    # Mock timer to run callback immediately
    def timer_side_effect(msec, context, method):
        if callable(member := method): member()
    mock_timer.side_effect = timer_side_effect
    
    def thread_side_effect(target, daemon=True):
        target()
        return MagicMock()
    mock_thread.side_effect = thread_side_effect
    mock_copy.return_value = {'copied': 1, 'merged': 0}
    
    mock_app.skillModel.getSelectedPaths.return_value = ["/p1"]
    mock_app.skillModel._all_skills = [{"local_path": "/p1", "name": "S1"}]
    
    ops_controller.copy_selected_to_target("/target")
    
    mock_copy.assert_called_once()
    mock_app._set_status.assert_any_call("Copy complete: 1 new")
    mock_timer.assert_called()

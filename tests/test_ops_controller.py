import json
from unittest.mock import MagicMock, patch

import pytest

from skill_manager.controllers.ops_controller import OpsController


@pytest.fixture
def ops_controller(mock_app):
    return OpsController(mock_app)


def test_ops_controller_toggle_archive(ops_controller, mock_app):
    mock_app._selected_skill = {"local_path": "/path/s", "is_archived": False}
    with patch("skill_manager.controllers.ops_controller.save_archive") as mock_save:
        ops_controller.toggle_archive()

        assert "/path/s" in mock_app._archive_paths
        assert mock_app._selected_skill["is_archived"] is True
        mock_app._library_model._apply_filter.assert_called()
        mock_app.selectedSkillChanged.emit.assert_called()
        mock_save.assert_called_with(mock_app._archive_paths)


def test_ops_controller_toggle_archive_restore(ops_controller, mock_app):
    mock_app._selected_skill = {"local_path": "/path/s", "is_archived": True}
    mock_app._archive_paths = ["/path/s"]
    with patch("skill_manager.controllers.ops_controller.save_archive") as mock_save:
        ops_controller.toggle_archive()

        assert "/path/s" not in mock_app._archive_paths
        assert mock_app._selected_skill["is_archived"] is False
        mock_save.assert_called_with(mock_app._archive_paths)


def test_ops_controller_toggle_archive_no_skill(ops_controller, mock_app):
    mock_app._selected_skill = None
    ops_controller.toggle_archive()
    mock_app.selectedSkillChanged.emit.assert_not_called()


def test_ops_controller_toggle_archive_no_path(ops_controller, mock_app):
    mock_app._selected_skill = {"name": "NoPath"}
    ops_controller.toggle_archive()
    mock_app.selectedSkillChanged.emit.assert_not_called()


def test_ops_controller_toggle_starred(ops_controller, mock_app):
    mock_app._selected_skill = {"local_path": "/path/e", "is_starred": False}
    with patch("skill_manager.controllers.ops_controller.save_starred") as mock_save:
        ops_controller.toggle_starred()

        assert "/path/e" in mock_app._starred_paths
        assert mock_app._selected_skill["is_starred"] is True
        mock_save.assert_called_with(mock_app._starred_paths)


def test_ops_controller_toggle_starred_remove(ops_controller, mock_app):
    mock_app._selected_skill = {"local_path": "/path/e", "is_starred": True}
    mock_app._starred_paths = ["/path/e"]
    with patch("skill_manager.controllers.ops_controller.save_starred") as mock_save:
        ops_controller.toggle_starred()

        assert "/path/e" not in mock_app._starred_paths
        assert mock_app._selected_skill["is_starred"] is False
        mock_save.assert_called_with(mock_app._starred_paths)


def test_ops_controller_toggle_starred_no_path(ops_controller, mock_app):
    mock_app._selected_skill = {"name": "NoPath"}
    ops_controller.toggle_starred()
    mock_app.selectedSkillChanged.emit.assert_not_called()


@patch("skill_manager.controllers.ops_controller.delete_project_skill_folders")
@patch("skill_manager.controllers.ops_controller.QTimer.singleShot")
@patch("threading.Thread")
def test_ops_controller_delete_commands(
    mock_thread, mock_timer, mock_del, ops_controller, mock_app, tmp_path
):
    def side_effect(target, daemon=True):
        target()
        return MagicMock()

    mock_thread.side_effect = side_effect

    cmd_file = tmp_path / "test.md"
    cmd_file.write_text("content")

    items = [{"local_path": str(cmd_file), "is_command": True}]
    with patch.object(ops_controller, "_patch_cache_remove") as mock_patch:
        ops_controller.delete_skills(items)
        assert not cmd_file.exists()
        mock_patch.assert_called_with([str(cmd_file)])


@patch("skill_manager.controllers.ops_controller.delete_project_skill_folders")
@patch("skill_manager.controllers.ops_controller.QTimer.singleShot")
@patch("threading.Thread")
def test_ops_controller_delete_skills(mock_thread, mock_timer, mock_del, ops_controller, mock_app):
    def side_effect(target, daemon=True):
        target()
        return MagicMock()

    mock_thread.side_effect = side_effect
    mock_del.return_value = {"deleted": 1, "failed": 0}

    items = [{"local_path": "/p1", "is_command": False}]
    with patch.object(ops_controller, "_patch_cache_remove") as mock_patch:
        ops_controller.delete_skills(items)
        mock_app._library_model.removeSkillsByPath.assert_called_with(["/p1"])
        mock_del.assert_called_once()
        mock_patch.assert_called_with(["/p1"])


def test_ops_controller_patch_cache_remove(ops_controller, tmp_path):
    cache_file = tmp_path / "cache.json"
    cache_data = {"skills": [{"local_path": "/p1"}, {"local_path": "/p2"}]}
    cache_file.write_text(json.dumps(cache_data))

    with patch("skill_manager.core.config.SKILL_LIBRARY_CACHE_FILE", str(cache_file)):
        ops_controller._patch_cache_remove(["/p1"])

        updated_data = json.loads(cache_file.read_text())
        assert len(updated_data["skills"]) == 1
        assert updated_data["skills"][0]["local_path"] == "/p2"


def test_ops_controller_cleanup_temp_copies(ops_controller, tmp_path):
    temp_dir = tmp_path / "temp_skill"
    temp_dir.mkdir()
    temp_file = tmp_path / "temp_file.txt"
    temp_file.write_text("temp")

    with (
        patch(
            "skill_manager.controllers.ops_controller.load_temp_registry",
            return_value=[str(temp_dir), str(temp_file)],
        ),
        patch("skill_manager.controllers.ops_controller.save_temp_registry") as mock_save,
    ):
        ops_controller.cleanup_temp_copies()

        assert not temp_dir.exists()
        assert not temp_file.exists()
        mock_save.assert_called_with([])


@patch("skill_manager.core.copier.copy_skill_folders_to_projects")
@patch("skill_manager.controllers.ops_controller.QTimer.singleShot")
@patch("threading.Thread")
def test_ops_controller_copy_selected(mock_thread, mock_timer, mock_copy, ops_controller, mock_app):
    def thread_side_effect(target, daemon=True):
        target()
        return MagicMock()

    mock_thread.side_effect = thread_side_effect
    mock_copy.return_value = {"copied": 1, "merged": 0, "details": []}

    mock_app.skillModel.getSelectedPaths.return_value = ["/p1"]
    mock_app.skillModel._all_skills = [{"local_path": "/p1", "name": "S1"}]

    ops_controller.copy_selected_to_project("/project")

    mock_copy.assert_called_once()
    mock_app._set_status.assert_any_call("Copying 1 skills...")


@patch("skill_manager.core.copier.copy_skill_folders_to_projects")
@patch("skill_manager.controllers.ops_controller.QTimer.singleShot")
@patch("threading.Thread")
def test_ops_controller_copy_selected_temporary(
    mock_thread, mock_timer, mock_copy, ops_controller, mock_app
):
    def thread_side_effect(target, daemon=True):
        target()
        return MagicMock()

    mock_thread.side_effect = thread_side_effect
    mock_copy.return_value = {
        "copied": 1,
        "merged": 0,
        "details": [{"status": "copied", "message": "/project/S1"}],
    }

    mock_app.skillModel.getSelectedPaths.return_value = ["/p1"]
    mock_app.skillModel._all_skills = [{"local_path": "/p1", "name": "S1"}]

    with (
        patch("skill_manager.controllers.ops_controller.load_temp_registry", return_value=[]),
        patch("skill_manager.controllers.ops_controller.save_temp_registry") as mock_save,
    ):
        ops_controller.copy_selected_to_project("/project", is_temporary=True)

        mock_save.assert_called_with(["/project/S1"])

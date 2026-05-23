from unittest.mock import patch

import pytest

from skill_manager.controllers.ops_controller import OpsController


@pytest.fixture
def ops_controller(mock_app):
    return OpsController(mock_app)


def test_ops_controller_toggle_archive(ops_controller, mock_app):
    mock_app._selected_skill = {"local_path": "/path/s", "is_archived": False}
    with patch("skill_manager.controllers.ops_controller.save_archive") as mock_save:
        ops_controller.toggleArchive()

        assert "/path/s" in mock_app._archive_paths
        assert mock_app._selected_skill["is_archived"] is True
        mock_app.selectedSkillChanged.emit.assert_called()
        mock_save.assert_called_with(mock_app._archive_paths)


def test_ops_controller_toggle_archive_restore(ops_controller, mock_app):
    mock_app._selected_skill = {"local_path": "/path/s", "is_archived": True}
    mock_app._archive_paths = ["/path/s"]
    with patch("skill_manager.controllers.ops_controller.save_archive") as mock_save:
        ops_controller.toggleArchive()

        assert "/path/s" not in mock_app._archive_paths
        assert mock_app._selected_skill["is_archived"] is False
        mock_save.assert_called_with(mock_app._archive_paths)


def test_ops_controller_toggle_archive_no_skill(ops_controller, mock_app):
    mock_app._selected_skill = None
    ops_controller.toggleArchive()
    mock_app.selectedSkillChanged.emit.assert_not_called()


def test_ops_controller_toggle_archive_no_path(ops_controller, mock_app):
    mock_app._selected_skill = {"name": "NoPath"}
    ops_controller.toggleArchive()
    mock_app.selectedSkillChanged.emit.assert_not_called()


def test_ops_controller_toggle_starred(ops_controller, mock_app):
    mock_app._selected_skill = {"local_path": "/path/e", "is_starred": False}
    with patch("skill_manager.controllers.ops_controller.save_starred") as mock_save:
        ops_controller.toggleStarred()

        assert "/path/e" in mock_app._starred_paths
        assert mock_app._selected_skill["is_starred"] is True
        mock_save.assert_called_with(mock_app._starred_paths)


def test_ops_controller_toggle_starred_remove(ops_controller, mock_app):
    mock_app._selected_skill = {"local_path": "/path/e", "is_starred": True}
    mock_app._starred_paths = ["/path/e"]
    with patch("skill_manager.controllers.ops_controller.save_starred") as mock_save:
        ops_controller.toggleStarred()

        assert "/path/e" not in mock_app._starred_paths
        assert mock_app._selected_skill["is_starred"] is False
        mock_save.assert_called_with(mock_app._starred_paths)


def test_ops_controller_toggle_starred_no_path(ops_controller, mock_app):
    mock_app._selected_skill = {"name": "NoPath"}
    ops_controller.toggleStarred()
    mock_app.selectedSkillChanged.emit.assert_not_called()


@patch("skill_manager.controllers.ops_controller.delete_project_skill_folders")
@patch("skill_manager.controllers.ops_controller.QTimer.singleShot")
def test_ops_controller_delete_commands(mock_timer, mock_del, ops_controller, mock_app, tmp_path):
    cmd_file = tmp_path / "test.md"
    cmd_file.write_text("content")

    items = [{"local_path": str(cmd_file), "is_command": True}]
    with patch("skill_manager.controllers.ops_controller.patch_cache_remove") as mock_patch:
        ops_controller.deleteSkills(items)
        assert not cmd_file.exists()
        mock_patch.assert_called_with([str(cmd_file)])


@patch("skill_manager.controllers.ops_controller.delete_project_skill_folders")
@patch("skill_manager.controllers.ops_controller.QTimer.singleShot")
def test_ops_controller_delete_skills(mock_timer, mock_del, ops_controller, mock_app):
    mock_del.return_value = {
        "deleted": 1,
        "failed": 0,
        "details": [{"path": "/p1", "status": "deleted"}],
    }

    items = [{"local_path": "/p1", "is_command": False}]
    with patch("skill_manager.controllers.ops_controller.patch_cache_remove") as mock_patch:
        ops_controller.deleteSkills(items)
        mock_del.assert_called_once()
        mock_patch.assert_called_with(["/p1"])


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
def test_ops_controller_copy_selected(mock_timer, mock_copy, ops_controller, mock_app):
    mock_copy.return_value = {"copied": 1, "merged": 0, "details": []}

    mock_app.skillModel.getSelectedPaths.return_value = ["/p1"]
    mock_app.skillModel._all_skills = [{"local_path": "/p1", "name": "S1"}]

    ops_controller.copySelectedSkillsToProject("/project")

    mock_copy.assert_called_once()
    mock_app._set_status.assert_any_call("Copying 1 skills...")


@patch("skill_manager.core.copier.copy_skill_folders_to_projects")
@patch("skill_manager.controllers.ops_controller.QTimer.singleShot")
def test_ops_controller_copy_selected_temporary(mock_timer, mock_copy, ops_controller, mock_app):
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
        ops_controller.copySelectedSkillsToProject("/project", is_temporary=True)

        mock_save.assert_called_with(["/project/S1"])


def test_ops_controller_update_models_source(ops_controller, mock_app):
    skill_library = {"local_path": "/path/s", "is_archived": False, "is_starred": False}
    skill_quick_copy = {"local_path": "/path/s", "is_archived": False, "is_starred": False}

    mock_app._library_model._all_skills = [skill_library]
    mock_app._quick_copy_model._all_skills = [skill_quick_copy]

    ops_controller._updateModelsSource("/path/s", "is_archived", True)

    assert skill_library["is_archived"] is True
    assert skill_quick_copy["is_archived"] is True


def test_ops_controller_toggle_archive_updates_all_skills_list(ops_controller, mock_app):
    mock_app._selected_skill = {"local_path": "/path/s", "is_archived": False}
    skill_library = {"local_path": "/path/s", "is_archived": False}
    skill_quick_copy = {"local_path": "/path/s", "is_archived": False}

    mock_app._library_model._all_skills = [skill_library]
    mock_app._quick_copy_model._all_skills = [skill_quick_copy]

    with patch("skill_manager.controllers.ops_controller.save_archive") as mock_save:
        ops_controller.toggleArchive()

        assert skill_library["is_archived"] is True
        assert skill_quick_copy["is_archived"] is True
        mock_save.assert_called_once()


def test_ops_controller_toggle_starred_updates_all_skills_list(ops_controller, mock_app):
    mock_app._selected_skill = {"local_path": "/path/e", "is_starred": False}
    skill_library = {"local_path": "/path/e", "is_starred": False}
    skill_quick_copy = {"local_path": "/path/e", "is_starred": False}

    mock_app._library_model._all_skills = [skill_library]
    mock_app._quick_copy_model._all_skills = [skill_quick_copy]

    with patch("skill_manager.controllers.ops_controller.save_starred") as mock_save:
        ops_controller.toggleStarred()

        assert skill_library["is_starred"] is True
        assert skill_quick_copy["is_starred"] is True
        mock_save.assert_called_once()


@patch("skill_manager.core.copier.copy_skill_folders_to_projects")
@patch("skill_manager.controllers.ops_controller.QTimer.singleShot")
def test_ops_controller_copy_selected_targeted_discovery_and_dynamic_update(
    mock_timer, mock_copy, ops_controller, mock_app
):
    mock_copy.return_value = {
        "copied": 1,
        "merged": 0,
        "details": [{"status": "copied", "message": "/project/S1", "project": "/project"}],
    }

    mock_app.skillModel.getSelectedPaths.return_value = ["/p1"]
    mock_app.skillModel._all_skills = [{"local_path": "/p1", "name": "S1"}]
    mock_app._sources = []
    mock_app._projects = ["/project"]
    mock_app._archive_paths = []
    mock_app._starred_paths = []
    mock_app._project_aliases = {}
    mock_app._categories = ["General"]

    # Mock discover_single_skill to return a mock skill dict
    mock_skill_data = {
        "local_path": "/project/S1",
        "name": "S1",
        "category": "Development",
        "project_label": "Project S1",
    }

    # Intercept QTimer.singleShot callback execution
    timer_callbacks = []

    def mock_single_shot(ms, obj, callback):
        timer_callbacks.append(callback)

    mock_timer.side_effect = mock_single_shot

    with (
        patch(
            "skill_manager.core.discovery.DiscoveryService.discover_single_skill",
            return_value=mock_skill_data,
        ) as mock_discover,
        patch("skill_manager.controllers.ops_controller.patch_cache_add") as mock_patch_cache,
    ):
        ops_controller.copySelectedSkillsToProject("/project")

        mock_copy.assert_called_once()
        mock_discover.assert_called_once()
        mock_patch_cache.assert_called_once_with([mock_skill_data])

        # Execute singleShot callbacks to verify UI updates
        for cb in timer_callbacks:
            cb()

        # Check QML models updated surgically
        mock_app._library_model.addOrUpdateSkills.assert_called_once_with([mock_skill_data])
        mock_app._quick_copy_model.addOrUpdateSkills.assert_called_once_with([mock_skill_data])
        assert "Development" in mock_app._categories


def test_ops_controller_copy_selected_no_project(ops_controller, mock_app):
    ops_controller.copySelectedSkillsToProject("")
    mock_app._set_status.assert_not_called()


def test_ops_controller_copy_selected_no_selection(ops_controller, mock_app):
    mock_app.skillModel.getSelectedPaths.return_value = []
    ops_controller.copySelectedSkillsToProject("/project")
    mock_app._set_status.assert_called_with("No skills selected to copy")


@patch("skill_manager.core.copier.copy_skill_folders_to_projects")
@patch("skill_manager.controllers.ops_controller.QTimer.singleShot")
def test_ops_controller_copy_selected_exception(mock_timer, mock_copy, ops_controller, mock_app):
    # Execute singleShot callbacks immediately
    mock_timer.side_effect = lambda ms, obj, cb: cb()

    mock_copy.side_effect = RuntimeError("Disk full")
    mock_app.skillModel.getSelectedPaths.return_value = ["/p1"]
    mock_app.skillModel._all_skills = [{"local_path": "/p1"}]

    ops_controller.copySelectedSkillsToProject("/project")

    mock_app._set_status.assert_called_with("Copy failed: Disk full")


@patch("skill_manager.controllers.ops_controller.delete_project_skill_folders")
@patch("skill_manager.controllers.ops_controller.QTimer.singleShot")
def test_ops_controller_delete_skills_partial_failure(mock_timer, mock_del, ops_controller, mock_app):
    # Execute singleShot callbacks immediately
    mock_timer.side_effect = lambda ms, obj, cb: cb()

    # Simulate 1 deleted, 1 failed
    mock_del.return_value = {
        "deleted": 1,
        "failed": 1,
        "details": [{"path": "/p1", "status": "deleted"}],
    }

    items = [{"local_path": "/p1"}, {"local_path": "/p2"}]
    ops_controller.deleteSkills(items)

    mock_app._set_status.assert_called_with("Deletion complete: 1 deleted, 1 failed")

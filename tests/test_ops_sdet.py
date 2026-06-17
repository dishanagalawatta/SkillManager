from unittest.mock import MagicMock, patch

import pytest

from skill_manager.controllers.ops_controller import OpsController


@pytest.fixture
def mock_app():
    app = MagicMock()
    app._library_model = MagicMock()
    app._quick_copy_model = MagicMock()
    app.skillModel = MagicMock()
    app.config_controller = MagicMock()
    app.ui_controller = MagicMock()
    app.task_runner = MagicMock()

    app._archive_paths = []
    app._starred_paths = []
    app._selected_skill = None

    # Mock task_runner to run immediately
    app.task_runner.run.side_effect = lambda f: f()

    return app


@pytest.fixture
def controller(mock_app):
    with patch("skill_manager.controllers.ops_controller.QTimer.singleShot") as mock_timer:
        # Simulate immediate execution of the functor
        mock_timer.side_effect = lambda msec, functor: functor()
        return OpsController(mock_app)


class TestOpsControllerSDET:
    def test_toggle_archive_success(self, controller, mock_app):
        # Setup
        path = "/path/to/skill"
        mock_app._selected_skill = {"local_path": path, "is_archived": False}
        mock_app._library_model.updateSkillProperty.return_value = True
        mock_app._quick_copy_model.updateSkillProperty.return_value = True

        # Act
        controller.toggleArchive()

        # Assert
        assert path in mock_app._archive_paths
        assert mock_app._selected_skill["is_archived"] is True
        mock_app._library_model.updateSkillProperty.assert_called_with(path, "is_archived", True)
        mock_app._quick_copy_model.updateSkillProperty.assert_called_with(path, "is_archived", True)
        mock_app.selectedSkillChanged.emit.assert_called()

    def test_toggle_starred_off(self, controller, mock_app):
        # Setup
        path = "/path/to/starred"
        mock_app._starred_paths = [path]
        mock_app._selected_skill = {"local_path": path, "is_starred": True}
        mock_app._library_model.updateSkillProperty.return_value = True

        # Act
        controller.toggleStarred()

        # Assert
        assert path not in mock_app._starred_paths
        assert mock_app._selected_skill["is_starred"] is False
        mock_app._library_model.updateSkillProperty.assert_called_with(path, "is_starred", False)

    def test_delete_skills_with_validation(self, controller, mock_app):
        # Setup
        valid_item = {
            "name": "Skill 1",
            "local_path": "/path/1",
            "project_path": "/proj",
            "category": "Cat",
        }
        invalid_item = {"missing": "fields"}

        items = [valid_item, invalid_item]

        with patch(
            "skill_manager.controllers.ops_controller.delete_project_skill_folders"
        ) as mock_delete_fs:
            mock_delete_fs.return_value = {
                "deleted": 1,
                "failed": 0,
                "details": [{"path": "/path/1", "status": "deleted"}],
            }

            # Act
            controller.deleteSkills(items)

            # Assert
            # Should only process valid_item
            mock_app._library_model.removeSkillsByPath.assert_called_with(["/path/1"])
            mock_delete_fs.assert_called_once()
            args = mock_delete_fs.call_args[0][0]
            assert len(args) == 1
            assert args[0]["local_path"] == "/path/1"

    def test_delete_mixed_items(self, controller, mock_app, tmp_path):
        # Setup
        skill_path = tmp_path / "skill_dir"
        cmd_path = tmp_path / "cmd.CLI.md"
        cmd_path.touch()

        items = [
            {
                "name": "Skill",
                "local_path": str(skill_path),
                "project_path": str(tmp_path),
                "is_command": False,
            },
            {
                "name": "Cmd",
                "local_path": str(cmd_path),
                "project_path": str(tmp_path),
                "is_command": True,
            },
        ]

        with patch(
            "skill_manager.controllers.ops_controller.delete_project_skill_folders"
        ) as mock_delete_fs:
            mock_delete_fs.return_value = {"deleted": 1, "failed": 0, "details": []}

            # Act
            controller.deleteSkills(items)

            # Assert
            # Filesystem check for command
            assert not cmd_path.exists()
            # FS call check for skill
            mock_delete_fs.assert_called_once()

    def test_archive_selected_skills(self, controller, mock_app):
        # Setup
        mock_app.skillModel.getSelectedPaths.return_value = ["/path/1", "/path/2"]
        mock_app._archive_paths = []

        # Act
        controller.archiveSelectedSkills()

        # Assert
        assert "/path/1" in mock_app._archive_paths
        assert "/path/2" in mock_app._archive_paths
        assert mock_app._library_model.updateSkillProperty.call_count == 2
        mock_app.skillModel.clearSelection.assert_called_once()

    def test_update_models_property_no_match(self, controller, mock_app):
        # Setup
        mock_app._library_model.updateSkillProperty.return_value = False
        mock_app._quick_copy_model.updateSkillProperty.return_value = False

        # Act
        controller._updateModelsProperty("/non/existent", "is_starred", True)

        # Assert
        mock_app._library_model.updateSkillProperty.assert_called()
        # No crashes, just silent

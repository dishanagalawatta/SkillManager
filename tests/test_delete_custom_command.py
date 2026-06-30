"""Tests for deleting custom commands — verifies both the ops_controller Slot and Pydantic validation."""

from unittest.mock import patch

import pytest

from skill_manager.controllers.ops_controller import OpsController


@pytest.fixture
def ops_controller(mock_app):
    with patch("skill_manager.controllers.ops_controller.QTimer.singleShot") as mock_timer:
        mock_timer.side_effect = lambda msec, functor: functor()
        yield OpsController(mock_app)


def test_delete_custom_command_success(tmp_path, mock_app, ops_controller):
    """deleteCustomCommand should locate the command file, validate, and delete it."""
    # Set up temp project structure
    project_dir = tmp_path / "my_project"
    commands_dir = project_dir / ".agents" / "commands"
    commands_dir.mkdir(parents=True, exist_ok=True)

    command_file = commands_dir / "my_cmd.md"
    command_file.write_text("# My Command\n")

    assert command_file.is_file()

    # Configure project and mock label matching
    mock_app._projects = [str(project_dir)]

    with patch("skill_manager.core.commands.find_project_path_by_label", return_value=project_dir), \
         patch.object(ops_controller, "deleteSkills") as mock_delete:

        ops_controller.deleteCustomCommand("my_cmd", ["my_project_label"])

        # Verify deleteSkills was called
        mock_delete.assert_called_once()
        items = mock_delete.call_args[0][0]
        assert len(items) == 1

        # Ensure name and local_path are correct (so validation passes)
        assert items[0]["name"] == "my_cmd"
        assert items[0]["local_path"] == str(command_file)
        assert items[0]["is_command"] is True


def test_delete_custom_command_not_found(mock_app, ops_controller):
    """deleteCustomCommand with non-existent command or project should set status."""
    mock_app._projects = []

    ops_controller.deleteCustomCommand("nonexistent_cmd", ["some_project"])
    mock_app._set_status.assert_called_with("Command not found in selected projects")

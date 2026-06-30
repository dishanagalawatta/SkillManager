"""Tests for deleteSkillsByPaths — search both models, not just active view."""

from unittest.mock import patch

import pytest

from skill_manager.controllers.ops_controller import OpsController


@pytest.fixture
def ops_controller(mock_app):
    with patch("skill_manager.controllers.ops_controller.QTimer.singleShot") as mock_timer:
        mock_timer.side_effect = lambda msec, functor: functor()
        yield OpsController(mock_app)


def test_delete_by_paths_finds_in_library(mock_app, ops_controller):
    """deleteSkillsByPaths should find skills in library model even when quick copy is active."""
    skill = {"name": "S1", "local_path": "/path/s1", "is_command": False}
    mock_app._library_model._all_skills = [skill]
    mock_app._quick_copy_model._all_skills = []
    mock_app.skillModel = mock_app._quick_copy_model  # quick copy is active view

    with patch.object(ops_controller, "deleteSkills") as mock_delete:
        ops_controller.deleteSkillsByPaths(["/path/s1"])
        mock_delete.assert_called_once()
        assert mock_delete.call_args[0][0] == [skill]


def test_delete_by_paths_finds_in_quick_copy(mock_app, ops_controller):
    """deleteSkillsByPaths should find skills in quick copy model."""
    skill = {"name": "S2", "local_path": "/path/s2", "is_command": False}
    mock_app._library_model._all_skills = []
    mock_app._quick_copy_model._all_skills = [skill]
    mock_app.skillModel = mock_app._library_model  # library is active view

    with patch.object(ops_controller, "deleteSkills") as mock_delete:
        ops_controller.deleteSkillsByPaths(["/path/s2"])
        mock_delete.assert_called_once()
        assert mock_delete.call_args[0][0] == [skill]


def test_delete_by_paths_deduplicates_across_models(mock_app, ops_controller):
    """When same path exists in both models, only delete once."""
    skill = {"name": "S3", "local_path": "/path/s3", "is_command": False}
    mock_app._library_model._all_skills = [skill]
    mock_app._quick_copy_model._all_skills = [{"name": "S3b", "local_path": "/path/s3", "is_command": False}]

    with patch.object(ops_controller, "deleteSkills") as mock_delete:
        ops_controller.deleteSkillsByPaths(["/path/s3"])
        mock_delete.assert_called_once()
        # Should only have one record, not two
        assert len(mock_delete.call_args[0][0]) == 1


def test_delete_by_paths_empty_list(mock_app, ops_controller):
    """deleteSkillsByPaths with empty list should set status and return."""
    ops_controller.deleteSkillsByPaths([])
    mock_app._set_status.assert_called_with("No skills selected for deletion")


def test_delete_by_paths_no_match(mock_app, ops_controller):
    """deleteSkillsByPaths with path not found in any model should set status."""
    mock_app._library_model._all_skills = []
    mock_app._quick_copy_model._all_skills = []
    ops_controller.deleteSkillsByPaths(["/nonexistent/path"])
    mock_app._set_status.assert_called_with("No skills selected for deletion")

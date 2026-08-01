"""Tests for deleteSkillsByPaths — search both models, not just active view."""

from unittest.mock import patch

import pytest

from skill_manager.controllers.ops_controller import OpsController


@pytest.fixture
def ops_controller(mock_app):
    with patch("skill_manager.controllers.ops._helpers.QTimer.singleShot") as mock_timer:
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
    mock_app._quick_copy_model._all_skills = [
        {"name": "S3b", "local_path": "/path/s3", "is_command": False}
    ]

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


def test_delete_by_paths_dataclass_skill(mock_app, ops_controller):
    """deleteSkillsByPaths should handle dataclass Skill objects without AttributeError."""
    from skill_manager.core.models.entities import Skill

    skill_obj = Skill(name="DataClassSkill", local_path="/path/dataclass_s1")
    mock_app._library_model._all_skills = [skill_obj]
    mock_app._quick_copy_model._all_skills = []

    with patch.object(ops_controller, "deleteSkills") as mock_delete:
        ops_controller.deleteSkillsByPaths(["/path/dataclass_s1"])
        mock_delete.assert_called_once()
        assert mock_delete.call_args[0][0] == [skill_obj]


def test_delete_by_paths_direct_file_fallback(tmp_path, mock_app, ops_controller):
    """deleteSkillsByPaths should delete unindexed direct files on disk."""
    screenshot_file = tmp_path / "screenshots" / "Screenshot_123.png"
    screenshot_file.parent.mkdir(parents=True, exist_ok=True)
    screenshot_file.write_text("dummy image data")

    mock_app._library_model._all_skills = []
    mock_app._quick_copy_model._all_skills = []

    with patch.object(ops_controller, "deleteSkills") as mock_delete:
        ops_controller.deleteSkillsByPaths([str(screenshot_file)])
        mock_delete.assert_called_once()
        records = mock_delete.call_args[0][0]
        assert len(records) == 1
        assert records[0]["local_path"] == str(screenshot_file)
        assert records[0]["is_screenshot"] is True


def test_delete_skill_from_projects_screenshot(tmp_path, mock_app, ops_controller):
    """deleteSkillFromProjects should handle screenshot files under .agents/screenshots/."""
    from skill_manager.core.commands import project_label

    proj_dir = tmp_path / "my_project"
    scr_dir = proj_dir / ".agents" / "screenshots"
    scr_dir.mkdir(parents=True, exist_ok=True)
    screenshot_file = scr_dir / "Screenshot_456.png"
    screenshot_file.write_text("image content")

    mock_app._projects = [str(proj_dir)]
    label = project_label(proj_dir)

    with patch.object(ops_controller, "deleteSkills") as mock_delete:
        ops_controller.deleteSkillFromProjects(str(screenshot_file), [label])
        mock_delete.assert_called_once()
        records = mock_delete.call_args[0][0]
        assert len(records) == 1
        assert records[0]["local_path"] == str(screenshot_file)
        assert records[0]["is_screenshot"] is True


def test_delete_resets_selected_skill_and_closes_inspector(mock_app, ops_controller):
    """When the currently selected item is deleted, set_selected_skill({}) must be called to close inspector."""
    from unittest.mock import MagicMock

    skill = {"name": "S_Opened", "local_path": "/path/opened_s1", "is_command": False}
    mock_app._library_model._all_skills = [skill]
    mock_app._quick_copy_model._all_skills = []
    mock_app._selected_skill = MagicMock(local_path="/path/opened_s1")

    ops_controller.deleteSkills([skill])

    mock_app.set_selected_skill.assert_called_with({})

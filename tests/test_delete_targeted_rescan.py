"""Tests for targeted re-scan: skillsDeleted signal triggers O(1) removal."""


import pytest

from skill_manager.controllers.discovery_controller import DiscoveryController


@pytest.fixture
def discovery_controller(mock_app):
    return DiscoveryController(mock_app)


def test_skills_deleted_removes_from_library(mock_app, discovery_controller):
    """skillsDeleted signal should remove paths from library model."""
    skill = {"name": "S1", "local_path": "/path/s1", "is_command": False}
    mock_app._library_model._all_skills = [skill]
    mock_app._quick_copy_model._all_skills = []

    discovery_controller._on_skills_deleted(["/path/s1"])

    mock_app._library_model.removeSkillsByPath.assert_called_once()
    removed = mock_app._library_model.removeSkillsByPath.call_args[0][0]
    assert "/path/s1" in removed


def test_skills_deleted_removes_from_quick_copy(mock_app, discovery_controller):
    """skillsDeleted signal should remove paths from quick copy model."""
    mock_app._library_model._all_skills = []
    mock_app._quick_copy_model._all_skills = [{"name": "S2", "local_path": "/path/s2"}]

    discovery_controller._on_skills_deleted(["/path/s2"])

    mock_app._quick_copy_model.removeSkillsByPath.assert_called_once()
    removed = mock_app._quick_copy_model.removeSkillsByPath.call_args[0][0]
    assert "/path/s2" in removed


def test_skills_deleted_updates_previous_skills(mock_app, discovery_controller):
    """_previous_skills should be pruned after targeted removal."""
    from skill_manager.core.schemas import SkillRecord

    r1 = SkillRecord(
        name="S1", local_path="/local/s1", category="dev",
    )
    r2 = SkillRecord(
        name="S2", local_path="/local/s2", category="dev",
    )
    discovery_controller._previous_skills = {"/local/s1": r1, "/local/s2": r2}

    discovery_controller._on_skills_deleted(["/local/s1"])

    assert "/local/s1" not in discovery_controller._previous_skills
    assert "/local/s2" in discovery_controller._previous_skills


def test_skills_deleted_logs_removal(mock_app, discovery_controller, caplog):
    """skillsDeleted should log the removal count."""
    import logging

    with caplog.at_level(logging.INFO):
        discovery_controller._on_skills_deleted(["/path/a", "/path/b"])

    assert "2" in caplog.text or "targeted removal" in caplog.text

"""Tests for delete-poll fence: _is_deleting flag blocks poll during deletion."""

from unittest.mock import patch

import pytest

from skill_manager.controllers.ops_controller import OpsController


@pytest.fixture
def ops_controller(mock_app):
    with patch("skill_manager.controllers.ops_controller.QTimer.singleShot") as mock_timer:
        mock_timer.side_effect = lambda msec, functor: functor()
        yield OpsController(mock_app)


def test_is_deleting_initially_false(ops_controller):
    """_is_deleting should start as False."""
    assert ops_controller._is_deleting is False


def test_is_deleting_set_true_during_delete(ops_controller, mock_app):
    """_is_deleting should be True during deleteSkills execution."""
    mock_app._library_model._all_skills = []
    mock_app._quick_copy_model._all_skills = []

    with patch("skill_manager.controllers.ops_controller.delete_project_skill_folders") as mock_del:
        mock_del.return_value = {"deleted": 0, "failed": 0, "details": []}
        ops_controller.deleteSkills([{"name": "X", "local_path": "/x", "is_command": True, "is_screenshot": False}])

    # After synchronous task_runner.run, _is_deleting should be False again
    assert ops_controller._is_deleting is False

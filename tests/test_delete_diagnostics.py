"""Tests for delete diagnostics — logging, entry breadcrumbs, per-skill warnings."""

import logging
from unittest.mock import patch

import pytest

from skill_manager.controllers.ops_controller import OpsController


@pytest.fixture
def ops_controller(mock_app):
    with patch("skill_manager.controllers.ops_controller.QTimer.singleShot") as mock_timer:
        mock_timer.side_effect = lambda msec, functor: functor()
        yield OpsController(mock_app)


def test_delete_logs_entry(ops_controller, caplog):
    """deleteSkills should log entry with item count."""
    with caplog.at_level(logging.INFO):
        ops_controller.deleteSkills(
            [{"name": "X", "local_path": "/x", "is_command": True, "is_screenshot": False}]
        )

    assert "[DELETE] deleteSkills called with" in caplog.text


def test_delete_logs_warning_for_skipped(ops_controller, tmp_path, caplog):
    """deleteSkills should log warnings for skipped items."""
    # A path that is a directory (not a file) should be skipped
    d = tmp_path / "not_a_file"
    d.mkdir()
    items = [{"name": "Bad", "local_path": str(d), "is_command": True, "is_screenshot": False}]

    with caplog.at_level(logging.WARNING):
        ops_controller.deleteSkills(items)

    assert "skipped" in caplog.text.lower() or "not a file" in caplog.text.lower()


def test_delete_logs_failed_item(ops_controller, tmp_path, caplog):
    """deleteSkills should log errors for failed deletions."""
    # Create a read-only file to cause unlink failure
    f = tmp_path / "readonly.md"
    f.write_text("data")
    items = [{"name": "RO", "local_path": str(f), "is_command": True, "is_screenshot": False}]

    with (
        patch(
            "skill_manager.controllers.ops_controller.Path.unlink",
            side_effect=PermissionError("denied"),
        ),
        caplog.at_level(logging.ERROR),
    ):
        ops_controller.deleteSkills(items)

    assert "FAILED" in caplog.text or "denied" in caplog.text

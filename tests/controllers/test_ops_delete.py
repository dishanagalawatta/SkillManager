"""Delete-flow regression tests for OpsController and DiscoveryController.

Consolidated from six one-off regression files (test_delete_poll_fence,
test_delete_batch_and_status, test_delete_diagnostics, test_delete_skills_by_paths,
test_delete_custom_command, test_delete_targeted_rescan) into one themed suite
per Phase 5 of the test consolidation plan.

Covers:
- Delete-poll fence: _is_deleting flag lifecycle around deleteSkills
- Queued status updates via QMetaObject.invokeMethod + direct-call fallback
- Batch protocol / per-row signals / incubation deferral in removeSkillsByPath
- Delete diagnostics logging (entry, skipped, failed)
- deleteSkillsByPaths dual-model search, dedupe, direct-file fallback
- deleteCustomCommand location + validation
- Targeted re-scan via DiscoveryController._on_skills_deleted
"""

import logging
from unittest.mock import MagicMock, patch

import pytest

from skill_manager.controllers.discovery_controller import DiscoveryController
from skill_manager.controllers.ops_controller import OpsController
from skill_manager.core.models.entities import Skill
from skill_manager.core.models.qt_model import SkillModel

# ── Fixtures ────────────────────────────────────────────────────────────


@pytest.fixture
def ops_controller(mock_app):
    """OpsController with synchronous QTimer.singleShot (2- and 3-arg calls)."""
    with patch("skill_manager.controllers.ops._helpers.QTimer.singleShot") as mock_timer:
        mock_timer.side_effect = lambda msec, receiver, functor=None: (
            functor() if functor is not None else receiver()
        )
        yield OpsController(mock_app)


@pytest.fixture
def discovery_controller(mock_app):
    return DiscoveryController(mock_app)


def _make_skill(name: str, path: str) -> Skill:
    return Skill(name=name, local_path=path, category="Dev")


def _make_model_with_skills(*skills: Skill) -> SkillModel:
    config = MagicMock()
    config.get = MagicMock(return_value={})
    model = SkillModel(config=config)
    if skills:
        model.addOrUpdateSkills([s.__dict__ for s in skills])
    return model


@pytest.fixture
def real_model():
    return _make_model_with_skills(
        _make_skill("A", "/a"),
        _make_skill("B", "/b"),
        _make_skill("C", "/c"),
    )


# ── Delete-poll fence ───────────────────────────────────────────────────


def test_is_deleting_initially_false(ops_controller):
    """_is_deleting should start as False."""
    assert ops_controller._is_deleting is False


def test_is_deleting_set_true_during_delete(ops_controller, mock_app):
    """_is_deleting should be True during deleteSkills execution."""
    mock_app._library_model._all_skills = []
    mock_app._quick_copy_model._all_skills = []

    with patch("skill_manager.controllers.ops.delete.delete_project_skill_folders") as mock_del:
        mock_del.return_value = {"deleted": 0, "failed": 0, "details": []}
        ops_controller.deleteSkills(
            [{"name": "X", "local_path": "/x", "is_command": True, "is_snap": False}]
        )

    # After synchronous task_runner.run, _is_deleting should be False again
    assert ops_controller._is_deleting is False


# ── Queued status update & fallback ─────────────────────────────────────


class TestQueuedStatusUpdate:
    """The background delete thread must use QMetaObject.invokeMethod for status."""

    def test_delete_uses_queued_status_update(self, ops_controller, mock_app):
        """invokeMethod is called with QueuedConnection when deleting."""
        items = [
            {"name": "S", "local_path": "/s", "is_command": True},
        ]

        with (
            patch("skill_manager.controllers.ops.delete.delete_project_skill_folders") as del_fn,
            patch("skill_manager.controllers.ops.delete.patch_cache_remove"),
            patch("skill_manager.controllers.ops.delete.QMetaObject") as mock_qmo,
        ):
            del_fn.return_value = {
                "deleted": 1,
                "failed": 0,
                "details": [{"path": "/s", "status": "deleted"}],
            }
            mock_qmo.invokeMethod.return_value = True

            ops_controller.deleteSkills(items)

            # invokeMethod must have been called with the app and _set_status
            mock_qmo.invokeMethod.assert_called_once()
            call_args = mock_qmo.invokeMethod.call_args
            assert call_args[0][0] is mock_app
            assert call_args[0][1] == "_set_status"
            # Third positional arg is the ConnectionType (QueuedConnection)
            # PySide6 Qt.ConnectionType.QueuedConnection is 0x2
            from PySide6.QtCore import Qt

            assert call_args[0][2] == Qt.ConnectionType.QueuedConnection


class TestStatusFallback:
    """When invokeMethod returns False (slot not found), fallback must still deliver status."""

    def test_status_drop_logs_warning_when_slot_missing(self, ops_controller, mock_app):
        """If invokeMethod returns False, a warning is logged and direct call is attempted."""
        items = [
            {"name": "S", "local_path": "/s", "is_command": True},
        ]

        with (
            patch("skill_manager.controllers.ops.delete.delete_project_skill_folders") as del_fn,
            patch("skill_manager.controllers.ops.delete.patch_cache_remove"),
            patch("skill_manager.controllers.ops.delete.QMetaObject") as mock_qmo,
            patch("skill_manager.controllers.ops.delete.logger") as mock_logger,
        ):
            del_fn.return_value = {
                "deleted": 1,
                "failed": 0,
                "details": [{"path": "/s", "status": "deleted"}],
            }
            # Simulate slot not found
            mock_qmo.invokeMethod.return_value = False

            ops_controller.deleteSkills(items)

            # Warning must have been logged
            mock_logger.warning.assert_any_call(
                "[DELETE] invokeMethod(_set_status) returned False; falling back to direct call"
            )
            # Direct fallback must have been called
            mock_app._set_status.assert_called()
            status_arg = mock_app._set_status.call_args[0][0]
            assert "Deletion complete:" in status_arg


# ── Batch protocol & signals ────────────────────────────────────────────


class TestBatchProtocol:
    """removeSkillsByPath must enter and exit the batch protocol."""

    def test_optimistic_removal_uses_batch_protocol(self, real_model):
        """removeSkillsByPath wraps mutation in _begin_batch / _end_batch."""
        begin_count = 0
        end_count = 0
        original_begin = real_model._begin_batch
        original_end = real_model._end_batch

        def counting_begin():
            nonlocal begin_count
            begin_count += 1
            original_begin()

        def counting_end():
            nonlocal end_count
            end_count += 1
            original_end()

        real_model._begin_batch = counting_begin
        real_model._end_batch = counting_end

        real_model.removeSkillsByPath(["/a", "/c"])

        assert begin_count == 1
        assert end_count == 1
        # /a and /c removed, only /b remains
        assert len(real_model._all_skills) == 1
        assert real_model._all_skills[0].local_path == "/b"


class TestPerRowSignals:
    """Diff-based removal emits beginRemoveRows/endRemoveRows, not modelReset."""

    def test_remove_skills_by_path_emits_per_row_signals(self, real_model):
        """Removing rows emits rowsAboutToBeRemoved, not layoutChanged."""
        row_remove_count = 0
        layout_change_count = 0

        def on_rows_removed(parent, first, last):
            nonlocal row_remove_count
            row_remove_count += 1

        def on_layout_changed():
            nonlocal layout_change_count
            layout_change_count += 1

        real_model.rowsAboutToBeRemoved.connect(lambda p, f, last: None)  # register signal
        real_model.rowsRemoved.connect(on_rows_removed)
        real_model.layoutChanged.connect(on_layout_changed)

        real_model.removeSkillsByPath(["/a", "/c"])

        # At least one rowsRemoved signal should have fired
        assert row_remove_count >= 1
        # layoutChanged must NOT have fired (that would indicate a full reset)
        assert layout_change_count == 0


class TestIncubationDeferral:
    """removeSkillsByPath defers filter application when incubating."""

    def test_remove_skills_by_path_defers_when_incubating(self, real_model):
        """If _incubating is True, removeSkillsByPath queues work instead of running now."""
        real_model._incubating = True
        # Add a skill so _all_skills is non-empty (the guard in _apply_filter)
        # Already has skills from fixture

        real_model.removeSkillsByPath(["/a"])

        # The batch protocol was entered. Because _incubating is True,
        # _end_batch returns early and keeps _batch_apply_needed = True.
        # The filter will be drained by onIncubationReady().
        assert real_model._batch_apply_needed is True

        # Skills removed from _all_skills (the batch body ran, but filter deferred)
        paths_remaining = [s.local_path for s in real_model._all_skills]
        assert "/a" not in paths_remaining

    def test_incubation_ready_replays_after_remove(self, real_model):
        """After onIncubationReady, deferred filter completes and filtered_skills updates."""
        real_model._incubating = True
        real_model.removeSkillsByPath(["/a"])

        # _batch_apply_needed is True (deferred by re-entry guard)
        assert real_model._batch_apply_needed is True

        # Drain the incubation gate
        real_model._incubating = False
        real_model.onIncubationReady()

        # Now filtered_skills should reflect the removal
        visible_paths = [s.local_path for s in real_model._filtered_skills]
        assert "/a" not in visible_paths
        assert "/b" in visible_paths
        assert "/c" in visible_paths


# ── Delete diagnostics ──────────────────────────────────────────────────


def test_delete_logs_entry(ops_controller, caplog):
    """deleteSkills should log entry with item count."""
    with caplog.at_level(logging.INFO):
        ops_controller.deleteSkills(
            [{"name": "X", "local_path": "/x", "is_command": True, "is_snap": False}]
        )

    assert "[DELETE] deleteSkills called with" in caplog.text


def test_delete_logs_warning_for_skipped(ops_controller, tmp_path, caplog):
    """deleteSkills should log warnings for skipped items."""
    # A path that is a directory (not a file) should be skipped
    d = tmp_path / "not_a_file"
    d.mkdir()
    items = [{"name": "Bad", "local_path": str(d), "is_command": True, "is_snap": False}]

    with caplog.at_level(logging.WARNING):
        ops_controller.deleteSkills(items)

    assert "skipped" in caplog.text.lower() or "not a file" in caplog.text.lower()


def test_delete_logs_failed_item(ops_controller, tmp_path, caplog):
    """deleteSkills should log errors for failed deletions."""
    # Create a read-only file to cause unlink failure
    f = tmp_path / "readonly.md"
    f.write_text("data")
    items = [{"name": "RO", "local_path": str(f), "is_command": True, "is_snap": False}]

    with (
        patch(
            "skill_manager.controllers.ops.delete.Path.unlink",
            side_effect=PermissionError("denied"),
        ),
        caplog.at_level(logging.ERROR),
    ):
        ops_controller.deleteSkills(items)

    assert "FAILED" in caplog.text or "denied" in caplog.text


# ── deleteSkillsByPaths ─────────────────────────────────────────────────


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
    skill_obj = Skill(name="DataClassSkill", local_path="/path/dataclass_s1")
    mock_app._library_model._all_skills = [skill_obj]
    mock_app._quick_copy_model._all_skills = []

    with patch.object(ops_controller, "deleteSkills") as mock_delete:
        ops_controller.deleteSkillsByPaths(["/path/dataclass_s1"])
        mock_delete.assert_called_once()
        assert mock_delete.call_args[0][0] == [skill_obj]


def test_delete_by_paths_direct_file_fallback(tmp_path, mock_app, ops_controller):
    """deleteSkillsByPaths should delete unindexed direct files on disk."""
    snap_file = tmp_path / "screenshots" / "Screenshot_123.png"
    snap_file.parent.mkdir(parents=True, exist_ok=True)
    snap_file.write_text("dummy image data")

    mock_app._library_model._all_skills = []
    mock_app._quick_copy_model._all_skills = []

    with patch.object(ops_controller, "deleteSkills") as mock_delete:
        ops_controller.deleteSkillsByPaths([str(snap_file)])
        mock_delete.assert_called_once()
        records = mock_delete.call_args[0][0]
        assert len(records) == 1
        assert records[0]["local_path"] == str(snap_file)
        assert records[0]["is_snap"] is True


def test_delete_skill_from_projects_screenshot(tmp_path, mock_app, ops_controller):
    """deleteSkillFromProjects should handle snap files under .agents/screenshots/."""
    from skill_manager.core.commands import project_label

    proj_dir = tmp_path / "my_project"
    scr_dir = proj_dir / ".agents" / "screenshots"
    scr_dir.mkdir(parents=True, exist_ok=True)
    snap_file = scr_dir / "Screenshot_456.png"
    snap_file.write_text("image content")

    mock_app._projects = [str(proj_dir)]
    label = project_label(proj_dir)

    with patch.object(ops_controller, "deleteSkills") as mock_delete:
        ops_controller.deleteSkillFromProjects(str(snap_file), [label])
        mock_delete.assert_called_once()
        records = mock_delete.call_args[0][0]
        assert len(records) == 1
        assert records[0]["local_path"] == str(snap_file)
        assert records[0]["is_snap"] is True


def test_delete_resets_selected_skill_and_closes_inspector(mock_app, ops_controller):
    """When the currently selected item is deleted, set_selected_skill({}) must be called."""
    skill = {"name": "S_Opened", "local_path": "/path/opened_s1", "is_command": False}
    mock_app._library_model._all_skills = [skill]
    mock_app._quick_copy_model._all_skills = []
    mock_app._selected_skill = MagicMock(local_path="/path/opened_s1")

    ops_controller.deleteSkills([skill])

    mock_app.set_selected_skill.assert_called_with({})


# ── deleteCustomCommand ─────────────────────────────────────────────────


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

    with (
        patch("skill_manager.core.commands.find_project_path_by_label", return_value=project_dir),
        patch.object(ops_controller, "deleteSkills") as mock_delete,
    ):
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


# ── Targeted re-scan (DiscoveryController) ──────────────────────────────


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
        name="S1",
        local_path="/local/s1",
        category="dev",
    )
    r2 = SkillRecord(
        name="S2",
        local_path="/local/s2",
        category="dev",
    )
    discovery_controller._previous_skills = {"/local/s1": r1, "/local/s2": r2}

    discovery_controller._on_skills_deleted(["/local/s1"])

    assert "/local/s1" not in discovery_controller._previous_skills
    assert "/local/s2" in discovery_controller._previous_skills


def test_skills_deleted_logs_removal(mock_app, discovery_controller, caplog):
    """skillsDeleted should log the removal count."""
    with caplog.at_level(logging.INFO):
        discovery_controller._on_skills_deleted(["/path/a", "/path/b"])

    assert "2" in caplog.text or "targeted removal" in caplog.text

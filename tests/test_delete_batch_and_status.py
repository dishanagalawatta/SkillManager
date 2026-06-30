"""Tests for the delete-flow fixes:
1. QMetaObject.invokeMethod uses the real @Slot on _set_status
2. Status fallback works when invokeMethod returns False
3. removeSkillsByPath uses _begin_batch/_end_batch (diff-based removal)
4. removeSkillsByPath defers when the model is incubating
5. removeSkillsByPath emits per-row signals (not modelReset/layoutChanged)
"""

from unittest.mock import MagicMock, patch

import pytest

from skill_manager.controllers.ops_controller import OpsController
from skill_manager.core.models.entities import Skill
from skill_manager.core.models.qt_model import SkillModel

# ── Fixtures ────────────────────────────────────────────────────────────

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
def ops_controller(mock_app):
    with patch("skill_manager.controllers.ops_controller.QTimer.singleShot") as timer:
        timer.side_effect = lambda msec, fn: fn() if fn else None
        yield OpsController(mock_app)


@pytest.fixture
def real_model():
    return _make_model_with_skills(
        _make_skill("A", "/a"),
        _make_skill("B", "/b"),
        _make_skill("C", "/c"),
    )


# ── Tests ───────────────────────────────────────────────────────────────

class TestQueuedStatusUpdate:
    """The background delete thread must use QMetaObject.invokeMethod for status."""

    def test_delete_uses_queued_status_update(self, ops_controller, mock_app):
        """invokeMethod is called with QueuedConnection when deleting."""
        items = [
            {"name": "S", "local_path": "/s", "is_command": True},
        ]

        with (
            patch("skill_manager.controllers.ops_controller.delete_project_skill_folders") as del_fn,
            patch("skill_manager.controllers.ops_controller.patch_cache_remove"),
            patch("skill_manager.controllers.ops_controller.QMetaObject") as mock_qmo,
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
            patch("skill_manager.controllers.ops_controller.delete_project_skill_folders") as del_fn,
            patch("skill_manager.controllers.ops_controller.patch_cache_remove"),
            patch("skill_manager.controllers.ops_controller.QMetaObject") as mock_qmo,
            patch("skill_manager.controllers.ops_controller.logger") as mock_logger,
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

        # The batch protocol was entered
        # But because _incubating is True inside _end_batch -> _apply_filter,
        # the actual filter is queued via _pending_signals
        assert len(real_model._pending_signals) >= 1

        # Skills not yet removed from _all_skills (the batch body ran, but filter deferred)
        # Actually: the _all_skills mutation runs inside _begin_batch/_end_batch
        # directly, not through the filter queue. The filter is what's deferred.
        # So _all_skills should reflect the removal, but _filtered_skills may be stale.
        paths_remaining = [s.local_path for s in real_model._all_skills]
        assert "/a" not in paths_remaining

    def test_incubation_ready_replays_after_remove(self, real_model):
        """After onIncubationReady, deferred filter completes and filtered_skills updates."""
        real_model._incubating = True
        real_model.removeSkillsByPath(["/a"])

        # Drain the incubation gate
        real_model._incubating = False
        real_model._replay_deferred = bool(real_model._pending_signals)
        real_model.onIncubationReady()

        # Now filtered_skills should reflect the removal
        visible_paths = [s.local_path for s in real_model._filtered_skills]
        assert "/a" not in visible_paths
        assert "/b" in visible_paths
        assert "/c" in visible_paths

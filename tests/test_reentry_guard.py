"""Tests for the _end_batch re-entry guard in SkillModel.

The guard prevents a second mutation's layoutChanged from destroying
delegates still incubating from the first mutation's drained signals.
"""

import os
from unittest.mock import MagicMock, patch

import pytest

os.environ["SKILL_MANAGER_TESTING"] = "1"

from skill_manager.core.models.qt_model import SkillModel  # noqa: E402


@pytest.fixture
def model():
    m = SkillModel.__new__(SkillModel)
    m._all_skills = []
    m._filtered_skills = []
    m._all_filtered_skills = []
    m._selected_ids = set()
    m._suppress_layout = False
    m._batch_apply_needed = False
    m._batch_reset_needed = False
    m._incubating = False
    m._replay_deferred = False
    m._pending_signals = []
    m._reset_pending = False
    m.state = MagicMock()
    m.state.filter_text = ""
    m.state.collapsed_categories = set()
    m._engine = MagicMock()
    m._engine.prepare_rows = MagicMock(return_value=[])
    m._engine.build_visible_rows = MagicMock(return_value=[])
    m._search_engine = None
    m._incubation_timer = MagicMock()
    m.incubatingChanged = MagicMock()
    m.layoutAboutToBeChanged = MagicMock()
    m.layoutChanged = MagicMock()
    m.aboutToMutateStructure = MagicMock()
    m.structureMutated = MagicMock()
    m.selectionStateChanged = MagicMock()
    m.totalSelectableCountCountChanged = MagicMock()
    m.beginResetModel = MagicMock()
    m.endResetModel = MagicMock()
    m._cached_selected_count = 0
    m._cached_visible_selectable = 0
    m._cached_visible_selected = 0
    m._cached_total_selectable = 0
    m._save_filters = MagicMock()
    return m


class TestEndBatchReEntryGuard:
    """Tests for the re-entry guard in _end_batch."""

    def test_end_batch_defers_when_incubating(self, model):
        """_end_batch defers filter pass when _incubating is True."""
        model._all_skills = [MagicMock()]  # non-empty
        model._batch_apply_needed = True
        model._incubating = True

        model._end_batch()

        # _batch_apply_needed should still be True (deferred)
        assert model._batch_apply_needed is True
        # _suppress_layout should be False (cleared before guard)
        assert model._suppress_layout is False

    def test_end_batch_defers_when_replay_deferred(self, model):
        """_end_batch defers filter pass when _replay_deferred is True."""
        model._all_skills = [MagicMock()]
        model._batch_apply_needed = True
        model._replay_deferred = True

        model._end_batch()

        assert model._batch_apply_needed is True

    def test_end_batch_defers_when_pending_signals(self, model):
        """_end_batch defers filter pass when _pending_signals is non-empty."""
        model._all_skills = [MagicMock()]
        model._batch_apply_needed = True
        model._pending_signals.append(lambda: None)

        model._end_batch()

        assert model._batch_apply_needed is True

    def test_end_batch_runs_normally_when_not_incubating(self, model):
        """_end_batch runs filter synchronously when not incubating."""
        model._all_skills = [MagicMock()]
        model._batch_apply_needed = True
        model._incubating = False
        model._replay_deferred = False
        model._pending_signals = []
        model._batch_reset_needed = False

        with patch.object(model, "_apply_filter_with_diff") as mock_diff:
            model._end_batch()
            mock_diff.assert_called_once()

        assert model._batch_apply_needed is False

    def test_end_batch_bypasses_guard_when_model_empty(self, model):
        """_end_batch bypasses guard when _all_skills is empty."""
        model._all_skills = []  # empty
        model._batch_apply_needed = True
        model._incubating = True

        with patch.object(model, "_apply_filter_with_diff") as mock_diff:
            model._end_batch()
            mock_diff.assert_called_once()

        assert model._batch_apply_needed is False

    def test_reentry_after_drain_works_normally(self, model):
        """After incubation completes, next _end_batch runs synchronously."""
        # Mutation 1: incubating
        model._all_skills = [MagicMock()]
        model._batch_apply_needed = True
        model._incubating = True

        model._end_batch()
        assert model._batch_apply_needed is True  # deferred

        # Incubation completes
        model._incubating = False
        model._replay_deferred = False
        model._pending_signals = []

        # Mutation 2: should run synchronously
        model._batch_apply_needed = True
        model._batch_reset_needed = False

        with patch.object(model, "_apply_filter_with_diff") as mock_diff:
            model._end_batch()
            mock_diff.assert_called_once()

        assert model._batch_apply_needed is False

    def test_begin_batch_resets_flags(self, model):
        """_begin_batch sets _suppress_layout and clears batch flags."""
        model._suppress_layout = False
        model._batch_apply_needed = True
        model._batch_reset_needed = True

        model._begin_batch()

        assert model._suppress_layout is True
        assert model._batch_apply_needed is False
        assert model._batch_reset_needed is False


class TestOnIncubationReadyDrainsBatch:
    """Tests that onIncubationReady drains deferred batch flags."""

    def test_drains_batch_when_not_incubating(self, model):
        """onIncubationReady drains _batch_apply_needed if incubation is done."""
        model._replay_deferred = False
        model._batch_apply_needed = True
        model._batch_reset_needed = False
        model._incubating = False
        model._all_skills = [MagicMock()]

        with patch.object(model, "_apply_filter_with_diff") as mock_diff:
            model.onIncubationReady()
            mock_diff.assert_called_once()

        assert model._batch_apply_needed is False

    def test_does_not_drain_batch_while_incubating(self, model):
        """onIncubationReady does NOT drain batch while still incubating."""
        model._replay_deferred = False
        model._batch_apply_needed = True
        model._incubating = True

        with patch.object(model, "_apply_filter_with_diff") as mock_diff:
            model.onIncubationReady()
            mock_diff.assert_not_called()

        assert model._batch_apply_needed is True  # still deferred

    def test_drains_pending_signals(self, model):
        """onIncubationReady replays pending signals when _replay_deferred is True."""
        called = []
        model._pending_signals.append(lambda: called.append(1))
        model._pending_signals.append(lambda: called.append(2))
        model._replay_deferred = True
        model._batch_apply_needed = False
        model._incubating = False

        model.onIncubationReady()

        assert called == [1, 2]
        assert model._replay_deferred is False
        assert model._pending_signals == []

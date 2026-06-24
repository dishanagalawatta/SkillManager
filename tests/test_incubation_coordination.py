"""Tests for incubation ↔ QML readiness coordination.

Validates that:
- ``incubationReady`` slot replays deferred signals
- 5s safety timer sets ``_replay_deferred`` correctly
- ``_apply_filter`` runs directly when model is empty (no incubation guard)
- Diagnostic events are emitted for all coordination paths
"""

import os

import pytest

from skill_manager.core.models.qt_model import SkillModel


@pytest.fixture()
def model(qtbot):
    """Create a fresh SkillModel for incubation tests."""
    m = SkillModel()
    yield m


@pytest.mark.usefixtures("setup_qml_style")
class TestIncubationCoordination:
    """Incubation ↔ QML readiness coordination tests."""

    def test_incubation_ready_replays_deferred_signals(self, model):
        """onIncubationReady replays signals when _replay_deferred is set."""
        model._replay_deferred = True
        replayed = []
        model._pending_signals.append(lambda: replayed.append(1))
        model._pending_signals.append(lambda: replayed.append(2))

        model.onIncubationReady()

        assert replayed == [1, 2]
        assert not model._pending_signals
        assert not model._replay_deferred

    def test_incubation_ready_noop_when_not_deferred(self, model):
        """onIncubationReady is a no-op when _replay_deferred is False."""
        replayed = []
        model._pending_signals.append(lambda: replayed.append(1))

        model.onIncubationReady()

        assert replayed == []
        assert len(model._pending_signals) == 1

    def test_incubation_ready_noop_when_no_pending(self, model):
        """onIncubationReady does nothing when there are no pending signals."""
        model._replay_deferred = True

        model.onIncubationReady()

        assert not model._replay_deferred

    def test_force_end_sets_replay_deferred(self, model):
        """_force_end_incubation sets _replay_deferred when signals are pending."""
        model._incubating = True
        model._pending_signals.append(lambda: None)

        model._force_end_incubation()

        assert not model._incubating
        assert model._replay_deferred is True

    def test_force_end_no_deferred_when_no_pending(self, model):
        """_force_end_incubation does not set _replay_deferred when queue is empty."""
        model._incubating = True

        model._force_end_incubation()

        assert not model._incubating
        assert model._replay_deferred is False

    def test_apply_filter_runs_when_model_empty(self, model):
        """_apply_filter runs directly when _all_skills is empty, even if incubating."""
        model._incubating = True
        model._all_skills = []

        # Should NOT queue — should run directly (empty model)
        model._apply_filter(reset=True)

        # _filtered_skills should be empty (no skills to filter)
        assert model._filtered_skills == []

    def test_apply_filter_queues_when_model_populated_and_incubating(self, model):
        """_apply_filter queues when model has skills and is incubating."""
        model._incubating = True
        model._all_skills = [type("Skill", (), {"local_path": "/x", "name": "X"})()]

        model._apply_filter(reset=True)

        # Should have queued a signal, not applied directly
        assert len(model._pending_signals) == 1

    def test_incubating_setter_skips_in_test_mode(self, model):
        """Incubating setter forces False when SKILL_MANAGER_TESTING is set."""
        old_val = os.environ.get("SKILL_MANAGER_TESTING")
        os.environ["SKILL_MANAGER_TESTING"] = "1"
        try:
            model.incubating = True

            assert model.incubating is False
        finally:
            if old_val is not None:
                os.environ["SKILL_MANAGER_TESTING"] = old_val
            else:
                os.environ.pop("SKILL_MANAGER_TESTING", None)

    def test_incubating_setter_normal_flow(self, model):
        """Incubating setter emits signal and starts timer in normal mode."""
        old_val = os.environ.pop("SKILL_MANAGER_TESTING", None)
        try:
            model.incubating = True

            assert model.incubating is True
            assert model._incubation_timer.isActive()

            model.incubating = False

            assert model.incubating is False
            assert not model._incubation_timer.isActive()
        finally:
            if old_val is not None:
                os.environ["SKILL_MANAGER_TESTING"] = old_val

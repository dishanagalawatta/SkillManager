"""Incubation ↔ QML readiness coordination for the SkillModel facade.

When the model is mutated while QML is still instantiating delegate
views, ``layoutChanged`` / ``modelReset`` signals can fire on objects
that are about to be torn down — producing the benign-but-noisy
"Object or context destroyed during incubation" warning and (more
importantly) an inconsistent row count. The protocol is:

  1. C++/Python mutator calls ``incubating = True`` when a batch
     of changes is about to happen.
  2. ``_apply_filter`` / ``_apply_filter_with_diff`` notice the
     flag and queue their work as a callable on ``_pending_signals``
     instead of running it now. If ``_all_skills`` is empty the
     queue is bypassed (nothing to incubate against).
  3. Either the QML side calls ``onIncubationReady()`` once its
     delegates are rendered, or the 5s safety timer expires and
     calls ``_force_end_incubation()``.
  4. Both paths drain ``_pending_signals`` in order and clear
     ``_replay_deferred`` so the next mutation goes through.
"""

import logging
import os

from PySide6.QtCore import Property, Slot

from skill_manager.core.diagnostics import get_diagnostic_logger
from skill_manager.core.models.entities import PreparedModelState
from skill_manager.core.models.roles import RolesMixin

incubatingChanged = RolesMixin.incubatingChanged  # noqa: N816

logger = logging.getLogger(__name__)


class IncubationMixin:
    """Incubation flag, deferred-signal replay, and prepared-state swap."""

    @Property(bool, notify=incubatingChanged)
    def incubating(self):  # type: ignore[reportRedeclaration]
        return self._incubating

    @incubating.setter  # type: ignore[func-attr]
    def incubating(self, value):
        if os.environ.get("SKILL_MANAGER_TESTING") == "1":
            # Tests must run synchronously: force the flag off so the
            # pending-signal queue is bypassed and the model resolves
            # immediately. The signal still fires so QML test stubs
            # that listen for the transition can observe it.
            self._incubating = False
            self.incubatingChanged.emit()
            return
        if self._incubating != value:
            self._incubating = value
            self.incubatingChanged.emit()
            if value:
                self._incubation_timer.start()
            else:
                self._incubation_timer.stop()

    @Slot()
    def onIncubationReady(self):
        """QML calls this slot once its delegate views are instantiated.

        Replays any signals we deferred while ``_incubating`` was True.
        No-op if nothing was deferred.
        """
        logger.debug(
            "onIncubationReady: replay=%s pending=%d batch_apply=%s",
            self._replay_deferred,
            len(self._pending_signals),
            self._batch_apply_needed,
        )
        if self._replay_deferred:
            self._replay_pending_signals()
            self._replay_deferred = False
        # If _end_batch was deferred (batch_apply still set) and we're now
        # past incubation, drain the batch filter pass immediately.
        if self._batch_apply_needed and not self._incubating:
            logger.debug("onIncubationReady: draining deferred batch")
            self._batch_apply_needed = False
            if self._batch_reset_needed:
                self._apply_filter(reset=True)
            else:
                self._apply_filter_with_diff()

    def _force_end_incubation(self):
        """End the incubation window and arm deferred replay.

        Called either by the 5s safety timer or by a layout commit that
        has just settled. Sets ``_replay_deferred`` only if there are
        actually pending signals to replay — otherwise the next mutation
        would re-arm a no-op round-trip.
        """
        logger.debug(
            "_force_end_incubation: incubating=%s pending=%d",
            self._incubating,
            len(self._pending_signals),
        )
        if not self._incubating and not self._pending_signals:
            return
        self._incubating = False
        self._replay_deferred = bool(self._pending_signals)
        self._incubation_timer.stop()
        self.incubatingChanged.emit()

    def _replay_pending_signals(self):
        """Execute and clear all queued signal emitters in FIFO order."""
        pending = self._pending_signals
        self._pending_signals = []
        for emit in pending:
            try:
                emit()
            except Exception as e:  # noqa: BLE001 — defensive: one bad emitter must not break the rest
                logger.warning("Error replaying deferred signal: %s", e)

    def replacePreparedState(self, state: PreparedModelState) -> bool:
        """Swap in a fully pre-computed model state in a single reset.

        Called from the main thread after a background thread has already done
        all the heavy lifting: Skill construction, FilterEngine pass,
        SearchEngine build, row preparation, and visibility calculation.

        The internal data is set immediately, but the actual
        ``beginResetModel``/``endResetModel`` is deferred via
        ``Qt.callLater`` so that QML can process the
        ``aboutToMutateStructure`` signal (which zeros ``cacheBuffer``)
        before delegates are destroyed.  This prevents the "Object
        destroyed during incubation" warning.

        If the model is currently incubating, the reset is queued behind
        the existing pending-signal queue instead.

        Cancellation is handled by the caller (DiscoveryController) before
        emitting the signal.
        """
        if self._incubating and self._all_skills:
            diag = get_diagnostic_logger()
            diag.log_event(
                "DEBUG",
                "replace_prepared_state_deferred",
                f"Deferring replacePreparedState — incubating, "
                f"{len(state.all_skills)} skills waiting",
            )
            self._pending_signals.append(lambda s=state: self._apply_prepared_state_now(s))
            return True

        if not self._all_skills:
            # If the model is completely empty (e.g., at startup), there are no existing
            # delegates to protect. Apply synchronously to ensure initial population and
            # subsequent startup filters happen in the same tick, avoiding split-tick race conditions.
            self._apply_prepared_state_now(state)
            return True

        # Phase 1: set internal data and signal QML to abort incubators.
        self._all_skills = state.all_skills
        self._search_engine = state.search_engine
        self._all_filtered_skills = state.all_filtered_skills
        self._filtered_skills = state.visible_rows

        self.aboutToMutateStructure.emit()
        self._reset_pending = True

        # Phase 2: defer the actual model reset so QML can process
        # aboutToMutateStructure (zero cacheBuffer) before delegates
        # are destroyed by beginResetModel.
        def _deferred_reset():
            self._reset_pending = False
            self.beginResetModel()
            self.endResetModel()
            self.structureMutated.emit()
            self._update_selection_counts()
            self.selectionStateChanged.emit()
            self.totalSelectableCountChanged.emit()

        from PySide6.QtCore import QTimer

        QTimer.singleShot(0, _deferred_reset)

        return True

    def _apply_prepared_state_now(self, state: PreparedModelState) -> None:
        """Apply a pre-computed model state immediately via a single reset.

        Extracted from ``replacePreparedState`` so it can be called either
        directly (when not incubating) or replayed from the deferred queue.
        """
        self._all_skills = state.all_skills
        self._search_engine = state.search_engine
        self._all_filtered_skills = state.all_filtered_skills
        self._filtered_skills = state.visible_rows

        self.aboutToMutateStructure.emit()
        self.beginResetModel()
        self.endResetModel()
        self.structureMutated.emit()
        self._update_selection_counts()
        self.selectionStateChanged.emit()
        self.totalSelectableCountChanged.emit()

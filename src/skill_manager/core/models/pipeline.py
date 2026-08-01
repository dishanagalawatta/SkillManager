"""Filter pipeline for the SkillModel facade.

Dispatch/apply of filter passes (with incubation-aware deferral),
batch suppression via ``_begin_batch``/``_end_batch``, the synchronous
filter logic, and the collapse checks shared with the selection and
``data()`` code.
"""

import logging
import os

from PySide6.QtCore import QModelIndex

from skill_manager.core.models.entities import Skill

logger = logging.getLogger(__name__)


class PipelineMixin:
    """Filter pipeline, batch suppression, and collapse checks."""

    def _apply_filter(self, reset=False):
        """Dispatch a filter pass — run now or queue behind incubation.

        Three gates, in priority order:

        1. ``_suppress_layout`` is True (we're inside a ``_begin_batch``
           block) → defer to ``_end_batch()`` via the batch flag.
        2. ``_incubating`` is True AND the model has skills → QML is
           not ready yet, queue the work for ``onIncubationReady``.
        3. Otherwise → run the filter synchronously.
        """
        if self._suppress_layout:
            self._batch_apply_needed = True
            if reset:
                self._batch_reset_needed = True
            return

        if self._incubating and self._all_skills:
            self._pending_signals.append(lambda r=reset: self._do_apply_filter_now(r))
            return

        self._do_apply_filter_now(reset)

    def _do_apply_filter_now(self, reset=False):
        """Applies filters and updates the model synchronously (with deferred signals)."""
        try:
            skills = self._execute_filter_logic()
            new_all_filtered = self._engine.prepare_rows(skills)
            new_filtered = self._engine.build_visible_rows(
                new_all_filtered, self.state.collapsed_categories
            )
        except Exception as e:
            logger.error("Error applying filter: %s", e)
            return

        self._all_filtered_skills = new_all_filtered
        self._filtered_skills = new_filtered

        if self._reset_pending:
            return

        if os.environ.get("SKILL_MANAGER_TESTING") == "1":
            # Run synchronously in tests so assertions pass immediately
            self.aboutToMutateStructure.emit()
            if reset:
                self.beginResetModel()
                self.endResetModel()
            else:
                self.layoutAboutToBeChanged.emit()
                self.layoutChanged.emit()
            self.structureMutated.emit()
            self._update_selection_counts()
            self.selectionStateChanged.emit()
            self.totalSelectableCountChanged.emit()
            return

        self.aboutToMutateStructure.emit()
        self._reset_pending = True

        def _deferred_apply():
            self._reset_pending = False
            if reset:
                self.beginResetModel()
                self.endResetModel()
            else:
                self.layoutAboutToBeChanged.emit()
                self.layoutChanged.emit()

            self.structureMutated.emit()
            self._update_selection_counts()
            self.selectionStateChanged.emit()
            self.totalSelectableCountChanged.emit()

        from PySide6.QtCore import QTimer

        QTimer.singleShot(0, _deferred_apply)

    def _apply_filter_with_diff(self):
        """Apply a filter pass using list diffing — queue if incubating.

        See ``_apply_filter`` for the queue-or-run dispatch semantics.
        """
        if self._incubating and self._all_skills:
            self._pending_signals.append(self._do_apply_filter_with_diff_now)
            return
        self._do_apply_filter_with_diff_now()

    def _do_apply_filter_with_diff_now(self):
        """Applies filters but uses list diffing to emit correct Qt signals for sleek animations (deferred)."""
        if self._reset_pending:
            try:
                skills = self._execute_filter_logic()
                self._all_filtered_skills = self._engine.prepare_rows(skills)
                self._filtered_skills = self._engine.build_visible_rows(
                    self._all_filtered_skills, self.state.collapsed_categories
                )
            except Exception as e:
                logger.error("Error applying filter for diff: %s", e)
            return

        old_list = list(self._filtered_skills)
        try:
            skills = self._execute_filter_logic()
            new_all_filtered = self._engine.prepare_rows(skills)
            new_list = self._engine.build_visible_rows(
                new_all_filtered, self.state.collapsed_categories
            )
        except Exception as e:
            logger.error("Error applying filter for diff: %s", e)
            return

        if os.environ.get("SKILL_MANAGER_TESTING") == "1":
            # Run synchronously in tests
            self._all_filtered_skills = new_all_filtered
            self.aboutToMutateStructure.emit()

            import difflib

            old_keys = [s.local_path if s.local_path else str(id(s)) for s in old_list]
            new_keys = [s.local_path if s.local_path else str(id(s)) for s in new_list]

            matcher = difflib.SequenceMatcher(None, old_keys, new_keys)

            for tag, i1, i2, j1, j2 in reversed(matcher.get_opcodes()):
                if tag == "replace":
                    self.beginRemoveRows(QModelIndex(), i1, i2 - 1)
                    del self._filtered_skills[i1:i2]
                    self.endRemoveRows()
                    self.beginInsertRows(QModelIndex(), i1, i1 + (j2 - j1) - 1)
                    self._filtered_skills[i1:i1] = new_list[j1:j2]
                    self.endInsertRows()
                elif tag == "delete":
                    self.beginRemoveRows(QModelIndex(), i1, i2 - 1)
                    del self._filtered_skills[i1:i2]
                    self.endRemoveRows()
                elif tag == "insert":
                    self.beginInsertRows(QModelIndex(), i1, i1 + (j2 - j1) - 1)
                    self._filtered_skills[i1:i1] = new_list[j1:j2]
                    self.endInsertRows()
                elif tag == "equal":
                    for idx in range(i1, i2):
                        self._filtered_skills[idx] = new_list[j1 + (idx - i1)]
                    if i2 > i1:
                        self.dataChanged.emit(self.index(i1, 0), self.index(i2 - 1, 0))

            self.structureMutated.emit()
            self._update_selection_counts()
            self.selectionStateChanged.emit()
            self.totalSelectableCountChanged.emit()
            return

        self.aboutToMutateStructure.emit()
        self._reset_pending = True

        def _deferred_diff_apply():
            self._reset_pending = False
            self._all_filtered_skills = new_all_filtered

            import difflib

            old_keys = [s.local_path if s.local_path else str(id(s)) for s in old_list]
            new_keys = [s.local_path if s.local_path else str(id(s)) for s in new_list]

            matcher = difflib.SequenceMatcher(None, old_keys, new_keys)

            for tag, i1, i2, j1, j2 in reversed(matcher.get_opcodes()):
                if tag == "replace":
                    self.beginRemoveRows(QModelIndex(), i1, i2 - 1)
                    del self._filtered_skills[i1:i2]
                    self.endRemoveRows()
                    self.beginInsertRows(QModelIndex(), i1, i1 + (j2 - j1) - 1)
                    self._filtered_skills[i1:i1] = new_list[j1:j2]
                    self.endInsertRows()
                elif tag == "delete":
                    self.beginRemoveRows(QModelIndex(), i1, i2 - 1)
                    del self._filtered_skills[i1:i2]
                    self.endRemoveRows()
                elif tag == "insert":
                    self.beginInsertRows(QModelIndex(), i1, i1 + (j2 - j1) - 1)
                    self._filtered_skills[i1:i1] = new_list[j1:j2]
                    self.endInsertRows()
                elif tag == "equal":
                    for idx in range(i1, i2):
                        self._filtered_skills[idx] = new_list[j1 + (idx - i1)]
                    if i2 > i1:
                        self.dataChanged.emit(self.index(i1, 0), self.index(i2 - 1, 0))

            self.structureMutated.emit()
            self._update_selection_counts()
            self.selectionStateChanged.emit()
            self.totalSelectableCountChanged.emit()

        from PySide6.QtCore import QTimer

        QTimer.singleShot(0, _deferred_diff_apply)

    def _begin_batch(self):
        """Suppress layout signals and filter work until _end_batch()."""
        logger.debug(
            "_begin_batch: incubating=%s replay=%s pending=%d",
            self._incubating,
            self._replay_deferred,
            len(self._pending_signals),
        )
        self._suppress_layout = True
        self._batch_apply_needed = False
        self._batch_reset_needed = False

    def _end_batch(self):
        """Re-enable layout signals and emit a single layoutChanged or modelReset.

        Re-entry guard: if the model is still incubating from a previous
        mutation (QML not yet finished rendering delegates), or signals are
        queued for replay, defer this batch's filter pass.
        ``onIncubationReady()`` will drain it after the current incubation
        completes. Prevents the race where a second mutation's
        ``layoutChanged`` destroys delegates still being rendered from the
        first mutation's drained signals.
        """
        self._suppress_layout = False
        if self._batch_apply_needed:
            needs_defer = (
                self._incubating or self._replay_deferred or self._pending_signals
            ) and self._all_skills
            if needs_defer:
                logger.debug(
                    "_end_batch DEFERRED: incubating=%s replay=%s pending=%d",
                    self._incubating,
                    self._replay_deferred,
                    len(self._pending_signals),
                )
                return
            if self._batch_reset_needed:
                self._apply_filter(reset=True)
            else:
                self._apply_filter_with_diff()
            self._batch_apply_needed = False
            logger.debug("_end_batch: applied filter synchronously")

    def _execute_filter_logic(self) -> list[Skill]:
        """Internal synchronous logic for filtering and searching."""
        if self.state.filter_text and self._search_engine:
            valid_paths = {
                s.local_path for s in self._engine.filter_skills(self._all_skills, self.state)
            }
            results = self._search_engine.query(self.state.filter_text, valid_paths=valid_paths)
            path_to_skill = {s.local_path: s for s in self._all_skills}
            return [
                path_to_skill.get(r[0].get("local_path", ""), Skill.from_dict(r[0]))
                for r in results
            ]
        skills = self._engine.filter_skills(self._all_skills, self.state)
        skills.sort(key=self._engine.sort_key)
        return skills

    def _is_main_collapsed(self, skill: Skill):
        return (
            skill.main_category_name or self._engine.get_main_category(skill)
        ) in self.state.collapsed_categories

    def _is_sub_collapsed(self, skill: Skill):
        return (
            skill.section_name or self._engine.get_section(skill)
        ) in self.state.collapsed_categories

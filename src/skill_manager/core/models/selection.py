"""Selection subsystem for the SkillModel facade.

Count properties, selection slots, project-scoped selection persistence,
and the project-selection swap used by the ``projectFilter`` setter on
the facade. Signals are module-level aliases of the declarations in
``roles.py`` so the ``@Property(notify=...)`` decorators can reference
them at class-definition time.
"""

import logging
import os

from PySide6.QtCore import Property, Slot

from skill_manager.core.models.roles import RolesMixin

selectionStateChanged = RolesMixin.selectionStateChanged  # noqa: N816
totalSelectableCountChanged = RolesMixin.totalSelectableCountChanged  # noqa: N816

logger = logging.getLogger(__name__)


class SelectionMixin:
    """Selection state, counts, and project-selection persistence.

    Count semantics (intentionally separated):

    * ``selectedCount`` — total selected items in ``_selected_ids``,
      independent of current search/filter/collapse. This is the badge
      number the user sees ("3 selected") and must not flicker when
      the user types in the search box.
    * ``filteredSelectedCount`` — selected items that survive the current
      filter pipeline (project + category + search …). Useful for
      filter-aware operations.
    * ``visibleSelectedCount`` / ``visibleSelectableCount`` — collapsed-state
      aware counts derived from ``_filtered_skills``.
    * ``totalSelectableCount`` — length of ``_all_filtered_skills``
      (filter-aware, collapse-agnostic).
    """

    @Property(int, notify=selectionStateChanged)
    def selectedCount(self):
        """Total selected count, stable across search/filter changes."""
        return self._cached_selected_count

    @Property(int, notify=selectionStateChanged)
    def filteredSelectedCount(self):
        """Selected count limited to the current filtered set."""
        return self._cached_filtered_selected

    @Property(int, notify=selectionStateChanged)
    def visibleSelectableCount(self):
        """Returns the number of skills currently visible in the view (not collapsed)."""
        return self._cached_visible_selectable

    @Property(int, notify=selectionStateChanged)
    def visibleSelectedCount(self):
        """Returns the number of selected skills that are currently visible."""
        return self._cached_visible_selected

    @Property(int, notify=totalSelectableCountChanged)
    def totalSelectableCount(self):
        return self._cached_total_selectable

    def _update_selection_counts(self):
        """Recomputes all cached selection/visibility counts.

        The critical invariant: ``selectedCount`` must NOT be derived from
        ``_all_filtered_skills`` (which is search/filter-dependent). It
        represents the user's total selection and is therefore derived
        from ``_selected_ids`` alone, optionally intersected with
        ``_all_skills`` to exclude ghost paths for skills that no longer
        exist on disk.
        """
        # --- total selected (filter-independent) ---
        all_skills = getattr(self, "_all_skills", None)
        if all_skills:
            existing_paths = {s.local_path for s in all_skills if getattr(s, "local_path", None)}
            if existing_paths:
                # Exclude orphaned selections (skill deleted externally)
                self._cached_selected_count = sum(
                    1 for p in self._selected_ids if p in existing_paths
                )
            else:
                self._cached_selected_count = len(self._selected_ids)
        else:
            self._cached_selected_count = len(self._selected_ids)

        # --- filtered selected (filter-aware, collapse-agnostic) ---
        filtered_paths = {s.local_path for s in self._all_filtered_skills if s.local_path}
        self._cached_filtered_selected = sum(1 for p in self._selected_ids if p in filtered_paths)

        # --- visible (collapse-aware) ---
        self._cached_visible_selectable = sum(1 for s in self._filtered_skills if s.local_path)
        self._cached_visible_selected = sum(
            1 for s in self._filtered_skills if s.local_path and s.local_path in self._selected_ids
        )
        self._cached_total_selectable = len(self._all_filtered_skills)

        logger.debug(
            "selection counts: total=%d filtered=%d visible=%d/%d totalSelectable=%d",
            self._cached_selected_count,
            self._cached_filtered_selected,
            self._cached_visible_selected,
            self._cached_visible_selectable,
            self._cached_total_selectable,
        )

    def _sync_current_project_selection(self) -> None:
        """Keep ``_selections_by_project[current_project]`` in sync with ``_selected_ids``."""
        proj = (
            self.state.project_filter
            if hasattr(self, "state")
            and self.state
            and isinstance(getattr(self.state, "project_filter", None), str)
            else ""
        )
        self._selections_by_project[proj] = list(self._selected_ids)

    @Slot(int)
    def toggleSelection(self, row):
        if 0 <= row < len(self._filtered_skills):
            skill = self._filtered_skills[row]
            path = skill.local_path
            if not path or self._is_main_collapsed(skill) or self._is_sub_collapsed(skill):
                return
            if path in self._selected_ids:
                self._selected_ids.pop(path, None)
            else:
                self._selected_ids[path] = None
            idx = self.index(row, 0)
            self.dataChanged.emit(idx, idx, [self.IsSelectedRole])
            self._update_selection_counts()
            self.selectionStateChanged.emit()
            self._sync_current_project_selection()
            self._save_project_selections()

    @Slot()
    def clearSelection(self):
        self._selected_ids.clear()
        self._emit_selection_data_changed()
        self._update_selection_counts()
        self.selectionStateChanged.emit()
        self._sync_current_project_selection()
        self._save_project_selections()

    @Slot()
    def selectAll(self):
        for skill in self._all_filtered_skills:
            if skill.local_path:
                self._selected_ids[skill.local_path] = None
        self._emit_selection_data_changed()
        self._update_selection_counts()
        self.selectionStateChanged.emit()
        self._sync_current_project_selection()
        self._save_project_selections()

    @Slot(result=list)
    def getSelectedPaths(self):
        return list(self._selected_ids)

    @Slot(result=list)
    def getSelectedNames(self):
        path_to_name = {s.local_path: s.name for s in self._all_skills if s.local_path}
        return [path_to_name.get(p, os.path.basename(p)) for p in self._selected_ids if p]

    @Slot(result=list)
    def getFilteredSelectedPaths(self):
        """Return selected paths limited to currently filtered (project-scoped) skills."""
        filtered_paths = {s.local_path for s in self._all_filtered_skills if s.local_path}
        return [p for p in self._selected_ids if p in filtered_paths]

    @Slot(list)
    def selectByPaths(self, paths):
        for path in paths:
            if path:
                self._selected_ids[path] = None
        self._emit_selection_data_changed()
        self._update_selection_counts()
        self.selectionStateChanged.emit()
        self._sync_current_project_selection()
        self._save_project_selections()

    @Slot(int, bool)
    def setSelected(self, row, selected):
        if 0 <= row < len(self._filtered_skills):
            path = self._filtered_skills[row].local_path
            if not path:
                return
            if selected:
                self._selected_ids[path] = None
            else:
                self._selected_ids.pop(path, None)
            idx = self.index(row, 0)
            self.dataChanged.emit(idx, idx, [self.IsSelectedRole])
            self._update_selection_counts()
            self.selectionStateChanged.emit()
            self._sync_current_project_selection()
            self._save_project_selections()

    def _emit_selection_data_changed(self):
        if not self._filtered_skills:
            return
        self.dataChanged.emit(
            self.index(0, 0),
            self.index(len(self._filtered_skills) - 1, 0),
            [self.IsSelectedRole],
        )

    def _swap_project_selection(self, old_project: str, new_project: str) -> None:
        """Save the current selection under the old project and load the new project's.

        Extracted from the ``projectFilter`` setter on the facade so the
        per-project selection bookkeeping lives with the selection subsystem.
        """
        if old_project is not None:
            self._selections_by_project[old_project] = list(self._selected_ids)
        if new_project in self._selections_by_project:
            self._selected_ids = dict.fromkeys(self._selections_by_project[new_project])
        else:
            self._selected_ids.clear()

    def _save_project_selections(self):
        if not self._config:
            return
        if self._project_selections_save_timer is None:
            from PySide6.QtCore import QTimer

            self._project_selections_save_timer = QTimer()
            self._project_selections_save_timer.setSingleShot(True)
            self._project_selections_save_timer.timeout.connect(self._do_save_project_selections)
            self._project_selections_save_timer.setInterval(500)
        self._project_selections_save_timer.start()

    def _do_save_project_selections(self):
        if self._config is not None:
            self._sync_current_project_selection()
            self._config.set("project_selections", self._selections_by_project)

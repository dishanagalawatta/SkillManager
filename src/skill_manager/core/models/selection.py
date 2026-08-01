"""Selection subsystem for the SkillModel facade.

Count properties, selection slots, project-scoped selection persistence,
and the project-selection swap used by the ``projectFilter`` setter on
the facade. Signals are module-level aliases of the declarations in
``roles.py`` so the ``@Property(notify=...)`` decorators can reference
them at class-definition time.
"""

import os

from PySide6.QtCore import Property, Slot

from skill_manager.core.models.roles import RolesMixin

selectionStateChanged = RolesMixin.selectionStateChanged  # noqa: N816
totalSelectableCountChanged = RolesMixin.totalSelectableCountChanged  # noqa: N816


class SelectionMixin:
    """Selection state, counts, and project-selection persistence."""

    @Property(int, notify=selectionStateChanged)
    def selectedCount(self):
        return self._cached_selected_count

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
        """Recomputes cached selection/visibility counts."""
        self._cached_selected_count = sum(
            1 for s in self._all_filtered_skills if s.local_path in self._selected_ids
        )
        self._cached_visible_selectable = sum(1 for s in self._filtered_skills if s.local_path)
        self._cached_visible_selected = sum(
            1 for s in self._filtered_skills if s.local_path and s.local_path in self._selected_ids
        )
        self._cached_total_selectable = len(self._all_filtered_skills)

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
            self._save_project_selections()

    @Slot()
    def clearSelection(self):
        self._selected_ids.clear()
        self._emit_selection_data_changed()
        self._update_selection_counts()
        self.selectionStateChanged.emit()
        self._save_project_selections()

    @Slot()
    def selectAll(self):
        for skill in self._all_filtered_skills:
            if skill.local_path:
                self._selected_ids[skill.local_path] = None
        self._emit_selection_data_changed()
        self._update_selection_counts()
        self.selectionStateChanged.emit()
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
        if old_project:
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
            self._config.set("project_selections", self._selections_by_project)

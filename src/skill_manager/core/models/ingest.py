"""Skill ingestion and row lookup for the SkillModel facade."""

import os
from typing import Any

from PySide6.QtCore import Slot

from skill_manager.core.models.entities import Skill
from skill_manager.core.search import SearchEngine


class IngestMixin:
    """Skill list ingestion, property updates, and path lookups."""

    def removeSkillsByPath(self, paths: list):
        path_set = set(paths)
        if not path_set:
            return
        self._begin_batch()
        try:
            self._all_skills = [s for s in self._all_skills if s.local_path not in path_set]
            for path in path_set:
                self._selected_ids.pop(path, None)
            if self._search_engine:
                self._search_engine.remove_from_index(list(path_set))
            self._apply_filter()
        finally:
            self._end_batch()
        self._save_project_selections()

    def updateSkillProperty(self, path: str, key: str, value: Any) -> bool:
        """Updates a property for a skill identified by its local_path.
        Returns True if at least one skill was updated.
        """
        changed = False
        # Update in the master list
        for skill in self._all_skills:
            lp = skill.local_path if hasattr(skill, "local_path") else skill.get("local_path")
            if lp == path:
                if isinstance(skill, dict):
                    skill[key] = value
                else:
                    setattr(skill, key, value)
                changed = True

        if not changed:
            return False

        if key == "is_starred":
            self._apply_filter_with_diff()
            return True

        # If it's in the currently filtered list, emit dataChanged
        for i, skill in enumerate(self._filtered_skills):
            lp = skill.local_path if hasattr(skill, "local_path") else skill.get("local_path")
            if lp == path:
                idx = self.index(i, 0)
                # Find role by name if possible, or just emit all
                self.dataChanged.emit(idx, idx)
                break

        self.selectionStateChanged.emit()
        return True

    @Slot(list)
    def setSkills(self, skills: list[dict[str, Any]]):
        self._all_skills = [Skill.from_dict_fast(s) for s in skills]
        self._search_engine = SearchEngine(skills)
        self._apply_filter(reset=True)

    @Slot(result=list)
    def get_known_paths(self) -> list[str]:
        """Return all skill local_path values currently in the model.

        Used by the stat-polling safety net to check existence of known
        skill directories without doing a full rescan.
        """
        return [s.local_path for s in self._all_skills if s.local_path]

    def find_by_path(self, local_path: str) -> Skill | None:
        """Find a skill by its local_path.

        Searches the filtered (visible) skills first, then falls back to the
        full master list. Returns the Skill object or None if no match is found.
        """
        for skill in self._filtered_skills:
            if skill.local_path == local_path:
                return skill

        for skill in self._all_skills:
            if skill.local_path == local_path:
                return skill

        return None

    @Slot(str)
    def refresh_emoji_for_path(self, local_path: str) -> None:
        """Emit ``dataChanged`` for the ``EmojiRole`` of the row matching ``local_path``.

        Used by ``AppController`` after an emoji override is set/cleared so the
        visible delegate re-reads the new value without a full model reset.
        """
        normalized = os.path.normpath(local_path)
        for i, skill in enumerate(self._filtered_skills):
            if os.path.normpath(skill.local_path) == normalized:
                self.dataChanged.emit(self.index(i, 0), self.index(i, 0), [self.EmojiRole])
                break

    @Slot(list)
    def addOrUpdateSkills(self, new_skills: list[dict[str, Any]]):
        was_empty = len(self._all_skills) == 0
        updated_paths = {s_dict.get("local_path", "") for s_dict in new_skills}
        skills_dict = {s.local_path: s for s in self._all_skills}

        # Recompute project_label from project_path to ensure the label
        # matches what getProjectLabel (dropdown) produces for the same path.
        # The project_path is the raw root path (not .agents/skills), matching
        # how getProjectLabel receives it from app._projects.
        from skill_manager.core.diagnostics import (
            CATEGORY_PROJECT_LABEL_MISMATCH,
            get_diagnostic_logger,
        )
        from skill_manager.core.quick_copy import project_label as canonical_label

        project_aliases = self._config.get("project_aliases", {}) if self._config else {}
        diag = get_diagnostic_logger()

        for s_dict in new_skills:
            skill = Skill.from_dict_fast(s_dict)
            if skill.project_path:
                new_label = canonical_label(skill.project_path, project_aliases=project_aliases)
                incoming = s_dict.get("project_label", "")
                if incoming and incoming != new_label:
                    diag.log_event(
                        "WARNING",
                        CATEGORY_PROJECT_LABEL_MISMATCH,
                        f"project_label mismatch: incoming={incoming!r}, "
                        f"recomputed={new_label!r} for path={skill.project_path!r}",
                        data={
                            "local_path": skill.local_path,
                            "incoming_label": incoming,
                            "recomputed_label": new_label,
                            "raw_project_path": skill.project_path,
                        },
                    )
                skill.project_label = new_label
            skills_dict[skill.local_path] = skill
        self._all_skills = list(skills_dict.values())

        # Use incremental update if engine exists, else full init
        if self._search_engine:
            self._search_engine.update_index(new_skills)
        else:
            self._search_engine = SearchEngine(new_skills)

        self._apply_filter(reset=was_empty)

        if updated_paths and not was_empty:
            for row, skill in enumerate(self._filtered_skills):
                if skill.local_path in updated_paths:
                    idx = self.index(row, 0)
                    self.dataChanged.emit(idx, idx, self._ALL_ROLES)

    @Slot(int, result=dict)
    def get_skill_at(self, row):
        if 0 <= row < len(self._filtered_skills):
            # QML expects a dict or object it can access.
            # dataclasses are accessible in QML if registered,
            # but here we might need to return a dict for safety.
            import dataclasses

            return dataclasses.asdict(self._filtered_skills[row])
        return {}

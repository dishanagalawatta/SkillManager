"""Model-sync operations for the OpsController."""

import logging
from pathlib import Path

from PySide6.QtCore import Slot

from skill_manager.core.diagnostics import (
    CATEGORY_SELECTION_REFRESHED,
    get_diagnostic_logger,
)

logger = logging.getLogger(__name__)


class SyncMixin:
    """Merge discovered skills into the models and keep the selection fresh."""

    def _merge_discovered_skills(self, discovered: list):
        """Internal helper to merge newly discovered skills into both models.

        Parameter name matches :py:meth:`BaseController._merge_discovered_skills`
        so subclasses with the same method override without an incompatible
        signature warning.
        """
        self.app._library_model.addOrUpdateSkills(discovered)
        self.app._quick_copy_model.addOrUpdateSkills(discovered)

        # Update categories if new ones appeared
        new_cats = False
        for s in discovered:
            cat = s.get("category")
            if cat and cat not in self.app._categories:
                self.app._categories.append(cat)
                new_cats = True

        if new_cats:
            self.app._categories.sort()
            self.app.categoriesChanged.emit()

    def _refresh_selected_skill(self, local_path: str, rename_path: str | None = None) -> None:
        """Refresh ``_selected_skill`` after a model mutation.

        For renames, pass ``rename_path`` (the new path) when
        ``local_path`` is the old path that no longer exists in the model.
        """
        diag = get_diagnostic_logger()
        selected = self.app._selected_skill

        # Resolve the current selected path — handle controller, QMap, or dict.
        if hasattr(selected, "local_path"):
            selected_path = selected.local_path
        elif hasattr(selected, "value"):
            selected_path = selected.value("local_path")
        elif isinstance(selected, dict):
            selected_path = selected.get("local_path")
        else:
            selected_path = None

        if not selected_path:
            diag.log_event("INFO", CATEGORY_SELECTION_REFRESHED, "noop: nothing selected")
            return

        if selected_path != local_path:
            diag.log_event(
                "INFO",
                CATEGORY_SELECTION_REFRESHED,
                f"not_selected: mutated {local_path}, selected is {selected_path}",
            )
            return

        lookup_path = rename_path or local_path
        model = self.app.skillModel

        for i in range(len(model._filtered_skills)):
            skill = model._filtered_skills[i]
            if skill.local_path == lookup_path:
                fresh = model.get_skill_at(i)
                sel = self.app._selected_skill
                if hasattr(sel, "setSelection"):
                    sel.setSelection(fresh)
                else:
                    sel.clear()
                    sel.update(fresh)
                diag.log_event(
                    "INFO",
                    CATEGORY_SELECTION_REFRESHED,
                    f"refreshed: {lookup_path}"
                    + (f" (renamed from {local_path})" if rename_path else ""),
                    data={"fresh_body": (fresh.get("body_content") or "")[:80]},
                )
                return

        for skill in model._all_skills:
            if skill.local_path == lookup_path:
                import dataclasses

                if dataclasses.is_dataclass(skill) and not isinstance(skill, type):
                    fresh_dict = dataclasses.asdict(skill)
                else:
                    fresh_dict = dict(vars(skill))
                sel = self.app._selected_skill
                if hasattr(sel, "setSelection"):
                    sel.setSelection(fresh_dict)
                else:
                    sel.clear()
                    sel.update(fresh_dict)
                diag.log_event(
                    "INFO",
                    CATEGORY_SELECTION_REFRESHED,
                    f"refreshed_from_all_skills: {lookup_path}"
                    + (f" (renamed from {local_path})" if rename_path else ""),
                    data={"fresh_body": (fresh_dict.get("body_content") or "")[:80]},
                )
                return

        diag.log_event(
            "WARNING",
            CATEGORY_SELECTION_REFRESHED,
            f"not_in_view: {lookup_path} not found in active model",
        )

    def _apply_targeted_refresh(
        self, affected_project_paths: set[Path], all_discovered: list[dict]
    ) -> set[str]:
        """Merge discovered skills and remove stale paths for the affected projects.

        Returns the set of stale ``local_path`` values that were removed, so
        callers can log accurate diagnostics.
        """
        # Function-level import: resolves the module attribute at call time so
        # tests patching skill_manager.core.persistence.patch_cache_add see it.
        from skill_manager.core.persistence import patch_cache_add

        pre_paths = self._snapshot_affected_paths(affected_project_paths)
        new_paths = {s.get("local_path", "") for s in all_discovered if s.get("local_path")}
        stale_paths = pre_paths - new_paths

        self.app._library_model._begin_batch()
        self.app._quick_copy_model._begin_batch()
        try:
            if all_discovered:
                patch_cache_add(all_discovered)
                self._merge_discovered_skills(all_discovered)
            if stale_paths:
                self.app._library_model.removeSkillsByPath(list(stale_paths))
                self.app._quick_copy_model.removeSkillsByPath(list(stale_paths))
        finally:
            self.app._library_model._end_batch()
            self.app._quick_copy_model._end_batch()

        return stale_paths

    @Slot(str, result=list)
    def skillProjectsForPath(self, local_path: str) -> "list[str]":
        """Return project labels that hold a copy of this skill folder."""
        from skill_manager.core.quick_copy import project_label, project_root_for_project

        path = Path(local_path)
        if not path.is_dir():
            return []

        folder_name = path.name
        holders = []
        for project_root in self.app._projects or []:
            pr = Path(project_root)
            # Skills live under .agents/skills/ inside the project root
            candidate = project_root_for_project(pr) / ".agents" / "skills" / folder_name
            if candidate.is_dir():
                holders.append(project_label(pr))
        return holders

"""Toggle (archive/starred) operations for the OpsController."""

import logging
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import Slot

from skill_manager.core.analytics import capture_event
from skill_manager.core.persistence import save_archive, save_starred

logger = logging.getLogger(__name__)


class TogglesMixin:
    """Archive/starred status toggles for skills."""

    def _updateModelsProperty(self, path: str, key: str, value: Any) -> None:
        """Updates a property for all skills matching the local_path across both models."""
        updated = False
        for model in (self.app._library_model, self.app._quick_copy_model):
            if model.updateSkillProperty(path, key, value):
                updated = True

        if updated:
            logger.debug("Updated property '%s' to %s for path: %s", key, value, path)

    def _toggle_skill_boolean(
        self, attr_name: str, path_list: list[str], persist_fn: Callable[..., Any], event_name: str
    ):
        """Generic helper to toggle a boolean property on a skill."""
        skill = self.app._selected_skill
        if not skill or not skill.local_path:
            return

        path = skill.local_path
        current_val = getattr(skill, attr_name, False) or False
        new_state = not current_val

        # Update global list
        if new_state:
            if path not in path_list:
                path_list.append(path)
        else:
            if path in path_list:
                path_list.remove(path)

        # Persist and Sync
        persist_fn()
        self._updateModelsProperty(path, attr_name, new_state)

        setattr(skill, attr_name, new_state)
        status_label = attr_name.replace("is_", "") + ("d" if not attr_name.endswith("d") else "")
        action = status_label if new_state else "un" + status_label
        self.app._set_status(f"Skill {action}")
        capture_event(event_name, {"action": action})

    @Slot()
    def toggleArchive(self):
        """Toggles archived status for the currently selected skill."""
        self._toggle_skill_boolean(
            "is_archived", self.app._archive_paths, self._saveArchive, "skill_archived"
        )

    @Slot()
    def toggleCurrentSkillArchive(self):
        """Alias for toggleArchive, called from QML."""
        self.toggleArchive()

    @Slot()
    def toggleStarred(self):
        """Toggles starred status for the currently selected skill."""
        self._toggle_skill_boolean(
            "is_starred", self.app._starred_paths, self._saveStarred, "skill_starred"
        )

    @Slot()
    def toggleCurrentSkillStarred(self):
        """Alias for toggleStarred, called from QML."""
        self.toggleStarred()

    @Slot()
    def archiveSelectedSkills(self):
        """Archives all currently selected skills."""
        if (
            hasattr(self.app, "ui_controller")
            and getattr(self.app.ui_controller, "currentView", "") == "QuickCopy"
            and hasattr(self.app, "quickCopyModel")
        ):
            model = self.app.quickCopyModel
        else:
            model = getattr(self.app, "skillModel", None)

        raw_paths = model.getSelectedPaths() if model is not None else []
        selected_paths = list(raw_paths) if isinstance(raw_paths, (list, tuple, set)) else []
        if not selected_paths and model is not getattr(self.app, "quickCopyModel", None):
            qc_model = getattr(self.app, "quickCopyModel", None)
            if qc_model is not None:
                qc_paths = qc_model.getSelectedPaths()
                if isinstance(qc_paths, (list, tuple, set)) and qc_paths:
                    selected_paths = list(qc_paths)
        if not selected_paths and model is not getattr(self.app, "skillModel", None):
            sm_model = getattr(self.app, "skillModel", None)
            if sm_model is not None:
                sm_paths = sm_model.getSelectedPaths()
                if isinstance(sm_paths, (list, tuple, set)) and sm_paths:
                    selected_paths = list(sm_paths)

        if not selected_paths:
            self.app._set_status("No skills selected for archiving")
            return

        count = 0
        for path in selected_paths:
            if path and path not in self.app._archive_paths:
                self.app._archive_paths.append(path)
                count += 1

        if count > 0:
            self._saveArchive()
            for path in selected_paths:
                self._updateModelsProperty(path, "is_archived", True)
            if hasattr(self.app, "skillModel"):
                self.app.skillModel.clearSelection()
            if hasattr(self.app, "quickCopyModel"):
                self.app.quickCopyModel.clearSelection()
            self.app._set_status(f"{count} skills archived")
        else:
            self.app._set_status("Selected skills are already archived")

    @Slot(str)
    def addToArchive(self, skill_local_path: str):
        """Adds a specific skill path to the archive list."""
        if skill_local_path and skill_local_path not in self.app._archive_paths:
            self.app._archive_paths.append(skill_local_path)
            self._saveArchive()
            self._updateModelsProperty(skill_local_path, "is_archived", True)
            self.app._set_status(f"Skill archived: {skill_local_path}")

    def _saveArchive(self):
        """Internal helper to persist archive state."""
        save_archive(self.app._archive_paths)

    def _saveStarred(self):
        """Internal helper to persist starred state."""
        save_starred(self.app._starred_paths)

"""
Purpose: Manages skill operations like copying, deleting, and status toggles.
Usage: Accessed via AppController.ops
"""
import json
import threading
from pathlib import Path
from PySide6.QtCore import QTimer, Slot
from skill_manager.controllers.base import BaseController
from skill_manager.core.analytics import capture_event
from skill_manager.core.persistence import save_archive, save_essentials
from skill_manager.core.quick_copy import (
    delete_project_skill_folders,
)


class OpsController(BaseController):
    """Controller for skill-related operations."""

    def toggle_archive(self):
        """Toggles archived status for the currently selected skill."""
        skill = self.app._selected_skill
        if not skill:
            return

        path = skill.get("local_path")
        if not path:
            return

        is_archived = skill.get("is_archived", False)
        new_state = not is_archived

        skill["is_archived"] = new_state

        if new_state:
            if path not in self.app._archive_paths:
                self.app._archive_paths.append(path)
        else:
            if path in self.app._archive_paths:
                self.app._archive_paths.remove(path)

        save_archive(self.app._archive_paths)

        self.app.selectedSkillChanged.emit()
        self.app._library_model._apply_filter()
        self.app._quick_copy_model._apply_filter()

        status = "archived" if new_state else "restored"
        self.app._set_status(f"Skill {status}")
        capture_event("skill_archived", {"action": status})

    def toggle_essential(self):
        """Toggles essential status for the currently selected skill."""
        skill = self.app._selected_skill
        if not skill:
            return

        path = skill.get("local_path")
        if not path:
            return

        is_essential = skill.get("is_essential", False)
        new_state = not is_essential

        skill["is_essential"] = new_state

        if new_state:
            if path not in self.app._essential_paths:
                self.app._essential_paths.append(path)
        else:
            if path in self.app._essential_paths:
                self.app._essential_paths.remove(path)

        save_essentials(self.app._essential_paths)

        self.app.selectedSkillChanged.emit()
        self.app._library_model._apply_filter()
        self.app._quick_copy_model._apply_filter()

        status = "added to essentials" if new_state else "removed from essentials"
        self.app._set_status(f"Skill {status}")

    def delete_skills(self, items: list):
        """Core optimistic-delete handler."""
        paths_to_remove = [s.get("local_path", "") for s in items]
        skill_items = [s for s in items if not s.get("is_command", False)]
        command_items = [s for s in items if s.get("is_command", False)]
        count = len(items)

        # ── Step 1: Instant visual removal
        self.app._library_model.removeSkillsByPath(paths_to_remove)
        self.app._quick_copy_model.removeSkillsByPath(paths_to_remove)
        self.app._set_status(f"Deleting {count} item{'s' if count != 1 else ''}…")
        capture_event("skills_deleted", {"count": count})

        # ── Step 2: Background disk + cache work
        def _background_delete():
            deleted, failed = 0, 0
            if skill_items:
                result = delete_project_skill_folders(skill_items)
                deleted += result.get("deleted", 0)
                failed += result.get("failed", 0)

            for cmd in command_items:
                p = Path(cmd.get("local_path", ""))
                try:
                    if p.is_file():
                        p.unlink()
                        deleted += 1
                except Exception as exc:
                    print(f"[DELETE] FAILED {p}: {exc}")
                    failed += 1

            self._patch_cache_remove(paths_to_remove)

            # ── Step 3: Report back
            parts = [f"{deleted} deleted"] if deleted else []
            if failed:
                parts.append(f"{failed} failed")
            status = f"Deletion complete: {', '.join(parts) or 'nothing happened'}"
            QTimer.singleShot(0, self.app, lambda: self.app._set_status(status))

        threading.Thread(target=_background_delete, daemon=True).start()

    def _patch_cache_remove(self, paths_to_remove: list):
        """Surgically remove entries from cache JSON."""
        try:
            from skill_manager.core.config import SKILL_LIBRARY_CACHE_FILE
            cache_path = Path(SKILL_LIBRARY_CACHE_FILE)
            if not cache_path.exists():
                return

            path_set = set(paths_to_remove)
            with open(cache_path, encoding="utf-8") as f:
                data = json.load(f)

            data["skills"] = [s for s in data.get("skills", []) if s.get("local_path") not in path_set]
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as exc:
            print(f"[CACHE] Patch failed: {exc}")

    def copy_selected_to_target(self, target_path: str):
        """Copies selected skills to a target project."""
        if not target_path:
            return
        
        selected_paths = self.app.skillModel.getSelectedPaths()
        selected_skills = [s for s in self.app.skillModel._all_skills if s.get("local_path") in selected_paths]
        
        if not selected_skills:
            self.app._set_status("No skills selected to copy")
            return

        self.app._set_status(f"Copying {len(selected_skills)} skills...")

        def run_copy():
            try:
                from skill_manager.core.copier import copy_skill_folders_to_targets
                result = copy_skill_folders_to_targets(selected_skills, [target_path])
                
                parts = []
                if result['copied']: parts.append(f"{result['copied']} new")
                if result['merged']: parts.append(f"{result['merged']} updated")
                
                msg = f"Copy complete: {', '.join(parts) or 'nothing copied'}"
                QTimer.singleShot(0, self.app, lambda: self.app._set_status(msg))
                QTimer.singleShot(0, self.app, self.app.refreshSkills)
                QTimer.singleShot(0, self.app, self.app.skillModel.clearSelection)
            except Exception as e:
                QTimer.singleShot(0, self.app, lambda: self.app._set_status(f"Copy failed: {e}"))

        threading.Thread(target=run_copy, daemon=True).start()

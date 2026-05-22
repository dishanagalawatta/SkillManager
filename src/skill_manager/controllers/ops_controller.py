"""
Purpose: Manages skill operations like copying, deleting, and status toggles.
Usage: Accessed via AppController.ops
"""

from pathlib import Path

from PySide6.QtCore import QTimer

from skill_manager.controllers.base import BaseController
from skill_manager.core.analytics import capture_event, capture_exception
from skill_manager.core.persistence import (
    load_temp_registry,
    patch_cache_add,
    patch_cache_remove,
    save_archive,
    save_starred,
    save_temp_registry,
)
from skill_manager.core.quick_copy import (
    delete_project_skill_folders,
)


class OpsController(BaseController):
    """Controller for skill-related operations."""

    def _update_models_source(self, path: str, key: str, value: bool) -> None:
        """Updates a property for all skills matching the local_path across both models."""
        for model in (self.app._library_model, self.app._quick_copy_model):
            all_skills = getattr(model, "_all_skills", None)
            if isinstance(all_skills, list):
                for skill in all_skills:
                    if skill.get("local_path") == path:
                        if isinstance(skill, dict):
                            skill[key] = value
                        else:
                            setattr(skill, key, value)

    def toggle_archive(self):
        """Toggles archived status for the currently selected skill."""
        skill = self.app._selected_skill
        if not skill:
            return

        path = skill.get("local_path") if isinstance(skill, dict) else getattr(skill, "local_path", None)
        if not path:
            return

        is_archived = skill.get("is_archived", False) if isinstance(skill, dict) else getattr(skill, "is_archived", False)
        new_state = not is_archived

        if isinstance(skill, dict):
            skill["is_archived"] = new_state
        else:
            skill.is_archived = new_state

        self._update_models_source(path, "is_archived", new_state)

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

    def toggle_starred(self):
        """Toggles starred status for the currently selected skill."""
        skill = self.app._selected_skill
        if not skill:
            return

        path = skill.get("local_path") if isinstance(skill, dict) else getattr(skill, "local_path", None)
        if not path:
            return

        is_starred = skill.get("is_starred", False) if isinstance(skill, dict) else getattr(skill, "is_starred", False)
        new_state = not is_starred

        if isinstance(skill, dict):
            skill["is_starred"] = new_state
        else:
            skill.is_starred = new_state

        self._update_models_source(path, "is_starred", new_state)

        if new_state:
            if path not in self.app._starred_paths:
                self.app._starred_paths.append(path)
        else:
            if path in self.app._starred_paths:
                self.app._starred_paths.remove(path)

        save_starred(self.app._starred_paths)

        self.app.selectedSkillChanged.emit()
        self.app._library_model._apply_filter()
        self.app._quick_copy_model._apply_filter()

        status = "starred" if new_state else "unstarred"
        self.app._set_status(f"Skill {status}")

    def delete_skills(self, items: list):
        """Core optimistic-delete handler."""
        paths_to_remove = [
            (s.get("local_path", "") if isinstance(s, dict) else s.local_path) for s in items
        ]
        skill_items = [
            s
            for s in items
            if not (s.get("is_command", False) if isinstance(s, dict) else s.is_command)
        ]
        command_items = [
            s
            for s in items
            if (s.get("is_command", False) if isinstance(s, dict) else s.is_command)
        ]
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
                # Convert to dict for core utility if needed, or update utility
                dict_items = [
                    (s if isinstance(s, dict) else vars(s)) for s in skill_items
                ]
                result = delete_project_skill_folders(dict_items)
                deleted += result.get("deleted", 0)
                failed += result.get("failed", 0)

            for cmd in command_items:
                path_str = cmd.get("local_path", "") if isinstance(cmd, dict) else cmd.local_path
                p = Path(path_str)
                try:
                    if p.is_file():
                        p.unlink()
                        deleted += 1
                except Exception as exc:
                    print(f"[DELETE] FAILED {p}: {exc}")
                    failed += 1

            patch_cache_remove(paths_to_remove)

            # ── Step 3: Report back
            parts = [f"{deleted} deleted"] if deleted else []
            if failed:
                parts.append(f"{failed} failed")
            status = f"Deletion complete: {', '.join(parts) or 'nothing happened'}"
            QTimer.singleShot(0, self.app, lambda: self.app._set_status(status))

        self.app.task_runner.run(_background_delete)

    def cleanup_temp_copies(self):
        """Deletes all temporary copies recorded in the registry."""
        temp_paths = load_temp_registry()
        if not temp_paths:
            return

        import shutil

        deleted_count = 0
        for path_str in temp_paths:
            p = Path(path_str)
            try:
                if p.is_dir():
                    shutil.rmtree(p)
                    deleted_count += 1
                elif p.is_file():
                    p.unlink()
                    deleted_count += 1
            except Exception as e:
                print(f"[TEMP_CLEANUP] Failed to delete {path_str}: {e}")
                capture_exception(e)

        # Clear the registry after cleanup
        save_temp_registry([])
        if deleted_count > 0:
            print(f"[TEMP_CLEANUP] Cleaned up {deleted_count} temporary paths.")

    def copy_selected_to_project(self, project_path: str, is_temporary: bool = False):
        """Copies selected skills to a project."""
        if not project_path:
            return

        selected_paths = self.app.skillModel.getSelectedPaths()
        selected_skills = [
            s for s in self.app.skillModel._all_skills if s.get("local_path") in selected_paths
        ]

        if not selected_skills:
            self.app._set_status("No skills selected to copy")
            return

        self.app._set_status(f"Copying {len(selected_skills)} skills...")

        def run_copy():
            try:
                from skill_manager.core.copier import copy_skill_folders_to_projects
                from skill_manager.core.discovery import DiscoveryService

                result = copy_skill_folders_to_projects(selected_skills, [project_path])

                parts = []
                if result["copied"]:
                    parts.append(f"{result['copied']} new")
                if result["merged"]:
                    parts.append(f"{result['merged']} updated")

                msg = f"Copy complete: {', '.join(parts) or 'nothing copied'}"

                # Capture analytics
                capture_event(
                    "skill_copied_to_project",
                    {
                        "skills_copied": result.get("copied", 0),
                        "skills_merged": result.get("merged", 0),
                        "skills_failed": result.get("failed", 0),
                        "skills_count": len(selected_skills),
                    },
                )

                if is_temporary and result["details"]:
                    new_temp_paths = [
                        d["message"]
                        for d in result["details"]
                        if d["status"] in ("copied", "merged")
                    ]
                    if new_temp_paths:
                        existing = load_temp_registry()
                        # Use set to avoid duplicates
                        updated = list(set(existing + new_temp_paths))
                        save_temp_registry(updated)

                # Targeted discovery for the copied skills
                discovered_skills = []
                if result["details"]:
                    service = DiscoveryService(
                        sources=list(self.app._sources),
                        projects=self.app._projects,
                        archive_paths=self.app._archive_paths,
                        starred_paths=self.app._starred_paths,
                        project_aliases=self.app._project_aliases,
                    )
                    for detail in result["details"]:
                        if detail["status"] in ("copied", "merged") and detail.get("message"):
                            skill_path = Path(detail["message"])
                            proj_path = Path(detail["project"])
                            try:
                                skill_data = service.discover_single_skill(skill_path, proj_path)
                                if skill_data:
                                    discovered_skills.append(skill_data)
                            except Exception as exc:
                                print(f"[TARGETED SCAN] Failed scanning {skill_path}: {exc}")

                if discovered_skills:
                    # Patch JSON cache on disk
                    patch_cache_add(discovered_skills)

                    # Dynamic update of models in main UI thread
                    def update_ui():
                        # Update category lists in app controller
                        new_cats = sorted({s["category"] for s in discovered_skills if s.get("category")})
                        if new_cats:
                            current_cats = set(self.app._categories)
                            for cat in new_cats:
                                current_cats.add(cat)
                            self.app._categories = sorted(current_cats)
                            self.app.categoriesChanged.emit()

                        self.app._library_model.addOrUpdateSkills(discovered_skills)
                        self.app._quick_copy_model.addOrUpdateSkills(discovered_skills)
                        self.app._set_status(msg)
                        self.app.skillModel.clearSelection()

                    QTimer.singleShot(0, self.app, update_ui)
                else:
                    QTimer.singleShot(0, self.app, lambda: self.app._set_status(msg))
                    QTimer.singleShot(0, self.app, self.app.skillModel.clearSelection)

            except Exception as e:
                err_msg = f"Copy failed: {e}"
                capture_exception(e)
                QTimer.singleShot(0, self.app, lambda: self.app._set_status(err_msg))

        self.app.task_runner.run(run_copy)

    def copy_skill_to_clipboard(self, path: str):
        """Finds skill by path and copies its reference to clipboard."""
        skill = next((s for s in self.app.skillModel._all_skills if s.get("local_path") == path), None)
        if skill:
            self.copy_skill_reference(skill)
        else:
            self.copy_text_to_clipboard(path)

    def copy_current_selection_or_focused_skill(self):
        """Orchestrates copying based on selection or focus."""
        if self.app.skillModel.selectedCount > 0:
            self.copy_selected_skills_to_clipboard()
            return
        if self.app._selected_skill and self.app._selected_skill.get("local_path"):
            self.copy_skill_reference(self.app._selected_skill)
            return
        first_skill = self.app.skillModel.get_skill_at(0)
        if first_skill:
            self.copy_skill_reference(first_skill)
            return
        self.app._set_status("No skill available to copy")

    def copy_selected_skills_to_clipboard(self):
        """Copies all selected skill references to clipboard."""
        from skill_manager.core.quick_copy import format_project_skill_reference
        paths = self.app.skillModel.getSelectedPaths()
        if not paths:
            self.app._set_status("No skills selected")
            return

        references = []
        for path in paths:
            skill = next(
                (s for s in self.app.skillModel._all_skills if s.get("local_path") == path), None
            )
            if skill:
                references.append(format_project_skill_reference(skill, self.app._client_format))
            else:
                references.append(path)

        content = " ".join(references)
        self.app._clipboard.setText(content)
        self.app._set_status(f"Copied {len(references)} skills to clipboard")

    def copy_text_to_clipboard(self, content: str):
        """Copies raw text to system clipboard."""
        self.app._clipboard.setText(str(content))
        self.app._set_status("Copied to clipboard")

    def copy_skill_reference(self, skill: dict, arg: str = ""):
        """Copies a formatted skill reference to clipboard."""
        from skill_manager.core.quick_copy import format_project_skill_reference
        ref = format_project_skill_reference(skill, self.app._client_format)
        if arg:
            ref += f"({arg})"
        self.app._clipboard.setText(ref)
        self.app._set_status(f"Copied reference: {ref}")

    def create_custom_command(self, name: str, client: str, body: str, project_label: str, category: str):
        """Creates a new Custom Command .md file in the project's commands/ directory."""
        from skill_manager.core.commands import create_custom_command_file
        result = create_custom_command_file(
            name=name,
            client=client,
            body=body,
            project_label_name=project_label,
            category=category,
            project_paths=self.app._projects,
        )
        self.app._set_status(result.message)
        if result.ok:
            self.app.refreshSkills()


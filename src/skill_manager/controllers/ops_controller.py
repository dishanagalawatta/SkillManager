"""
Purpose: Manages skill operations like copying, deleting, and status toggles.
Usage: Accessed via AppController.ops
"""

import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

from PySide6.QtCore import QTimer, Signal, Slot

from skill_manager.controllers.base import BaseController
from skill_manager.core.analytics import capture_event, capture_exception
from skill_manager.core.diagnostics import (
    CATEGORY_COMMAND_CREATED,
    CATEGORY_COMMAND_UPDATED,
    CATEGORY_SELECTION_REFRESHED,
    get_diagnostic_logger,
)
from skill_manager.core.persistence import (
    load_temp_registry,
    load_temp_screenshots_registry,
    patch_cache_add,
    patch_cache_remove,
    save_archive,
    save_starred,
    save_temp_registry,
    save_temp_screenshots_registry,
)
from skill_manager.core.quick_copy import (
    delete_project_skill_folders,
)
from skill_manager.core.schemas import SkillRecord

logger = logging.getLogger(__name__)


class OpsController(BaseController):
    """Controller for skill-related operations."""

    minimizeAppRequested = Signal()
    commandSkillsCarryPrompt = Signal(str, str, str)
    commandPendingRemovals = Signal(str, list)

    _pending_command_update: dict | None = None

    def _maybeMinimizeOnCopy(self):
        """Requests app minimization if the setting is enabled and current view is QuickCopy."""
        if (
            self.app.config_controller.autoMinimizeOnQuickCopy
            and self.app.ui_controller.currentView == "QuickCopy"
        ):
            self.minimizeAppRequested.emit()
            logger.info("Auto-minimize on Quick Copy triggered.")

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
        if not skill:
            return

        path = (
            skill.get("local_path")
            if isinstance(skill, dict)
            else getattr(skill, "local_path", None)
        )
        if not path:
            return

        current_val = (
            skill.get(attr_name, False)
            if isinstance(skill, dict)
            else getattr(skill, attr_name, False)
        )
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

        # Update the selected object reference
        if isinstance(skill, dict):
            skill[attr_name] = new_state
        else:
            setattr(skill, attr_name, new_state)

        self.app.selectedSkillChanged.emit()
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

    def deleteSkills(self, items: list):
        """Orchestrates deletion of skills (folders and local copies)."""
        if not items:
            return

        validated_records = []
        for item in items:
            try:
                # Handle both dicts and dataclasses (Skill objects)
                if hasattr(item, "__dataclass_fields__"):
                    from dataclasses import asdict

                    data = asdict(item)
                else:
                    data = item

                # We use model_validate to enforce structure (Zod equivalent)
                record = SkillRecord.model_validate(data)
                validated_records.append(record)
            except Exception as e:
                logger.warning("Invalid item skipped during deletion: %s. Error: %s", item, e)

        if not validated_records:
            return

        # ── Step 0: Optimistic UI Removal
        paths_to_delete = [r.local_path for r in validated_records if r.local_path]
        self.app._library_model.removeSkillsByPath(paths_to_delete)
        self.app._quick_copy_model.removeSkillsByPath(paths_to_delete)

        def _background_delete():
            deleted = 0
            failed = 0
            paths_to_remove = []

            skill_items = [
                r.model_dump()
                for r in validated_records
                if not r.is_command and not r.is_screenshot
            ]
            command_items = [r for r in validated_records if r.is_command]
            screenshot_items = [r for r in validated_records if r.is_screenshot]

            # ── Step 1: Delete Skill Folders (FS)
            if skill_items:
                result = delete_project_skill_folders(skill_items)
                deleted += result["deleted"]
                failed += result["failed"]
                paths_to_remove.extend(
                    [d["path"] for d in result["details"] if d["status"] == "deleted"]
                )

            # ── Step 2: Delete Files (Commands + Screenshots) via unlink
            file_items = command_items + screenshot_items
            for record in file_items:
                p = Path(record.local_path)
                try:
                    if p.is_file():
                        p.unlink()
                        deleted += 1
                        paths_to_remove.append(record.local_path)
                except Exception as exc:
                    logger.error("[DELETE] FAILED %s: %s", p, exc)
                    failed += 1

            patch_cache_remove(paths_to_remove)

            # ── Step 3: Report back
            parts = [f"{deleted} deleted"] if deleted else []
            if failed:
                parts.append(f"{failed} failed")
            status = f"Deletion complete: {', '.join(parts) or 'nothing happened'}"

            # Use a safer way to call back to the UI, especially for tests
            if hasattr(self.app, "_set_status"):
                try:
                    QTimer.singleShot(0, lambda: self.app._set_status(status))
                except TypeError:
                    # Fallback for environments where QTimer.singleShot signature matches fail (like MagicMock context)
                    self.app._set_status(status)

        self.app.task_runner.run(_background_delete)

    @Slot(str)
    def deleteSkill(self, path: str):
        """Deletes a single skill by its local path."""
        if not path:
            return
        skill = next(
            (s for s in self.app.skillModel._all_skills if s.get("local_path") == path), None
        )
        if skill:
            self.deleteSkills([skill])

    @Slot()
    def deleteSelectedSkills(self):
        """Deletes all currently selected skills."""
        selected_paths = self.app.skillModel.getSelectedPaths()
        selected = [
            s for s in self.app.skillModel._all_skills if s.get("local_path") in selected_paths
        ]
        if selected:
            self.deleteSkills(selected)
        else:
            self.app._set_status("No skills selected for deletion")

    @Slot()
    def archiveSelectedSkills(self):
        """Archives all currently selected skills."""
        selected_paths = self.app.skillModel.getSelectedPaths()
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
            self.app.skillModel.clearSelection()
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
                logger.error("[TEMP_CLEANUP] Failed to delete %s: %s", path_str, e)
                capture_exception(e)

        save_temp_registry([])
        if deleted_count > 0:
            logger.info("[TEMP_CLEANUP] Cleaned up %d temporary paths.", deleted_count)

    def cleanup_temp_screenshots(self):
        """Deletes all temporary screenshots recorded in the registry."""
        temp_paths = load_temp_screenshots_registry()
        if not temp_paths:
            return

        deleted_count = 0
        for path_str in temp_paths:
            p = Path(path_str)
            try:
                if p.is_file():
                    p.unlink()
                    deleted_count += 1
            except Exception as e:
                logger.error("[TEMP_SCREENSHOT_CLEANUP] Failed to delete %s: %s", path_str, e)
                capture_exception(e)

        if temp_paths:
            patch_cache_remove(temp_paths)

        save_temp_screenshots_registry([])
        if deleted_count > 0:
            logger.info(
                "[TEMP_SCREENSHOT_CLEANUP] Cleaned up %d temporary screenshots.",
                deleted_count,
            )

    @Slot(str)
    def copySelectedSkillsToProject(self, project_path: str, is_temporary: bool = False):
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
                        updated = list(set(existing + new_temp_paths))
                        save_temp_registry(updated)

                discovered_skills = []
                if result["details"]:
                    diag = get_diagnostic_logger()
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
                                skill_data = service.discover_single(skill_path, proj_path)
                                if skill_data:
                                    discovered_skills.append(skill_data)
                                else:
                                    diag.log_event(
                                        "WARNING",
                                        CATEGORY_SELECTION_REFRESHED,
                                        f"discover_single returned None for skill: {skill_path}",
                                    )
                            except Exception as exc:
                                logger.error(
                                    "[TARGETED SCAN] Failed scanning %s: %s", skill_path, exc
                                )

                if discovered_skills:
                    patch_cache_add(discovered_skills)

                    def update_ui():
                        self._merge_discovered_skills(discovered_skills)
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

    @Slot(str)
    def copySelectedSkillsToProjectTemporarily(self, project_path: str):
        """Exposed slot for temporary copying."""
        self.copySelectedSkillsToProject(project_path, is_temporary=True)

    @Slot(str)
    def copySkillToClipboard(self, path: str):
        """Finds skill by path and copies its reference to clipboard."""
        skill = next(
            (s for s in self.app.skillModel._all_skills if s.get("local_path") == path), None
        )
        if skill:
            self.copySkillReference(skill)  # type: ignore[arg-type]
        else:
            self.copyTextToClipboard(path)

    @Slot()
    def copyCurrentSelectionOrFocusedSkill(self):
        """Orchestrates copying based on selection or focus."""
        if self.app.skillModel.selectedCount > 0:
            self.copySelectedSkillsToClipboard()
            return
        if self.app._selected_skill and self.app._selected_skill.get("local_path"):
            self.copySkillReference(self.app._selected_skill)
            return
        first_skill = self.app.skillModel.get_skill_at(0)
        if first_skill:
            self.copySkillReference(first_skill)
            return
        self.app._set_status("No skill available to copy")

    @Slot()
    def copySelectedSkillsToClipboard(self):
        """Copies selected skill references for the current project to clipboard."""
        from skill_manager.core.quick_copy import format_project_skill_reference

        paths = self.app.skillModel.getFilteredSelectedPaths()
        if not paths:
            self.app._set_status("No skills selected")
            return

        references = []
        for path in paths:
            skill = next(
                (s for s in self.app.skillModel._all_filtered_skills if s.local_path == path), None
            )
            if skill:
                references.append(
                    format_project_skill_reference(
                        skill, self.app._client_format, all_skills=self.app.skillModel._all_skills
                    )
                )
            else:
                references.append(path)

        content = " ".join(references)
        self.app._clipboard.setText(content)
        self.app._set_status(f"Copied {len(references)} skills to clipboard")
        self._maybeMinimizeOnCopy()

    @Slot(str)
    def copyTextToClipboard(self, content: str):
        """Copies raw text to system clipboard."""
        self.app._clipboard.setText(str(content))
        self.app._set_status("Copied to clipboard")
        self._maybeMinimizeOnCopy()

    @Slot(dict, str)
    def copySkillReference(self, skill: dict, arg: str = ""):
        """Copies a formatted skill reference to clipboard."""
        from skill_manager.core.quick_copy import format_project_skill_reference

        ref = format_project_skill_reference(
            skill, self.app._client_format, all_skills=self.app.skillModel._all_skills
        )
        if arg:
            ref += f"({arg})"
        self.app._clipboard.setText(ref)
        self.app._set_status(f"Copied reference: {ref}")
        self._maybeMinimizeOnCopy()

    @Slot(str)
    def copyCollectionToClipboard(self, name: str):
        """Copies a collection's skill references to clipboard and auto-pastes."""
        from skill_manager.core.quick_copy import format_project_skill_reference

        entry = self.app._custom_collections.get(name, {})
        if not isinstance(entry, dict):
            return

        paths = entry.get("paths", [])
        if not paths:
            self.app._set_status(f"Collection '{name}' has no skills")
            return

        references = []
        for path in paths:
            skill = next((s for s in self.app.skillModel._all_skills if s.local_path == path), None)
            if skill:
                references.append(
                    format_project_skill_reference(
                        skill,
                        self.app._client_format,
                        all_skills=self.app.skillModel._all_skills,
                    )
                )
            else:
                references.append(path)

        content = " ".join(references)
        self.app._clipboard.setText(content)
        self.app._set_status(f"Copied collection '{name}' ({len(references)} skills)")

        # Auto-paste after a short delay to allow focus to settle
        delay = 120 if self.app.config_controller.autoMinimizeOnQuickCopy else 50
        if self.app.config_controller.autoMinimizeOnQuickCopy:
            self.minimizeAppRequested.emit()
        QTimer.singleShot(delay, self._send_paste_to_focused_window)

    def _send_paste_to_focused_window(self):
        """Helper that calls the Win32 paste function."""
        from skill_manager.utils.win32 import send_paste_to_focused_window

        if not send_paste_to_focused_window():
            self.app._set_status("Copied, but could not paste automatically")

    @Slot(str, str, "QStringList", str)
    def createCustomCommand(self, name: str, body: str, project_labels: "list[str]", category: str):
        """Creates Custom Command .md files in one or more projects."""
        diag = get_diagnostic_logger()
        diag.log_event("INFO", CATEGORY_COMMAND_CREATED, f"name={name}, projects={project_labels}")
        from skill_manager.core.commands import create_custom_command_files_multi

        results = create_custom_command_files_multi(
            name=name,
            body=body,
            project_labels=list(project_labels),
            category=category,
            project_paths=self.app._projects,
        )

        created = [r for r in results if r.ok]
        failed = [r for r in results if not r.ok]

        if not created:
            msg = failed[0].message if failed else "Error: No projects selected"
            self.app._set_status(msg)
            return

        self.app._set_status(f"Created command in {len(created)} project(s)")

        for result in created:
            if result.path:
                from skill_manager.core.discovery import DiscoveryService
                from skill_manager.core.persistence import patch_cache_add

                service = DiscoveryService(
                    sources=list(self.app._sources),
                    projects=self.app._projects,
                    archive_paths=self.app._archive_paths,
                    starred_paths=self.app._starred_paths,
                    project_aliases=self.app._project_aliases,
                )
                try:
                    skill_data = service.discover_single(result.path, result.path.parent)
                    if skill_data:
                        patch_cache_add([skill_data])
                        self._merge_discovered_skills([skill_data])
                        self._refresh_selected_skill(str(result.path))
                    else:
                        diag.log_event(
                            "WARNING",
                            CATEGORY_SELECTION_REFRESHED,
                            f"discover_single returned None for command: {result.path}",
                        )
                except Exception as exc:
                    logger.error("[CREATE COMMAND] Failed scanning %s: %s", result.path, exc)

    @Slot(str, str, str, str, "QStringList", str)
    def updateCustomCommandFull(
        self,
        local_path: str,
        name: str,
        body: str,
        category: str,
        project_labels: "list[str]",
        on_conflict: str = "",
        confirmed_removals: list[str] | None = None,
    ):
        """Updates an existing Custom Command .md file across projects."""
        diag = get_diagnostic_logger()
        diag.log_event(
            "INFO",
            CATEGORY_COMMAND_UPDATED,
            f"path={local_path}, name={name}, projects={project_labels}, on_conflict={on_conflict}",
        )
        from skill_manager.core.commands import update_custom_command_file_multi

        results = update_custom_command_file_multi(
            local_path=local_path,
            name=name,
            body=body,
            category=category,
            project_labels=list(project_labels),
            project_paths=self.app._projects,
            on_conflict=on_conflict or None,
            confirmed_removals=confirmed_removals,
        )

        canonical = results[0] if results else None
        if canonical and canonical.needs_conflict_resolution and canonical.conflicting_path:
            self.app.commandUpdateConflict.emit(
                local_path,
                str(canonical.conflicting_path),
                canonical.suggested_rename or "",
            )
            return

        # Check if confirmation is needed for project removals
        confirm_results = [r for r in results if r.needs_confirm]
        if confirm_results:
            pending: list[str] = []
            for r in confirm_results:
                pending.extend(r.pending_removals)
            # Store args so confirmCommandRemovals can re-invoke
            self._pending_command_update = {
                "local_path": local_path,
                "name": name,
                "body": body,
                "category": category,
                "project_labels": list(project_labels),
                "on_conflict": on_conflict,
            }
            self.commandPendingRemovals.emit(local_path, pending)
            return

        updated = [r for r in results if r.ok]
        failed = [r for r in results if not r.ok]

        if not updated:
            msg = failed[0].message if failed else "Error: No projects updated"
            self.app._set_status(msg)
            return

        self.app._set_status(f"Updated command in {len(updated)} project(s)")

        # ── Targeted rescan: collect unique affected project paths
        from skill_manager.core.commands import find_project_path_by_label
        from skill_manager.core.discovery import DiscoveryService
        from skill_manager.core.persistence import patch_cache_add
        from skill_manager.core.quick_copy import project_root_for_project

        service = DiscoveryService(
            sources=list(self.app._sources),
            projects=self.app._projects,
            archive_paths=self.app._archive_paths,
            starred_paths=self.app._starred_paths,
            project_aliases=self.app._project_aliases,
        )

        affected_project_paths: set[Path] = set()

        for result in updated:
            if result.path:
                # Walk up from result.path.parent to find project root
                proj_path = project_root_for_project(result.path.parent)
                affected_project_paths.add(proj_path)

        # Include paths of any removed projects
        if canonical and canonical.pending_removals:
            for label in canonical.pending_removals:
                target = find_project_path_by_label(label, self.app._projects)
                if target:
                    affected_project_paths.add(project_root_for_project(target))

        all_discovered: list[dict] = []
        for proj_path in affected_project_paths:
            try:
                discovered = service.discover_project(proj_path)
                all_discovered.extend(discovered)
            except Exception as exc:
                logger.error("[UPDATE COMMAND] Failed rescan of %s: %s", proj_path, exc)

        # Defer merge to avoid blocking UI
        def _apply_merge():
            if all_discovered:
                patch_cache_add(all_discovered)
                self._merge_discovered_skills(all_discovered)
            if updated and updated[0].path:
                self._refresh_selected_skill(local_path, rename_path=str(updated[0].path))
                self.app.notify_command_updated(local_path, str(updated[0].path))

        QTimer.singleShot(0, _apply_merge)

    def confirmCommandRemovals(self, local_path: str, confirmed_labels: list[str]):
        """Re-invoke updateCustomCommandFull with confirmed removals."""
        pending = self._pending_command_update
        if not pending or pending.get("local_path") != local_path:
            logger.warning("[UPDATE COMMAND] No pending command update for %s", local_path)
            return
        self._pending_command_update = None
        self.updateCustomCommandFull(
            local_path=pending["local_path"],
            name=pending["name"],
            body=pending["body"],
            category=pending["category"],
            project_labels=pending["project_labels"],
            on_conflict=pending["on_conflict"],
            confirmed_removals=confirmed_labels,
        )

    @Slot(str, result="QStringList")
    def commandProjectsForPath(self, local_path: str) -> "list[str]":
        """Return project labels that hold a copy of this command."""
        from skill_manager.core.commands import find_command_holder_projects

        path = Path(local_path)
        if not path.is_file():
            return []

        stem = path.stem
        return find_command_holder_projects(stem, self.app._projects)

    @Slot(str, "QStringList")
    def deleteCustomCommand(self, command_name: str, project_labels: "list[str]"):
        """Delete a command from the listed projects."""
        from skill_manager.core.commands import build_command_filename, find_project_path_by_label
        from skill_manager.core.quick_copy import project_root_for_project

        safe_name = build_command_filename(command_name)
        items = []
        for label in project_labels:
            target = find_project_path_by_label(label, self.app._projects)
            if not target:
                continue
            commands_dir = project_root_for_project(target) / ".agents" / "commands"
            file_path = commands_dir / safe_name
            if file_path.is_file():
                items.append({"local_path": str(file_path), "is_command": True})

        if items:
            self.deleteSkills(items)
        else:
            self.app._set_status("Command not found in selected projects")

    def _saveArchive(self):
        """Internal helper to persist archive state."""
        save_archive(self.app._archive_paths)

    def _saveStarred(self):
        """Internal helper to persist starred state."""
        save_starred(self.app._starred_paths)

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

        If the mutated skill matches the currently selected one, replace
        the stale snapshot with a fresh dict from the model and emit
        ``selectedSkillChanged`` so QML re-binds.

        For renames, pass ``rename_path`` (the new path) when
        ``local_path`` is the old path that no longer exists in the model.

        Called from ``createCustomCommand``, ``updateCustomCommandFull``,
        and any other site that calls ``addOrUpdateSkills`` (or
        ``setSkills``) after a mutation that may change the selected
        skill's data.

        See ``docs/adr/0011-selection-refresh-invariant.md``.
        """
        diag = get_diagnostic_logger()
        selected = self.app._selected_skill
        selected_path = selected.get("local_path") if isinstance(selected, dict) else None

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

        # For renames, the old path no longer exists. Try the new path.
        lookup_path = rename_path or local_path

        # Find the row in the active model
        model = self.app.skillModel
        for i in range(len(model._filtered_skills)):
            skill = model._filtered_skills[i]
            if skill.local_path == lookup_path:
                self.app._selected_skill = model.get_skill_at(i)
                self.app.selectedSkillChanged.emit()
                diag.log_event(
                    "INFO",
                    CATEGORY_SELECTION_REFRESHED,
                    f"refreshed: {lookup_path}"
                    + (f" (renamed from {local_path})" if rename_path else ""),
                )
                return

        diag.log_event(
            "WARNING",
            CATEGORY_SELECTION_REFRESHED,
            f"not_in_view: {lookup_path} not found in active model",
        )

    # -----------------------------------------------------------------
    # Carry: copy commands with skill dependency detection
    # -----------------------------------------------------------------

    @Slot(str, str)
    def copyCommandsToProjectWithCarry(self, project_path: str, command_paths_json: str):
        """Copy commands to *project_path*; if skills are missing, prompt carry."""
        import json
        from pathlib import Path

        command_paths = json.loads(command_paths_json or "[]")
        if not command_paths or not project_path:
            return

        from skill_manager.core.copier import copy_commands_with_skill_carry

        commands = [{"local_path": p, "name": Path(p).stem} for p in command_paths]

        def _run():
            result = copy_commands_with_skill_carry(
                commands,
                project_path,
                self.app._library_model._all_skills,  # type: ignore[attr-defined]
                confirmed_skills=None,
            )
            missing = result.get("missing_skills") or []
            if missing:
                QTimer.singleShot(
                    0,
                    self,
                    lambda: self.commandSkillsCarryPrompt.emit(
                        json.dumps(command_paths), project_path, json.dumps(missing)
                    ),
                )
            else:
                QTimer.singleShot(
                    0,
                    self.app,
                    lambda: self.app._set_status(
                        f"Copied {len(command_paths)} command(s); no skills to carry."
                    ),
                )

        self.app.task_runner.run(_run)

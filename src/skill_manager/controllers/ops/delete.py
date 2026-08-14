"""Delete operations for the OpsController."""

import logging
from pathlib import Path

from PySide6.QtCore import Q_ARG, QMetaObject, Qt, Slot

from skill_manager.controllers.ops._helpers import _get_item_attr
from skill_manager.core.analytics import capture_exception
from skill_manager.core.persistence import (
    load_temp_registry,
    load_temp_snaps_registry,
    patch_cache_remove,
    save_temp_registry,
    save_temp_snaps_registry,
)
from skill_manager.core.quick_copy import delete_project_skill_folders
from skill_manager.core.schemas import SkillRecord

logger = logging.getLogger(__name__)


class DeleteMixin:
    """Skill, command, snap and temp-file deletion flows."""

    def deleteSkills(self, items: list):
        """Orchestrates deletion of skills (folders and local copies)."""
        logger.info("[DELETE] deleteSkills called with %d items", len(items))
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
            logger.info("[DELETE] no valid records after validation, returning")
            return

        self._is_deleting = True

        # ── Step 0: Optimistic UI Removal
        paths_to_delete = [r.local_path for r in validated_records if r.local_path]
        logger.info("[DELETE] removing %d paths from models", len(paths_to_delete))
        self.app._library_model.removeSkillsByPath(paths_to_delete)
        self.app._quick_copy_model.removeSkillsByPath(paths_to_delete)

        current_sel_path = getattr(self.app._selected_skill, "local_path", "")
        if current_sel_path and current_sel_path in set(paths_to_delete):
            logger.info(
                "[DELETE] currently selected skill %s is being deleted; resetting selectedSkill",
                current_sel_path,
            )
            self.app.set_selected_skill({})

        def _background_delete():
            deleted = 0
            failed = 0
            skipped = 0
            paths_to_remove = []

            skill_items = [
                r.model_dump() for r in validated_records if not r.is_command and not r.is_snap
            ]
            command_items = [r for r in validated_records if r.is_command]
            snap_items = [r for r in validated_records if r.is_snap]

            # ── Step 1: Delete Skill Folders (FS)
            if skill_items:
                result = delete_project_skill_folders(skill_items)
                deleted += result["deleted"]
                failed += result["failed"]
                skipped += result.get("skipped", 0)
                paths_to_remove.extend(
                    [d["path"] for d in result["details"] if d["status"] == "deleted"]
                )
                for d in result["details"]:
                    if d["status"] in ("skipped", "failed"):
                        logger.warning(
                            "[DELETE] %s: %s — %s", d["skill"], d["status"], d["message"]
                        )

            # ── Step 2: Delete Files (Commands + Screenshots) via unlink
            file_items = command_items + snap_items
            for record in file_items:
                p = Path(record.local_path)
                try:
                    if p.is_file():
                        p.unlink()
                        deleted += 1
                        paths_to_remove.append(record.local_path)
                        logger.info("[DELETE] deleted file: %s", p)
                    else:
                        logger.warning("[DELETE] skipped file (not a file): %s", p)
                        skipped += 1
                except Exception as exc:
                    logger.error("[DELETE] FAILED %s: %s", p, exc)
                    failed += 1

            patch_cache_remove(paths_to_remove)

            # ── Step 3: Report back
            parts = []
            if deleted:
                parts.append(f"{deleted} deleted")
            if failed:
                parts.append(f"{failed} failed")
            if skipped:
                parts.append(f"{skipped} skipped")
            if parts:
                status = f"Deletion complete: {', '.join(parts)}"
            else:
                status = "Deletion complete: no items processed"

            # Cross-thread-safe status update via QMetaObject
            if hasattr(self.app, "_set_status"):
                try:
                    ok = QMetaObject.invokeMethod(
                        self.app,
                        "_set_status",
                        Qt.ConnectionType.QueuedConnection,
                        Q_ARG(str, status),
                    )
                    if not ok:
                        logger.warning(
                            "[DELETE] invokeMethod(_set_status) returned False; falling back to direct call"
                        )
                        try:
                            self.app._set_status(status)
                        except Exception as exc:
                            logger.warning("[DELETE] direct status update failed: %s", exc)
                except TypeError:
                    # Mock objects / test environments where invokeMethod fails
                    try:
                        self.app._set_status(status)
                    except Exception as exc:
                        logger.warning("[DELETE] status update failed: %s", exc)

            # Signal discovery to apply targeted re-scan
            removed = set(paths_to_remove)
            if removed and hasattr(self.app, "discovery"):
                try:
                    self.app.discovery.skillsDeleted.emit(list(removed))
                except Exception as exc:
                    logger.warning("[DELETE] failed to signal discovery: %s", exc)

            self._is_deleting = False

        self.app.task_runner.run(_background_delete)

    @Slot(str)
    def deleteSkill(self, path: str):
        """Deletes a single skill by its local_path."""
        if not path:
            return
        skill = next(
            (s for s in self.app.skillModel._all_skills if _get_item_attr(s, "local_path") == path),
            None,
        )
        if skill:
            self.deleteSkills([skill])
        else:
            self.deleteSkillsByPaths([path])

    @Slot(list)
    def deleteSkillsByPaths(self, paths: list[str]):
        """Deletes skills by their local paths, searching BOTH models."""
        logger.info("[DELETE] deleteSkillsByPaths called with %d paths", len(paths))
        if not paths:
            self.app._set_status("No skills selected for deletion")
            return
        path_set = set(paths)
        records = []
        for model in (self.app._library_model, self.app._quick_copy_model):
            for s in model._all_skills:
                lp = _get_item_attr(s, "local_path")
                if lp in path_set:
                    records.append(s)
                    path_set.discard(lp)

        for p in list(path_set):
            file_p = Path(p)
            if file_p.is_file():
                records.append(
                    {
                        "local_path": str(file_p),
                        "is_snap": file_p.parent.name == "screenshots"
                        or file_p.suffix in (".png", ".jpg", ".jpeg"),
                        "is_command": file_p.suffix in (".sh", ".md", ".bash")
                        and file_p.parent.name == "commands",
                    }
                )
                path_set.discard(p)

        if not records:
            logger.warning("[DELETE] no records found for paths: %s", list(paths))
            self.app._set_status("No skills selected for deletion")
            return
        logger.info("[DELETE] found %d records across models/files", len(records))
        self.deleteSkills(records)

    @Slot()
    def deleteSelectedSkills(self):
        """Deletes all currently selected skills from the active view's model."""
        selected_paths = self.app.skillModel.getSelectedPaths()
        self.deleteSkillsByPaths(selected_paths)

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

    def cleanup_temp_snaps(self):
        """Deletes all temporary screenshots recorded in the registry."""
        temp_paths = load_temp_snaps_registry()
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
                logger.error("[TEMP_SNAP_CLEANUP] Failed to delete %s: %s", path_str, e)
                capture_exception(e)

        if temp_paths:
            patch_cache_remove(temp_paths)

        save_temp_snaps_registry([])
        if deleted_count > 0:
            logger.info(
                "[TEMP_SNAP_CLEANUP] Cleaned up %d temporary screenshots.",
                deleted_count,
            )

    @Slot(str, list)
    def deleteSkillFromProjects(self, path: str, project_labels: "list[str]"):
        """Delete a skill folder or file from the specified projects only."""
        if not path or not project_labels:
            return

        from skill_manager.core.commands import find_project_path_by_label

        skill_path = Path(path)
        folder_name = skill_path.name
        items_to_delete = []

        for label in project_labels:
            target = find_project_path_by_label(label, self.app._projects)
            if not target:
                continue
            skill_folder = target / ".agents" / "skills" / folder_name
            snap_file = target / ".agents" / "screenshots" / folder_name
            command_file = target / ".agents" / "commands" / folder_name

            if skill_folder.is_dir():
                items_to_delete.append(
                    {
                        "local_path": str(skill_folder),
                        "project_path": str(target),
                        "name": folder_name,
                    }
                )
            elif snap_file.is_file():
                items_to_delete.append(
                    {
                        "local_path": str(snap_file),
                        "project_path": str(target),
                        "name": folder_name,
                        "is_snap": True,
                    }
                )
            elif command_file.is_file():
                items_to_delete.append(
                    {
                        "local_path": str(command_file),
                        "project_path": str(target),
                        "name": folder_name,
                        "is_command": True,
                    }
                )

        if not items_to_delete and skill_path.exists():
            self.deleteSkillsByPaths([path])
            return

        if items_to_delete:
            self.deleteSkills(items_to_delete)
        else:
            self.app._set_status("Skill not found in selected projects")

    @Slot(str, list)
    def deleteCustomCommand(self, command_name: str, project_labels: "list[str]"):
        """Delete a command from the listed projects."""
        from skill_manager.core.commands import build_command_filename, find_project_path_by_label
        from skill_manager.core.quick_copy import project_root_for_project

        safe_name = build_command_filename(command_name)
        items = []
        for label in project_labels:
            target = find_project_path_by_label(
                label, self.app._projects, project_aliases=self.app._project_aliases
            )
            if not target:
                continue
            commands_dir = project_root_for_project(target) / ".agents" / "commands"
            file_path = commands_dir / safe_name
            if file_path.is_file():
                items.append(
                    {"name": command_name, "local_path": str(file_path), "is_command": True}
                )

        if items:
            self.deleteSkills(items)
        else:
            self.app._set_status("Command not found in selected projects")

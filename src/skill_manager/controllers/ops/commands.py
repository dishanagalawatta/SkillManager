"""Custom command operations for the OpsController."""

import logging
from pathlib import Path

from PySide6.QtCore import Slot

from skill_manager.controllers.ops._helpers import QTimer, _build_discovery_service, _get_item_attr
from skill_manager.core.diagnostics import (
    CATEGORY_COMMAND_CREATED,
    CATEGORY_COMMAND_TARGETED_REFRESH,
    CATEGORY_COMMAND_UPDATED,
    CATEGORY_SELECTION_REFRESHED,
    get_diagnostic_logger,
)

logger = logging.getLogger(__name__)


class CommandsMixin:
    """Create/update/remove custom commands across projects."""

    @Slot(str, str, list, str, result=str)
    def createCustomCommand(
        self, name: str, body: str, project_labels: "list[str]", category: str
    ) -> str:
        """Creates Custom Command .md files in one or more projects.

        Returns the local path of the first successfully created command
        ``.md`` file (empty string if none were created).
        """
        diag = get_diagnostic_logger()
        diag.log_event("INFO", CATEGORY_COMMAND_CREATED, f"name={name}, projects={project_labels}")
        from skill_manager.core.commands import create_custom_command_files_multi

        results = create_custom_command_files_multi(
            name=name,
            body=body,
            project_labels=list(project_labels),
            category=category,
            project_paths=self.app._projects,
            project_aliases=self.app._project_aliases,
        )

        created = [r for r in results if r.ok]
        failed = [r for r in results if not r.ok]

        if not created:
            msg = failed[0].message if failed else "Error: No projects selected"
            self.app._set_status(msg)
            return ""

        self.app._set_status(f"Created command in {len(created)} project(s)")

        for result in created:
            if result.path:
                from skill_manager.core.persistence import patch_cache_add

                service = _build_discovery_service(self.app)
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

        # Check for missing skill dependencies
        from skill_manager.core.quick_copy import project_root_for_project

        for result in created:
            if result.path:
                project_path = project_root_for_project(result.path)
                self._emit_missing_skills_prompt(project_path, result.path, body, "CREATE")

        return str(created[0].path) if created else ""

    def _snapshot_affected_paths(self, affected_project_paths: set[Path]) -> set[str]:
        """Return local_paths in both models whose project_path matches an affected project."""
        from skill_manager.core.copier import get_skills_dir

        affected_norm = {str(get_skills_dir(p)) for p in affected_project_paths}
        snap: set[str] = set()
        for model in (self.app._library_model, self.app._quick_copy_model):
            for skill in model._all_skills:
                sp = (
                    skill.project_path
                    if hasattr(skill, "project_path")
                    else skill.get("project_path", "")
                )
                if not sp:
                    continue
                if str(get_skills_dir(sp)) in affected_norm:
                    lp = (
                        skill.local_path
                        if hasattr(skill, "local_path")
                        else skill.get("local_path", "")
                    )
                    if lp:
                        snap.add(lp)
        return snap

    def _get_all_known_skills(self) -> list:
        """Return combined unique skills from library, quick copy, and active models."""
        skills: list = []
        seen_paths: set[str] = set()
        models = [
            getattr(self.app, "_library_model", None),
            getattr(self.app, "_quick_copy_model", None),
            getattr(self.app, "skillModel", None),
        ]
        for model in models:
            if not model:
                continue
            all_s = getattr(model, "_all_skills", []) or []
            for s in all_s:
                lp = _get_item_attr(s, "local_path")
                if lp and lp not in seen_paths:
                    seen_paths.add(lp)
                    skills.append(s)
                elif not lp and s not in skills:
                    skills.append(s)
        return skills

    def _emit_missing_skills_prompt(self, proj_root: Path, command_path: Path, body: str, tag: str):
        """Check *command_path* for missing skill dependencies and prompt the carry dialog.

        ``proj_root`` is the project root the command belongs to, ``tag`` is a
        log prefix (e.g. ``CREATE``/``UPDATE``) used to keep diagnostics stable.
        """
        import json
        from dataclasses import asdict

        from skill_manager.core.copier import find_missing_skills_for_commands

        cmd_dict = {"local_path": str(command_path), "body": body, "name": command_path.stem}
        logger.info(
            "[CARRY %s] Checking missing skills for command: %s in project: %s",
            tag,
            command_path,
            proj_root,
        )
        missing = find_missing_skills_for_commands(
            [cmd_dict],
            proj_root,
            self._get_all_known_skills(),
        )
        logger.info("[CARRY %s] Found missing skills: %s", tag, missing)
        if missing:
            missing_dicts = [
                asdict(m)
                if hasattr(m, "__dataclass_fields__")
                else (m.to_dict() if hasattr(m, "to_dict") else dict(m))
                for m in missing
            ]
            QTimer.singleShot(
                0,
                self,
                lambda p=proj_root, rp=command_path, m=missing_dicts: (
                    self.commandSkillsCarryPrompt.emit(json.dumps([str(rp)]), str(p), json.dumps(m))
                ),
            )

    @Slot(str, str, str, str, list, str)
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
            project_aliases=self.app._project_aliases,
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

        added = sum(1 for r in updated if r.set_membership in ("canonical", "fanout_add"))
        skipped = sum(1 for r in updated if r.set_membership == "fanout_skip")
        removed = sum(1 for r in updated if r.set_membership == "removal")
        parts = [f"Updated command in {added} project(s)"]
        if skipped:
            parts.append(f"{skipped} already up to date")
        if removed:
            parts.append(f"{removed} removed")
        self.app._set_status(", ".join(parts))

        # ── Instant body refresh: update _selected_skill immediately
        # so the CommandInspector reflects the new content without
        # waiting for the deferred discovery-rescan pipeline.
        sel = self.app._selected_skill
        path = sel.local_path if hasattr(sel, "local_path") else sel.get("local_path")
        if path == local_path:
            if hasattr(sel, "local_path"):
                sel.body_content = body
                sel.name = name
            else:
                sel["body_content"] = body
                sel["name"] = name

        # ── Targeted rescan: collect unique affected project paths
        from skill_manager.core.commands import find_project_path_by_label
        from skill_manager.core.quick_copy import project_root_for_project

        service = _build_discovery_service(self.app)

        affected_project_paths: set[Path] = set()

        for result in updated:
            if result.path:
                # Walk up from result.path.parent to find project root
                proj_path = project_root_for_project(result.path.parent)
                affected_project_paths.add(proj_path)

        # Include paths of any removed projects
        if canonical and canonical.pending_removals:
            for label in canonical.pending_removals:
                target = find_project_path_by_label(
                    label, self.app._projects, project_aliases=self.app._project_aliases
                )
                if target:
                    affected_project_paths.add(project_root_for_project(target))

        # Also include paths from confirmed removals (the re-invocation case
        # where pending_removals is empty but the user confirmed deletions)
        if confirmed_removals:
            for label in confirmed_removals:
                target = find_project_path_by_label(
                    label, self.app._projects, project_aliases=self.app._project_aliases
                )
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
            stale_paths = self._apply_targeted_refresh(affected_project_paths, all_discovered)

            if updated and updated[0].path:
                self._refresh_selected_skill(local_path, rename_path=str(updated[0].path))
                # Force-update body_content on _selected_skill with the
                # authoritative value from the update args.  The model
                # may still carry stale data if the discovery rescan
                # re-read the file before the write flushed.
                selected = self.app._selected_skill
                sel_path = None
                if hasattr(selected, "value"):
                    sel_path = selected.value("local_path")
                elif isinstance(selected, dict):
                    sel_path = selected.get("local_path")
                target_path = str(updated[0].path)
                if sel_path == target_path and body:
                    if hasattr(selected, "insert"):
                        selected.insert("body_content", body)
                    elif isinstance(selected, dict):
                        selected["body_content"] = body
                self.app.notify_command_updated(local_path, str(updated[0].path))

            if stale_paths:
                diag = get_diagnostic_logger()
                diag.log_event(
                    "INFO",
                    CATEGORY_COMMAND_TARGETED_REFRESH,
                    "targeted_refresh_complete",
                    data={
                        "added_or_updated": len(all_discovered),
                        "stale_removed": len(stale_paths),
                        "affected_projects": len(affected_project_paths),
                    },
                )

            # Check for missing skill dependencies after merge
            from skill_manager.core.quick_copy import project_root_for_project

            for r in updated:
                if r.path:
                    proj_root = project_root_for_project(r.path)
                    self._emit_missing_skills_prompt(proj_root, r.path, body, "UPDATE")

        QTimer.singleShot(0, _apply_merge)

    @Slot(str, list)
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

    @Slot(str, result=list)
    def commandProjectsForPath(self, local_path: str) -> "list[str]":
        """Return project labels that hold a copy of this command."""
        from skill_manager.core.commands import find_command_holder_projects

        path = Path(local_path)
        if not path.is_file():
            return []

        stem = path.stem
        return find_command_holder_projects(
            stem, self.app._projects, project_aliases=self.app._project_aliases
        )

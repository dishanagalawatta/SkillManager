"""Custom command operations for the OpsController."""

import logging
from pathlib import Path

from PySide6.QtCore import Slot

from skill_manager.controllers.ops._helpers import QTimer, _build_discovery_service, _get_item_attr
from skill_manager.core.diagnostics import (
    CATEGORY_COMMAND_CREATED,
    CATEGORY_COMMAND_UPDATED,
    CATEGORY_SELECTION_REFRESHED,
    get_diagnostic_logger,
)

logger = logging.getLogger(__name__)


class CommandsMixin:
    """Create/update/remove custom commands across projects."""

    def _canonical_command_project(self) -> Path | None:
        """Resolve the project that owns the canonical command file.

        The Library is the single source of truth for a command: the dialog
        no longer asks for a set of projects, it edits the command where it
        lives. New commands are created in the Library's active project;
        when no project is active the first configured project is used.
        """
        from skill_manager.core.commands import find_project_path_by_label

        projects = list(self.app._projects)
        if not projects:
            return None

        label = getattr(self.app, "_current_project_label", "") or ""
        if label:
            found = find_project_path_by_label(
                label, projects, project_aliases=self.app._project_aliases
            )
            if found:
                return found
        return Path(projects[0])

    @Slot(str, str, str, str, result=str)
    def createCustomCommand(
        self, name: str, body: str, category: str, on_conflict: str = ""
    ) -> str:
        """Create the canonical command file in the Library's active project.

        The dialog does not pick projects any more: the command is created
        once, in the Library, and deployed to other projects later through
        the Library's own copy flow.

        A name that already exists in that project is not an error: the
        conflict is reported through ``commandCreateConflict`` so the dialog
        can offer overwrite / rename / cancel, exactly like the update path.

        Returns the local path of the created command ``.md`` file (empty
        string when nothing was created).
        """
        diag = get_diagnostic_logger()
        diag.log_event("INFO", CATEGORY_COMMAND_CREATED, f"name={name}, on_conflict={on_conflict}")
        from skill_manager.core.commands import create_custom_command_file

        project_path = self._canonical_command_project()
        if project_path is None:
            self.app._set_status("Add a project before creating a command.")
            return ""

        from skill_manager.core.quick_copy import project_label

        result = create_custom_command_file(
            name=name,
            body=body,
            project_label_name=project_label(project_path),
            category=category,
            project_paths=list(self.app._projects),
            project_aliases=self.app._project_aliases,
            on_conflict=on_conflict or None,
        )

        if result.needs_conflict_resolution and result.conflicting_path:
            self.app.commandCreateConflict.emit(
                str(result.conflicting_path), result.suggested_rename or ""
            )
            return ""

        if not result.ok:
            self.app._set_status(result.message)
            return ""
        if not result.path:
            self.app._set_status(result.message)
            return ""

        self.app._set_status(result.message)

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

        # A new command can reference skills the owning project does not
        # have yet, so the carry check runs for creates exactly like it
        # does for updates and for project deployments.
        from skill_manager.core.quick_copy import project_root_for_project

        pairs = [(project_root_for_project(result.path), result.path)]
        self._emit_missing_skills_batch(self._collect_missing_skills_batch(pairs, body, "CREATE"))

        return str(result.path)

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

    def _collect_missing_skills_batch(
        self, pairs: "list[tuple[Path, Path]]", body: str, tag: str
    ) -> list[dict]:
        """Return per-project missing-skills entries for *pairs*.

        Each entry is ``{"project_path": str, "command_paths": [str],
        "missing_skills": [dict]}`` — only projects with non-empty missing
        are included. Shared filesystem check makes the result idempotent:
        once skills are carried to every project, a re-edit yields ``[]``.
        """
        from dataclasses import asdict

        from skill_manager.core.copier import find_missing_skills_for_commands

        all_known = self._get_all_known_skills()
        batch: list[dict] = []
        for proj_root, command_path in pairs:
            cmd_dict = {
                "local_path": str(command_path),
                "body": body,
                "name": command_path.stem,
            }
            logger.info(
                "[CARRY %s] Checking missing skills for command: %s in project: %s",
                tag,
                command_path,
                proj_root,
            )
            missing = find_missing_skills_for_commands([cmd_dict], proj_root, all_known)
            logger.info("[CARRY %s] Found missing skills: %s", tag, missing)
            if not missing:
                continue
            missing_dicts = [
                asdict(m)
                if hasattr(m, "__dataclass_fields__")
                else (m.to_dict() if hasattr(m, "to_dict") else dict(m))
                for m in missing
            ]
            batch.append(
                {
                    "project_path": str(proj_root),
                    "command_paths": [str(command_path)],
                    "missing_skills": missing_dicts,
                }
            )
        return batch

    def _emit_missing_skills_batch(self, batch: list[dict]):
        """Emit a single batched carry prompt (no-op when empty).

        A single emission replaces the old per-project loop, which
        overwrote the single-instance QML dialog (last-writer-wins) so
        only the last project ever received carried skills.
        """
        import json

        if not batch:
            return
        if len(batch) == 1:
            entry = batch[0]
            QTimer.singleShot(
                0,
                self,
                lambda e=entry: self.commandSkillsCarryPrompt.emit(
                    json.dumps(e["command_paths"]),
                    e["project_path"],
                    json.dumps(e["missing_skills"]),
                ),
            )
            return
        payload = json.dumps(batch)
        QTimer.singleShot(0, self, lambda p=payload: self.commandSkillsCarryBatchPrompt.emit(p))

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

    @Slot(str, str, str, str, str)
    def updateCustomCommandFull(
        self,
        local_path: str,
        name: str,
        body: str,
        category: str,
        on_conflict: str = "",
    ):
        """Update the canonical command file in place.

        The dialog edits the Library's own copy of the command — there is no
        project fan-out any more. Deploying the updated command to other
        projects is the Library copy flow's job (Copy to Project), which
        detects the already-present files and asks whether to overwrite
        them.
        """
        diag = get_diagnostic_logger()
        diag.log_event(
            "INFO",
            CATEGORY_COMMAND_UPDATED,
            f"path={local_path}, name={name}, on_conflict={on_conflict}",
        )
        from skill_manager.core.commands import update_custom_command_file

        result = update_custom_command_file(
            local_path=local_path,
            name=name,
            body=body,
            category=category,
            on_conflict=on_conflict or None,
        )

        # A conflict takes precedence over a generic failure: the user has
        # to choose between overwrite, rename and cancel.
        if result.needs_conflict_resolution and result.conflicting_path:
            self.app.commandUpdateConflict.emit(
                local_path,
                str(result.conflicting_path),
                result.suggested_rename or "",
            )
            return

        if not result.ok:
            self.app._set_status(result.message)
            return

        if not result.path:
            self.app._set_status("Error: Command update produced no file")
            return

        self.app._set_status(f"Updated command {name}")

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

        # ── Targeted rescan of the project that owns the command.
        from skill_manager.core.quick_copy import project_root_for_project

        service = _build_discovery_service(self.app)
        affected_project_paths: set[Path] = {project_root_for_project(result.path.parent)}

        all_discovered: list[dict] = []
        for proj_path in affected_project_paths:
            try:
                discovered = service.discover_project(proj_path)
                all_discovered.extend(discovered)
            except Exception as exc:
                logger.error("[UPDATE COMMAND] Failed rescan of %s: %s", proj_path, exc)

        def _apply_merge():
            self._apply_targeted_refresh(affected_project_paths, all_discovered)
            self._refresh_selected_skill(local_path, rename_path=str(result.path))
            self.app.notify_command_updated(local_path, str(result.path))

            # An update can introduce a new skill reference, so the carry
            # check runs for updates exactly like it does for adds.
            pairs = [(project_root_for_project(result.path), result.path)]
            self._emit_missing_skills_batch(
                self._collect_missing_skills_batch(pairs, body, "UPDATE")
            )

        QTimer.singleShot(0, _apply_merge)

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

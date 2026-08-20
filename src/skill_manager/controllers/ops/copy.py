"""Copy-to-project operations for the OpsController."""

import logging
from pathlib import Path

from PySide6.QtCore import Slot

from skill_manager.controllers.ops._helpers import QTimer, _build_discovery_service, _get_item_attr
from skill_manager.core.analytics import capture_event, capture_exception
from skill_manager.core.diagnostics import (
    CATEGORY_SELECTION_REFRESHED,
    get_diagnostic_logger,
)
from skill_manager.core.persistence import (
    load_temp_registry,
    patch_cache_add,
    save_temp_registry,
)

logger = logging.getLogger(__name__)


class CopyMixin:
    """Copy skills/commands into projects, with optional carry and rescan."""

    @Slot(str)
    def copySelectedSkillsToProject(self, project_path: str, is_temporary: bool = False):
        """Copies selected skills to a project."""
        if not project_path:
            return

        if (
            hasattr(self.app, "ui_controller")
            and getattr(self.app.ui_controller, "currentView", "") == "QuickCopy"
            and hasattr(self.app, "quickCopyModel")
        ):
            model = self.app.quickCopyModel
        else:
            model = getattr(self.app, "skillModel", None)

        selected_paths = model.getSelectedPaths() if model is not None else []
        if not selected_paths and hasattr(self.app, "skillModel"):
            model = self.app.skillModel
            selected_paths = model.getSelectedPaths()
        if not selected_paths and hasattr(self.app, "quickCopyModel"):
            model = self.app.quickCopyModel
            selected_paths = model.getSelectedPaths()

        selected_skills = []
        if model is not None:
            selected_skills = [
                s
                for s in getattr(model, "_all_skills", [])
                if _get_item_attr(s, "local_path") in selected_paths
            ]

        if not selected_skills:
            self.app._set_status("No skills selected to copy")
            return

        self.app._set_status(f"Copying {len(selected_skills)} skills...")

        def run_copy():
            try:
                from skill_manager.core.copier import copy_skill_folders_to_projects

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
                    service = _build_discovery_service(self.app)
                    for detail in result["details"]:
                        if detail["status"] in ("copied", "merged") and detail.get("message"):
                            skill_path = Path(detail["message"])
                            proj_path = Path(detail["project"])
                            try:
                                skill_data = service.discover_single(
                                    skill_path, proj_path, is_package=False
                                )
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

    @Slot(str, str)
    def copyCommandsToProjectWithCarry(self, project_path: str, command_paths_json: str):
        """Copy commands to *project_path*; if skills are missing, prompt carry."""
        import json

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
                from dataclasses import asdict

                missing_dicts = [
                    asdict(m) if hasattr(m, "__dataclass_fields__") else m for m in missing
                ]
                QTimer.singleShot(
                    0,
                    self,
                    lambda: self.commandSkillsCarryPrompt.emit(
                        json.dumps(command_paths), project_path, json.dumps(missing_dicts)
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

    @Slot(str, str, str)
    def confirmCommandSkillsCarry(
        self, project_path: str, command_paths_json: str, confirmed_skills_json: str
    ):
        """Second-phase of copy commands with carry. Copies commands and confirmed missing skills."""
        import json

        from skill_manager.core.copier import copy_commands_with_skill_carry

        command_paths = json.loads(command_paths_json or "[]")
        confirmed_skills = json.loads(confirmed_skills_json or "[]")

        commands = [{"local_path": p, "name": Path(p).stem} for p in command_paths]

        def _run():
            result = copy_commands_with_skill_carry(
                commands,
                project_path,
                self.app._library_model._all_skills,  # type: ignore[attr-defined]
                confirmed_skills=confirmed_skills,
            )
            copied_cmds = result.get("copied", 0)
            copied_skills = result.get("skills_copied", 0)
            failed_skills = result.get("skills_failed", 0)

            msg = f"Copied {copied_cmds} command(s) and {copied_skills} skill(s) to project."
            if failed_skills > 0:
                msg += f" ({failed_skills} skill(s) failed)"

            # ── Targeted rescan of the affected project ──
            all_discovered: list[dict] = []
            if copied_skills > 0:
                from skill_manager.core.quick_copy import project_root_for_project

                proj_root = project_root_for_project(Path(project_path))
                service = _build_discovery_service(self.app)
                try:
                    all_discovered = service.discover_project(proj_root)
                except Exception as exc:
                    logger.error("[CARRY] Failed rescan of %s: %s", proj_root, exc)

            # ── Merge on the main thread ──
            def _apply():
                self.app._set_status(msg)
                if all_discovered:
                    self._apply_targeted_refresh({Path(project_path)}, all_discovered)
                    logger.info(
                        "[CARRY] Targeted refresh: %d skills merged for %s",
                        len(all_discovered),
                        project_path,
                    )

            QTimer.singleShot(0, self, _apply)

        self.app.task_runner.run(_run)

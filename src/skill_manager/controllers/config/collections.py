"""Custom collection CRUD, missing-skill checks/copies, and diagnostics for the ConfigController facade."""

import json
from pathlib import Path

from PySide6.QtCore import Property, Signal, Slot

from skill_manager.core.diagnostics import get_diagnostic_logger
from skill_manager.core.schemas import CollectionConfig


def _is_command_path(p: str) -> bool:
    """True if path points to a command file in .agents/commands/."""
    if not isinstance(p, str):
        return False
    normalized = p.replace("\\", "/")
    return "/.agents/commands/" in normalized


class CollectionsMixin:
    """Custom collections CRUD, carry/copy operations, and diagnostics.

    ``customCollectionsChanged`` is re-declared here for the
    ``@Property(notify=...)`` decorator; the facade class re-declares it
    as its canonical class attribute.
    """

    customCollectionsChanged = Signal()

    @Property(list, notify=customCollectionsChanged)
    def customCollections(self):
        return sorted(self.app._custom_collections.keys())

    def _emit_collections_changed(self):
        """Emit both collection change signals."""
        self.app.customCollectionsChanged.emit()
        self.customCollectionsChanged.emit()

    @Slot(str, list, list)
    def saveCustomCollection(self, name: str, paths: list, projects: list):
        """Saves a collection with paths and projects."""
        if not name:
            return
        if isinstance(paths, list):
            paths = list(paths)
        config = CollectionConfig(paths=paths, projects=projects)
        self.app._custom_collections[name] = config.model_dump()
        self.config.set("custom_collections", self.app._custom_collections)
        self._emit_collections_changed()
        self.app._set_status(f"Collection saved: {name}")
        get_diagnostic_logger().log_event(
            "INFO",
            "collection_saved",
            f"Collection saved: {name}",
            data={
                "name": name,
                "path_count": len(paths),
                "project_count": len(projects),
            },
        )

    @Slot(str)
    def deleteCustomCollection(self, name: str):
        """Deletes a named collection."""
        if name in self.app._custom_collections:
            del self.app._custom_collections[name]
            self.config.set("custom_collections", self.app._custom_collections)
            self._emit_collections_changed()
            self.app._set_status(f"Collection deleted: {name}")

    @Slot(str)
    def applyCollectionSelection(self, name: str):
        """Selects all skills in the active model that belong to the collection."""
        if name in self.app._custom_collections:
            entry = self.app._custom_collections[name]
            paths = entry["paths"] if isinstance(entry, dict) and "paths" in entry else entry
            self.app.skillModel.clearSelection()
            self.app.skillModel.selectByPaths(paths)  # type: ignore[arg-type]
            if hasattr(self.app, "_quick_copy_model"):
                self.app._quick_copy_model.clearSelection()
                self.app._quick_copy_model.selectByPaths(paths)
            self.app._set_status(f"Applied collection: {name}")

    @Slot(str, result=list)
    def getCollectionPaths(self, name: str) -> list:
        """Returns the list of paths for a named collection."""
        entry = self.app._custom_collections.get(name, {})
        if isinstance(entry, dict) and "paths" in entry:
            return entry["paths"]
        return entry if isinstance(entry, list) else []

    @Slot(str, result=list)
    def getCollectionProjects(self, name: str) -> list:
        """Returns the list of projects for a named collection."""
        entry = self.app._custom_collections.get(name, {})
        if isinstance(entry, dict) and "projects" in entry:
            return entry["projects"]
        return []

    @Slot(str, result=str)
    def checkMissingSkills(self, name: str) -> str:
        """Checks if collection skills/commands exist in selected projects. Returns JSON of missing items."""
        entry = self.app._custom_collections.get(name, {})
        if not isinstance(entry, dict) or "paths" not in entry:
            return json.dumps({})

        paths = entry["paths"]
        if not isinstance(paths, list):
            return json.dumps({})

        projects = entry.get("projects", [])
        if not projects:
            return json.dumps({})

        from skill_manager.core.copier import get_commands_dir, get_skills_dir

        missing = {}
        projects_checked = []
        projects_with_missing = []
        total_checked = 0

        for project_label in projects:
            if not isinstance(project_label, str):
                continue
            project_path = self.getProjectPath(project_label)
            if not project_path:
                continue

            skills_dir = get_skills_dir(project_path)
            commands_dir = get_commands_dir(project_path)
            skills_dir_exists = skills_dir.exists() if skills_dir else False
            projects_checked.append(project_label)

            missing_in_project = []
            for item_path in paths:
                if not isinstance(item_path, str):
                    continue

                if _is_command_path(item_path):
                    cmd_filename = Path(item_path).name
                    cmd_target = commands_dir / cmd_filename
                    exists = cmd_target.exists()
                    total_checked += 1

                    get_diagnostic_logger().log_event(
                        "DEBUG",
                        "missing_skills_per_skill",
                        f"{'exists' if exists else 'MISSING'}: {cmd_filename} in {project_label}",
                        data={
                            "collection": name,
                            "label": project_label,
                            "skill_path": item_path,
                            "skill_folder": cmd_filename,
                            "target_full_path": str(cmd_target),
                            "exists": exists,
                            "is_missing": not exists,
                            "is_command": True,
                        },
                    )

                    if not exists:
                        missing_in_project.append(item_path)
                else:
                    skill_folder = Path(item_path).name
                    target_full = skills_dir / skill_folder if skill_folder else None
                    exists = target_full.exists() if target_full else False
                    total_checked += 1

                    get_diagnostic_logger().log_event(
                        "DEBUG",
                        "missing_skills_per_skill",
                        f"{'exists' if exists else 'MISSING'}: {skill_folder} in {project_label}",
                        data={
                            "collection": name,
                            "label": project_label,
                            "skill_path": item_path,
                            "skill_folder": skill_folder,
                            "target_full_path": str(target_full) if target_full else "",
                            "exists": exists,
                            "is_missing": not exists,
                            "is_command": False,
                        },
                    )

                    if skill_folder and not exists:
                        missing_in_project.append(item_path)

            # INFO: per-project summary (low volume, production-visible)
            missing_count = len(missing_in_project)
            missing_skills_preview = (
                [Path(p).name for p in missing_in_project[:5]] if missing_in_project else []
            )
            if missing_count > 5:
                missing_skills_preview.append(f"... and {missing_count - 5} more")

            get_diagnostic_logger().log_event(
                "INFO",
                "missing_skills_check",
                f"Project '{project_label}': {missing_count} missing "
                f"(skills_dir={skills_dir}, exists={skills_dir_exists})",
                data={
                    "collection": name,
                    "label": project_label,
                    "raw_project_path": project_path,
                    "computed_skills_dir": str(skills_dir),
                    "skills_dir_exists": skills_dir_exists,
                    "missing_count": missing_count,
                    "missing_skills": missing_skills_preview,
                },
            )

            if missing_in_project:
                missing[project_label] = missing_in_project
                projects_with_missing.append(project_label)

        # INFO: overall summary
        total_missing = sum(len(v) for v in missing.values()) if isinstance(missing, dict) else 0
        get_diagnostic_logger().log_event(
            "INFO",
            "missing_skills_result",
            f"Collection '{name}': {total_missing} missing across {len(projects_with_missing)}/{len(projects_checked)} projects "
            f"({total_checked} items checked)",
            data={
                "collection": name,
                "total_projects": len(projects_checked),
                "projects_checked": projects_checked,
                "total_missing": total_missing,
                "projects_with_missing": projects_with_missing,
            },
        )

        return json.dumps(missing)

    @Slot(str, list)
    def copyMissingSkills(self, name: str, project_labels: list):
        """Copies missing skills and commands to specified projects."""
        entry = self.app._custom_collections.get(name, {})
        if not isinstance(entry, dict) or "paths" not in entry:
            return

        paths = entry["paths"]

        from skill_manager.core.copier import (
            copy_command_files_to_projects,
            copy_skill_folders_to_projects,
            get_skills_dir,
        )

        skill_paths = [p for p in paths if isinstance(p, str) and not _is_command_path(p)]
        command_paths = [p for p in paths if isinstance(p, str) and _is_command_path(p)]

        for project_label in project_labels:
            project_path = self.getProjectPath(project_label)
            if not project_path:
                continue

            target_dir = get_skills_dir(project_path)

            if skill_paths:
                skills_to_copy = []
                for skill_path in skill_paths:
                    skill_folder = Path(skill_path).name
                    skills_to_copy.append({"local_path": skill_path, "name": skill_folder})

                result = copy_skill_folders_to_projects(skills_to_copy, [project_path])

                get_diagnostic_logger().log_event(
                    "INFO",
                    "missing_skills_copy",
                    f"Copied to '{project_label}': {result['copied']} copied, {result['failed']} failed",
                    data={
                        "collection": name,
                        "label": project_label,
                        "project_path": project_path,
                        "target_dir": str(target_dir),
                        "copied": result["copied"],
                        "merged": result.get("merged", 0),
                        "failed": result["failed"],
                        "skills_copied": len(skills_to_copy),
                    },
                )

            if command_paths:
                commands_to_copy = []
                for cmd_path in command_paths:
                    cmd_name = Path(cmd_path).name
                    commands_to_copy.append({"local_path": cmd_path, "name": cmd_name})

                result = copy_command_files_to_projects(commands_to_copy, [project_path])

                get_diagnostic_logger().log_event(
                    "INFO",
                    "missing_commands_copy",
                    f"Copied commands to '{project_label}': {result['copied']} copied, {result['failed']} failed",
                    data={
                        "collection": name,
                        "label": project_label,
                        "project_path": project_path,
                        "target_dir": str(get_skills_dir(project_path)),
                        "copied": result["copied"],
                        "failed": result["failed"],
                        "commands_copied": len(commands_to_copy),
                    },
                )

    @Slot(str, list)
    def copyCollectionCommandsWithCarry(self, name: str, project_labels: list):
        """Copy command-only collections to projects, carrying missing skills."""
        entry = self.app._custom_collections.get(name, {})
        paths = entry.get("paths", []) if isinstance(entry, dict) else []
        command_paths = [p for p in paths if _is_command_path(p)]
        if not command_paths:
            return

        for project_label in project_labels:
            project_path = self.getProjectPath(project_label)
            if not project_path:
                continue
            self.app.ops_controller.copyCommandsToProjectWithCarry(
                project_path, json.dumps(command_paths)
            )

    @Slot(result=str)
    def getCollectionsDiagnostic(self) -> str:
        """Returns JSON dump of all collections with type-coerced views for diagnostics."""
        result = {}
        for name, entry in self.app._custom_collections.items():
            if isinstance(entry, dict):
                result[name] = {
                    "paths": [str(p) for p in entry.get("paths", []) if p is not None],
                    "projects": [str(p) for p in entry.get("projects", []) if p is not None],
                    "paths_type": type(entry.get("paths")).__name__,
                    "projects_type": type(entry.get("projects")).__name__,
                }
            elif isinstance(entry, list):
                result[name] = {
                    "paths": [str(p) for p in entry if p is not None],
                    "projects": [],
                    "paths_type": "list (legacy)",
                    "projects_type": "N/A",
                }
            else:
                result[name] = {
                    "paths": [],
                    "projects": [],
                    "paths_type": type(entry).__name__,
                    "error": "unexpected entry type",
                }
        return json.dumps(result, indent=2)

    @Slot(result=str)
    def getProjectResolutionTable(self) -> str:
        """Returns JSON list of project label → path resolution for diagnostics."""
        from skill_manager.core.copier import get_skills_dir

        rows = []
        for project_label in self.app._custom_collections.get("projects", []):
            if not isinstance(project_label, str):
                continue
            resolved = self.getProjectPath(project_label)
            skills_dir = get_skills_dir(resolved) if resolved else None
            rows.append(
                {
                    "label": project_label,
                    "path": resolved,
                    "resolved_skills_dir": str(skills_dir) if skills_dir else "",
                    "skills_dir_exists": skills_dir.exists() if skills_dir else False,
                    "resolvable": bool(resolved),
                }
            )

        # Also include all registered project labels
        all_labels = []
        for p in self.app._projects:
            label = self.getProjectLabel(p)
            skills_dir = get_skills_dir(p)
            all_labels.append(
                {
                    "label": label,
                    "path": p,
                    "resolved_skills_dir": str(skills_dir),
                    "skills_dir_exists": skills_dir.exists() if skills_dir else False,
                    "resolvable": True,
                }
            )

        return json.dumps(
            {
                "registered_projects": all_labels,
                "collection_project_labels": rows,
            },
            indent=2,
        )

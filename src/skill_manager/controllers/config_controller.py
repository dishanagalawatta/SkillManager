"""
Purpose: Manages skill sources, projects, and configuration state.
Usage: Accessed via AppController.config_mgr
"""

import logging
from pathlib import Path
from typing import Any

from PySide6.QtCore import Property, Signal, Slot

from skill_manager.controllers.base import BaseController
from skill_manager.core.analytics import capture_event, capture_exception
from skill_manager.core.diagnostics import get_diagnostic_logger
from skill_manager.core.schemas import AppConfig, CollectionConfig

logger = logging.getLogger(__name__)


def _is_command_path(p: str) -> bool:
    """True if path points to a command file in .agents/commands/."""
    if not isinstance(p, str):
        return False
    normalized = p.replace("\\", "/")
    return "/.agents/commands/" in normalized


class ConfigController(BaseController):
    """Controller for project configuration and sources.

    Uses Pydantic (AppConfig) for strict validation of configuration updates.
    """

    shortcutsChanged = Signal()
    isRecordingShortcutChanged = Signal()
    updateProjectsChanged = Signal()
    clientFormatsChanged = Signal()
    customCollectionsChanged = Signal()
    scrollSpeedMultiplierChanged = Signal()
    showMenuIconsChanged = Signal()
    compactMenuChanged = Signal()
    skillPackageAutoUpdateChanged = Signal()
    skillPackageAutoUpdateModeChanged = Signal()
    autoMinimizeOnScreenshotChanged = Signal()
    autoMinimizeOnQuickCopyChanged = Signal()
    temporaryScreenshotsChanged = Signal()

    # Cached property values (invalidated via _invalidate_project_cache)
    _cached_update_projects: list[dict] | None = None
    _cached_project_labels: list[str] | None = None

    def _set_config_value(self, key: str, value: Any, signal: Signal = None):
        """Unified setter that validates against AppConfig before persisting."""
        try:
            # Create a partial config to validate this specific key
            validated = AppConfig.model_validate({key: value})
            final_value = getattr(validated, key)

            if self.config.get(key) != final_value:
                self.config.set(key, final_value)
                if signal:
                    signal.emit()
                return True
        except Exception as e:
            logger.warning("[CONFIG] Validation failed for %s=%s: %s", key, value, e)
        return False

    @Property(float, notify=scrollSpeedMultiplierChanged)
    def scrollSpeedMultiplier(self):
        return self.config.get("scroll_speed_multiplier", 1.0)

    @scrollSpeedMultiplier.setter
    def scrollSpeedMultiplier(self, value):
        self._set_config_value("scroll_speed_multiplier", value, self.scrollSpeedMultiplierChanged)

    @Property(bool, notify=showMenuIconsChanged)
    def showMenuIcons(self):
        return self.config.get("show_menu_icons", True)

    @showMenuIcons.setter
    def showMenuIcons(self, value):
        self._set_config_value("show_menu_icons", value, self.showMenuIconsChanged)

    @Property(bool, notify=compactMenuChanged)
    def compactMenu(self):
        return self.config.get("compact_menu", False)

    @compactMenu.setter
    def compactMenu(self, value):
        self._set_config_value("compact_menu", value, self.compactMenuChanged)

    @Property(bool, notify=skillPackageAutoUpdateChanged)
    def skillPackageAutoUpdate(self):
        return self.config.get("skill_package_auto_update", True)

    @skillPackageAutoUpdate.setter
    def skillPackageAutoUpdate(self, value):
        self._set_config_value(
            "skill_package_auto_update", value, self.skillPackageAutoUpdateChanged
        )

    @Property(str, notify=skillPackageAutoUpdateModeChanged)
    def skillPackageAutoUpdateMode(self):
        return self.config.get("skill_package_auto_update_mode", "prompt")

    @skillPackageAutoUpdateMode.setter
    def skillPackageAutoUpdateMode(self, value):
        self._set_config_value(
            "skill_package_auto_update_mode", value, self.skillPackageAutoUpdateModeChanged
        )

    @Property(bool, notify=autoMinimizeOnScreenshotChanged)
    def autoMinimizeOnScreenshot(self):
        return self.config.get("auto_minimize_on_screenshot", False)

    @autoMinimizeOnScreenshot.setter
    def autoMinimizeOnScreenshot(self, value):
        self._set_config_value(
            "auto_minimize_on_screenshot", value, self.autoMinimizeOnScreenshotChanged
        )

    @Property(bool, notify=autoMinimizeOnQuickCopyChanged)
    def autoMinimizeOnQuickCopy(self):
        return self.config.get("auto_minimize_on_quick_copy", False)

    @autoMinimizeOnQuickCopy.setter
    def autoMinimizeOnQuickCopy(self, value):
        self._set_config_value(
            "auto_minimize_on_quick_copy", value, self.autoMinimizeOnQuickCopyChanged
        )

    @Property(bool, notify=temporaryScreenshotsChanged)
    def temporaryScreenshots(self):
        return self.config.get("temporary_screenshots", False)

    @temporaryScreenshots.setter
    def temporaryScreenshots(self, value):
        self._set_config_value("temporary_screenshots", value, self.temporaryScreenshotsChanged)

    @Property(dict, notify=updateProjectsChanged)
    def project_aliases(self):
        return self.app._project_aliases

    @Property(str, notify=shortcutsChanged)
    def shortcutSearch(self):
        return self.get_shortcut("search")

    @Property(str, notify=shortcutsChanged)
    def shortcutCopy(self):
        return self.get_shortcut("copy")

    @Property(str, notify=shortcutsChanged)
    def shortcutArchive(self):
        return self.get_shortcut("archive")

    @Property(str, notify=shortcutsChanged)
    def shortcutDelete(self):
        return self.get_shortcut("delete")

    @Property(str, notify=shortcutsChanged)
    def shortcutRefresh(self):
        return self.get_shortcut("refresh")

    @Property(str, notify=shortcutsChanged)
    def shortcutExpandAll(self):
        return self.get_shortcut("expand_all")

    @Property(str, notify=shortcutsChanged)
    def shortcutCollapseAll(self):
        return self.get_shortcut("collapse_all")

    @Property(str, notify=shortcutsChanged)
    def shortcutTopOfList(self):
        return self.get_shortcut("top_of_list")

    @Property(str, notify=shortcutsChanged)
    def shortcutClearSelection(self):
        return self.get_shortcut("clear_selection")

    @Property(str, notify=shortcutsChanged)
    def shortcutThemeToggle(self):
        return self.get_shortcut("theme_toggle")

    @Property(str, notify=shortcutsChanged)
    def shortcutQuickCopyView(self):
        return self.get_shortcut("quick_copy_view")

    @Property(str, notify=shortcutsChanged)
    def shortcutLibraryView(self):
        return self.get_shortcut("library_view")

    @Property(str, notify=shortcutsChanged)
    def shortcutUpdatesView(self):
        return self.get_shortcut("updates_view")

    @Property(str, notify=shortcutsChanged)
    def shortcutSettingsView(self):
        return self.get_shortcut("settings_view")

    @Property(str, notify=shortcutsChanged)
    def shortcutScreenshot(self):
        return self.get_shortcut("screenshot")

    @Property(bool, notify=isRecordingShortcutChanged)
    def isRecordingShortcut(self):
        return self.app._is_recording_shortcut

    @isRecordingShortcut.setter
    def isRecordingShortcut(self, value):
        if self.app._is_recording_shortcut != value:
            self.app._is_recording_shortcut = value
            self.isRecordingShortcutChanged.emit()

    def _normalize_path(self, raw_url: str) -> str:
        """Helper to convert file URLs or raw strings to absolute local paths."""
        if not raw_url:
            return ""
        path_str = (
            raw_url.replace("file:///", "").replace("/", "\\")
            if raw_url.startswith("file://")
            else raw_url
        )
        try:
            # Expand ~ and make absolute
            return str(Path(path_str).expanduser().resolve())
        except Exception:
            return path_str

    @Slot(str)
    def addSource(self, url: str):
        """Adds a local skill source directory."""
        resolved_path = self._normalize_path(url)
        if not resolved_path:
            return

        try:
            if resolved_path not in self.app._sources:
                self.app._sources.append(resolved_path)
                self.config.set("sources", self.app._sources)
                self.app.sourcesChanged.emit()
                self.app._set_status(f"Added source: {resolved_path}")
                capture_event("skill_package_added", {"source_type": "local"})
        except Exception as e:
            self.app._set_status(f"Failed to add source: {e}")
            capture_exception(e)

    @Slot(str)
    def removeSource(self, path: str):
        """Removes a local skill source directory."""
        if path in self.app._sources:
            self.app._sources.remove(path)
            self.config.set("sources", self.app._sources)
            self.app.sourcesChanged.emit()
            self.app._set_status(f"Removed source: {path}")
            capture_event("skill_package_removed", {"source_type": "local"})

    @Slot(int)
    def removeSourceByIndex(self, index: int):
        """Removes a local skill source directory by its index in the list."""
        if 0 <= index < len(self.app._sources):
            self.removeSource(self.app._sources[index])

    @Slot(str)
    def addProject(self, url: str):
        """Adds a project directory."""
        if not url or not str(url).strip():
            return

        from skill_manager.core.copier import normalize_project_skills_path

        # First try specialized normalization for .agents/skills
        path_str = (
            url.replace("file:///", "").replace("/", "\\") if url.startswith("file://") else url
        )
        resolved_path, error = normalize_project_skills_path(path_str)
        if error:
            # Fallback to standard absolute path
            resolved_path = self._normalize_path(url)

        if resolved_path and resolved_path not in self.app._projects:
            self.app._projects.append(resolved_path)
            self.config.set("projects", self.app._projects)
            self._emit_projects_changed()
            self.app._set_status(f"Added project: {resolved_path}")
            capture_event("project_target_added", {"target_count": len(self.app._projects)})

            get_diagnostic_logger().log_event(
                "INFO",
                "project_added",
                f"Project added: {resolved_path}",
                data={
                    "raw_input": url,
                    "normalized": resolved_path,
                    "error": error,
                },
            )

    @Slot(str)
    def removeProject(self, path: str):
        """Removes a project directory."""
        if path in self.app._projects:
            self.app._projects.remove(path)
            if path in self.app._syncing_projects:
                self.app._syncing_projects.remove(path)
            if path in self.app._project_aliases:
                del self.app._project_aliases[path]
                self.config.set("project_aliases", self.app._project_aliases)
            self.config.set("projects", self.app._projects)
            self._emit_projects_changed()
            self.app._set_status(f"Removed project: {path}")

    @Slot(int)
    def removeUpdateProject(self, index: int):
        """Removes a project by its index in the updates view."""
        if 0 <= index < len(self.app._projects):
            self.removeProject(self.app._projects[index])

    @Property(list, notify=clientFormatsChanged)
    def clientFormats(self):
        return ["Plain Text", "Gemini CLI", "Antigravity", "Codex"]

    @Property(list, notify=customCollectionsChanged)
    def customCollections(self):
        return sorted(self.app._custom_collections.keys())

    @Slot(dict)
    def save_cache(self, data: dict):
        """Saves discovered skills to cache."""
        from skill_manager.core.persistence import save_cache

        save_cache(data)

    @Slot(result=dict)
    def load_cache(self):
        """Loads discovered skills from cache."""
        from skill_manager.core.persistence import load_cache

        return load_cache()

    @Slot(str, result=str)
    def getProjectPath(self, label: str) -> str:
        """Returns the project path for a given label."""
        for p in self.app._projects:
            if self.getProjectLabel(p) == label:
                return p
        return ""

    @Slot(str, result=str)
    def getProjectLabel(self, path: str) -> str:
        """Returns the human-readable label for a project path."""
        if not path:
            return ""
        norm_path = path.replace("\\", "/")
        label = self.app._project_aliases.get(path) or self.app._project_aliases.get(norm_path)
        if not label:
            p = Path(path)
            if norm_path.endswith("/.agents/skills"):
                label = p.parent.parent.name
            elif p.name.lower() == "skills" and len(p.parts) > 2:
                parent = p.parent.name
                label = p.parent.parent.name if parent == ".agents" else parent
            else:
                label = p.name
        return label

    @Property(list, notify=updateProjectsChanged)
    def updateProjects(self):
        """Returns a list of project info with skill counts and sync status for the UI."""
        if self._cached_update_projects is not None:
            return self._cached_update_projects
        results = []

        for p in self.app._projects:
            count = 0
            try:
                resolved_path = Path(p)
                if resolved_path.name.lower() not in ("skills", ".agents"):
                    potential = resolved_path / ".agents" / "skills"
                    if potential.exists() and potential.is_dir():
                        resolved_path = potential
                    else:
                        resolved_path = resolved_path / ".agents" / "skills"

                if resolved_path.exists():
                    count = len([d for d in resolved_path.iterdir() if d.is_dir()])
            except Exception:
                pass
            results.append(
                {
                    "name": self.getProjectLabel(p),
                    "path": p,
                    "skill_count": count,
                    "is_updating": p in self.app._syncing_projects,
                }
            )
        self._cached_update_projects = results
        return results

    @Property(list, notify=updateProjectsChanged)
    def projectLabels(self):
        """Returns a list of human-readable labels for all projects."""
        if self._cached_project_labels is not None:
            return self._cached_project_labels
        self._cached_project_labels = [self.getProjectLabel(p) for p in self.app._projects]
        return self._cached_project_labels

    def _invalidate_project_cache(self):
        """Invalidate cached project data so properties recompute on next access."""
        self._cached_update_projects = None
        self._cached_project_labels = None

    def _emit_projects_changed(self):
        """Emit both project signals and invalidate cache."""
        self.app.projectsChanged.emit()
        self._invalidate_project_cache()
        self.updateProjectsChanged.emit()

    def _emit_collections_changed(self):
        """Emit both collection change signals."""
        self.app.customCollectionsChanged.emit()
        self.customCollectionsChanged.emit()

    @Slot(str, str)
    def setProjectAlias(self, path: str, alias: str):
        """Sets a custom alias for a project."""
        if not path:
            return
        if not alias:
            if path in self.app._project_aliases:
                del self.app._project_aliases[path]
        else:
            self.app._project_aliases[path] = alias

        self.config.set("project_aliases", self.app._project_aliases)
        self._emit_projects_changed()

        new_label = self.getProjectLabel(path)
        for model in (self.app._library_model, self.app._quick_copy_model):
            model._begin_batch()
            try:
                all_skills = getattr(model, "_all_skills", None)
                if isinstance(all_skills, list):
                    for skill in all_skills:
                        sp = (
                            skill.get("project_path")
                            if isinstance(skill, dict)
                            else getattr(skill, "project_path", None)
                        )
                        if sp and str(sp) == str(path):
                            if isinstance(skill, dict):
                                skill["project_label"] = new_label
                            else:
                                skill.project_label = new_label
            finally:
                model._end_batch()

        self.app._set_status(f"Renamed project to: {alias or 'Default'}")

    @Slot(str, str, result=str)
    def verifyGitPackage(self, url: str, token: str = None) -> str:
        """Verifies a git repository and returns its latest tag."""
        if not url:
            return ""
        from skill_manager.core.skill_packages import get_git_tag

        self.app._set_status(f"Verifying repository: {url}")
        tag = get_git_tag(url, is_remote=True, token=token)
        if tag:
            self.app._set_status(f"Repository verified. Latest version: {tag}")
        else:
            self.app._set_status(f"Verification failed for: {url}")
        return tag or ""

    def get_shortcut(self, key: str) -> str:
        """Gets a configured shortcut sequence."""
        return self.config.get("shortcuts", {}).get(key, "")

    @Slot(str, str)
    def setShortcut(self, action: str, sequence: str):
        """Sets a shortcut sequence for an action."""
        shortcuts = self.config.get("shortcuts", {})
        if action in shortcuts and shortcuts[action] != sequence:
            shortcuts[action] = sequence
            self.config.set("shortcuts", shortcuts)
            self.shortcutsChanged.emit()
            self.app._set_status(f"Shortcut for {action} set to: {sequence}")

    @Slot()
    def resetShortcuts(self):
        """Resets all shortcuts to defaults."""
        from skill_manager.core.config import DEFAULT_SHORTCUTS

        self.config.set("shortcuts", DEFAULT_SHORTCUTS.copy())
        self.shortcutsChanged.emit()
        self.app._set_status("All shortcuts reset to defaults")

    @Slot(str)
    def setStatus(self, msg: str):
        """Sets the application status message from QML."""
        self.app._set_status(msg)

    @Slot(str, list, list)
    def saveCustomCollection(self, name: str, paths: list, projects: list):
        """Saves a collection with paths and projects."""
        if not name:
            return
        # Commands live in .agents/commands/ — they're per-project, not installable across projects.
        # Exclude them so checkMissingSkills doesn't report false positives.
        if isinstance(paths, list):
            paths = [p for p in paths if not _is_command_path(p)]
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
            self.app.skillModel.selectByPaths(paths)
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
        """Checks if collection skills exist in selected projects. Returns JSON of missing skills."""
        import json

        entry = self.app._custom_collections.get(name, {})
        if not isinstance(entry, dict) or "paths" not in entry:
            return json.dumps({})

        paths = entry["paths"]
        if not isinstance(paths, list):
            return json.dumps({})

        projects = entry.get("projects", [])
        if not projects:
            return json.dumps({})

        from skill_manager.core.copier import get_skills_dir

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
            skills_dir_exists = skills_dir.exists() if skills_dir else False
            projects_checked.append(project_label)

            missing_in_project = []
            for skill_path in paths:
                if not isinstance(skill_path, str):
                    continue
                if _is_command_path(skill_path):
                    continue  # Commands are not installable across projects
                skill_folder = Path(skill_path).name
                target_full = skills_dir / skill_folder if skill_folder else None
                exists = target_full.exists() if target_full else False
                total_checked += 1

                # DEBUG: per-skill trace (high volume, dev only)
                get_diagnostic_logger().log_event(
                    "DEBUG",
                    "missing_skills_per_skill",
                    f"{'exists' if exists else 'MISSING'}: {skill_folder} in {project_label}",
                    data={
                        "collection": name,
                        "label": project_label,
                        "skill_path": skill_path,
                        "skill_folder": skill_folder,
                        "target_full_path": str(target_full) if target_full else "",
                        "exists": exists,
                        "is_missing": not exists,
                    },
                )

                if skill_folder and not exists:
                    missing_in_project.append(skill_path)

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
            f"({total_checked} skills checked)",
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
        """Copies missing skills to specified projects."""
        entry = self.app._custom_collections.get(name, {})
        if not isinstance(entry, dict) or "paths" not in entry:
            return

        paths = entry["paths"]

        from skill_manager.core.copier import copy_skill_folders_to_projects, get_skills_dir

        for project_label in project_labels:
            project_path = self.getProjectPath(project_label)
            if not project_path:
                continue

            target_dir = get_skills_dir(project_path)
            skills_to_copy = []
            for skill_path in paths:
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
                    "merged": result["merged"],
                    "failed": result["failed"],
                    "skills_copied": len(skills_to_copy),
                },
            )

    @Slot(result=str)
    def getCollectionsDiagnostic(self) -> str:
        """Returns JSON dump of all collections with type-coerced views for diagnostics."""
        import json

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
        import json

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

    # --- Diagnostic Slots (Agent-Accessible) ---

    @Slot(result=str)
    def getDiagnosticLogPath(self) -> str:
        """Returns the path to the diagnostic log file."""
        return get_diagnostic_logger().get_log_path()

    @Slot(int, result=str)
    def getRecentDiagnosticEvents(self, count: int = 100) -> str:
        """Returns JSON array of the most recent diagnostic events."""
        import json

        events = get_diagnostic_logger().get_recent_events(count)
        return json.dumps(events, ensure_ascii=False, default=str)

    @Slot(str, result=str)
    def exportDiagnosticBundle(self, output_dir: str = "") -> str:
        """Export diagnostic bundle (logs + manifest) as a zip file.

        Args:
            output_dir: Directory to write the zip. Defaults to log dir.

        Returns:
            Path to the created zip, or empty string on failure.
        """
        dir_path = output_dir if output_dir else None
        return get_diagnostic_logger().export_bundle(dir_path)

    @Slot()
    def clearDiagnosticLogs(self):
        """Clear all diagnostic log files and ring buffer."""
        get_diagnostic_logger().clear_logs()
        self.app._set_status("Diagnostic logs cleared")

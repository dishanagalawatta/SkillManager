"""
Purpose: Manages skill sources, projects, and configuration state.
Usage: Accessed via AppController.config_mgr
"""

import logging
from pathlib import Path
from typing import Any

from PySide6.QtCore import Property, Signal, SignalInstance, Slot

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
    skillPackageAutoUpdateModeChanged = Signal()
    autoMinimizeOnScreenshotChanged = Signal()
    autoMinimizeOnQuickCopyChanged = Signal()
    temporaryScreenshotsChanged = Signal()
    diagnosticLoggingChanged = Signal()

    # Cached property values (invalidated via _invalidate_project_cache)
    _cached_update_projects: list[dict] | None = None
    _cached_project_labels: list[str] | None = None

    def _set_config_value(self, key: str, value: Any, signal: SignalInstance | None = None):
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
    def scrollSpeedMultiplier(self):  # type: ignore[reportRedeclaration]
        return self.config.get("scroll_speed_multiplier", 1.0)

    @scrollSpeedMultiplier.setter  # type: ignore[func-attr]
    def scrollSpeedMultiplier(self, value):
        self._set_config_value("scroll_speed_multiplier", value, self.scrollSpeedMultiplierChanged)

    @Property(str, notify=skillPackageAutoUpdateModeChanged)
    def skillPackageAutoUpdateMode(self):  # type: ignore[reportRedeclaration]
        return self.config.get("skill_package_auto_update_mode", "prompt")

    @skillPackageAutoUpdateMode.setter  # type: ignore[func-attr]
    def skillPackageAutoUpdateMode(self, value):
        self._set_config_value(
            "skill_package_auto_update_mode", value, self.skillPackageAutoUpdateModeChanged
        )

    @Property(bool, notify=autoMinimizeOnScreenshotChanged)
    def autoMinimizeOnScreenshot(self):  # type: ignore[reportRedeclaration]
        return self.config.get("auto_minimize_on_screenshot", False)

    @autoMinimizeOnScreenshot.setter  # type: ignore[func-attr]
    def autoMinimizeOnScreenshot(self, value):
        self._set_config_value(
            "auto_minimize_on_screenshot", value, self.autoMinimizeOnScreenshotChanged
        )

    @Property(bool, notify=autoMinimizeOnQuickCopyChanged)
    def autoMinimizeOnQuickCopy(self):  # type: ignore[reportRedeclaration]
        return self.config.get("auto_minimize_on_quick_copy", False)

    @autoMinimizeOnQuickCopy.setter  # type: ignore[func-attr]
    def autoMinimizeOnQuickCopy(self, value):
        self._set_config_value(
            "auto_minimize_on_quick_copy", value, self.autoMinimizeOnQuickCopyChanged
        )

    @Property(bool, notify=temporaryScreenshotsChanged)
    def temporaryScreenshots(self):  # type: ignore[reportRedeclaration]
        return self.config.get("temporary_screenshots", False)

    @temporaryScreenshots.setter  # type: ignore[func-attr]
    def temporaryScreenshots(self, value):
        self._set_config_value("temporary_screenshots", value, self.temporaryScreenshotsChanged)

    @Property(bool, notify=diagnosticLoggingChanged)
    def diagnosticLogging(self):  # type: ignore[reportRedeclaration]
        return self.config.get("diagnostic_logging", False)

    @diagnosticLogging.setter  # type: ignore[func-attr]
    def diagnosticLogging(self, value):
        if self._set_config_value("diagnostic_logging", value, self.diagnosticLoggingChanged):
            # Apply immediately at runtime — no restart required
            get_diagnostic_logger().set_enabled(value)

    @Property(dict, notify=updateProjectsChanged)
    def project_aliases(self):
        return self.app._project_aliases

    @Property(str, notify=shortcutsChanged)
    def shortcutSearch(self):
        return self.get_shortcut("search")

    @Property(str, notify=shortcutsChanged)
    def shortcutSelectAll(self):
        return self.get_shortcut("select_all")

    @Property(str, notify=shortcutsChanged)
    def shortcutClearSelection(self):
        return self.get_shortcut("clear_selection")

    @Property(str, notify=shortcutsChanged)
    def shortcutCopy(self):
        return self.get_shortcut("copy")

    @Property(str, notify=shortcutsChanged)
    def shortcutRefresh(self):
        return self.get_shortcut("refresh")

    @Property(str, notify=shortcutsChanged)
    def shortcutArchive(self):
        return self.get_shortcut("archive")

    @Property(str, notify=shortcutsChanged)
    def shortcutDelete(self):
        return self.get_shortcut("delete")

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
    def shortcutThemeToggle(self):
        return self.get_shortcut("theme_toggle")

    @Property(str, notify=shortcutsChanged)
    def shortcutScreenshot(self):
        return self.get_shortcut("screenshot")

    # --- Per-shortcut enabled state (read-only properties) ---

    @Property(bool, notify=shortcutsChanged)
    def shortcutSearchEnabled(self):
        return self.isShortcutEnabled("search")

    @Property(bool, notify=shortcutsChanged)
    def shortcutSelectAllEnabled(self):
        return self.isShortcutEnabled("select_all")

    @Property(bool, notify=shortcutsChanged)
    def shortcutClearSelectionEnabled(self):
        return self.isShortcutEnabled("clear_selection")

    @Property(bool, notify=shortcutsChanged)
    def shortcutCopyEnabled(self):
        return self.isShortcutEnabled("copy")

    @Property(bool, notify=shortcutsChanged)
    def shortcutRefreshEnabled(self):
        return self.isShortcutEnabled("refresh")

    @Property(bool, notify=shortcutsChanged)
    def shortcutArchiveEnabled(self):
        return self.isShortcutEnabled("archive")

    @Property(bool, notify=shortcutsChanged)
    def shortcutDeleteEnabled(self):
        return self.isShortcutEnabled("delete")

    @Property(bool, notify=shortcutsChanged)
    def shortcutExpandAllEnabled(self):
        return self.isShortcutEnabled("expand_all")

    @Property(bool, notify=shortcutsChanged)
    def shortcutCollapseAllEnabled(self):
        return self.isShortcutEnabled("collapse_all")

    @Property(bool, notify=shortcutsChanged)
    def shortcutTopOfListEnabled(self):
        return self.isShortcutEnabled("top_of_list")

    @Property(bool, notify=shortcutsChanged)
    def shortcutQuickCopyViewEnabled(self):
        return self.isShortcutEnabled("quick_copy_view")

    @Property(bool, notify=shortcutsChanged)
    def shortcutLibraryViewEnabled(self):
        return self.isShortcutEnabled("library_view")

    @Property(bool, notify=shortcutsChanged)
    def shortcutUpdatesViewEnabled(self):
        return self.isShortcutEnabled("updates_view")

    @Property(bool, notify=shortcutsChanged)
    def shortcutSettingsViewEnabled(self):
        return self.isShortcutEnabled("settings_view")

    @Property(bool, notify=shortcutsChanged)
    def shortcutThemeToggleEnabled(self):
        return self.isShortcutEnabled("theme_toggle")

    @Property(bool, notify=shortcutsChanged)
    def shortcutScreenshotEnabled(self):
        return self.isShortcutEnabled("screenshot")

    @Property(bool, notify=isRecordingShortcutChanged)
    def isRecordingShortcut(self):  # type: ignore[reportRedeclaration]
        return self.app._is_recording_shortcut

    @isRecordingShortcut.setter  # type: ignore[func-attr]
    def isRecordingShortcut(self, value):
        if self.app._is_recording_shortcut != value:
            self.app._is_recording_shortcut = value
            self.isRecordingShortcutChanged.emit()

    def normalize_path(self, raw_url: str) -> str:
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
        resolved_path = self.normalize_path(url)
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
            resolved_path = self.normalize_path(url)

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

    @Slot(int, int)
    def reorderProjects(self, from_index: int, to_index: int):
        """Moves a project from one position to another in the list."""
        projects = self.app._projects
        if (
            not projects
            or from_index == to_index
            or from_index < 0
            or from_index >= len(projects)
            or to_index < 0
            or to_index >= len(projects)
        ):
            return

        project = projects.pop(from_index)
        projects.insert(to_index, project)
        self.config.set("projects", projects)
        self._emit_projects_changed()

    @Slot(int)
    def removeUpdateProject(self, index: int):
        """Removes a project by its index in the updates view."""
        if 0 <= index < len(self.app._projects):
            self.removeProject(self.app._projects[index])

    @Property(list, notify=clientFormatsChanged)
    def topBarClients(self):  # type: ignore[reportRedeclaration]
        return self.config.get(
            "top_bar_clients", ["Plain Text", "Gemini CLI", "Antigravity", "Codex"]
        )

    @topBarClients.setter  # type: ignore[func-attr]
    def topBarClients(self, value):
        self._set_config_value("top_bar_clients", value, self.clientFormatsChanged)

    @Property(list, notify=clientFormatsChanged)
    def availableClientFormats(self):
        return ["Plain Text", "Gemini CLI", "Antigravity", "Codex", "OpenCode"]

    @Property(list, notify=clientFormatsChanged)
    def clientFormats(self):
        return self.topBarClients

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
    def verifyGitPackage(self, url: str, token: str | None = None) -> str:
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
        """Resets all shortcuts to defaults (enabled with default sequences)."""
        from skill_manager.core.config import DEFAULT_DISABLED_SHORTCUTS, DEFAULT_SHORTCUTS

        self.config.set("shortcuts", DEFAULT_SHORTCUTS.copy())
        self.config.set("disabled_shortcuts", DEFAULT_DISABLED_SHORTCUTS.copy())
        self.clearAllCollectionShortcuts()
        self.shortcutsChanged.emit()
        self.app._set_status("All shortcuts reset to defaults")

    @Slot(str, result=bool)
    def isShortcutEnabled(self, action: str) -> bool:
        """Returns True if the given shortcut action is enabled."""
        disabled: list[str] = self.config.get("disabled_shortcuts", [])
        return action not in disabled

    @Slot(str, bool)
    def setShortcutEnabled(self, action: str, enabled: bool) -> None:
        """Enable or disable a shortcut action. Emits shortcutsChanged."""
        disabled: list[str] = list(self.config.get("disabled_shortcuts", []))
        was_disabled = action in disabled
        if enabled and was_disabled:
            disabled.remove(action)
            self.config.set("disabled_shortcuts", disabled)
            self.shortcutsChanged.emit()
            self.app._set_status(f"Shortcut '{action}' enabled")
        elif not enabled and not was_disabled:
            disabled.append(action)
            self.config.set("disabled_shortcuts", disabled)
            self.shortcutsChanged.emit()
            self.app._set_status(f"Shortcut '{action}' disabled")

    @Slot(str)
    def setStatus(self, msg: str):
        """Sets the application status message from QML."""
        self.app._set_status(msg)

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

    # --- Per-collection shortcuts ---

    def _claim_sequence(self, seq: str, owner_name: str) -> list[str]:
        """Forcibly clears `seq` from any built-in action and any other collection.

        Returns a human-readable list of entities that were freed so the
        caller can include them in a status message.
        """
        if not seq:
            return []

        freed: list[str] = []

        # 1. Free from built-in shortcuts
        shortcuts = self.config.get("shortcuts", {})
        for action, bound_seq in list(shortcuts.items()):
            if bound_seq == seq:
                shortcuts[action] = ""
                freed.append(action)

        if freed:
            self.config.set("shortcuts", shortcuts)

        # 2. Free from other collections
        for name, entry in self.app._custom_collections.items():
            if name == owner_name:
                continue
            if isinstance(entry, dict) and entry.get("shortcut") == seq:
                entry["shortcut"] = ""
                freed.append(name)

        if freed:
            self.config.set("custom_collections", self.app._custom_collections)
            self.shortcutsChanged.emit()
            self.customCollectionsChanged.emit()

        return freed

    @Slot(str, str)
    def setCollectionShortcut(self, name: str, seq: str):
        """Sets a shortcut sequence for a collection with auto-claim semantics."""
        entry = self.app._custom_collections.get(name)
        if entry is None:
            return
        if not isinstance(entry, dict):
            return
        old = entry.get("shortcut", "")
        if old == seq:
            return

        freed = self._claim_sequence(seq, name)

        entry["shortcut"] = seq
        self.config.set("custom_collections", self.app._custom_collections)
        self.shortcutsChanged.emit()
        self.customCollectionsChanged.emit()

        msg = (
            f"Collection '{name}' bound to {seq}"
            if seq
            else f"Collection '{name}' shortcut cleared"
        )
        if freed:
            msg += f" (reassigned from: {', '.join(freed)})"
        self.app._set_status(msg)

    @Slot(str, bool)
    def setCollectionShortcutEnabled(self, name: str, enabled: bool):
        """Enable or disable the shortcut for a collection without losing the sequence."""
        entry = self.app._custom_collections.get(name)
        if entry is None or not isinstance(entry, dict):
            return
        old = entry.get("shortcut_enabled", True)
        if old == enabled:
            return
        entry["shortcut_enabled"] = enabled
        self.config.set("custom_collections", self.app._custom_collections)
        self.customCollectionsChanged.emit()

    @Slot(str, result=str)
    def getCollectionShortcut(self, name: str) -> str:
        """Returns the shortcut sequence for a named collection."""
        entry = self.app._custom_collections.get(name, {})
        if isinstance(entry, dict):
            return entry.get("shortcut", "")
        return ""

    @Slot(str, result=bool)
    def getCollectionShortcutEnabled(self, name: str) -> bool:
        """Returns whether the shortcut is enabled for a named collection."""
        entry = self.app._custom_collections.get(name, {})
        if isinstance(entry, dict):
            return entry.get("shortcut_enabled", True)
        return True

    def clearAllCollectionShortcuts(self):
        """Clears all collection shortcuts. Called by resetShortcuts."""
        changed = False
        for _name, entry in self.app._custom_collections.items():
            if isinstance(entry, dict) and (
                entry.get("shortcut") or not entry.get("shortcut_enabled", True)
            ):
                entry["shortcut"] = ""
                entry["shortcut_enabled"] = True
                changed = True
        if changed:
            self.config.set("custom_collections", self.app._custom_collections)
            self.customCollectionsChanged.emit()

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

    @Slot(result=str)
    def getDiagnosticCounts(self) -> str:
        """Returns JSON dict of diagnostic event counts by level."""
        import json

        return json.dumps(get_diagnostic_logger().get_diagnostic_counts())

    @Slot(result=str)
    def getDiagnosticHealthStatus(self) -> str:
        """Returns 'green', 'yellow', or 'red' health status."""
        return get_diagnostic_logger().get_health_status()

    @Slot(int, result=str)
    def getRecentEventsHuman(self, count: int = 20) -> str:
        """Returns JSON array of recent events in human-readable format."""
        import json

        events = get_diagnostic_logger().get_recent_events_human(count)
        return json.dumps(events, ensure_ascii=False)

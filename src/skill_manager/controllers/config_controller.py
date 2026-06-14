"""
Purpose: Manages skill sources, projects, and configuration state.
Usage: Accessed via AppController.config_mgr
"""

import os

from PySide6.QtCore import Property, Signal, Slot

from skill_manager.controllers.base import BaseController
from skill_manager.core.analytics import capture_event, capture_exception


class ConfigController(BaseController):
    """Controller for project configuration and sources."""

    shortcutsChanged = Signal()
    isRecordingShortcutChanged = Signal()
    updateProjectsChanged = Signal()
    clientFormatsChanged = Signal()
    customCollectionsChanged = Signal()
    scrollSpeedMultiplierChanged = Signal()
    showMenuIconsChanged = Signal()
    compactMenuChanged = Signal()
    autoCheckUpdatesChanged = Signal()
    autoDownloadUpdatesChanged = Signal()
    updateCheckIntervalHoursChanged = Signal()
    skillPackageAutoUpdateChanged = Signal()
    skillPackageAutoUpdateModeChanged = Signal()
    autoMinimizeOnScreenshotChanged = Signal()
    temporaryScreenshotsChanged = Signal()

    # Cached property values (invalidated via _invalidate_project_cache)
    _cached_update_projects: list[dict] | None = None
    _cached_project_labels: list[str] | None = None

    @Property(float, notify=scrollSpeedMultiplierChanged)
    def scrollSpeedMultiplier(self):
        return self.config.get("scroll_speed_multiplier", 1.0)

    @scrollSpeedMultiplier.setter
    def scrollSpeedMultiplier(self, value):
        if self.scrollSpeedMultiplier != value:
            self.config.set("scroll_speed_multiplier", float(value))
            self.scrollSpeedMultiplierChanged.emit()

    @Property(bool, notify=showMenuIconsChanged)
    def showMenuIcons(self):
        return self.config.get("show_menu_icons", True)

    @showMenuIcons.setter
    def showMenuIcons(self, value):
        if self.showMenuIcons != value:
            self.config.set("show_menu_icons", bool(value))
            self.showMenuIconsChanged.emit()

    @Property(bool, notify=compactMenuChanged)
    def compactMenu(self):
        return self.config.get("compact_menu", False)

    @compactMenu.setter
    def compactMenu(self, value):
        if self.compactMenu != value:
            self.config.set("compact_menu", bool(value))
            self.compactMenuChanged.emit()

    @Property(bool, notify=autoCheckUpdatesChanged)
    def autoCheckUpdates(self):
        return self.config.get("auto_check_updates", True)

    @autoCheckUpdates.setter
    def autoCheckUpdates(self, value):
        if self.autoCheckUpdates != value:
            self.config.set("auto_check_updates", bool(value))
            self.autoCheckUpdatesChanged.emit()

    @Property(bool, notify=autoDownloadUpdatesChanged)
    def autoDownloadUpdates(self):
        return self.config.get("auto_download_updates", False)

    @autoDownloadUpdates.setter
    def autoDownloadUpdates(self, value):
        if self.autoDownloadUpdates != value:
            self.config.set("auto_download_updates", bool(value))
            self.autoDownloadUpdatesChanged.emit()

    @Property(int, notify=updateCheckIntervalHoursChanged)
    def updateCheckIntervalHours(self):
        return self.config.get("update_check_interval_hours", 24)

    @updateCheckIntervalHours.setter
    def updateCheckIntervalHours(self, value):
        if self.updateCheckIntervalHours != value:
            self.config.set("update_check_interval_hours", int(value))
            self.updateCheckIntervalHoursChanged.emit()

    @Property(bool, notify=skillPackageAutoUpdateChanged)
    def skillPackageAutoUpdate(self):
        return self.config.get("skill_package_auto_update", True)

    @skillPackageAutoUpdate.setter
    def skillPackageAutoUpdate(self, value):
        if self.skillPackageAutoUpdate != value:
            self.config.set("skill_package_auto_update", bool(value))
            self.skillPackageAutoUpdateChanged.emit()

    @Property(str, notify=skillPackageAutoUpdateModeChanged)
    def skillPackageAutoUpdateMode(self):
        return self.config.get("skill_package_auto_update_mode", "prompt")

    @skillPackageAutoUpdateMode.setter
    def skillPackageAutoUpdateMode(self, value):
        if self.skillPackageAutoUpdateMode != value:
            self.config.set("skill_package_auto_update_mode", str(value))
            self.skillPackageAutoUpdateModeChanged.emit()

    @Property(bool, notify=autoMinimizeOnScreenshotChanged)
    def autoMinimizeOnScreenshot(self):
        return self.config.get("auto_minimize_on_screenshot", False)

    @autoMinimizeOnScreenshot.setter
    def autoMinimizeOnScreenshot(self, value):
        if self.autoMinimizeOnScreenshot != value:
            self.config.set("auto_minimize_on_screenshot", bool(value))
            self.autoMinimizeOnScreenshotChanged.emit()

    @Property(bool, notify=temporaryScreenshotsChanged)
    def temporaryScreenshots(self):
        return self.config.get("temporary_screenshots", False)

    @temporaryScreenshots.setter
    def temporaryScreenshots(self, value):
        if self.temporaryScreenshots != value:
            self.config.set("temporary_screenshots", bool(value))
            self.temporaryScreenshotsChanged.emit()

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

    @Slot(str)
    def addSource(self, url: str):
        """Adds a local skill source directory."""
        path = url.replace("file:///", "").replace("/", "\\") if url.startswith("file://") else url
        raw_path = str(path or "").strip()
        if not raw_path:
            return

        try:
            resolved_path = os.path.abspath(os.path.expanduser(raw_path))
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
        path = url.replace("file:///", "").replace("/", "\\") if url.startswith("file://") else url
        from skill_manager.core.copier import normalize_project_skills_path

        resolved_path, error = normalize_project_skills_path(path)
        if error:
            resolved_path = os.path.abspath(os.path.expanduser(path))
        if resolved_path not in self.app._projects:
            self.app._projects.append(resolved_path)
            self.config.set("projects", self.app._projects)
            self._emit_projects_changed()
            self.app._set_status(f"Added project: {resolved_path}")
            capture_event("project_target_added", {"target_count": len(self.app._projects)})

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
            if norm_path.endswith("/.agents/skills"):
                label = os.path.basename(os.path.dirname(os.path.dirname(path)))
            elif os.path.basename(path).lower() == "skills" and len(norm_path.split("/")) > 2:
                parent = norm_path.split("/")[-2]
                label = norm_path.split("/")[-3] if parent == ".agents" else parent
            else:
                label = os.path.basename(path)
        return label

    @Property(list, notify=updateProjectsChanged)
    def updateProjects(self):
        """Returns a list of project info with skill counts and sync status for the UI."""
        if self._cached_update_projects is not None:
            return self._cached_update_projects
        results = []
        from pathlib import Path

        for p in self.app._projects:
            count = 0
            try:
                resolved_path = Path(p)
                if resolved_path.name.lower() not in ("skills", ".agents"):
                    found = False
                    potential = resolved_path / ".agents" / "skills"
                    if potential.exists() and potential.is_dir():
                        resolved_path = potential
                        found = True
                    if not found:
                        resolved_path = resolved_path / ".agents" / "skills"
                scan_path = str(resolved_path)
                if os.path.exists(scan_path):
                    count = len(
                        [
                            d
                            for d in os.listdir(scan_path)
                            if os.path.isdir(os.path.join(scan_path, d))
                        ]
                    )
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
                        sp = skill.get("project_path") if isinstance(skill, dict) else getattr(skill, "project_path", None)
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

    @Slot(str, list)
    def saveCustomCollection(self, name: str, paths: list):
        """Saves a list of skill paths as a named collection."""
        if not name:
            return
        self.app._custom_collections[name] = paths
        self.config.set("custom_collections", self.app._custom_collections)
        self._emit_collections_changed()
        self.app._set_status(f"Collection saved: {name}")

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
            paths = self.app._custom_collections[name]
            self.app.skillModel.clearSelection()
            self.app.skillModel.selectByPaths(paths)
            self.app._set_status(f"Applied collection: {name}")

    @Slot(str, result=list)
    def getCollectionPaths(self, name: str) -> list:
        """Returns the list of paths for a named collection."""
        return self.app._custom_collections.get(name, [])

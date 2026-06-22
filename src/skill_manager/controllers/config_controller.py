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
            self.app.projectsChanged.emit()
            self.updateProjectsChanged.emit()
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
            self.app.projectsChanged.emit()
            self.updateProjectsChanged.emit()
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
        return results

    @Property(list, notify=updateProjectsChanged)
    def projectLabels(self):
        """Returns a list of human-readable labels for all projects."""
        return [self.getProjectLabel(p) for p in self.app._projects]

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
        self.app.projectsChanged.emit()
        self.updateProjectsChanged.emit()
        self.app.refreshSkills()
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
        self.app.customCollectionsChanged.emit()
        self.customCollectionsChanged.emit()
        self.app._set_status(f"Collection saved: {name}")

    @Slot(str)
    def deleteCustomCollection(self, name: str):
        """Deletes a named collection."""
        if name in self.app._custom_collections:
            del self.app._custom_collections[name]
            self.config.set("custom_collections", self.app._custom_collections)
            self.app.customCollectionsChanged.emit()
            self.customCollectionsChanged.emit()
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

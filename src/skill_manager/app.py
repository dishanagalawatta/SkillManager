"""
Purpose: Main entry point for Skill Manager (PySide6 version).
Usage: python run.py
"""

import ctypes
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Property, QObject, Qt, QTimer, Signal, Slot
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtQml import QQmlApplicationEngine, qmlRegisterSingletonInstance
from PySide6.QtQuickControls2 import QQuickStyle

# Try to import pywinstyles for Mica/Acrylic
try:
    import pywinstyles

    HAS_PYWINSTYLES = True
except ImportError:
    HAS_PYWINSTYLES = False

import contextlib

from skill_manager.controllers.config_controller import ConfigController
from skill_manager.controllers.ops_controller import OpsController
from skill_manager.controllers.ui_controller import UIController
from skill_manager.controllers.update_controller import UpdateController
from skill_manager.core.analytics import (
    capture_event,
    capture_exception,
    shutdown as posthog_shutdown,
)
from skill_manager.core.categories import get_category_emoji
from skill_manager.core.commands import create_custom_command_file
from skill_manager.core.config import (
    ConfigManager,
)
from skill_manager.core.discovery import DiscoveryService
from skill_manager.core.models import SkillModel
from skill_manager.core.parsing import (
    build_skill_search_text,
    categorize_skill,
    parse_skill_md,
)
from skill_manager.core.persistence import (
    load_archive,
    load_starred,
    save_archive,
    save_starred,
)
from skill_manager.core.quick_copy import (
    CLIENT_FORMATS,
    format_project_skill_reference,
)
from skill_manager.core.resources import (
    logo_asset_for_client,
    qml_components_dir,
    resource_path as resolve_resource_path,
)
from skill_manager.utils.task_runner import BackgroundTaskRunner


class AppController(QObject):
    skillModelChanged = Signal()
    selectedSkillChanged = Signal()
    isLoadingChanged = Signal()
    statusMessageChanged = Signal()
    sourcesChanged = Signal()
    projectsChanged = Signal()
    discoveredProjectsChanged = Signal()
    clientFormatChanged = Signal()
    categoriesChanged = Signal()
    clientFormatsChanged = Signal()
    customCollectionsChanged = Signal()
    currentViewChanged = Signal()
    windowWidthChanged = Signal()
    windowHeightChanged = Signal()
    windowXChanged = Signal()
    windowYChanged = Signal()
    darkModeChanged = Signal()
    startupViewChanged = Signal()
    rememberFiltersChanged = Signal()
    defaultProjectFilterChanged = Signal()
    reducedMotionChanged = Signal()
    compactListRowsChanged = Signal()
    statsChanged = Signal()
    updateResultsChanged = Signal()
    updatePackagesChanged = Signal()
    isPackageOnlyChanged = Signal()
    shortcutsChanged = Signal()
    isRecordingShortcutChanged = Signal()

    def __init__(self, skip_initial_load=False):
        super().__init__()
        # 1. Core Models and Configuration
        self._config = ConfigManager()
        self.task_runner = BackgroundTaskRunner()
        self._library_model = SkillModel(config=self._config)
        self._quick_copy_model = SkillModel(config=self._config)

        # 2. Basic Attribute Initialization
        self._selected_skill = {}
        self._is_loading = False
        self._status_message = ""
        self._discovered_projects = []
        self._categories = []
        self._clipboard = QGuiApplication.clipboard()
        self._is_recording_shortcut = False

        self._client_format = self._config.get("client_format", "Antigravity")
        self._sources = self._config.get("sources", [])
        self._projects = self._config.get("projects", [])
        self._project_aliases = self._config.get("project_aliases", {})
        self._update_packages = self._config.get("skills", [])
        for s in self._update_packages:
            s["is_updating"] = False
            if "current_version" not in s:
                s["current_version"] = ""
            if "latest_version" not in s:
                s["latest_version"] = ""
        self._custom_collections = self._config.get("custom_collections", {})

        # Updates and Syncing State
        self._stats_up_to_date = 0
        self._stats_outdated = 0
        self._stats_missing = 0
        self._update_results = []
        self._syncing_projects = []

        # 3. Initialize Sub-Controllers
        self.ui = UIController(self)
        self.config_mgr = ConfigController(self)
        self.ops = OpsController(self)
        self.updates = UpdateController(self)

        # 4. Lifecycle Hooks
        self.ops.cleanup_temp_copies()  # Crash recovery
        app_inst = QGuiApplication.instance()
        if app_inst:
            app_inst.aboutToQuit.connect(self.ops.cleanup_temp_copies)

        # 4. Initial Model Configuration
        self._library_model.showCommands = False
        self._library_model.isPackageOnly = True
        self._library_model.showStarred = True

        self._quick_copy_model.showCommands = True
        self._quick_copy_model.isPackageOnly = False
        self._quick_copy_model.showStarred = True
        self._quick_copy_model.filterByClient = False


        # 5. Load Persistence and Start Discovery
        self._archive_paths = load_archive()
        self._starred_paths = load_starred()

        # In tests, we often want to skip the initial background discovery
        skip_initial = skip_initial_load or os.environ.get("SKILL_MANAGER_SKIP_INITIAL_LOAD") == "1"

        if not skip_initial:
            QTimer.singleShot(100, self.load_initial_data)

    # --- Properties ---

    @Property(QObject, notify=skillModelChanged)
    def skillModel(self):
        if self.ui._current_view == "Library":
            return self._library_model
        return self._quick_copy_model

    @Property(QObject, notify=skillModelChanged)
    def libraryModel(self):
        return self._library_model

    @Property(QObject, notify=skillModelChanged)
    def quickCopyModel(self):
        return self._quick_copy_model

    @Property(dict, notify=selectedSkillChanged)
    def selectedSkill(self):
        return self._selected_skill or {}

    @Property(bool, notify=isLoadingChanged)
    def isLoading(self):
        return self._is_loading

    @Property(str, notify=statusMessageChanged)
    def statusMessage(self):
        return self._status_message

    @Property(list, notify=sourcesChanged)
    def sources(self):
        return self._sources

    @Property(list, notify=projectsChanged)
    def projects(self):
        return self._projects

    @Property(list, notify=projectsChanged)
    def syncingProjects(self):
        return self._syncing_projects

    @Property(list, notify=projectsChanged)
    def updateProjects(self):
        results = []
        for p in self._projects:
            count = 0
            try:
                # Dynamic Resolution for accurate skill count in UI
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
                    "is_updating": p in self._syncing_projects,
                }
            )
        return results

    @Property(int, notify=statsChanged)
    def statsUpToDate(self):
        return self._stats_up_to_date

    @Property(int, notify=statsChanged)
    def statsOutdated(self):
        return self._stats_outdated

    @Property(int, notify=statsChanged)
    def statsMissing(self):
        return self._stats_missing

    @Property(list, notify=updateResultsChanged)
    def updateResults(self):
        return self._update_results

    @Property(str, notify=clientFormatChanged)
    def clientFormat(self):
        return self._client_format

    @Property(list, notify=categoriesChanged)
    def categories(self):
        return self._categories

    @Property(list, notify=discoveredProjectsChanged)
    def discoveredProjects(self):
        return self._discovered_projects

    @Property(list, notify=projectsChanged)
    def projectLabels(self):
        return [self.getProjectLabel(p) for p in self._projects]

    @Property(list, notify=clientFormatsChanged)
    def clientFormats(self):
        order = ["Plain Text", "Gemini CLI", "Antigravity", "Codex"]
        return [fmt for fmt in order if fmt in CLIENT_FORMATS]

    @Property(list, notify=customCollectionsChanged)
    def customCollections(self):
        return sorted(self._custom_collections.keys())

    @Property(list, notify=updatePackagesChanged)
    def updatePackages(self):
        return self._update_packages

    @Property(str, notify=clientFormatChanged)
    def logoSource(self):
        return self.ui.get_asset_uri(logo_asset_for_client(self._client_format))

    @Slot(str, result=str)
    def getLogoSource(self, fmt):
        return self.ui.get_asset_uri(logo_asset_for_client(fmt))

    @Slot(str, result=str)
    def getCategoryEmoji(self, category_name: str) -> str:
        """Returns the standard emoji for a given category name.
        This is the primary visual identifier for the categorization system.
        """
        return get_category_emoji(category_name)

    @Slot(str, result=str)
    def getAssetUri(self, path):
        return self.ui.get_asset_uri(path)

    @Property(dict, notify=projectsChanged)
    def projectAliases(self):
        return self._project_aliases

    @Property(str, notify=currentViewChanged)
    def currentView(self):
        return self.ui._current_view

    @currentView.setter
    def currentView(self, value):
        normalized = self._normalize_view_name(value)
        if self.ui._current_view != normalized:
            self.ui._current_view = normalized
            self.ui.save_ui_state()
            self.currentViewChanged.emit()
            self.skillModelChanged.emit()

    @Property(int, notify=windowWidthChanged)
    def windowWidth(self):
        return self.ui._window_width

    @windowWidth.setter
    def windowWidth(self, value):
        if self.ui._window_width != value and value >= 1050:
            self.ui._window_width = value
            self.ui.trigger_save()
            self.windowWidthChanged.emit()

    @Property(int, notify=windowHeightChanged)
    def windowHeight(self):
        return self.ui._window_height

    @windowHeight.setter
    def windowHeight(self, value):
        if self.ui._window_height != value and value >= 650:
            self.ui._window_height = value
            self.ui.trigger_save()
            self.windowHeightChanged.emit()

    @Property(int, notify=windowXChanged)
    def windowX(self):
        return self.ui._window_x

    @windowX.setter
    def windowX(self, value):
        if self.ui._window_x != value:
            self.ui._window_x = value
            self.ui.trigger_save()
            self.windowXChanged.emit()

    @Property(int, notify=windowYChanged)
    def windowY(self):
        return self.ui._window_y

    @windowY.setter
    def windowY(self, value):
        if self.ui._window_y != value:
            self.ui._window_y = value
            self.ui.trigger_save()
            self.windowYChanged.emit()

    @Property(bool, notify=darkModeChanged)
    def darkMode(self):
        return self.ui._dark_mode

    @darkMode.setter
    def darkMode(self, value):
        if self.ui._dark_mode != value:
            self.ui._dark_mode = value
            self.ui.trigger_save()
            self.darkModeChanged.emit()

    @Property(str, notify=startupViewChanged)
    def startupView(self):
        return self.ui._startup_view

    @startupView.setter
    def startupView(self, value):
        normalized = self._normalize_view_name(value)
        if self.ui._startup_view != normalized:
            self.ui._startup_view = normalized
            self.ui.trigger_save()
            self.startupViewChanged.emit()

    @Property(bool, notify=rememberFiltersChanged)
    def rememberFilters(self):
        return self.ui._remember_filters

    @rememberFilters.setter
    def rememberFilters(self, value):
        if self.ui._remember_filters != value:
            self.ui._remember_filters = value
            if not value:
                self.clearViewFilters()
            self.ui.trigger_save()
            self.rememberFiltersChanged.emit()

    @Property(str, notify=defaultProjectFilterChanged)
    def defaultProjectFilter(self):
        return self.ui._default_project_filter

    @defaultProjectFilter.setter
    def defaultProjectFilter(self, value):
        normalized = value if value in {"last", "all"} else "last"
        if self.ui._default_project_filter != normalized:
            self.ui._default_project_filter = normalized
            if normalized == "all":
                self.setViewFilterForView("QuickCopy", "project", "")
            self.ui.trigger_save()
            self.defaultProjectFilterChanged.emit()

    @Property(bool, notify=reducedMotionChanged)
    def reducedMotion(self):
        return self.ui._reduced_motion

    @reducedMotion.setter
    def reducedMotion(self, value):
        if self.ui._reduced_motion != value:
            self.ui._reduced_motion = value
            self.ui.trigger_save()
            self.reducedMotionChanged.emit()

    @Property(bool, notify=compactListRowsChanged)
    def compactListRows(self):
        return self.ui._compact_list_rows
    @compactListRows.setter
    def compactListRows(self, value):
        if self.ui._compact_list_rows != value:
            self.ui._compact_list_rows = value
            self.ui.trigger_save()
            self.compactListRowsChanged.emit()

    @Property(bool, notify=isRecordingShortcutChanged)
    def isRecordingShortcut(self):
        return self._is_recording_shortcut

    @isRecordingShortcut.setter
    def isRecordingShortcut(self, value):
        if self._is_recording_shortcut != value:
            self._is_recording_shortcut = value
            self.isRecordingShortcutChanged.emit()

    # --- Shortcut Properties ---

    def _get_shortcut(self, key):
        return self._config.get("shortcuts", {}).get(key, "")

    @Property(str, notify=shortcutsChanged)
    def shortcutSearch(self): return self._get_shortcut("search")
    @Property(str, notify=shortcutsChanged)
    def shortcutCopy(self): return self._get_shortcut("copy")
    @Property(str, notify=shortcutsChanged)
    def shortcutArchive(self): return self._get_shortcut("archive")
    @Property(str, notify=shortcutsChanged)
    def shortcutDelete(self): return self._get_shortcut("delete")
    @Property(str, notify=shortcutsChanged)
    def shortcutRefresh(self): return self._get_shortcut("refresh")
    @Property(str, notify=shortcutsChanged)
    def shortcutExpandAll(self): return self._get_shortcut("expand_all")
    @Property(str, notify=shortcutsChanged)
    def shortcutCollapseAll(self): return self._get_shortcut("collapse_all")
    @Property(str, notify=shortcutsChanged)
    def shortcutTopOfList(self): return self._get_shortcut("top_of_list")
    @Property(str, notify=shortcutsChanged)
    def shortcutClearSelection(self): return self._get_shortcut("clear_selection")
    @Property(str, notify=shortcutsChanged)
    def shortcutThemeToggle(self): return self._get_shortcut("theme_toggle")
    @Property(str, notify=shortcutsChanged)
    def shortcutQuickCopyView(self): return self._get_shortcut("quick_copy_view")
    @Property(str, notify=shortcutsChanged)
    def shortcutLibraryView(self): return self._get_shortcut("library_view")
    @Property(str, notify=shortcutsChanged)
    def shortcutUpdatesView(self): return self._get_shortcut("updates_view")
    @Property(str, notify=shortcutsChanged)
    def shortcutSettingsView(self): return self._get_shortcut("settings_view")

    @Slot(str, str)
    def setShortcut(self, action, sequence):
        shortcuts = self._config.get("shortcuts", {})
        if action in shortcuts and shortcuts[action] != sequence:
            shortcuts[action] = sequence
            self._config.set("shortcuts", shortcuts)
            self.shortcutsChanged.emit()
            self._set_status(f"Shortcut for {action} set to: {sequence}")

    @Slot()
    def resetShortcuts(self):
        from skill_manager.core.config import DEFAULT_SHORTCUTS
        self._config.set("shortcuts", DEFAULT_SHORTCUTS.copy())
        self.shortcutsChanged.emit()
        self._set_status("All shortcuts reset to defaults")

    # --- Slots ---

    @Property(Qt.CheckState, notify=isPackageOnlyChanged)
    def isPackageOnly(self):
        return self._library_model.isPackageOnly

    @isPackageOnly.setter
    def isPackageOnly(self, value):
        self._library_model.isPackageOnly = value
        self._quick_copy_model.isPackageOnly = value
        self.isPackageOnlyChanged.emit()

    # --- Methods / Slots ---

    def _normalize_view_name(self, value):
        view = str(value or "").replace(" ", "").replace("-", "")
        view_map = {
            "quickcopy": "QuickCopy",
            "library": "Library",
            "updates": "Updates",
            "settings": "Settings",
        }
        return view_map.get(view.lower(), "Library")

    def load_initial_data(self):
        """Initial scan of skills on application startup in a background thread."""
        self._is_loading = True
        self.isLoadingChanged.emit()
        self._set_status("Scanning skills...")

        import os

        discovery_sources = list(self._sources)
        for src in self._update_packages:
            pkg_path = src.get("package_path") or src.get("local_path")
            if pkg_path and os.path.exists(pkg_path) and pkg_path not in discovery_sources:
                discovery_sources.append(pkg_path)

        service = DiscoveryService(
            sources=discovery_sources,
            projects=self._projects,
            archive_paths=self._archive_paths,
            starred_paths=self._starred_paths,
            project_aliases=self._project_aliases,
        )

        def run_discovery():
            try:

                def cache_callback(cached_data):
                    print(
                        f"[CACHE] Loading {len(cached_data.get('skills', []))} skills from cache..."
                    )
                    QTimer.singleShot(
                        0,
                        self,
                        lambda: self._finalize_loading(
                            cached_data.get("skills", []),
                            cached_data.get("projects", []),
                            cached_data.get("categories", []),
                            cached_data.get("project_labels", []),
                            f"Loaded {len(cached_data.get('skills', []))} skills from cache (Refreshing...)",
                            is_final=False,
                        ),
                    )

                result = service.discover_all(cache_callback=cache_callback)

                # Signal completion back to main thread
                QTimer.singleShot(
                    0,
                    self,
                    lambda: self._finalize_loading(
                        result["skills"],
                        result["projects"],
                        result["categories"],
                        result["project_labels"],
                        result["status"],
                        is_final=True,
                    ),
                )
            except Exception as e:
                error_msg = f"Error scanning skills: {e}"
                import traceback

                traceback.print_exc()
                QTimer.singleShot(0, self, lambda: self._handle_loading_error(error_msg))

        self.task_runner.run(run_discovery)

    def _finalize_loading(
        self, all_skills, _projects_state, cats, proj_labels, status, is_final=True
    ):
        """Updates model and UI state on the main thread after discovery completes."""
        del proj_labels

        if self._categories != cats:
            self._categories = cats
            self.categoriesChanged.emit()

        # Update both models with the shared skill list
        self._library_model.setSkills(all_skills)
        self._quick_copy_model.setSkills(all_skills)

        # Ensure client filters are set
        self._library_model.clientFilter = self._client_format
        self._quick_copy_model.clientFilter = self._client_format

        if self.ui._default_project_filter == "all":
            self._library_model.projectFilter = ""
            self._quick_copy_model.projectFilter = ""

        self._set_status(status)

        if is_final:
            self._is_loading = False
            self.isLoadingChanged.emit()

    def _handle_loading_error(self, error_msg):
        """Handles discovery errors on the main thread."""
        self._set_status(error_msg)
        self._is_loading = False
        self.isLoadingChanged.emit()

    @Slot(int)
    def selectSkill(self, index):
        if index == -1:
            self._selected_skill = {}
        else:
            self._selected_skill = self.skillModel.get_skill_at(index)
        self.selectedSkillChanged.emit()

    @Slot(str)
    def copySkillToClipboard(self, path):
        # Find skill by path in all_skills
        skill = next((s for s in self.skillModel._all_skills if s.get("local_path") == path), None)
        if skill:
            self.copySkillReference(skill)
        else:
            self.copyTextToClipboard(path)

    @Slot()
    def copyCurrentSelectionOrFocusedSkill(self):
        if self.skillModel.selectedCount > 0:
            self.copySelectedSkillsToClipboard()
            return
        if self._selected_skill and self._selected_skill.get("local_path"):
            self.copySkillReference(self._selected_skill)
            return
        first_skill = self.skillModel.get_skill_at(0)
        if first_skill:
            self.copySkillReference(first_skill)
            return
        self._set_status("No skill available to copy")

    @Slot()
    def copySelectedSkillsToClipboard(self):
        paths = self.skillModel.getSelectedPaths()
        if not paths:
            self._set_status("No skills selected")
            return

        references = []
        for path in paths:
            skill = next(
                (s for s in self.skillModel._all_skills if s.get("local_path") == path), None
            )
            if skill:
                references.append(format_project_skill_reference(skill, self._client_format))
            else:
                references.append(path)

        content = " ".join(references)
        self._clipboard.setText(content)
        self._set_status(f"Copied {len(references)} skills to clipboard")

    @Slot(str)
    def copyTextToClipboard(self, content):
        self._clipboard.setText(str(content))
        self._set_status("Copied to clipboard")

    @Slot(dict, str)
    def copySkillReference(self, skill, arg=""):
        # Use core formatter
        ref = format_project_skill_reference(skill, self._client_format)
        if arg:
            ref += f"({arg})"
        self._clipboard.setText(ref)
        self._set_status(f"Copied reference: {ref}")

    @Slot()
    def toggleCurrentSkillArchive(self):
        self.ops.toggle_archive()

    @Slot()
    def toggleCurrentSkillStarred(self):
        self.ops.toggle_starred()

    @Slot()
    def selectAllVisibleSkills(self):
        self.skillModel.selectAll()
        self._set_status(f"Selected {self.skillModel.selectedCount} visible skills")

    @Slot()
    def clearVisibleSelection(self):
        self.skillModel.clearSelection()
        self._set_status("Selection cleared")

    @Slot()
    def toggleAllVisibleCategories(self):
        self.skillModel.toggleAll()
        state = "expanded" if self.skillModel.isAllExpanded else "collapsed"
        self._set_status(f"All categories {state}")

    @Slot(str)
    def deleteSkill(self, path):
        if not path:
            return
        skill = next((s for s in self.skillModel._all_skills if s.get("local_path") == path), None)
        if skill:
            self.ops.delete_skills([skill])

    @Slot()
    def deleteSelectedSkills(self):
        selected_paths = self.skillModel.getSelectedPaths()
        selected = [s for s in self.skillModel._all_skills if s.get("local_path") in selected_paths]
        if selected:
            self.ops.delete_skills(selected)
        else:
            self._set_status("No skills selected for deletion")

    @Slot()
    def archiveSelectedSkills(self):
        selected_paths = self.skillModel.getSelectedPaths()
        if not selected_paths:
            self._set_status("No skills selected for archiving")
            return

        count = 0
        for path in selected_paths:
            if path and path not in self._archive_paths:
                self._archive_paths.append(path)
                count += 1

        if count > 0:
            self._save_archive()
            self.skillModel.clearSelection()
            self._set_status(f"{count} skills archived")
            self.load_initial_data()  # Refresh models
        else:
            self._set_status("Selected skills are already archived")

    @Slot(str)
    def copySelectedSkillsToProject(self, project_path):
        self.ops.copy_selected_to_project(project_path)

    @Slot(str)
    def copySelectedSkillsToProjectTemporarily(self, project_path):
        self.ops.copy_selected_to_project(project_path, is_temporary=True)

    @Slot(str)
    def launchSkill(self, path):
        self.ui.launch_skill(path)

    @Slot(str)
    def openPath(self, path):
        self.ui.open_path(path)

    @Slot(str)
    def addSource(self, url):
        self.config_mgr.add_source(url)

    @Slot(str)
    def removeSource(self, path):
        self.config_mgr.remove_source(path)

    @Slot(int)
    def removeSourceByIndex(self, index):
        if 0 <= index < len(self._sources):
            self.config_mgr.remove_source(self._sources[index])

    @Slot(str)
    def addProject(self, url):
        self.config_mgr.add_project(url)

    @Slot(str)
    def removeProject(self, path):
        self.config_mgr.remove_project(path)

    @Slot(str, result=str)
    def getProjectLabel(self, path):
        return self.config_mgr.get_project_label(path)

    @Slot(int)
    def removeUpdateProject(self, index):
        if 0 <= index < len(self._projects):
            self.config_mgr.remove_project(self._projects[index])

    @Slot(str, str)
    def setProjectAlias(self, path, alias):
        self.config_mgr.set_project_alias(path, alias)

    @Slot(str, str, result=str)
    def verifyGitPackage(self, url, token=None):
        """Verify a git package and return the latest version tag/hash."""
        return self.config_mgr.verify_git_package(url, token)

    @Slot(str)
    def addUpdatePackage(self, package_name):
        if not package_name:
            return
        # Basic NPM-style source
        new_source = {
            "name": package_name,
            "source_type": "npm",
            "package_name": package_name,
            "last_updated": "Never",
            "is_updating": False,
        }
        self._update_packages.append(new_source)
        self._config.set("skills", self._update_packages)
        self.updatePackagesChanged.emit()
        self._set_status(f"Added update package: {package_name}")

    @Slot(dict)
    def addSkillPackage(self, data):
        if not data:
            return
        from skill_manager.core.skill_packages import (
            check_skill_package_versions,
            normalize_skill_package_config,
        )

        new_source = normalize_skill_package_config(data)
        new_source["is_updating"] = False
        new_source["last_updated"] = "Never"

        # Immediate version check
        new_source = check_skill_package_versions(new_source)

        self._update_packages.append(new_source)
        self._config.set("skills", self._update_packages)
        self.updatePackagesChanged.emit()
        self._set_status(f"Added skill package: {new_source.get('name')}")
        capture_event(
            "skill_package_added", {"source_type": new_source.get("source_type", "unknown")}
        )

    @Slot(int, dict)
    def updateUpdatePackage(self, index, data):
        if 0 <= index < len(self._update_packages):
            # Preserve internal state
            is_updating = self._update_packages[index].get("is_updating", False)

            # Use core logic to normalize and detect fields
            from skill_manager.core.skill_packages import (
                check_skill_package_versions,
                normalize_skill_package_config,
            )

            updated_source = normalize_skill_package_config(data)
            updated_source["is_updating"] = is_updating

            # Refresh versions
            updated_source = check_skill_package_versions(updated_source)

            self._update_packages[index] = updated_source
            self._config.set("skills", self._update_packages)
            self.updatePackagesChanged.emit()
            self._set_status(f"Updated skill package: {updated_source.get('name')}")

    @Slot(int)
    def removeUpdatePackage(self, index):
        if 0 <= index < len(self._update_packages):
            source = self._update_packages.pop(index)
            self._config.set("skills", self._update_packages)
            self.updatePackagesChanged.emit()
            self._set_status(f"Removed update package: {source.get('name')}")
            capture_event(
                "skill_package_removed", {"source_type": source.get("source_type", "unknown")}
            )

    @Slot(int)
    def clearPackageJustFinished(self, index):
        if 0 <= index < len(self._update_packages):
            self._update_packages[index]["just_finished"] = False
            # Force refresh
            self._update_packages[index] = dict(self._update_packages[index])
            self.updatePackagesChanged.emit()

    @Slot(int)
    def runPackageUpdate(self, index):
        if 0 <= index < len(self._update_packages):
            source = self._update_packages[index]
            source["is_updating"] = True
            source["just_finished"] = False
            self.updatePackagesChanged.emit()
            self._set_status(f"Updating {source.get('name')}...")

            def run():
                from pathlib import Path

                from skill_manager.core.skill_packages import run_skill_package_update

                try:
                    # If package_path is empty and we have master sources, use the first one as default destination
                    pkg_path = source.get("package_path") or source.get("local_path")
                    if not pkg_path and self._sources:
                        # Safety: ensure we don't accidentally relocate to the project root if it's listed as a source
                        potential_path = self._sources[0]
                        if Path(potential_path).resolve() == Path.cwd().resolve():
                            # If the source is the project root, we should target .agents/skills subfolder
                            source["package_path"] = str(
                                Path(potential_path) / ".agents" / "skills"
                            )
                        else:
                            source["package_path"] = potential_path
                    else:
                        source["package_path"] = pkg_path

                    # Pass a callback that also updates the status bar
                    def log_callback(msg):
                        QTimer.singleShot(0, self, lambda: self._set_status(msg))

                    updated_source = run_skill_package_update(source, log_callback)
                    source.update(updated_source)

                    # Update timestamp
                    source["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                    print(f"[UPDATE] Success: {source.get('name')}")
                    capture_event(
                        "skill_package_updated",
                        {"source_type": source.get("source_type", "unknown"), "success": True},
                    )
                except Exception as e:
                    print(f"[UPDATE] Failed: {source.get('name')} - Error: {e}")
                    import traceback

                    traceback.print_exc()
                    error_msg = str(e)
                    capture_event(
                        "skill_package_updated",
                        {"source_type": source.get("source_type", "unknown"), "success": False},
                    )
                    capture_exception(e)
                    err_msg = f"Update failed for {source.get('name')}: {error_msg}"
                    QTimer.singleShot(0, self, lambda msg=err_msg: self._set_status(msg))
                finally:

                    def finalize_ui():
                        try:
                            source["is_updating"] = False
                            source["just_finished"] = True

                            # Replace dict in list to force QML to see the change
                            self._update_packages[index] = dict(source)
                            self.updatePackagesChanged.emit()

                            self._set_status(f"Update finished for {source.get('name')}")
                            # Refresh skill library from all sources (background thread)
                            self.load_initial_data()

                            # Save state
                            self._config.set("skills", self._update_packages)
                        except Exception as e:
                            print(f"[ERROR] Error in finalize_ui for {source.get('name')}: {e}")
                            import traceback

                            traceback.print_exc()
                            self._set_status(f"Error finishing update: {e}")

                    QTimer.singleShot(0, self, finalize_ui)

            self.task_runner.run(run)

    def _save_archive(self):
        save_archive(self._archive_paths)

    def _save_starred(self):
        save_starred(self._starred_paths)

    # Fields that are expensive to store but read on-demand from disk.
    _CACHE_EXCLUDED_FIELDS = frozenset({"raw_content", "body_content"})

    def _save_cache(self, data):
        """Saves discovered skills to cache for faster startup.

        Strips raw_content and body_content — these are large per-skill blobs
        read on-demand from disk, not needed in the index cache.
        """
        try:
            from skill_manager.core.config import SKILL_LIBRARY_CACHE_FILE

            slim_data = dict(data)
            if "skills" in slim_data:
                slim_data["skills"] = [
                    {k: v for k, v in skill.items() if k not in self._CACHE_EXCLUDED_FIELDS}
                    for skill in slim_data["skills"]
                ]
            print(
                f"[CACHE] Saving {len(slim_data.get('skills', []))} skills to {SKILL_LIBRARY_CACHE_FILE}..."
            )
            with open(SKILL_LIBRARY_CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(slim_data, f, indent=2, default=str)
            size_mb = Path(SKILL_LIBRARY_CACHE_FILE).stat().st_size / 1024 / 1024
            print(f"[CACHE] Save successful ({size_mb:.1f} MB).")
        except Exception as e:
            print(f"Error saving cache: {e}")

    def _load_cache(self):
        """Loads skills from cache. Auto-deletes the file on corruption."""
        from skill_manager.core.config import SKILL_LIBRARY_CACHE_FILE

        cache_path = Path(SKILL_LIBRARY_CACHE_FILE)
        if not cache_path.exists():
            return None
        try:
            with open(cache_path, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError, OSError) as e:
            print(f"[CACHE] Corrupted cache deleted ({e}). Will rebuild on next scan.")
            with contextlib.suppress(OSError):
                cache_path.unlink(missing_ok=True)
        return None

    @Slot(str)
    def addToArchive(self, skill_local_path):
        if skill_local_path and skill_local_path not in self._archive_paths:
            self._archive_paths.append(skill_local_path)
            self._save_archive()
            self.load_initial_data()  # Refresh UI
            self._set_status(f"Skill archived: {skill_local_path}")

    @Slot(str)
    def setClientFormat(self, fmt):
        if self._client_format != fmt:
            self._client_format = fmt
            self._config.set("client_format", fmt)
            # Update both models
            self._library_model.clientFilter = fmt
            self._quick_copy_model.clientFilter = fmt
            self.clientFormatChanged.emit()
            self._set_status(f"Client format set to: {fmt}")

    @Slot(str)
    def setStartupView(self, view):
        self.startupView = view
        self._set_status(f"Startup view set to: {self.startupView}")

    @Slot(bool)
    def setRememberFilters(self, remember):
        self.rememberFilters = remember
        self._set_status("Filter memory enabled" if remember else "Filter memory disabled")

    @Slot(str)
    def setDefaultProjectFilter(self, mode):
        self.defaultProjectFilter = mode
        label = "All Projects" if self.defaultProjectFilter == "all" else "Last Project"
        self._set_status(f"Default project filter: {label}")

    @Slot(bool)
    def setReducedMotion(self, reduced):
        self.reducedMotion = reduced
        self._set_status("Reduced motion enabled" if reduced else "Reduced motion disabled")

    @Slot(bool)
    def setCompactListRows(self, compact):
        self.compactListRows = compact
        self._set_status("Compact list rows enabled" if compact else "Compact list rows disabled")

    @Slot()
    def refreshSkills(self):
        self._set_status("Refreshing library...")
        self.load_initial_data()

    @Slot(str, list)
    def saveCustomCollection(self, name, paths):
        if not name:
            return
        self._custom_collections[name] = paths
        self._config.set("custom_collections", self._custom_collections)
        self.customCollectionsChanged.emit()
        self._set_status(f"Collection saved: {name}")

    @Slot(str)
    def deleteCustomCollection(self, name):
        if name in self._custom_collections:
            del self._custom_collections[name]
            self._config.set("custom_collections", self._custom_collections)
            self.customCollectionsChanged.emit()
            self._set_status(f"Collection deleted: {name}")

    @Slot(str)
    def applyCollectionSelection(self, name):
        if name in self._custom_collections:
            paths = self._custom_collections[name]
            # Selection is usually specific to the active view
            self.skillModel.clearSelection()
            self.skillModel.selectByPaths(paths)
            self._set_status(f"Applied collection: {name}")

    @Slot(str, result=list)
    def getCollectionPaths(self, name):
        return self._custom_collections.get(name, [])

    @Slot(str, str, str, str, str)
    def createCustomCommand(self, name, client, body, project_label, category):
        """Creates a new Custom Command .md file in the project's commands/ directory."""
        result = create_custom_command_file(
            name=name,
            client=client,
            body=body,
            project_label_name=project_label,
            category=category,
            project_paths=self._projects,
        )
        self._set_status(result.message)
        if result.ok:
            self.refreshSkills()

    @Slot(str, str)
    def setViewFilter(self, filter_type, value):
        self._set_view_filter_for_model(self.skillModel, filter_type, value)

    @Slot(str, str, str)
    def setViewFilterForView(self, view, filter_type, value):
        self._set_view_filter_for_model(self._model_for_view(view), filter_type, value)

    def _model_for_view(self, view):
        normalized = self._normalize_view_name(view)
        return self._library_model if normalized == "Library" else self._quick_copy_model

    def _set_view_filter_for_model(self, model, filter_type, value):
        """
        Sets a specific filter on one view model.
        Library and Quick Copy filters are intentionally independent.
        """
        if not self.ui._remember_filters:
            model.filterText = ""

        if filter_type == "category":
            model.categoryFilter = value
            if value:
                capture_event("skill_searched", {"filter_type": "category"})
        elif filter_type == "collection":
            if not value:
                model.collectionFilter = False
            elif value == "true":
                model.collectionFilter = True
            else:
                # Custom collection name - handled via applyCollectionSelection usually,
                # but we keep the active filter property in sync.
                model.collectionFilter = False
        elif filter_type == "project":
            if model is self._quick_copy_model:
                model.projectFilter = value
        elif filter_type == "clear":
            model.filterText = ""
            model.categoryFilter = ""
            model.collectionFilter = False
            model.projectFilter = ""
        # We ignore "library" and "quick_copy" here as they are handled by currentView setter

        self._set_status(f"Filter applied: {filter_type} = {value if value else 'All'}")

    @Slot()
    def clearViewFilters(self):
        model = self.skillModel
        model.filterText = ""
        model.categoryFilter = ""
        model.collectionFilter = False
        model.projectFilter = ""
        self._set_status("Filters cleared")

    def _clear_all_view_filters(self):
        for model in [self._library_model, self._quick_copy_model]:
            model.filterText = ""
            model.categoryFilter = ""
            model.collectionFilter = False
            model.projectFilter = ""

    @Slot()
    def resetUiState(self):
        self._clear_all_view_filters()
        self.ui.reset_ui_state()
        self.currentViewChanged.emit()
        self.windowWidthChanged.emit()
        self.windowHeightChanged.emit()
        self.windowXChanged.emit()
        self.windowYChanged.emit()
        self.startupViewChanged.emit()
        self.rememberFiltersChanged.emit()
        self.defaultProjectFilterChanged.emit()
        self.reducedMotionChanged.emit()
        self.compactListRowsChanged.emit()
        self._set_status("UI state reset")

    @Slot(str)
    def syncProject(self, path):
        if path not in self._projects:
            return

        self._set_status(f"Updating {self.getProjectLabel(path)}...")
        if path not in self._syncing_projects:
            self._syncing_projects.append(path)
            self.projectsChanged.emit()

        def run_sync():
            try:
                # Re-scan sources
                from skill_manager.core.quick_copy import discover_package_skills

                source_skills = discover_package_skills(
                    sources=self._sources,
                    parse_skill_md=parse_skill_md,
                    categorize_skill=categorize_skill,
                    build_search_text=build_skill_search_text,
                )

                # Sync only to this project, update only
                from skill_manager.core.copier import copy_skill_folders_to_projects

                result = copy_skill_folders_to_projects(source_skills, [path], update_only=True)

                msg = f"Update complete for {self.getProjectLabel(path)}: {result['merged']} updated, {result['failed']} failed"
                QTimer.singleShot(0, self, lambda: self._set_status(msg))
            except Exception as e:
                err_msg = f"Update failed for {path}: {e}"
                QTimer.singleShot(0, self, lambda: self._set_status(err_msg))
            finally:
                if path in self._syncing_projects:
                    self._syncing_projects.remove(path)
                QTimer.singleShot(0, self, self.projectsChanged.emit)

        self.task_runner.run(run_sync)

    @Slot()
    def updateNow(self):
        self.updates.update_now()

    @Slot()
    def scanForUpdates(self):
        self.updates.scan_for_updates()

    @Slot()
    def updateAllOutdated(self):
        self.updates.update_now()

    @Slot(str, str)
    def updateSkillInProject(self, skill_name, project_name):
        self.updates.update_skill_in_project(skill_name, project_name)

    def _set_status(self, msg):
        self._status_message = msg
        self.statusMessageChanged.emit()
        print(f"Status: {msg}")

    def on_quit(self):
        """Ensures all pending state is saved before exit."""
        if self.ui._save_timer.isActive():
            self.ui._save_timer.stop()
            self.ui.save_ui_state()
        posthog_shutdown()


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    return resolve_resource_path(relative_path)


def main():  # pragma: no cover - QML application bootstrap is validated by startup/E2E smoke tests.
    # Set style to Basic to avoid issues with platform themes during debug
    QQuickStyle.setStyle("Basic")

    app = QGuiApplication(sys.argv)
    app.setWindowIcon(QIcon(resource_path("assets/brand/logo.png")))

    controller = AppController()

    # Register singletons - 6 arguments required: (Type, URI, Major, Minor, Name, Instance)
    qmlRegisterSingletonInstance(AppController, "App", 1, 0, "AppController", controller)

    app.aboutToQuit.connect(controller.on_quit)

    engine = QQmlApplicationEngine()

    # Add context property for compatibility
    engine.rootContext().setContextProperty("appController", controller)

    # Listen to warnings
    engine.warnings.connect(lambda msg: print(f"QML Warning: {msg}"))

    qml_dir = qml_components_dir(package_file=__file__)

    engine.addImportPath(str(qml_dir.parent))

    qml_file = qml_dir / "Main.qml"
    engine.load(str(qml_file))
    if not engine.rootObjects():
        print("CRITICAL: Failed to load QML root objects!")
        sys.exit(-1)

    capture_event("app_opened")

    # Apply native styles if available
    if HAS_PYWINSTYLES:

        def apply_native_styles():
            for root in engine.rootObjects():
                try:
                    hwnd = root.winId()
                    print(f"Applying native styles to HWND: {hwnd}")

                    # Apply Mica (Win11) or Acrylic (Win10)
                    # We use pywinstyles for the material effect
                    pywinstyles.apply_style(hwnd, "mica")

                    # DWMWA_WINDOW_CORNER_PREFERENCE = 33, DWMWCP_ROUND = 2
                    # DWMWA_USE_IMMERSIVE_DARK_MODE = 20
                    DWMWA_WINDOW_CORNER_PREFERENCE = 33
                    DWMWCP_ROUND = 2

                    try:
                        # Apply dark mode attribute if needed (helps with shadow/border visibility)
                        # We'll set it to 1 (True) as a good default for modern glass looks
                        ctypes.windll.dwmapi.DwmSetWindowAttribute(
                            hwnd, 20, ctypes.byref(ctypes.c_int(1)), 4
                        )

                        ctypes.windll.dwmapi.DwmSetWindowAttribute(
                            hwnd,
                            DWMWA_WINDOW_CORNER_PREFERENCE,
                            ctypes.byref(ctypes.c_int(DWMWCP_ROUND)),
                            4,
                        )
                    except Exception:
                        pass

                except Exception as e:
                    print(f"Failed to apply native style: {e}")

        # Delay slightly to ensure window is fully initialized
        QTimer.singleShot(500, apply_native_styles)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

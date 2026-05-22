"""
Purpose: Main entry point for Skill Manager (PySide6 version).
Usage: python run.py
"""

import ctypes
import os
import sys

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


from skill_manager.controllers.config_controller import ConfigController
from skill_manager.controllers.discovery_controller import DiscoveryController
from skill_manager.controllers.ops_controller import OpsController
from skill_manager.controllers.ui_controller import UIController
from skill_manager.controllers.update_controller import UpdateController
from skill_manager.core.analytics import (
    capture_event,
    shutdown as posthog_shutdown,
)
from skill_manager.core.categories import get_category_emoji
from skill_manager.core.config import (
    ConfigManager,
)
from skill_manager.core.models import SkillModel
from skill_manager.core.persistence import (
    load_archive,
    load_starred,
)
from skill_manager.core.quick_copy import (
    CLIENT_FORMATS,
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
        self.discovery = DiscoveryController(self)

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
        return self.config_mgr.get_update_projects()

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
        """Returns the standard emoji for a given category name."""
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
        normalized = self.ui._normalize_view_name(value)
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
        normalized = self.ui._normalize_view_name(value)
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

    @Property(str, notify=shortcutsChanged)
    def shortcutSearch(self): return self.config_mgr.get_shortcut("search")
    @Property(str, notify=shortcutsChanged)
    def shortcutCopy(self): return self.config_mgr.get_shortcut("copy")
    @Property(str, notify=shortcutsChanged)
    def shortcutArchive(self): return self.config_mgr.get_shortcut("archive")
    @Property(str, notify=shortcutsChanged)
    def shortcutDelete(self): return self.config_mgr.get_shortcut("delete")
    @Property(str, notify=shortcutsChanged)
    def shortcutRefresh(self): return self.config_mgr.get_shortcut("refresh")
    @Property(str, notify=shortcutsChanged)
    def shortcutExpandAll(self): return self.config_mgr.get_shortcut("expand_all")
    @Property(str, notify=shortcutsChanged)
    def shortcutCollapseAll(self): return self.config_mgr.get_shortcut("collapse_all")
    @Property(str, notify=shortcutsChanged)
    def shortcutTopOfList(self): return self.config_mgr.get_shortcut("top_of_list")
    @Property(str, notify=shortcutsChanged)
    def shortcutClearSelection(self): return self.config_mgr.get_shortcut("clear_selection")
    @Property(str, notify=shortcutsChanged)
    def shortcutThemeToggle(self): return self.config_mgr.get_shortcut("theme_toggle")
    @Property(str, notify=shortcutsChanged)
    def shortcutQuickCopyView(self): return self.config_mgr.get_shortcut("quick_copy_view")
    @Property(str, notify=shortcutsChanged)
    def shortcutLibraryView(self): return self.config_mgr.get_shortcut("library_view")
    @Property(str, notify=shortcutsChanged)
    def shortcutUpdatesView(self): return self.config_mgr.get_shortcut("updates_view")
    @Property(str, notify=shortcutsChanged)
    def shortcutSettingsView(self): return self.config_mgr.get_shortcut("settings_view")

    @Slot(str, str)
    def setShortcut(self, action, sequence):
        self.config_mgr.set_shortcut(action, sequence)

    @Slot()
    def resetShortcuts(self):
        self.config_mgr.reset_shortcuts()

    # --- Slots ---

    @Property(Qt.CheckState, notify=isPackageOnlyChanged)
    def isPackageOnly(self):
        return self._library_model.isPackageOnly

    @isPackageOnly.setter
    def isPackageOnly(self, value):
        self._library_model.isPackageOnly = value
        self._quick_copy_model.isPackageOnly = value
        self.isPackageOnlyChanged.emit()

    @Slot()
    def load_initial_data(self):
        self.discovery.load_initial_data()

    @Slot(int)
    def selectSkill(self, index):
        self.ui.select_skill(index)

    @Slot(str)
    def copySkillToClipboard(self, path):
        self.ops.copy_skill_to_clipboard(path)

    @Slot()
    def copyCurrentSelectionOrFocusedSkill(self):
        self.ops.copy_current_selection_or_focused_skill()

    @Slot()
    def copySelectedSkillsToClipboard(self):
        self.ops.copy_selected_skills_to_clipboard()

    @Slot(str)
    def copyTextToClipboard(self, content):
        self.ops.copy_text_to_clipboard(content)

    @Slot(dict, str)
    def copySkillReference(self, skill, arg=""):
        self.ops.copy_skill_reference(skill, arg)

    @Slot()
    def toggleCurrentSkillArchive(self):
        self.ops.toggle_archive()

    @Slot()
    def toggleCurrentSkillStarred(self):
        self.ops.toggle_starred()

    @Slot()
    def selectAllVisibleSkills(self):
        self.ui.select_all_visible_skills()

    @Slot()
    def clearVisibleSelection(self):
        self.ui.clear_visible_selection()

    @Slot()
    def toggleAllVisibleCategories(self):
        self.ui.toggle_all_visible_categories()

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
            self.ops._save_archive()
            self.skillModel.clearSelection()
            self._set_status(f"{count} skills archived")
            self.load_initial_data()
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
        return self.config_mgr.verify_git_package(url, token)

    @Slot(str)
    def addUpdatePackage(self, package_name):
        self.updates.add_update_package(package_name)

    @Slot(dict)
    def addSkillPackage(self, data):
        self.updates.add_skill_package(data)

    @Slot(int, dict)
    def updateUpdatePackage(self, index, data):
        self.updates.update_update_package(index, data)

    @Slot(int)
    def removeUpdatePackage(self, index):
        self.updates.remove_update_package(index)

    @Slot(int)
    def clearPackageJustFinished(self, index):
        if 0 <= index < len(self._update_packages):
            self._update_packages[index]["just_finished"] = False
            self._update_packages[index] = dict(self._update_packages[index])
            self.updatePackagesChanged.emit()

    @Slot(int)
    def runPackageUpdate(self, index):
        self.updates.run_package_update(index)

    @Slot(str)
    def addToArchive(self, skill_local_path):
        if skill_local_path and skill_local_path not in self._archive_paths:
            self._archive_paths.append(skill_local_path)
            self.ops._save_archive()
            self.load_initial_data()
            self._set_status(f"Skill archived: {skill_local_path}")

    @Slot(str)
    def setClientFormat(self, fmt):
        if self._client_format != fmt:
            self._client_format = fmt
            self._config.set("client_format", fmt)
            self._library_model.clientFilter = fmt
            self._quick_copy_model.clientFilter = fmt
            self.clientFormatChanged.emit()
            self._set_status(f"Client format set to: {fmt}")

    @Slot(str)
    def setStartupView(self, view):
        normalized = self.ui._normalize_view_name(view)
        if self.ui._startup_view != normalized:
            self.ui._startup_view = normalized
            self.ui.trigger_save()
            self.startupViewChanged.emit()
            self._set_status(f"Startup view set to: {self.ui._startup_view}")

    @Slot(bool)
    def setRememberFilters(self, remember):
        if self.ui._remember_filters != remember:
            self.ui._remember_filters = remember
            if not remember:
                self.clearViewFilters()
            self.ui.trigger_save()
            self.rememberFiltersChanged.emit()
            self._set_status("Filter memory enabled" if remember else "Filter memory disabled")

    @Slot(str)
    def setDefaultProjectFilter(self, mode):
        normalized = mode if mode in {"last", "all"} else "last"
        if self.ui._default_project_filter != normalized:
            self.ui._default_project_filter = normalized
            if self.ui._default_project_filter == "all":
                self.setViewFilterForView("QuickCopy", "project", "")
            self.ui.trigger_save()
            self.defaultProjectFilterChanged.emit()
            label = "All Projects" if self.ui._default_project_filter == "all" else "Last Project"
            self._set_status(f"Default project filter: {label}")

    @Slot(bool)
    def setReducedMotion(self, reduced):
        if self.ui._reduced_motion != reduced:
            self.ui._reduced_motion = reduced
            self.ui.trigger_save()
            self.reducedMotionChanged.emit()
            self._set_status("Reduced motion enabled" if reduced else "Reduced motion disabled")

    @Slot(bool)
    def setCompactListRows(self, compact):
        if self.ui._compact_list_rows != compact:
            self.ui._compact_list_rows = compact
            self.ui.trigger_save()
            self.compactListRowsChanged.emit()
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
            self.skillModel.clearSelection()
            self.skillModel.selectByPaths(paths)
            self._set_status(f"Applied collection: {name}")

    @Slot(str, result=list)
    def getCollectionPaths(self, name):
        return self._custom_collections.get(name, [])

    @Slot(str, str, str, str, str)
    def createCustomCommand(self, name, client, body, project_label, category):
        self.ops.create_custom_command(name, client, body, project_label, category)

    @Slot(str, str)
    def setViewFilter(self, filter_type, value):
        self._set_view_filter_for_model(self.skillModel, filter_type, value)

    @Slot(str, str, str)
    def setViewFilterForView(self, view, filter_type, value):
        self._set_view_filter_for_model(self._model_for_view(view), filter_type, value)

    def _model_for_view(self, view):
        normalized = self.ui._normalize_view_name(view)
        return self._library_model if normalized == "Library" else self._quick_copy_model

    def _set_view_filter_for_model(self, model, filter_type, value):
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
                model.collectionFilter = False
        elif filter_type == "project":
            if model is self._quick_copy_model:
                model.projectFilter = value
        elif filter_type == "clear":
            model.filterText = ""
            model.categoryFilter = ""
            model.collectionFilter = False
            model.projectFilter = ""

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
        self.updates.sync_project(path)

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

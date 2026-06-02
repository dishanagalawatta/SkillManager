"""
Purpose: Main entry point for Skill Manager (PySide6 version).
Usage: python run.py
"""

import ctypes
import os
import sys
import logging

logger = logging.getLogger(__name__)

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


from skill_manager.controllers.app_update_controller import AppUpdateController
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
from skill_manager.core.resources import (
    qml_components_dir,
    resource_path as resolve_resource_path,
)
from skill_manager.core.file_watch import SkillFolderWatcher
from skill_manager.utils.task_runner import BackgroundTaskRunner


class AppController(QObject):
    # Core State Signals
    skillModelChanged = Signal()
    selectedSkillChanged = Signal()
    isLoadingChanged = Signal()
    statusMessageChanged = Signal()

    # Bridge Signals (delegated to controllers but kept here for cross-controller notification)
    sourcesChanged = Signal()
    projectsChanged = Signal()
    discoveredProjectsChanged = Signal()
    clientFormatChanged = Signal()
    categoriesChanged = Signal()
    clientFormatsChanged = Signal()
    customCollectionsChanged = Signal()
    updateResultsChanged = Signal()
    updatePackagesChanged = Signal()
    isPackageOnlyChanged = Signal()

    @Property(bool, constant=True)
    def isTesting(self):
        return os.environ.get("SKILL_MANAGER_TESTING") == "1"

    # Legacy UI/Config Signals (Forwarded from sub-controllers)
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
    shortcutsChanged = Signal()
    isRecordingShortcutChanged = Signal()

    def __init__(self, skip_initial_load=False, config=None):
        super().__init__()
        # 1. Core Models and Configuration
        self._config = config if config else ConfigManager()
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
        self.app_updater = AppUpdateController(self)

        # 4. Connect Sub-Controller signals to Proxy Signals
        self.ui.currentViewChanged.connect(self.currentViewChanged.emit)
        self.ui.windowWidthChanged.connect(self.windowWidthChanged.emit)
        self.ui.windowHeightChanged.connect(self.windowHeightChanged.emit)
        self.ui.windowXChanged.connect(self.windowXChanged.emit)
        self.ui.windowYChanged.connect(self.windowYChanged.emit)
        self.ui.darkModeChanged.connect(self.darkModeChanged.emit)
        self.ui.startupViewChanged.connect(self.startupViewChanged.emit)
        self.ui.rememberFiltersChanged.connect(self.rememberFiltersChanged.emit)
        self.ui.defaultProjectFilterChanged.connect(self.defaultProjectFilterChanged.emit)
        self.ui.reducedMotionChanged.connect(self.reducedMotionChanged.emit)
        self.ui.compactListRowsChanged.connect(self.compactListRowsChanged.emit)

        self.config_mgr.shortcutsChanged.connect(self.shortcutsChanged.emit)
        self.config_mgr.isRecordingShortcutChanged.connect(self.isRecordingShortcutChanged.emit)
        self.config_mgr.updateProjectsChanged.connect(self.projectsChanged.emit)
        self.config_mgr.clientFormatsChanged.connect(self.clientFormatsChanged.emit)
        self.config_mgr.customCollectionsChanged.connect(self.customCollectionsChanged.emit)

        # 5. Lifecycle Hooks
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

        # Set up file watching for live refreshes
        watch_paths = self._sources.copy()
        for src in self._update_packages:
            pkg_path = src.get("package_path") or src.get("local_path")
            if pkg_path:
                watch_paths.append(pkg_path)

        self._watcher = SkillFolderWatcher(
            paths=watch_paths,
            callback=lambda path: QTimer.singleShot(0, self.refreshSkills)
        )

        # In tests, we often want to skip the initial background discovery
        skip_initial = skip_initial_load or os.environ.get("SKILL_MANAGER_SKIP_INITIAL_LOAD") == "1"

        if not skip_initial:
            self._watcher.start()
            QTimer.singleShot(100, self.loadInitialData)
            QTimer.singleShot(500, self.app_updater.checkForUpdates)

    # --- Gateway Properties ---

    @Property(QObject, constant=True)
    def ui_controller(self): return self.ui

    @Property(QObject, constant=True)
    def config_controller(self): return self.config_mgr

    @Property(QObject, constant=True)
    def ops_controller(self): return self.ops

    @Property(QObject, constant=True)
    def update_controller(self): return self.updates

    @Property(QObject, constant=True)
    def discovery_controller(self): return self.discovery

    @Property(QObject, constant=True)
    def app_update_controller(self): return self.app_updater

    # --- Core Properties ---

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

    @Property(str, notify=clientFormatChanged)
    def clientFormat(self):
        return self._client_format

    @Property(list, notify=categoriesChanged)
    def categories(self):
        return self._categories

    @Property(list, notify=discoveredProjectsChanged)
    def discoveredProjects(self):
        return self._discovered_projects

    @Property(list, notify=updatePackagesChanged)
    def updatePackages(self):
        return self._update_packages

    @Property(dict, notify=projectsChanged)
    def projectAliases(self):
        return self._project_aliases

    @Property(list, notify=updateResultsChanged)
    def updateResults(self):
        return self._update_results

    @Property(int, notify=statsChanged)
    def statsUpToDate(self):
        return self._stats_up_to_date

    @Property(int, notify=statsChanged)
    def statsOutdated(self):
        return self._stats_outdated

    @Property(int, notify=statsChanged)
    def statsMissing(self):
        return self._stats_missing

    # --- Proxy Properties (Temporary for QML compatibility) ---
    # These will be removed once QML is updated to use controller namespaces.

    @Property(str, notify=currentViewChanged)
    def currentView(self): return self.ui.currentView
    @currentView.setter
    def currentView(self, v): self.ui.currentView = v

    @Property(int, notify=windowWidthChanged)
    def windowWidth(self): return self.ui.windowWidth
    @windowWidth.setter
    def windowWidth(self, v): self.ui.windowWidth = v

    @Property(int, notify=windowHeightChanged)
    def windowHeight(self): return self.ui.windowHeight
    @windowHeight.setter
    def windowHeight(self, v): self.ui.windowHeight = v

    @Property(int, notify=windowXChanged)
    def windowX(self): return self.ui.windowX
    @windowX.setter
    def windowX(self, v): self.ui.windowX = v

    @Property(int, notify=windowYChanged)
    def windowY(self): return self.ui.windowY
    @windowY.setter
    def windowY(self, v): self.ui.windowY = v

    @Property(bool, notify=darkModeChanged)
    def darkMode(self): return self.ui.darkMode
    @darkMode.setter
    def darkMode(self, v): self.ui.darkMode = v

    @Property(str, notify=startupViewChanged)
    def startupView(self): return self.ui.startupView
    @startupView.setter
    def startupView(self, v): self.ui.startupView = v

    @Property(bool, notify=rememberFiltersChanged)
    def rememberFilters(self): return self.ui.rememberFilters
    @rememberFilters.setter
    def rememberFilters(self, v): self.ui.rememberFilters = v

    @Property(str, notify=defaultProjectFilterChanged)
    def defaultProjectFilter(self): return self.ui.defaultProjectFilter
    @defaultProjectFilter.setter
    def defaultProjectFilter(self, v): self.ui.defaultProjectFilter = v

    @Property(bool, notify=reducedMotionChanged)
    def reducedMotion(self): return self.ui.reducedMotion
    @reducedMotion.setter
    def reducedMotion(self, v): self.ui.reducedMotion = v

    @Property(bool, notify=compactListRowsChanged)
    def compactListRows(self): return self.ui.compactListRows
    @compactListRows.setter
    def compactListRows(self, v): self.ui.compactListRows = v

    @Property(str, notify=shortcutsChanged)
    def shortcutSearch(self): return self.config_mgr.shortcutSearch
    @Property(str, notify=shortcutsChanged)
    def shortcutCopy(self): return self.config_mgr.shortcutCopy
    @Property(str, notify=shortcutsChanged)
    def shortcutArchive(self): return self.config_mgr.shortcutArchive
    @Property(str, notify=shortcutsChanged)
    def shortcutDelete(self): return self.config_mgr.shortcutDelete
    @Property(str, notify=shortcutsChanged)
    def shortcutRefresh(self): return self.config_mgr.shortcutRefresh
    @Property(str, notify=shortcutsChanged)
    def shortcutExpandAll(self): return self.config_mgr.shortcutExpandAll
    @Property(str, notify=shortcutsChanged)
    def shortcutCollapseAll(self): return self.config_mgr.shortcutCollapseAll
    @Property(str, notify=shortcutsChanged)
    def shortcutTopOfList(self): return self.config_mgr.shortcutTopOfList
    @Property(str, notify=shortcutsChanged)
    def shortcutClearSelection(self): return self.config_mgr.shortcutClearSelection
    @Property(str, notify=shortcutsChanged)
    def shortcutThemeToggle(self): return self.config_mgr.shortcutThemeToggle
    @Property(str, notify=shortcutsChanged)
    def shortcutQuickCopyView(self): return self.config_mgr.shortcutQuickCopyView
    @Property(str, notify=shortcutsChanged)
    def shortcutLibraryView(self): return self.config_mgr.shortcutLibraryView
    @Property(str, notify=shortcutsChanged)
    def shortcutUpdatesView(self): return self.config_mgr.shortcutUpdatesView
    @Property(str, notify=shortcutsChanged)
    def shortcutSettingsView(self): return self.config_mgr.shortcutSettingsView

    @Property(str, notify=currentViewChanged)
    def logoSource(self): return self.ui.logoSource

    @Property(list, notify=projectsChanged)
    def updateProjects(self): return self.config_mgr.updateProjects

    @Property(list, notify=clientFormatsChanged)
    def clientFormats(self): return self.config_mgr.clientFormats

    @Property(list, notify=customCollectionsChanged)
    def customCollections(self): return self.config_mgr.customCollections

    @Property(list, notify=projectsChanged)
    def projectLabels(self): return self.config_mgr.projectLabels

    # --- Proxy Slots (Temporary for QML compatibility) ---

    @Slot()
    def load_initial_data(self): self.loadInitialData()

    @Slot(str, result=str)
    def getLogoSource(self, f): return self.ui.getLogoSource(f)

    @Slot(str, result=str)
    def getAssetUri(self, p): return self.ui.getAssetUri(p)

    @Slot(str, str)
    def setViewFilter(self, k, v): self.ui.setViewFilter(k, v)
    @Slot(str, str, str)
    def setViewFilterForView(self, view, k, v): self.ui.setViewFilterForView(view, k, v)
    @Slot()
    def clearViewFilters(self): self.ui.clearViewFilters()
    @Slot(int)
    def selectSkill(self, i): self.ui.selectSkill(i)
    @Slot()
    def clearVisibleSelection(self): self.ui.clearVisibleSelection()
    @Slot()
    def selectAllVisibleSkills(self): self.ui.selectAllVisibleSkills()
    @Slot()
    def toggleAllVisibleCategories(self): self.ui.toggleAllVisibleCategories()
    @Slot(str)
    def launchSkill(self, p): self.ui.launchSkill(p)
    @Slot(str)
    def openPath(self, p): self.ui.openPath(p)
    @Slot()
    def resetUiState(self): self.ui.resetUiState()
    @Slot(str)
    def setClientFormat(self, f): self.ui.setClientFormat(f)
    @Slot(str)
    def setStartupView(self, v): self.ui.setStartupView(v)
    @Slot(bool)
    def setRememberFilters(self, b): self.ui.setRememberFilters(b)
    @Slot(str)
    def setDefaultProjectFilter(self, f): self.ui.setDefaultProjectFilter(f)
    @Slot(bool)
    def setReducedMotion(self, b): self.ui.setReducedMotion(b)
    @Slot(bool)
    def setCompactListRows(self, b): self.ui.setCompactListRows(b)

    @Slot(str)
    def addSource(self, u): self.config_mgr.addSource(u)
    @Slot(str)
    def removeSource(self, p): self.config_mgr.removeSource(p)
    @Slot(int)
    def removeSourceByIndex(self, i): self.config_mgr.removeSourceByIndex(i)
    @Slot(str)
    def addProject(self, u): self.config_mgr.addProject(u)
    @Slot(str)
    def removeProject(self, p): self.config_mgr.removeProject(p)
    @Slot(int)
    def removeUpdateProject(self, i): self.config_mgr.removeUpdateProject(i)
    @Slot(str, str)
    def setProjectAlias(self, p, a): self.config_mgr.setProjectAlias(p, a)
    @Slot(str, str, result=str)
    def verifyGitPackage(self, u, t=None): return self.config_mgr.verifyGitPackage(u, t)
    @Slot(str, str)
    def setShortcut(self, a, s): self.config_mgr.setShortcut(a, s)
    @Slot()
    def resetShortcuts(self): self.config_mgr.resetShortcuts()
    @Slot(str, list)
    def saveCustomCollection(self, n, p): self.config_mgr.saveCustomCollection(n, p)
    @Slot(str)
    def deleteCustomCollection(self, n): self.config_mgr.deleteCustomCollection(n)
    @Slot(str)
    def applyCollectionSelection(self, n): self.config_mgr.applyCollectionSelection(n)
    @Slot(str, result=list)
    def getCollectionPaths(self, n): return self.config_mgr.getCollectionPaths(n)

    @Slot()
    def toggleCurrentSkillArchive(self): self.ops.toggleCurrentSkillArchive()
    @Slot()
    def toggleCurrentSkillStarred(self): self.ops.toggleCurrentSkillStarred()
    @Slot(str)
    def copySkillToClipboard(self, p): self.ops.copySkillToClipboard(p)
    @Slot()
    def copyCurrentSelectionOrFocusedSkill(self): self.ops.copyCurrentSelectionOrFocusedSkill()
    @Slot()
    def copySelectedSkillsToClipboard(self): self.ops.copySelectedSkillsToClipboard()
    @Slot(str)
    def copyTextToClipboard(self, c): self.ops.copyTextToClipboard(c)
    @Slot(dict, str)
    def copySkillReference(self, s, a=""): self.ops.copySkillReference(s, a)
    @Slot(str)
    def deleteSkill(self, p): self.ops.deleteSkill(p)
    @Slot()
    def deleteSelectedSkills(self): self.ops.deleteSelectedSkills()
    @Slot()
    def archiveSelectedSkills(self): self.ops.archiveSelectedSkills()
    @Slot(str)
    def copySelectedSkillsToProject(self, p): self.ops.copySelectedSkillsToProject(p)
    @Slot(str)
    def copySelectedSkillsToProjectTemporarily(self, p): self.ops.copySelectedSkillsToProjectTemporarily(p)
    @Slot(str, str, str, str, str)
    def createCustomCommand(self, n, cl, b, pl, cat): self.ops.createCustomCommand(n, cl, b, pl, cat)
    @Slot(str)
    def addToArchive(self, p): self.ops.addToArchive(p)

    @Slot()
    def updateNow(self): self.updates.updateNow()
    @Slot()
    def scanForUpdates(self): self.updates.scanForUpdates()
    @Slot()
    def updateAllOutdated(self): self.updates.updateAllOutdated()
    @Slot(str, str)
    def updateSkillInProject(self, s, p): self.updates.updateSkillInProject(s, p)
    @Slot(int)
    def runPackageUpdate(self, i): self.updates.runPackageUpdate(i)
    @Slot(str)
    def syncProject(self, p): self.updates.syncProject(p)
    @Slot(str)
    def addUpdatePackage(self, n): self.updates.addUpdatePackage(n)
    @Slot(dict)
    def addSkillPackage(self, d): self.updates.addSkillPackage(d)
    @Slot(int, dict)
    def updateUpdatePackage(self, i, d): self.updates.updateUpdatePackage(i, d)
    @Slot(int)
    def removeUpdatePackage(self, i): self.updates.removeUpdatePackage(i)
    @Slot(int)
    def clearPackageJustFinished(self, i): self.updates.clearPackageJustFinished(i)

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
    def loadInitialData(self):
        self.discovery.loadInitialData()

    @Slot(str, result=str)
    def getCategoryEmoji(self, category_name: str) -> str:
        return get_category_emoji(category_name)

    @Slot()
    def refreshSkills(self):
        self._set_status("Refreshing library...")
        self.loadInitialData()

    def _set_status(self, msg):
        self._status_message = msg
        self.statusMessageChanged.emit()
        logger.info(f"Status: {msg}")

    # Forwarding helper for sub-controllers to access labels
    def getProjectLabel(self, path):
        return self.config_mgr.getProjectLabel(path)

    def on_quit(self):
        """Ensures all pending state is saved before exit."""
        if hasattr(self, '_watcher'):
            self._watcher.stop()
        if self.ui._save_timer.isActive():
            self.ui._save_timer.stop()
            self.ui.saveUiState()
        posthog_shutdown()


def main():  # pragma: no cover
    if sys.platform == "win32":
        # Acquire mutex so Inno Setup installer can cleanly close the app
        global _app_mutex
        _app_mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "SkillManagerAppMutex")

    QQuickStyle.setStyle("Basic")
    app = QGuiApplication(sys.argv)
    app.setWindowIcon(QIcon(resolve_resource_path("assets/brand/logo.png")))
    controller = AppController()
    qmlRegisterSingletonInstance(AppController, "App", 1, 0, "AppController", controller)
    app.aboutToQuit.connect(controller.on_quit)
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("appController", controller)
    engine.warnings.connect(lambda msg: logger.warning(f"QML Warning: {msg}"))
    qml_dir = qml_components_dir(package_file=__file__)
    engine.addImportPath(str(qml_dir.parent))
    qml_file = qml_dir / "Main.qml"
    engine.load(str(qml_file))
    if not engine.rootObjects():
        logger.error("CRITICAL: Failed to load QML root objects!")
        sys.exit(-1)
    capture_event("app_opened")
    if HAS_PYWINSTYLES:
        def apply_native_styles():
            for root in engine.rootObjects():
                try:
                    hwnd = root.winId()
                    pywinstyles.apply_style(hwnd, "mica")
                    ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(ctypes.c_int(1)), 4)
                    ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 33, ctypes.byref(ctypes.c_int(2)), 4)
                except Exception as e:
                    logger.error(f"Failed to apply native style: {e}")
        QTimer.singleShot(500, apply_native_styles)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

"""
Purpose: Main entry point for Skill Manager (PySide6 version).
Usage: python run.py
"""

import contextlib
import ctypes
import logging
import os
import sys
from typing import Any

import sentry_sdk
from apscheduler.schedulers.qt import QtScheduler  # type: ignore[reportMissingImports]
from PySide6.QtCore import Property, QObject, Qt, QTimer, Signal, Slot
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtQml import QQmlApplicationEngine, qmlRegisterSingletonInstance
from PySide6.QtQuickControls2 import QQuickStyle

import skill_manager

# Try to import pywinstyles for Mica/Acrylic
try:
    import pywinstyles

    HAS_PYWINSTYLES = True
except ImportError:
    pywinstyles = None  # type: ignore[assignment]
    HAS_PYWINSTYLES = False

# DWM attribute for immersive dark mode title bar
DWMWA_USE_IMMERSIVE_DARK_MODE = 20


def _apply_immersive_dark(hwnd: int, enabled: bool) -> None:
    """Set the DWM immersive-dark-mode attribute on the window.

    ``enabled=True`` tells the OS to render the title bar and system
    buttons in dark style; ``enabled=False`` reverts to light.
    """
    with contextlib.suppress(Exception):
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_USE_IMMERSIVE_DARK_MODE,
            ctypes.byref(ctypes.c_int(1 if enabled else 0)),
            4,
        )


# The ``_apply_immersive_dark`` helper above is intentionally defined
# before these imports so the constant and helper sit next to the
# ``pywinstyles`` try/except that depends on the same DWM surface.
# ruff flags module-level imports that follow executable code as E402;
# suppress per-line so the import order remains readable.
from skill_manager.controllers.app_update_controller import AppUpdateController  # noqa: E402
from skill_manager.controllers.config_controller import ConfigController  # noqa: E402
from skill_manager.controllers.discovery_controller import DiscoveryController  # noqa: E402
from skill_manager.controllers.font_database_bridge import FontDatabaseBridge  # noqa: E402
from skill_manager.controllers.image_inspector_controller import (  # noqa: E402
    ImageInspectorController,
)
from skill_manager.controllers.ops_controller import OpsController  # noqa: E402
from skill_manager.controllers.screenshot_controller import ScreenshotController  # noqa: E402
from skill_manager.controllers.ui_controller import UIController  # noqa: E402
from skill_manager.controllers.update_controller import UpdateController  # noqa: E402
from skill_manager.core.analytics import (  # noqa: E402
    capture_event,
    shutdown as posthog_shutdown,
)
from skill_manager.core.categories import get_category_emoji  # noqa: E402
from skill_manager.core.config import (  # noqa: E402
    ConfigManager,
)
from skill_manager.core.diagnostics import (  # noqa: E402
    CATEGORY_SOURCE_MISSING,
    get_diagnostic_logger,
)
from skill_manager.core.file_watch import SkillFolderWatcher  # noqa: E402
from skill_manager.core.global_hotkey import GlobalHotkeyManager  # noqa: E402
from skill_manager.core.image_provider import ScreenshotImageProvider  # noqa: E402
from skill_manager.core.models import SkillModel  # noqa: E402
from skill_manager.core.persistence import (  # noqa: E402
    load_archive,
    load_starred,
)
from skill_manager.core.resources import (  # noqa: E402
    invalidate_qml_disk_cache_if_stale,
    qml_components_dir,
    resource_path as resolve_resource_path,
)
from skill_manager.core.schemas import UpdatePackageRecord  # noqa: E402
from skill_manager.utils.task_runner import BackgroundTaskRunner  # noqa: E402

logger = logging.getLogger(__name__)


def _handle_qml_warning(msg):
    """Filter benign QML warnings, such as component destruction during incubation."""
    msg_str = msg.toString() if hasattr(msg, "toString") else str(msg)
    if "Object or context destroyed during incubation" in msg_str:
        logger.debug(f"QML Warning (suppressed): {msg_str}")
    else:
        logger.warning(f"QML Warning: {msg_str}")


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
    currentProjectChanged = Signal()
    clientFormatChanged = Signal()
    categoriesChanged = Signal()
    clientFormatsChanged = Signal()
    defaultClientChanged = Signal()
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
    reducedMotionChanged = Signal()
    compactListRowsChanged = Signal()
    skillPackageAutoUpdateChanged = Signal()
    skillPackageAutoUpdateModeChanged = Signal()
    statsChanged = Signal()
    shortcutsChanged = Signal()
    isRecordingShortcutChanged = Signal()

    # Command update signals (cross-controller notification)
    commandUpdateConflict = Signal(str, str, str)   # oldPath, conflictPath, suggestedRename
    commandUpdateCompleted = Signal(str, str)        # oldPath, newPath

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

        default_client = self._config.get("default_client", "Last Selected")
        if default_client == "Last Selected":
            self._client_format = self._config.get("client_format", "Antigravity")
        else:
            self._client_format = default_client
            # Also sync the currently saved client format to match the default
            self._config.set("client_format", self._client_format)

        self._sources = self._config.get("sources", [])
        self._projects = self._config.get("projects", [])
        self._project_aliases = self._config.get("project_aliases", {})
        self._update_packages = []
        raw_skills = self._config.get("skills", [])
        for s in raw_skills:
            try:
                # Validate and normalize using Pydantic
                record = UpdatePackageRecord.model_validate(s)
                # Ensure is_updating is False on startup
                record.is_updating = False
                self._update_packages.append(record.model_dump())
            except Exception as e:
                logger.warning("Invalid skill package config found: %s. Error: %s", s, e)
        self._custom_collections = self._config.get("custom_collections", {})

        # Shared project state (syncs across all project selectors)
        self._current_project_label = ""

        # Updates and Syncing State
        self._stats_up_to_date = 0
        self._stats_outdated = 0
        self._stats_missing = 0
        self._update_results = []
        self._syncing_projects = []

        # 3. Initialize Sub-Controllers
        # The type: ignore comments on each `SubController(self)` call work around a
        # pyright strict-mode quirk: ``Self@AppController`` is not structurally
        # assignable to ``AppController`` even though they are the same class.
        # Runtime is unaffected — these are not local re-bindings, just construction.
        self.ui = UIController(self)  # type: ignore[arg-type]
        self.config_mgr = ConfigController(self)  # type: ignore[arg-type]
        self.ops = OpsController(self)  # type: ignore[arg-type]
        self.screenshot_provider = ScreenshotImageProvider()
        self.screenshot = ScreenshotController(self)  # type: ignore[arg-type]
        self.image_inspector = ImageInspectorController(self)  # type: ignore[arg-type]
        self.updates = UpdateController(self)  # type: ignore[arg-type]
        self.discovery = DiscoveryController(self)  # type: ignore[arg-type]
        self.app_updater = AppUpdateController(self)  # type: ignore[arg-type]
        self.global_hotkey = GlobalHotkeyManager(self)  # type: ignore[arg-type]

        # 4. Connect Sub-Controller signals to Proxy Signals
        self.ui.currentViewChanged.connect(self.currentViewChanged.emit)
        self.ui.windowWidthChanged.connect(self.windowWidthChanged.emit)
        self.ui.windowHeightChanged.connect(self.windowHeightChanged.emit)
        self.ui.windowXChanged.connect(self.windowXChanged.emit)
        self.ui.windowYChanged.connect(self.windowYChanged.emit)
        self.ui.darkModeChanged.connect(self.darkModeChanged.emit)
        self.ui.startupViewChanged.connect(self.startupViewChanged.emit)
        self.ui.rememberFiltersChanged.connect(self.rememberFiltersChanged.emit)
        self.ui.reducedMotionChanged.connect(self.reducedMotionChanged.emit)
        self.ui.compactListRowsChanged.connect(self.compactListRowsChanged.emit)

        self.config_mgr.shortcutsChanged.connect(self.shortcutsChanged.emit)
        self.config_mgr.isRecordingShortcutChanged.connect(self.isRecordingShortcutChanged.emit)
        self.config_mgr.updateProjectsChanged.connect(self.projectsChanged.emit)
        self.projectsChanged.connect(self._on_projects_changed)
        self.config_mgr.clientFormatsChanged.connect(self.clientFormatsChanged.emit)
        self.config_mgr.customCollectionsChanged.connect(self.customCollectionsChanged.emit)

        # 5. Lifecycle Hooks
        self.ops.cleanup_temp_copies()  # Crash recovery
        self.ops.cleanup_temp_screenshots()  # Crash recovery
        app_inst = QGuiApplication.instance()
        if app_inst:
            app_inst.aboutToQuit.connect(self.ops.cleanup_temp_copies)
            app_inst.aboutToQuit.connect(self.ops.cleanup_temp_screenshots)

        # 6. Global Hotkey Setup (screenshot hotkey works when app is minimized)
        self._hotkey_id_screenshot = 1
        self._setup_global_hotkeys()

        # 4. Initial Model Configuration
        self._library_model.showCommands = False
        # PySide6's ``isPackageOnly`` setter accepts ``Qt.CheckState | bool``;
        # pyright's stub only exposes ``Qt.CheckState``, so the ``True``/
        # ``False`` literals are flagged.
        self._library_model.isPackageOnly = True  # type: ignore[arg-type]
        self._library_model.showStarred = True
        self._library_model.filterByClient = True

        self._quick_copy_model.showCommands = True
        self._quick_copy_model.isPackageOnly = False  # type: ignore[arg-type]
        self._quick_copy_model.showStarred = True
        self._quick_copy_model.filterByClient = True

        # Reactive client filter: sync model filters when user selects a different client
        self.clientFormatChanged.connect(self._on_client_format_changed)

        # Initialize shared currentProject from persisted QuickCopy filter or first project
        saved = self._quick_copy_model.projectFilter
        if saved and saved in self.config_mgr.projectLabels:
            self._current_project_label = saved
        elif self.config_mgr.projectLabels:
            self._current_project_label = self.config_mgr.projectLabels[0]

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
            paths=watch_paths, callback=lambda _: QTimer.singleShot(0, self.refreshSkills)
        )

        # In tests, we often want to skip the initial background discovery
        skip_initial = skip_initial_load or os.environ.get("SKILL_MANAGER_SKIP_INITIAL_LOAD") == "1"

        # Validate source paths at startup — warn early if directories are missing
        if not skip_initial:
            self._validate_source_paths()

        if not skip_initial:
            self._watcher.start()
            QTimer.singleShot(100, self.loadInitialData)

            # Skill Package Update Scheduler
            self._scheduler = QtScheduler()
            self._scheduler.start()

            # Initial Startup Check
            if self._config.get("skill_package_auto_update_mode", "prompt") != "off":
                QTimer.singleShot(2000, self._run_startup_package_scan)
            self.config_mgr.skillPackageAutoUpdateModeChanged.connect(
                self._update_package_scheduler
            )

    def _run_startup_package_scan(self):
        """Runs the initial scan for skill package updates."""
        logger.info("Running startup skill package update scan...")
        self.updates.scanForUpdates()

        # If mode is silent, we might want to auto-update if outdated.
        # But we need to wait for scan to complete.
        # For now, scanForUpdates handles the logic of finding updates.
        # We can enhance scanForUpdates completion to check for auto-update mode.

    def _update_package_scheduler(self):
        """Placeholder for periodic skill package updates if we decide to add them later."""
        pass

    # --- Gateway Properties ---

    @Property(QObject, constant=True)
    def ui_controller(self):
        return self.ui

    @Property(QObject, constant=True)
    def config_controller(self):
        return self.config_mgr

    @Property(QObject, constant=True)
    def ops_controller(self):
        return self.ops

    @Property(QObject, constant=True)
    def update_controller(self):
        return self.updates

    @Property(QObject, constant=True)
    def discovery_controller(self):
        return self.discovery

    @Property(QObject, constant=True)
    def app_update_controller(self):
        return self.app_updater

    @Property(QObject, constant=True)
    def screenshot_controller(self):
        return self.screenshot

    @Property(QObject, constant=True)
    def image_inspector_controller(self):
        return self.image_inspector

    @Property(str, notify=currentProjectChanged)
    def currentProject(self):  # type: ignore[reportRedeclaration]
        return self._current_project_label

    @currentProject.setter  # type: ignore[func-attr]
    def currentProject(self, label):
        self.setCurrentProject(label)

    @Slot(str)
    def setCurrentProject(self, label):
        if self._current_project_label != label:
            self._current_project_label = label
            self._quick_copy_model.projectFilter = label
            self.currentProjectChanged.emit()

    # --- Core Properties ---

    @Property(QObject, notify=skillModelChanged)
    def skillModel(self):
        if self.ui.currentView == "Library":
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

    @Property(str, notify=defaultClientChanged)
    def defaultClient(self):
        return self._config.get("default_client", "Last Selected")

    @Slot(str)
    def setDefaultClient(self, f):
        if self.defaultClient != f:
            self._config.set("default_client", f)
            self.defaultClientChanged.emit()

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
    def currentView(self):  # type: ignore[reportRedeclaration]
        return self.ui.currentView

    @currentView.setter  # type: ignore[func-attr]
    def currentView(self, v):
        self.ui.currentView = v

    @Property(int, notify=windowWidthChanged)
    def windowWidth(self):  # type: ignore[reportRedeclaration]
        return self.ui.windowWidth

    @windowWidth.setter  # type: ignore[func-attr]
    def windowWidth(self, v):
        self.ui.windowWidth = v

    @Property(int, notify=windowHeightChanged)
    def windowHeight(self):  # type: ignore[reportRedeclaration]
        return self.ui.windowHeight

    @windowHeight.setter  # type: ignore[func-attr]
    def windowHeight(self, v):
        self.ui.windowHeight = v

    @Property(int, notify=windowXChanged)
    def windowX(self):  # type: ignore[reportRedeclaration]
        return self.ui.windowX

    @windowX.setter  # type: ignore[func-attr]
    def windowX(self, v):
        self.ui.windowX = v

    @Property(int, notify=windowYChanged)
    def windowY(self):  # type: ignore[reportRedeclaration]
        return self.ui.windowY

    @windowY.setter  # type: ignore[func-attr]
    def windowY(self, v):
        self.ui.windowY = v

    @Property(bool, notify=darkModeChanged)
    def darkMode(self):  # type: ignore[reportRedeclaration]
        return self.ui.darkMode

    @darkMode.setter  # type: ignore[func-attr]
    def darkMode(self, v):
        self.ui.darkMode = v

    @Property(str, notify=startupViewChanged)
    def startupView(self):  # type: ignore[reportRedeclaration]
        return self.ui.startupView

    @startupView.setter  # type: ignore[func-attr]
    def startupView(self, v):
        self.ui.startupView = v

    @Property(bool, notify=rememberFiltersChanged)
    def rememberFilters(self):  # type: ignore[reportRedeclaration]
        return self.ui.rememberFilters

    @rememberFilters.setter  # type: ignore[func-attr]
    def rememberFilters(self, v):
        self.ui.rememberFilters = v

    @Property(bool, notify=reducedMotionChanged)
    def reducedMotion(self):  # type: ignore[reportRedeclaration]
        return self.ui.reducedMotion

    @reducedMotion.setter  # type: ignore[func-attr]
    def reducedMotion(self, v):
        self.ui.reducedMotion = v

    @Property(bool, notify=compactListRowsChanged)
    def compactListRows(self):  # type: ignore[reportRedeclaration]
        return self.ui.compactListRows

    @compactListRows.setter  # type: ignore[func-attr]
    def compactListRows(self, v):
        self.ui.compactListRows = v

    @Property(str, notify=shortcutsChanged)
    def shortcutSearch(self):
        return self.config_mgr.shortcutSearch

    @Property(str, notify=shortcutsChanged)
    def shortcutSelectAll(self):
        return self.config_mgr.shortcutSelectAll

    @Property(str, notify=shortcutsChanged)
    def shortcutClearSelection(self):
        return self.config_mgr.shortcutClearSelection

    @Property(str, notify=shortcutsChanged)
    def shortcutCopy(self):
        return self.config_mgr.shortcutCopy

    @Property(str, notify=shortcutsChanged)
    def shortcutRefresh(self):
        return self.config_mgr.shortcutRefresh

    @Property(str, notify=shortcutsChanged)
    def shortcutArchive(self):
        return self.config_mgr.shortcutArchive

    @Property(str, notify=shortcutsChanged)
    def shortcutDelete(self):
        return self.config_mgr.shortcutDelete

    @Property(str, notify=shortcutsChanged)
    def shortcutExpandAll(self):
        return self.config_mgr.shortcutExpandAll

    @Property(str, notify=shortcutsChanged)
    def shortcutCollapseAll(self):
        return self.config_mgr.shortcutCollapseAll

    @Property(str, notify=shortcutsChanged)
    def shortcutTopOfList(self):
        return self.config_mgr.shortcutTopOfList

    @Property(str, notify=shortcutsChanged)
    def shortcutQuickCopyView(self):
        return self.config_mgr.shortcutQuickCopyView

    @Property(str, notify=shortcutsChanged)
    def shortcutLibraryView(self):
        return self.config_mgr.shortcutLibraryView

    @Property(str, notify=shortcutsChanged)
    def shortcutUpdatesView(self):
        return self.config_mgr.shortcutUpdatesView

    @Property(str, notify=shortcutsChanged)
    def shortcutSettingsView(self):
        return self.config_mgr.shortcutSettingsView

    @Property(str, notify=shortcutsChanged)
    def shortcutThemeToggle(self):
        return self.config_mgr.shortcutThemeToggle

    @Property(str, notify=shortcutsChanged)
    def shortcutScreenshot(self):
        return self.config_mgr.shortcutScreenshot

    @Property(str, notify=currentViewChanged)
    def logoSource(self):
        return self.ui.logoSource

    @Property(list, notify=projectsChanged)
    def updateProjects(self):
        return self.config_mgr.updateProjects

    @Property(list, notify=clientFormatsChanged)
    def clientFormats(self):
        return self.config_mgr.clientFormats

    @Property(list, notify=customCollectionsChanged)
    def customCollections(self):
        return self.config_mgr.customCollections

    @Property(list, notify=projectsChanged)
    def projectLabels(self):
        return self.config_mgr.projectLabels

    # --- Proxy Slots (Temporary for QML compatibility) ---

    @Slot()
    def load_initial_data(self):
        self.loadInitialData()

    @Slot(str, result=str)
    def getLogoSource(self, f):
        return self.ui.getLogoSource(f)

    @Slot(str, result=str)
    def getAssetUri(self, p):
        return self.ui.getAssetUri(p)

    @Slot(str, str)
    def setViewFilter(self, k, v):
        self.ui.setViewFilter(k, v)

    @Slot(str, str, str)
    def setViewFilterForView(self, view, k, v):
        self.ui.setViewFilterForView(view, k, v)

    @Slot()
    def clearViewFilters(self):
        self.ui.clearViewFilters()

    @Slot(int)
    def selectSkill(self, i):
        self.ui.selectSkill(i)

    @Slot()
    def clearVisibleSelection(self):
        self.ui.clearVisibleSelection()

    @Slot()
    def selectAllVisibleSkills(self):
        self.ui.selectAllVisibleSkills()

    @Slot()
    def toggleAllVisibleCategories(self):
        self.ui.toggleAllVisibleCategories()

    @Slot(str)
    def launchSkill(self, p):
        self.ui.launchSkill(p)

    @Slot(str)
    def openPath(self, p):
        self.ui.openPath(p)

    @Slot()
    def resetUiState(self):
        self.ui.resetUiState()

    @Slot(str)
    def setClientFormat(self, f):
        self.ui.setClientFormat(f)

    @Slot(str)
    def setStartupView(self, v):
        self.ui.setStartupView(v)

    @Slot(bool)
    def setRememberFilters(self, b):
        self.ui.setRememberFilters(b)

    @Slot(bool)
    def setReducedMotion(self, b):
        self.ui.setReducedMotion(b)

    @Slot(bool)
    def setCompactListRows(self, b):
        self.ui.setCompactListRows(b)

    @Slot(str)
    def addSource(self, u):
        self.config_mgr.addSource(u)

    @Slot(str)
    def removeSource(self, p):
        self.config_mgr.removeSource(p)

    @Slot(int)
    def removeSourceByIndex(self, i):
        self.config_mgr.removeSourceByIndex(i)

    @Slot(str)
    def addProject(self, u):
        self.config_mgr.addProject(u)

    @Slot(str)
    def removeProject(self, p):
        self.config_mgr.removeProject(p)

    @Slot(int, int)
    def reorderProjects(self, from_index, to_index):
        self.config_mgr.reorderProjects(from_index, to_index)

    @Slot(int)
    def removeUpdateProject(self, i):
        self.config_mgr.removeUpdateProject(i)

    @Slot(str, str)
    def setProjectAlias(self, p, a):
        self.config_mgr.setProjectAlias(p, a)

    @Slot(str, str, result=str)
    def verifyGitPackage(self, u, t=None):
        return self.config_mgr.verifyGitPackage(u, t)

    @Slot(str, str)
    def setShortcut(self, a, s):
        self.config_mgr.setShortcut(a, s)

    @Slot()
    def resetShortcuts(self):
        self.config_mgr.resetShortcuts()

    @Slot(str, list, list)
    def saveCustomCollection(self, n, p, proj):
        self.config_mgr.saveCustomCollection(n, p, proj)

    @Slot(str)
    def deleteCustomCollection(self, n):
        self.config_mgr.deleteCustomCollection(n)

    @Slot(str)
    def applyCollectionSelection(self, n):
        self.config_mgr.applyCollectionSelection(n)

    @Slot(str, result=list)
    def getCollectionPaths(self, n):
        return self.config_mgr.getCollectionPaths(n)

    @Slot(str, result=list)
    def getCollectionProjects(self, n):
        return self.config_mgr.getCollectionProjects(n)

    @Slot(str, result=str)
    def checkMissingSkills(self, n):
        return self.config_mgr.checkMissingSkills(n)

    @Slot(str, list)
    def copyMissingSkills(self, n, projects):
        self.config_mgr.copyMissingSkills(n, projects)

    @Slot()
    def toggleCurrentSkillArchive(self):
        self.ops.toggleCurrentSkillArchive()

    @Slot()
    def toggleCurrentSkillStarred(self):
        self.ops.toggleCurrentSkillStarred()

    @Slot(str)
    def copySkillToClipboard(self, p):
        self.ops.copySkillToClipboard(p)

    @Slot()
    def copyCurrentSelectionOrFocusedSkill(self):
        self.ops.copyCurrentSelectionOrFocusedSkill()

    @Slot()
    def copySelectedSkillsToClipboard(self):
        self.ops.copySelectedSkillsToClipboard()

    @Slot(str)
    def copyTextToClipboard(self, c):
        self.ops.copyTextToClipboard(c)

    @Slot(dict, str)
    def copySkillReference(self, s, a=""):
        self.ops.copySkillReference(s, a)

    @Slot(str)
    def copyCollectionToClipboard(self, n):
        self.ops.copyCollectionToClipboard(n)

    @Slot(str)
    def deleteSkill(self, p):
        self.ops.deleteSkill(p)

    @Slot()
    def deleteSelectedSkills(self):
        self.ops.deleteSelectedSkills()

    @Slot()
    def archiveSelectedSkills(self):
        self.ops.archiveSelectedSkills()

    @Slot(str)
    def copySelectedSkillsToProject(self, p):
        self.ops.copySelectedSkillsToProject(p)

    @Slot(str)
    def copySelectedSkillsToProjectTemporarily(self, p):
        self.ops.copySelectedSkillsToProjectTemporarily(p)

    @Slot(str, str, str, str, str, str)
    def updateCustomCommandFull(self, lp, n, b, cat, proj, on_conflict=""):
        self.ops.updateCustomCommandFull(lp, n, b, cat, proj, on_conflict)

    @Slot(str, str)
    def notify_command_updated(self, old_path: str, new_path: str) -> None:
        self.commandUpdateCompleted.emit(old_path, new_path)

    @Slot(str, str, str, str)
    def createCustomCommand(self, n, b, pl, cat):
        self.ops.createCustomCommand(n, b, pl, cat)

    @Slot(str)
    def addToArchive(self, p):
        self.ops.addToArchive(p)

    @Slot()
    def updateNow(self):
        self.updates.updateNow()

    @Slot()
    def scanForUpdates(self):
        self.updates.scanForUpdates()

    @Slot()
    def updateAllOutdated(self):
        self.updates.updateAllOutdated()

    @Slot(str, str)
    def updateSkillInProject(self, s, p):
        self.updates.updateSkillInProject(s, p)

    @Slot(int)
    def runPackageUpdate(self, i):
        self.updates.runPackageUpdate(i)

    @Slot(str)
    def syncProject(self, p):
        self.updates.syncProject(p)

    @Slot(str)
    def addUpdatePackage(self, n):
        self.updates.addUpdatePackage(n)

    @Slot(dict, result=str)
    def addSkillPackage(self, d):
        return self.updates.addSkillPackage(d)

    @Slot(int, dict, result=str)
    def updateUpdatePackage(self, i, d):
        return self.updates.updateUpdatePackage(i, d)

    @Slot(int)
    def removeUpdatePackage(self, i):
        self.updates.removeUpdatePackage(i)

    @Slot(int)
    def clearPackageJustFinished(self, i):
        self.updates.clearPackageJustFinished(i)

    @Slot(str, str, str)
    def logDiagnostic(self, level: str, category: str, msg: str):
        """QML-callable diagnostic logger — emits to the structured ring buffer."""
        get_diagnostic_logger().log_event(level, category, msg)

    # --- Slots ---

    @Property(Qt.CheckState, notify=isPackageOnlyChanged)
    def isPackageOnly(self):  # type: ignore[reportRedeclaration]
        return self._library_model.isPackageOnly

    @isPackageOnly.setter  # type: ignore[func-attr]
    def isPackageOnly(self, value):
        self._library_model.isPackageOnly = value
        self._quick_copy_model.isPackageOnly = value
        self.isPackageOnlyChanged.emit()

    @Slot()
    def loadInitialData(self):
        self.discovery.loadInitialData()

    @Slot(str, str, str)
    def logDiagnosticEvent(self, level: str, category: str, msg: str):
        try:
            get_diagnostic_logger().log_event(level, category, msg)
        except Exception as e:
            logger.error(f"Failed to log QML diagnostic event: {e}")

    @Slot(str, result=str)
    def getCategoryEmoji(self, category_name: str) -> str:
        return get_category_emoji(category_name)

    @Slot()
    def refreshSkills(self):
        self._set_status("Refreshing library...")
        self.loadInitialData()

    def _on_client_format_changed(self):
        self._quick_copy_model.clientFilter = self._client_format
        self._library_model.clientFilter = self._client_format

    def _on_projects_changed(self):
        labels = self.config_mgr.projectLabels
        if self._current_project_label not in labels:
            self._current_project_label = labels[0] if labels else ""
            self.currentProjectChanged.emit()

    def _set_status(self, msg):
        if getattr(self, "_status_message", "") == msg:
            return
        self._status_message = msg
        self.statusMessageChanged.emit()
        logger.info(f"Status: {msg}")
        get_diagnostic_logger().log_event(
            "DEBUG",
            "status_message",
            msg,
        )

    # Forwarding helper for sub-controllers to access labels
    def getProjectLabel(self, path):
        return self.config_mgr.getProjectLabel(path)

    def _setup_global_hotkeys(self):
        """Register global hotkeys and connect signals."""
        # Connect hotkey signal to screenshot trigger
        # Use QueuedConnection because the signal is emitted from a background thread
        from PySide6.QtCore import Qt

        self.global_hotkey.hotkeyPressed.connect(
            self._on_global_hotkey, Qt.ConnectionType.QueuedConnection
        )

        # Register screenshot hotkey at startup (only if enabled)
        screenshot_seq = self.config_mgr.get_shortcut("screenshot")
        if screenshot_seq and self.config_mgr.isShortcutEnabled("screenshot"):
            self.global_hotkey.register(self._hotkey_id_screenshot, screenshot_seq)

        # Re-register when shortcuts change
        self.config_mgr.shortcutsChanged.connect(self._on_shortcuts_changed)

        # Start the listener thread
        self.global_hotkey.start()

    def _validate_source_paths(self):
        """Check configured source/project paths exist at startup.

        Logs warnings for missing directories so that users see early
        feedback instead of a silent cache-wipe on next discovery.
        """
        diag = get_diagnostic_logger()
        missing: list[str] = []
        for src in self._sources:
            if not os.path.isdir(src):
                missing.append(src)
                diag.log_event(
                    "WARNING",
                    CATEGORY_SOURCE_MISSING,
                    f"Source directory not found at startup: {src}",
                    data={"source_path": src},
                )
        for proj in self._projects:
            if not os.path.isdir(proj):
                missing.append(proj)
                diag.log_event(
                    "WARNING",
                    CATEGORY_SOURCE_MISSING,
                    f"Project directory not found at startup: {proj}",
                    data={"source_path": proj},
                )
        if missing:
            logger.warning(
                "[APP] %d configured source/project directories not found: %s",
                len(missing),
                missing,
            )
            self._set_status(f"Warning: {len(missing)} configured directory(ies) not found")

    @Slot(int)
    def _on_global_hotkey(self, hotkey_id: int):
        """Handle global hotkey press."""
        if hotkey_id == self._hotkey_id_screenshot:
            self.screenshot.takeScreenshot()

    def _on_shortcuts_changed(self):
        """Re-register global hotkeys when shortcuts are updated."""
        screenshot_seq = self.config_mgr.get_shortcut("screenshot")
        if screenshot_seq and self.config_mgr.isShortcutEnabled("screenshot"):
            self.global_hotkey.register(self._hotkey_id_screenshot, screenshot_seq)
        else:
            self.global_hotkey.unregister(self._hotkey_id_screenshot)

    def on_quit(self):
        """Ensures all pending state is saved before exit."""
        # Stop global hotkey listener
        if hasattr(self, "global_hotkey"):
            self.global_hotkey.stop()

        if hasattr(self, "_watcher"):
            self._watcher.stop()
        if hasattr(self, "_scheduler") and self._scheduler.running:
            self._scheduler.shutdown(wait=False)
        if self.ui._save_timer.isActive():
            self.ui._save_timer.stop()
            self.ui.saveUiState()

        # Flush Sentry manually with a timeout
        try:
            import sentry_sdk

            sentry_sdk.flush(timeout=2.0)
        except Exception as e:
            logger.debug(f"Sentry flush error: {e}")

        # PostHog shutdown has no timeout and can hang indefinitely on network issues.
        # Run it in a daemon thread and wait for a maximum of 1.5 seconds.
        import threading

        t = threading.Thread(target=posthog_shutdown, daemon=True)
        t.start()
        t.join(timeout=1.5)


def main():  # pragma: no cover
    # Initialize Sentry as early as possible
    sentry_sdk.init(
        dsn=os.environ.get("SENTRY_DSN", ""),  # Placeholder for user's DSN
        traces_sample_rate=0.1,
        profiles_sample_rate=0.1,
        environment="production" if getattr(sys, "frozen", False) else "development",
        release=f"skill-manager@{skill_manager.__version__}",
        default_integrations=False,
    )

    # Acquire mutex so Inno Setup installer can cleanly close the app
    global _app_mutex
    _app_mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "SkillManagerAppMutex")

    # Use a standard AppUserModelID format
    myappid = "Antigravity.SkillManager.App.1.0"
    if not getattr(sys, "frozen", False):
        # Development mode: Append .dev to distinguish from release builds.
        # Do NOT append a timestamp, as it breaks Windows taskbar icon grouping.
        myappid += ".dev"

    try:
        res = ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        logger.info(
            f"Windows: Pre-init SetCurrentProcessExplicitAppUserModelID('{myappid}') returned {res}"
        )
    except Exception as e:
        logger.error(f"Failed to set AppUserModelID: {e}")

    # Safety net: drop any stale Qt QML disk cache before loading QML.
    # Runs even when QML_DISABLE_DISK_CACHE=1 is honored (defense in depth).
    invalidate_qml_disk_cache_if_stale(skill_manager.__version__)

    QQuickStyle.setStyle("Basic")
    app = QGuiApplication(sys.argv)

    # Set application name and version for better shell integration
    app.setApplicationName("SkillManager")
    app.setApplicationVersion(skill_manager.__version__)
    app.setOrganizationName("Antigravity")
    app.setOrganizationDomain("antigravity.io")

    # Robust icon loading
    icon_ext = "ico"
    icon_candidates = [
        resolve_resource_path(f"assets/brand/logo.{icon_ext}"),
        os.path.join(os.path.dirname(__file__), "assets", "brand", f"logo.{icon_ext}"),
        os.path.join(os.path.abspath("."), "assets", "brand", f"logo.{icon_ext}"),
        # Fallbacks to png just in case
        resolve_resource_path("assets/brand/logo.png"),
        os.path.join(os.path.dirname(__file__), "assets", "brand", "logo.png"),
        os.path.join(os.path.abspath("."), "assets", "brand", "logo.png"),
    ]

    app_icon = QIcon()
    loaded_icon = False
    loaded_icon_path = ""
    for icon_path in icon_candidates:
        if os.path.exists(icon_path):
            app_icon = QIcon(icon_path)
            if not app_icon.isNull():
                app.setWindowIcon(app_icon)
                logger.info(f"Successfully loaded and set application icon from: {icon_path}")
                loaded_icon = True
                loaded_icon_path = icon_path
                break
            logger.warning(f"QIcon failed to load existing file: {icon_path}")
        else:
            logger.debug(f"Icon candidate not found: {icon_path}")

    if not loaded_icon:
        logger.error("CRITICAL: All icon candidates failed to load.")
        # Check if PNG is even supported
        from PySide6.QtGui import QImageReader

        formats = [f.data().decode() for f in QImageReader.supportedImageFormats()]  # type: ignore[attr-defined]
        logger.info(f"Supported image formats: {formats}")
        if "png" not in formats:
            logger.error("PNG format is NOT supported by this PySide6 installation!")
    controller = AppController()
    # PySide6 6.11.0's type stub claims ``qml_name`` is ``bytes | bytearray |
    # memoryview[int]`` but the runtime actually requires ``str`` (which it
    # auto-encodes internally) and raises ``TypeError`` on ``bytes``. The
    # stub-vs-runtime mismatch is a known PySide6 limitation; suppress it
    # per-call so the running app keeps working.
    qmlRegisterSingletonInstance(
        AppController,
        "App",
        1,
        0,
        "AppController",  # type: ignore[arg-type]
        controller,
    )
    app.aboutToQuit.connect(controller.on_quit)

    # Register FontDatabaseBridge BEFORE the QQmlApplicationEngine is created.
    # Registering singleton QObject types after `engine = QQmlApplicationEngine()`
    # but before `engine.load()` interacts badly with the engine's type cache for
    # locally-registered QML components, surfacing as
    # "Cannot assign object of type X to list property 'data'; expected 'QObject'"
    # during Main.qml load.
    font_bridge = FontDatabaseBridge()
    qmlRegisterSingletonInstance(FontDatabaseBridge, "App", 1, 0, "FontDB", font_bridge)  # type: ignore[arg-type]

    engine = QQmlApplicationEngine()
    engine.addImageProvider("screenshot", controller.screenshot_provider)
    engine.rootContext().setContextProperty("appController", controller)
    engine.rootContext().setContextProperty("fontDB", font_bridge)
    engine.warnings.connect(_handle_qml_warning)

    qml_dir = qml_components_dir(package_file=__file__)
    engine.addImportPath(str(qml_dir.parent))
    qml_file = qml_dir / "Main.qml"
    engine.load(str(qml_file))
    if not engine.rootObjects():
        logger.error("CRITICAL: Failed to load QML root objects!")
        sys.exit(-1)
    diag = get_diagnostic_logger()
    diag.log_event(
        "INFO", "window_state", f"QML loaded, {len(engine.rootObjects())} root object(s)"
    )
    capture_event("app_opened")

    # Clamp window geometry to visible screen area to prevent off-screen windows.
    # Saved coordinates from a previous multi-monitor setup may be invalid if
    # the monitor was disconnected.
    screen = app.primaryScreen()
    if screen:
        geo = screen.availableGeometry()
        screen_x, screen_y = geo.x(), geo.y()
        screen_w, screen_h = geo.width(), geo.height()
        diag.log_event(
            "INFO",
            "window_state",
            f"Screen geometry: ({screen_x}, {screen_y}, {screen_w}, {screen_h})",
        )
        for root in engine.rootObjects():
            r: Any = root
            win_x, win_y = r.x(), r.y()
            win_w, win_h = r.width(), r.height()
            # Clamp so the window is at least partially visible
            new_x = max(screen_x, min(win_x, screen_x + screen_w - max(win_w, 100)))
            new_y = max(screen_y, min(win_y, screen_y + screen_h - max(win_h, 100)))
            if new_x != win_x or new_y != win_y:
                diag.log_event(
                    "WARN",
                    "window_state",
                    f"Window off-screen at ({win_x}, {win_y}) — clamping to ({new_x}, {new_y})",
                )
                r.setX(new_x)
                r.setY(new_y)

    # Explicitly set icon on each QML window — QGuiApplication.setWindowIcon()
    # doesn't reliably propagate to QML Window elements with FramelessWindowHint.
    if not app_icon.isNull():
        for i, root in enumerate(engine.rootObjects()):
            # ``engine.rootObjects()`` returns ``list[QObject]`` per the stub,
            # but QML roots are actually ``QWindow``/``QQuickWindow`` which
            # expose ``setIcon``/``show``/``winId``. Cast through ``Any`` so
            # pyright agrees with the runtime.
            root_any: Any = root
            root_any.setIcon(app_icon)
            if hasattr(root, "show"):
                root_any.show()
                diag.log_event(
                    "INFO",
                    "window_state",
                    f"Called root.show() on root {i} (visible={getattr(root, 'isVisible', lambda: 'unknown')()})",
                )

    def apply_native_styles():
        diag.log_event(
            "INFO",
            "window_state",
            f"apply_native_styles: processing {len(engine.rootObjects())} root object(s)",
        )
        dark = bool(controller.ui.darkMode)
        for root in engine.rootObjects():
            try:
                hwnd = int(root.winId())  # type: ignore[attr-defined]
                if HAS_PYWINSTYLES and pywinstyles is not None:
                    pywinstyles.apply_style(hwnd, "mica")
                    _apply_immersive_dark(hwnd, dark)
                    ctypes.windll.dwmapi.DwmSetWindowAttribute(
                        hwnd, 33, ctypes.byref(ctypes.c_int(2)), 4
                    )

                # Force native Windows taskbar icon via Win32 API.
                # LoadImageW with LR_LOADFROMFILE supports both ICO and PNG on Windows 10+.
                if loaded_icon_path:
                    WM_SETICON = 0x0080
                    ICON_SMALL = 0
                    ICON_BIG = 1
                    LR_LOADFROMFILE = 0x0010
                    IMAGE_ICON = 1

                    hIconSm = ctypes.windll.user32.LoadImageW(
                        None, loaded_icon_path, IMAGE_ICON, 16, 16, LR_LOADFROMFILE
                    )
                    if hIconSm:
                        ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, hIconSm)

                    hIconLg = ctypes.windll.user32.LoadImageW(
                        None, loaded_icon_path, IMAGE_ICON, 32, 32, LR_LOADFROMFILE
                    )
                    if hIconLg:
                        ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, hIconLg)
            except Exception as e:
                logger.error(f"Failed to apply native style/icon: {e}")

    QTimer.singleShot(0, apply_native_styles)

    def _reapply_immersive_dark_from_dark_mode() -> None:
        """Re-apply the DWM immersive-dark attribute when darkMode changes."""
        dark = bool(controller.ui.darkMode)
        for root in engine.rootObjects():
            try:
                hwnd = int(root.winId())  # type: ignore[attr-defined]
                _apply_immersive_dark(hwnd, dark)
            except Exception as e:
                diag.log_event(
                    "WARN",
                    "window_state",
                    f"Immersive-dark re-apply skipped for root: {e}",
                )

    controller.ui.darkModeChanged.connect(_reapply_immersive_dark_from_dark_mode)

    def _check_window_visible():
        for i, root in enumerate(engine.rootObjects()):
            try:
                r: Any = root
                vis = r.isVisible()
                x, y, w, h = r.x(), r.y(), r.width(), r.height()
                diag.log_event(
                    "INFO",
                    "window_state",
                    f"Watchdog: root {i} visible={vis}, geometry=({x}, {y}, {w}, {h})",
                )
                if not vis:
                    diag.log_event(
                        "WARN",
                        "window_state",
                        f"Watchdog: root {i} NOT VISIBLE after 5s — forcing show",
                    )
                    r.show()
                    r.raise_()
                    r.requestActivate()
            except Exception as e:
                diag.log_event("ERROR", "window_state", f"Watchdog error: {e}")

    QTimer.singleShot(5000, _check_window_visible)

    ret = app.exec()
    # Force exit to prevent background threads (like concurrent.futures or watchdog) from hanging shutdown
    os._exit(ret)


if __name__ == "__main__":
    main()

"""
Purpose: Main entry point for Skill Manager (PySide6 version).
Usage: python run.py
"""

import os
import sys
import threading
import time
from pathlib import Path
from typing import Any

# Suppress all Python warnings (especially loky resource_tracker warnings in child processes)
os.environ["PYTHONWARNINGS"] = "ignore"

import sentry_sdk
from apscheduler.schedulers.qt import QtScheduler  # type: ignore[reportMissingImports]
from PySide6.QtCore import (  # noqa: E402
    Property,
    QObject,
    Qt,
    QTimer,
    Signal,
    Slot,
)
from PySide6.QtGui import QGuiApplication  # noqa: E402
from PySide6.QtQml import QQmlApplicationEngine  # noqa: E402
from PySide6.QtQuick import QQuickWindow  # noqa: E402

# Phase 1 decomposition: modules extracted from app.py keep their public
# surface alive through these re-exports (see .omo/plans/refactor-codebase.md).
# noqa: F401 below marks intentional re-exports that are not used in this file.
# Shared with bootstrap.py so tests patching skill_manager.app.logger also
# intercept the moved startup/shutdown code (e.g. _handle_qml_warning).
from skill_manager.bootstrap import (  # noqa: E402, F401
    _handle_qml_warning,
    logger,  # noqa: E402, F401
    run_gui as main,
)
from skill_manager.controllers.app_proxies import AppControllerProxyMixin  # noqa: E402
from skill_manager.controllers.app_update_controller import AppUpdateController  # noqa: E402
from skill_manager.controllers.command_channel import CommandChannel  # noqa: E402
from skill_manager.controllers.config_controller import ConfigController  # noqa: E402
from skill_manager.controllers.discovery_controller import DiscoveryController  # noqa: E402
from skill_manager.controllers.font_database_bridge import FontDatabaseBridge  # noqa: E402, F401
from skill_manager.controllers.image_inspector_controller import (  # noqa: E402
    ImageInspectorController,
)
from skill_manager.controllers.ops_controller import OpsController  # noqa: E402
from skill_manager.controllers.selected_skill_controller import (  # noqa: E402
    SelectedSkillController,
)
from skill_manager.controllers.snap_controller import SnapController  # noqa: E402
from skill_manager.controllers.ui_controller import UIController  # noqa: E402
from skill_manager.controllers.update_controller import UpdateController  # noqa: E402
from skill_manager.core.analytics import shutdown as posthog_shutdown  # noqa: E402
from skill_manager.core.categories import get_category_emoji  # noqa: E402
from skill_manager.core.config import (  # noqa: E402
    ConfigManager,
    ScopedConfigManager,
    migrate_scoped_filter_keys,
)
from skill_manager.core.diagnostics import (  # noqa: E402
    CATEGORY_SOURCE_MISSING,
    get_diagnostic_logger,
)
from skill_manager.core.file_watch import SkillFolderWatcher  # noqa: E402
from skill_manager.core.global_hotkey import GlobalHotkeyManager  # noqa: E402
from skill_manager.core.image_provider import SnapImageProvider  # noqa: E402
from skill_manager.core.models import SkillModel  # noqa: E402
from skill_manager.core.persistence import (  # noqa: E402
    load_archive,
    load_starred,
)
from skill_manager.core.schemas import UpdatePackageRecord  # noqa: E402
from skill_manager.utils.clipboard_service import ClipboardService  # noqa: E402
from skill_manager.utils.native_styling import (  # noqa: E402
    DWMWA_USE_IMMERSIVE_DARK_MODE,  # noqa: F401
    HAS_PYWINSTYLES,  # noqa: F401
    _apply_immersive_dark,  # noqa: F401
    pywinstyles,  # noqa: F401
)
from skill_manager.utils.shutdown import dump_diagnostics  # noqa: E402
from skill_manager.utils.single_instance import release_lock  # noqa: E402
from skill_manager.utils.task_runner import BackgroundTaskRunner  # noqa: E402


class AppController(AppControllerProxyMixin, QObject):
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
    lastProjectChanged = Signal()
    clientFormatChanged = Signal()
    categoriesChanged = Signal()
    clientFormatsChanged = Signal()
    defaultClientChanged = Signal()
    customCollectionsChanged = Signal()
    updateResultsChanged = Signal()
    updatePackagesChanged = Signal()
    isPackageOnlyChanged = Signal()

    # QML engine — set by main() after construction. Used by CommandChannel._capture_screenshot
    # to grab the live window via QQuickWindow::grabWindow() (works minimised, no colour cast).
    _qml_engine: QQmlApplicationEngine | None = None

    # Debug overlay — toggled via CLI --debug-overlay or MCP sm_toggle_debug_overlay.
    debugOverlayEnabledChanged = Signal()

    @Property(bool, notify=debugOverlayEnabledChanged)
    def debugOverlayEnabled(self):  # type: ignore[no-redef]
        return self._debug_overlay_enabled

    @debugOverlayEnabled.setter  # type: ignore[func-attr,no-redef]
    def debugOverlayEnabled(self, val):
        if self._debug_overlay_enabled != val:
            self._debug_overlay_enabled = val
            self._config.set("debug_overlay_enabled", val)
            self.debugOverlayEnabledChanged.emit()

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
    commandUpdateConflict = Signal(str, str, str)  # oldPath, conflictPath, suggestedRename
    commandUpdateCompleted = Signal(str, str)  # oldPath, newPath
    commandSkillsCarryPrompt = Signal(str, str, str)
    commandPendingRemovals = Signal(str, list)

    def __init__(self, skip_initial_load=False, config=None):
        super().__init__()
        # 1. Core Models and Configuration
        self._config = config if config else ConfigManager()
        self.task_runner = BackgroundTaskRunner()

        # Migrate legacy un-namespaced filter keys to per-model namespaces
        migrate_scoped_filter_keys(self._config)

        # Create scoped configs so library and quick_copy models don't share filter state
        self._library_config = ScopedConfigManager(self._config, "library")
        self._quick_copy_config = ScopedConfigManager(self._config, "quickcopy")

        self._library_model = SkillModel(config=self._library_config)
        self._quick_copy_model = SkillModel(config=self._quick_copy_config)

        # 2. Basic Attribute Initialization
        # Live-bound QObject subscribing to model dataChanged, not a stale QMap.
        self._selected_skill = SelectedSkillController(self)
        self._is_loading = False
        self._status_message = ""
        # Startup debug-overlay flag: --debug-overlay enables the ribbon debug
        # overlay in QuickCopyView without needing the MCP toggle.
        self._debug_overlay_enabled = "--debug-overlay" in sys.argv
        self._discovered_projects = []
        self._last_poll_ts = 0.0
        self._categories = []
        self._clipboard = QGuiApplication.clipboard()
        self.clipboard_service = ClipboardService(
            self._clipboard,
            prefer_native=sys.platform == "linux",
        )

        default_client = self._config.get("default_client", "Last Selected")
        if default_client == "Last Selected":
            self._client_format = self._get_last_selected_client()
        else:
            self._client_format = default_client

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

        # Boot-normalize: rewrite any stored project, source, and package paths
        # so that paths are healthy, canonical, and self-healed on startup.
        self._normalize_paths_on_startup()

        # Shared project state (syncs across all project selectors)
        self._current_project_label = ""

        # Second project slot enabling the top-bar cycle button to toggle
        # back and forth between the two most-recently-used projects.
        self._last_project_label = self._config.get("last_project_label", "")

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

        # Navigation IPC channel for the MCP sm_screenshot tool (file-based).
        # Guarded: degrades to None if the watcher/dirs cannot be set up
        # (headless/CI), so it never crashes AppController.
        try:
            self.command_channel = CommandChannel(self)
        except Exception as exc:  # noqa: BLE001
            logger.warning("CommandChannel init failed: %s", exc)
            self.command_channel = None
        self.config_mgr = ConfigController(self)  # type: ignore[arg-type]
        self.ops = OpsController(self)  # type: ignore[arg-type]
        self.snap_provider = SnapImageProvider()
        self.snap = SnapController(self)  # type: ignore[arg-type]
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

        self.ops.commandPendingRemovals.connect(self.commandPendingRemovals.emit)
        self.ops.commandSkillsCarryPrompt.connect(self.commandSkillsCarryPrompt.emit)

        # 5. Lifecycle Hooks
        self.ops.cleanup_temp_copies()  # Crash recovery
        self.ops.cleanup_temp_snaps()  # Crash recovery
        app_inst = QGuiApplication.instance()
        if app_inst:
            app_inst.aboutToQuit.connect(self.ops.cleanup_temp_copies)
            app_inst.aboutToQuit.connect(self.ops.cleanup_temp_snaps)

        # 6. Global Hotkey Setup (snap hotkey works when app is minimized)
        self._setup_global_hotkeys()

        # 4. Initial Model Configuration
        self._library_model.showCommands = False
        # PySide6's ``isPackageOnly`` setter accepts ``Qt.CheckState | bool``;
        # pyright's stub only exposes ``Qt.CheckState``, so the ``True``/
        # ``False`` literals are flagged.
        self._library_model.isPackageOnly = True  # type: ignore[arg-type]
        self._library_model.showStarred = True
        self._library_model.filterByClient = True

        self._quick_copy_model._begin_batch()
        try:
            self._quick_copy_model.showCommands = True
            self._quick_copy_model.isPackageOnly = False  # type: ignore[arg-type]
            self._quick_copy_model.showStarred = True
            self._quick_copy_model.filterByClient = True
        finally:
            self._quick_copy_model._end_batch()

        # Reactive client filter: sync model filters when user selects a different client
        self.clientFormatChanged.connect(self._on_client_format_changed)
        self._on_client_format_changed()

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
        # The debounce timer coalesces rapid filesystem events into a single
        # refresh, preventing repeated scans when the watcher fires many
        # events in quick succession.
        self._watcher_debounce_timer = QTimer()
        self._watcher_debounce_timer.setSingleShot(True)
        self._watcher_debounce_timer.setInterval(400)  # ms
        self._watcher_debounce_timer.timeout.connect(
            lambda: self.refreshSkills("file-watcher", False)
        )

        watch_paths = self._sources.copy()
        for src in self._update_packages:
            pkg_path = (
                src.get("resolved_package_path") or src.get("package_path") or src.get("local_path")
            )
            if pkg_path:
                watch_paths.append(pkg_path)

        self._watcher = SkillFolderWatcher(
            paths=watch_paths,
            callback=lambda _: self._watcher_debounce_timer.start(),
        )

        # In tests, we often want to skip the initial background discovery
        skip_initial = skip_initial_load or os.environ.get("SKILL_MANAGER_SKIP_INITIAL_LOAD") == "1"

        # Validate source paths at startup — warn early if directories are missing
        if not skip_initial:
            self._validate_source_paths()

        if not skip_initial:
            self._watcher.start()
            QTimer.singleShot(100, self.loadInitialData)

            # Stat-polling safety net: check known skill paths every 30s
            # to catch deletions that watchdog may miss on Windows.
            self._poll_timer = QTimer()
            self._poll_timer.timeout.connect(self._poll_known_paths)
            self._poll_timer.start(30_000)

            # Skill Package Update Scheduler
            self._scheduler = QtScheduler()
            self._scheduler.start()

            # Initial Startup Check
            if self._config.get("skill_package_auto_update_mode", "prompt") != "off":
                QTimer.singleShot(2000, self._run_startup_package_scan)
            self.config_mgr.skillPackageAutoUpdateModeChanged.connect(
                self._update_package_scheduler
            )

    def _normalize_paths_on_startup(self):
        """Rewrite stored project, source, and skill package paths to their canonical form and auto-repair malformed paths.

        If a stored path contains duplicated prefix artifacts or missing leading slashes,
        auto-repairs it so that the user's config stays healthy.
        """
        from skill_manager.core.copier import (
            get_skills_dir,
            repair_malformed_path,
            url_to_local_path,
        )
        from skill_manager.core.skill_packages import (
            resolve_package_storage,
        )

        if os.environ.get("SKILL_MANAGER_SKIP_INITIAL_LOAD") == "1":
            return

        # 1. Projects normalization
        projects = getattr(self, "_projects", None)
        if projects:
            changed_projects = False
            normalized_projects = []
            for project_path in projects:
                try:
                    clean_path = url_to_local_path(project_path)
                    repaired = repair_malformed_path(clean_path)
                    if repaired != clean_path:
                        logger.info(
                            "Boot self-healing: repaired malformed project path %r -> %r",
                            project_path,
                            repaired,
                        )
                        clean_path = repaired
                        changed_projects = True

                    canonical = get_skills_dir(clean_path)
                    canonical_str = str(canonical)

                    cand_p = Path(canonical_str)
                    if not cand_p.exists() and not any(
                        p.is_dir() for p in cand_p.parents if len(p.parts) > 1
                    ):
                        logger.warning(
                            "Boot self-healing: removing non-existent stale project path %r",
                            project_path,
                        )
                        changed_projects = True
                        continue

                    if canonical_str != project_path:
                        logger.info("Boot normalization: %r -> %r", project_path, canonical_str)
                        normalized_projects.append(canonical_str)
                        changed_projects = True
                    else:
                        normalized_projects.append(project_path)
                except Exception as exc:
                    logger.warning("Boot normalization failed for %r: %s", project_path, exc)
                    normalized_projects.append(project_path)

            if changed_projects:
                self._projects = normalized_projects
                self._config.set("projects", self._projects)

        # 2. Sources normalization
        sources = getattr(self, "_sources", None)
        if sources:
            changed_sources = False
            normalized_sources = []
            for source_path in sources:
                try:
                    clean_path = url_to_local_path(source_path)
                    repaired = repair_malformed_path(clean_path)
                    if repaired != source_path:
                        logger.info(
                            "Boot self-healing: repaired malformed source path %r -> %r",
                            source_path,
                            repaired,
                        )
                        normalized_sources.append(repaired)
                        changed_sources = True
                    else:
                        normalized_sources.append(source_path)
                except Exception as exc:
                    logger.warning("Boot normalization failed for source %r: %s", source_path, exc)
                    normalized_sources.append(source_path)

            if changed_sources:
                self._sources = normalized_sources
                self._config.set("sources", self._sources)

        # 3. Skill Packages normalization
        update_packages = getattr(self, "_update_packages", None)
        if update_packages:
            try:
                refreshed = resolve_package_storage(update_packages)
                # Semantic comparison: only fields that affect storage behaviour.
                # Transient keys like "_previous_resolved_package_path" must be
                # ignored otherwise every boot appears dirty.
                SEMANTIC_KEYS = {
                    "package_path",
                    "resolved_package_path",
                    "local_path",
                    "storage_mode",
                    "configured_package_path",
                    "clone_path",
                    "package_id",
                    "name",
                }
                changed_packages = False
                for i, item in enumerate(refreshed):
                    if i < len(self._update_packages):
                        old = self._update_packages[i]
                        old_sem = {k: old.get(k) for k in SEMANTIC_KEYS}
                        new_sem = {k: item.get(k) for k in SEMANTIC_KEYS}
                        if old_sem != new_sem:
                            changed_packages = True
                            diff_keys = [
                                k for k in SEMANTIC_KEYS if old_sem.get(k) != new_sem.get(k)
                            ]
                            for k in diff_keys:
                                logger.info(
                                    "Boot self-healing: package[%d] field %r changed %r -> %r",
                                    i,
                                    k,
                                    old_sem.get(k),
                                    new_sem.get(k),
                                )
                            # Extra detail for the two most relevant fields at INFO
                            if "resolved_package_path" in diff_keys or "storage_mode" in diff_keys:
                                logger.debug(
                                    "Boot self-healing detail package[%d] resolved %r -> %r storage_mode %r -> %r",
                                    i,
                                    old.get("resolved_package_path"),
                                    item.get("resolved_package_path"),
                                    old.get("storage_mode"),
                                    item.get("storage_mode"),
                                )
                        self._update_packages[i].clear()
                        self._update_packages[i].update(item)
                    else:
                        logger.info(
                            "Boot self-healing: package[%d] new entry added %r",
                            i,
                            {k: item.get(k) for k in SEMANTIC_KEYS},
                        )
                        self._update_packages.append(item)
                        changed_packages = True
                if changed_packages:
                    logger.info("Boot self-healing: normalized skill package storage paths")
                    self._config.set("skills", self._update_packages)
            except Exception as exc:
                logger.warning("Boot normalization failed for skill packages: %s", exc)

    # Backward compatibility alias
    _normalize_project_paths_on_startup = _normalize_paths_on_startup

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

    @Property(OpsController, constant=True)
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
    def snap_controller(self):
        return self.snap

    @Property(QObject, constant=True)
    def image_inspector_controller(self):
        return self.image_inspector

    @Property(QObject, constant=True)
    def global_hotkey_controller(self):
        return self.global_hotkey

    @Property(str, notify=currentProjectChanged)
    def currentProject(self):  # type: ignore[reportRedeclaration]
        return self._current_project_label

    @currentProject.setter  # type: ignore[func-attr]
    def currentProject(self, label):
        self.setCurrentProject(label)

    @Property(str, notify=lastProjectChanged)
    def lastProject(self):
        return self._last_project_label

    @Slot(str)
    def setCurrentProject(self, label):
        self._set_current_project(label, record_last=True)

    def _set_current_project(self, label, record_last=True):
        old = self._current_project_label
        if old == label:
            return
        # Only a switch between two valid projects updates the "last" slot,
        # so the cycle button always toggles between real projects.
        if (
            record_last
            and old
            and label
            and old in self.config_mgr.projectLabels
            and label in self.config_mgr.projectLabels
            and old != label
        ):
            self._set_last_project(old)
        if label and label not in self.config_mgr.projectLabels:
            logger.warning(
                "setCurrentProject: label %r not in projectLabels; "
                "filter will show an empty list until a valid project is selected",
                label,
            )
        self._current_project_label = label
        self._quick_copy_model.projectFilter = label
        self.currentProjectChanged.emit()

    def _set_last_project(self, label):
        if self._last_project_label == label:
            return
        self._last_project_label = label
        self._config.set("last_project_label", label)
        self.lastProjectChanged.emit()

    @Slot()
    def cycleProject(self):
        """Toggle the current project with the previously-selected one."""
        last = self._last_project_label
        if not last:
            logger.info("cycleProject: no previous project to switch to")
            return
        if last not in self.config_mgr.projectLabels:
            # Stale reference (e.g. project removed) — clear it.
            self._set_last_project("")
            return
        current = self._current_project_label
        self._last_project_label = current
        self._config.set("last_project_label", current)
        self.lastProjectChanged.emit()
        self._current_project_label = last
        self._quick_copy_model.projectFilter = last
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

    @Property(QObject, notify=selectedSkillChanged)
    def selectedSkill(self):
        return self._selected_skill

    def set_selected_skill(self, skill_dict: dict[str, Any]) -> None:
        """Populate the selected skill via SelectedSkillController."""
        if skill_dict:
            self._selected_skill.setSelection(skill_dict)
        else:
            self._selected_skill.clearSelection()
        self.selectedSkillChanged.emit()

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

    def _get_last_selected_client(self) -> str:
        return (
            self._config.get("client_format")
            or self._config.get("quickcopy.client_format")
            or self._config.get("library.client_format")
            or "Antigravity"
        )

    @Slot(str)
    def setDefaultClient(self, f):
        if self.defaultClient != f:
            self._config.set("default_client", f)
            self.defaultClientChanged.emit()
            target_fmt = self._get_last_selected_client() if f == "Last Selected" else f
            if self._client_format != target_fmt:
                self._client_format = target_fmt
                self.clientFormatChanged.emit()
                if hasattr(self, "ui") and self.ui:
                    self.ui.currentViewChanged.emit()

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
    def shortcutSnap(self):
        return self.config_mgr.shortcutSnap

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

    # --- Slots ---

    @Property(Qt.CheckState, notify=isPackageOnlyChanged)
    def isPackageOnly(self):  # type: ignore[reportRedeclaration]
        return self._library_model.isPackageOnly

    @Slot()
    def loadInitialData(self, force_full_scan: bool = False):
        self.discovery.loadInitialData(force_full_scan=force_full_scan, silent=True)

    @Slot()
    def rebuildCache(self):
        """Delete all on-disk caches and trigger a full re-discovery.

        Clears both the JSON index and the granular diskcache directory
        so that stale skills (deleted on disk but still in cache) are
        properly removed.  Resets in-memory state so the next discovery
        produces a full diff.

        All cache-clearing and re-discovery runs in a background thread
        to keep the UI fully fluid.

        Accessible from Settings > Maintenance.
        """
        from skill_manager.core.diagnostics import (
            CATEGORY_CACHE_REBUILD_ASYNC,
            get_diagnostic_logger,
        )

        diag = get_diagnostic_logger()
        diag.log_event("INFO", CATEGORY_CACHE_REBUILD_ASYNC, "Cache rebuild requested")

        # Cancel any in-flight refresh and clear in-memory state
        self.discovery.cancel_inflight()
        if hasattr(self, "discovery"):
            self.discovery._previous_skills = {}

        def _clear_and_rebuild():
            """Background: clear caches then run a fresh discovery."""
            from skill_manager.core.config import SKILL_LIBRARY_CACHE_FILE

            # 1. Delete JSON index cache
            cache_path = os.path.join(SKILL_LIBRARY_CACHE_FILE)
            if os.path.exists(cache_path):
                try:
                    os.remove(cache_path)
                    logger.info("[CACHE] Deleted JSON index: %s", cache_path)
                except OSError as e:
                    logger.warning("[CACHE] Failed to delete JSON index: %s", e)

            # 2. Clear granular diskcache (discovery fingerprints + parsed results)
            try:
                from skill_manager.core.discovery import get_discovery_cache

                with get_discovery_cache() as dc:
                    dc.clear()
                logger.info("[CACHE] Cleared granular discovery cache")
            except Exception as e:
                logger.warning("[CACHE] Failed to clear discovery cache: %s", e)

            # 3. Run full discovery from the background thread
            self.discovery.loadInitialData(force_full_scan=True, silent=True)

        self.task_runner.run(_clear_and_rebuild)

    @Slot(str, str, str)
    def logDiagnosticEvent(self, level: str, category: str, msg: str):
        try:
            get_diagnostic_logger().log_event(level, category, msg)
        except Exception as e:
            logger.error(f"Failed to log QML diagnostic event: {e}")

    @Slot(str, result=str)
    def getCategoryEmoji(self, category_name: str) -> str:
        return get_category_emoji(category_name)

    @Slot(str, bool)
    def refreshSkills(self, source: str, force_full_scan: bool):
        """Trigger a silent background refresh.

        The refresh runs entirely in a background thread.  No ``isLoading``
        flag is set and no status message is shown — the UI stays fluid.
        Any in-flight refresh is cancelled and replaced.
        """
        logger.info(
            "[REFRESH] Triggering re-discovery (source=%s, force_full_scan=%s)",
            source,
            force_full_scan,
        )
        self.discovery.cancel_inflight()
        self.discovery.loadInitialData(force_full_scan=force_full_scan, silent=True)

    def _poll_known_paths(self) -> None:
        """Stat-polling safety net: check if known skill paths still exist.

        Catches deletions that watchdog may miss on Windows (recursive
        watching unreliability, event coalescing, etc.).  If any known
        path is missing, triggers a full refresh.  Runs every 30s via
        ``_poll_timer``; cost is negligible (~8.5ms for 1700 skills).

        Includes 5-second debounce to prevent the poll from triggering
        refreshes in a tight loop when the deletion is detected but the
        discovery hasn't yet propagated the removal to the model.
        """
        try:
            now = time.monotonic()
            if now - self._last_poll_ts < 5.0:
                return
            self._last_poll_ts = now

            known = self._quick_copy_model.get_known_paths()
            if not known:
                return
            missing = [p for p in known if not os.path.exists(p)]
            if missing:
                logger.info(
                    "[POLL] Detected %d missing skill path(s), triggering refresh: %s",
                    len(missing),
                    missing[:5],
                )
                self.refreshSkills("stat-poll", True)
        except Exception:
            logger.debug("[POLL] Exception during path polling", exc_info=True)

    def _on_client_format_changed(self):
        self._quick_copy_model.clientFilter = self._client_format
        self._library_model.clientFilter = self._client_format

    def _on_projects_changed(self):
        labels = self.config_mgr.projectLabels
        if self._current_project_label not in labels:
            self._current_project_label = labels[0] if labels else ""
            self.currentProjectChanged.emit()

    @Slot(str)
    def _set_status(self, msg):
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

    @property
    def _is_recording_shortcut(self) -> bool:
        return getattr(self.config_mgr, "_is_recording_shortcut", False)

    @_is_recording_shortcut.setter
    def _is_recording_shortcut(self, value: bool) -> None:
        self.config_mgr._is_recording_shortcut = value

    @property
    def _hotkey_id_snap(self) -> int:
        return self.global_hotkey._snap_hotkey_id

    def _setup_global_hotkeys(self):
        """Register global hotkeys and connect signals."""
        self.global_hotkey.setup_snap_hotkey(
            config_controller=self.config_mgr,
            snap_controller=self.snap,
            get_window_active=self._main_window_is_focused,
        )

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
        """Handle global hotkey press (delegates to GlobalHotkeyManager)."""
        self.global_hotkey._on_snap_hotkey_pressed(hotkey_id)

    def _main_window_is_focused(self) -> bool:
        """Return whether the main QML window currently has focus."""
        engine = getattr(self, "_qml_engine", None)
        if engine is None:
            return False
        roots = engine.rootObjects()
        if not roots:
            return False
        window = roots[0]
        if not isinstance(window, QQuickWindow):
            return False
        return window.isActive()

    def _on_shortcuts_changed(self):
        """Re-register global hotkeys when shortcuts are updated (delegates to GlobalHotkeyManager)."""
        self.global_hotkey._on_shortcuts_changed_snap()

    def on_quit(self):
        """Ensures all pending state is saved before exit.

        Called via ``app.aboutToQuit`` during the Qt event loop shutdown.
        Must not do heavy blocking I/O — those go in ``cleanup()``.
        """
        sys.__dict__["is_shutting_down"] = True
        logger.debug("[SHUTDOWN] on_quit entered")
        dump_diagnostics("on_quit enter")

        # Stop global hotkey listener (idempotent, safe to call multiple times)
        if hasattr(self, "global_hotkey"):
            self.global_hotkey.stop()

        # Release CommandChannel watcher/timer — QFileSystemWatcher holds an
        # inotify instance; without this every controller leaks one (system-wide
        # "inotify instance limit reached" when many are created, e.g. in tests).
        if hasattr(self, "command_channel") and self.command_channel is not None:
            self.command_channel.stop()

        # Stop periodic timers (watcher debounce + known-paths poll).
        for timer in ("_watcher_debounce_timer", "_poll_timer"):
            if hasattr(self, timer):
                getattr(self, timer).stop()

        if hasattr(self, "_watcher"):
            self._watcher.stop()
        if hasattr(self, "_scheduler") and self._scheduler.running:
            self._scheduler.shutdown(wait=False)
        if (
            hasattr(self, "ui")
            and hasattr(self.ui, "_save_timer")
            and self.ui._save_timer.isActive()
        ):
            self.ui._save_timer.stop()
            self.ui.saveUiState()

        # Flush pending model selections and collapsed category states to disk
        for model in (
            getattr(self, "_library_model", None),
            getattr(self, "_quick_copy_model", None),
        ):
            if model is not None:
                if (
                    getattr(model, "_project_selections_save_timer", None)
                    and model._project_selections_save_timer.isActive()
                ):
                    model._project_selections_save_timer.stop()
                    model._do_save_project_selections()
                elif hasattr(model, "_do_save_project_selections"):
                    model._do_save_project_selections()

                if (
                    getattr(model, "_collapse_save_timer", None)
                    and model._collapse_save_timer.isActive()
                ):
                    model._collapse_save_timer.stop()
                    model._do_save_collapsed()

        # Release the single-instance mutex / lock so another instance can start
        release_lock()

        logger.debug("[SHUTDOWN] on_quit complete")
        dump_diagnostics("on_quit complete")

    def cleanup(self):
        """Post-Qt cleanup: flush telemetry and break reference cycles.

        Runs *after* ``app.exec()`` returns. All operations are bounded
        to prevent the shutdown from hanging.
        """
        logger.debug("[SHUTDOWN] cleanup entered")
        dump_diagnostics("cleanup enter")

        # Clean up joblib temp folders manually
        try:
            import shutil
            import tempfile
            from pathlib import Path

            temp_dir = Path(tempfile.gettempdir())
            for folder in temp_dir.glob("joblib_memmapping_folder_*"):
                shutil.rmtree(folder, ignore_errors=True)
        except Exception as e:
            logger.debug(f"Joblib folder cleanup error: {e}")

        # Flush Sentry (best-effort, 0.5s bound)
        try:
            sentry_sdk.flush(timeout=0.5)
        except Exception as e:
            logger.debug(f"Sentry flush error: {e}")

        # PostHog shutdown in daemon thread (fire-and-forget)
        # No join — let it complete in the background.
        threading.Thread(target=posthog_shutdown, daemon=True).start()

        # Shutdown tracked background threads (1.0s bound)
        if hasattr(self, "task_runner"):
            self.task_runner.shutdown(timeout=1.0)

        logger.debug("[SHUTDOWN] cleanup complete")
        dump_diagnostics("cleanup complete")


if __name__ == "__main__":
    main()

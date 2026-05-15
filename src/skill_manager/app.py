"""
Purpose: Main entry point for Skill Manager (PySide6 version).
Usage: python run.py
"""
import ctypes
import json
import os
import re
import sys
import threading
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot
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

from skill_manager.core.analytics import (
    capture_event,
    capture_exception,
    shutdown as posthog_shutdown,
)
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
    load_essentials,
    save_archive,
    save_essentials,
)
from skill_manager.core.quick_copy import (
    CLIENT_FORMATS,
    delete_project_skill_folders,
    discover_project_skills,
    format_project_skill_reference,
)
from skill_manager.core.update_service import UpdateService
from skill_manager.controllers.ui_controller import UIController
from skill_manager.controllers.config_controller import ConfigController
from skill_manager.controllers.ops_controller import OpsController
from skill_manager.controllers.update_controller import UpdateController


class AppController(QObject):
    skillModelChanged = Signal()
    selectedSkillChanged = Signal()
    isLoadingChanged = Signal()
    statusMessageChanged = Signal()
    sourcesChanged = Signal()
    targetsChanged = Signal()
    clientFormatChanged = Signal()
    categoriesChanged = Signal()
    projectsChanged = Signal()
    clientFormatsChanged = Signal()
    customCollectionsChanged = Signal()
    currentViewChanged = Signal()
    windowWidthChanged = Signal()
    windowHeightChanged = Signal()
    windowXChanged = Signal()
    windowYChanged = Signal()
    darkModeChanged = Signal()
    statsChanged = Signal()
    updateResultsChanged = Signal()
    updateSourcesChanged = Signal()

    def __init__(self):
        super().__init__()
        # 1. Core Models and Configuration
        self._config = ConfigManager()
        self._library_model = SkillModel(config=self._config)
        self._quick_copy_model = SkillModel(config=self._config)

        # 2. Basic Attribute Initialization
        self._selected_skill = {}
        self._is_loading = False
        self._status_message = ""
        self._projects = []
        self._categories = []
        self._clipboard = QGuiApplication.clipboard()

        self._client_format = self._config.get("client_format", "Antigravity")
        self._sources = self._config.get("sources", [])
        self._targets = self._config.get("targets", [])
        self._target_aliases = self._config.get("target_aliases", {})
        self._update_sources = self._config.get("skills", [])
        for s in self._update_sources:
            s["is_updating"] = False
            if "current_version" not in s: s["current_version"] = ""
            if "latest_version" not in s: s["latest_version"] = ""
        self._custom_collections = self._config.get("custom_collections", {})

        # Updates and Syncing State
        self._stats_up_to_date = 0
        self._stats_outdated = 0
        self._stats_missing = 0
        self._update_results = []
        self._syncing_targets = []

        # 3. Initialize Sub-Controllers
        self.ui = UIController(self)
        self.config_mgr = ConfigController(self)
        self.ops = OpsController(self)
        self.updates = UpdateController(self)

        # 4. Initial Model Configuration
        self._library_model.showCommands = False
        self._library_model.isSourceOnly = True
        self._library_model.showEssentials = True

        self._quick_copy_model.showCommands = True
        self._quick_copy_model.isSourceOnly = False
        self._quick_copy_model.showEssentials = True

        # 5. Load Persistence and Start Discovery
        self._archive_paths = load_archive()
        self._essential_paths = load_essentials()
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

    @Property(list, notify=targetsChanged)
    def targets(self):
        return self._targets

    @Property(list, notify=targetsChanged)
    def syncingTargets(self):
        return self._syncing_targets

    @Property(list, notify=targetsChanged)
    def updateTargets(self):
        results = []
        for t in self._targets:
            count = 0
            try:
                if os.path.exists(t):
                    count = len([d for d in os.listdir(t) if os.path.isdir(os.path.join(t, d))])
            except: pass
            results.append({
                "name": self.getTargetLabel(t),
                "path": t,
                "skill_count": count,
                "is_updating": t in self._syncing_targets
            })
        return results

    @Property(int, notify=statsChanged)
    def statsUpToDate(self): return self._stats_up_to_date

    @Property(int, notify=statsChanged)
    def statsOutdated(self): return self._stats_outdated

    @Property(int, notify=statsChanged)
    def statsMissing(self): return self._stats_missing

    @Property(list, notify=updateResultsChanged)
    def updateResults(self): return self._update_results

    @Property(str, notify=clientFormatChanged)
    def clientFormat(self):
        return self._client_format

    @Property(list, notify=categoriesChanged)
    def categories(self):
        return self._categories

    @Property(list, notify=projectsChanged)
    def projects(self):
        return self._projects

    @Property(list, notify=targetsChanged)
    def targetLabels(self):
        return [self.getTargetLabel(t) for t in self._targets]

    @Property(list, notify=clientFormatsChanged)
    def clientFormats(self):
        return sorted(CLIENT_FORMATS)

    @Property(list, notify=customCollectionsChanged)
    def customCollections(self):
        return sorted(self._custom_collections.keys())


    @Property(list, notify=updateSourcesChanged)
    def updateSources(self):
        return self._update_sources

    @Property(str, notify=clientFormatChanged)
    def logoSource(self):
        fmt = self._client_format.lower()
        if "antigravity" in fmt:
            return self.ui.get_asset_uri("client-logo/antigravity-color.svg")
        if "gemini" in fmt:
            return self.ui.get_asset_uri("client-logo/geminicli-color.svg")
        if "codex" in fmt:
            return self.ui.get_asset_uri("client-logo/codex-color.svg")
        if "plain" in fmt:
            return self.ui.get_asset_uri("client-logo/plaintext-color.svg")

        return self.ui.get_asset_uri("logo/logo.png")

    @Slot(str, result=str)
    def getLogoSource(self, fmt):
        fmt_lower = fmt.lower()
        if "antigravity" in fmt_lower:
            return self.ui.get_asset_uri("client-logo/antigravity-color.svg")
        if "gemini" in fmt_lower:
            return self.ui.get_asset_uri("client-logo/geminicli-color.svg")
        if "codex" in fmt_lower:
            return self.ui.get_asset_uri("client-logo/codex-color.svg")
        if "plain" in fmt_lower:
            return self.ui.get_asset_uri("client-logo/plaintext-color.svg")

        return self.ui.get_asset_uri("logo/logo.png")

    @Slot(str, result=str)
    def getAssetUri(self, path):
        return self.ui.get_asset_uri(path)


    @Property(dict, notify=targetsChanged)
    def targetAliases(self):
        return self._target_aliases

    @Property(str, notify=currentViewChanged)
    def currentView(self):
        return self.ui._current_view

    @currentView.setter
    def currentView(self, value):
        if self.ui._current_view != value:
            self.ui._current_view = value
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


    # --- Methods / Slots ---

    def load_initial_data(self):
        """Initial scan of skills on application startup in a background thread."""
        self._is_loading = True
        self.isLoadingChanged.emit()
        self._set_status("Scanning skills...")

        import os
        discovery_sources = list(self._sources)
        for src in self._update_sources:
            lp = src.get("local_path")
            if lp and os.path.exists(lp) and lp not in discovery_sources:
                discovery_sources.append(lp)

        service = DiscoveryService(
            sources=discovery_sources,
            targets=self._targets,
            archive_paths=self._archive_paths,
            essential_paths=self._essential_paths,
            target_aliases=self._target_aliases
        )

        def run_discovery():
            try:
                def cache_callback(cached_data):
                    print(f"[CACHE] Loading {len(cached_data.get('skills', []))} skills from cache...")
                    QTimer.singleShot(0, self, lambda: self._finalize_loading(
                        cached_data.get("skills", []),
                        cached_data.get("projects", []),
                        cached_data.get("categories", []),
                        cached_data.get("project_labels", []),
                        f"Loaded {len(cached_data.get('skills', []))} skills from cache (Refreshing...)"
                    ))

                result = service.discover_all(cache_callback=cache_callback)

                # Signal completion back to main thread
                QTimer.singleShot(0, self, lambda: self._finalize_loading(
                    result["skills"],
                    result["projects"],
                    result["categories"],
                    result["project_labels"],
                    result["status"]
                ))
            except Exception as e:
                error_msg = f"Error scanning skills: {e}"
                import traceback
                traceback.print_exc()
                QTimer.singleShot(0, self, lambda: self._handle_loading_error(error_msg))

        threading.Thread(target=run_discovery, daemon=True).start()

    def _finalize_loading(self, all_skills, projects, cats, proj_labels, status):
        """Updates model and UI state on the main thread after discovery completes."""
        if self._categories != cats:
            self._categories = cats
            self.categoriesChanged.emit()

        # Update both models with the shared skill list
        self._library_model.setSkills(all_skills)
        self._quick_copy_model.setSkills(all_skills)

        # Ensure client filters are set
        self._library_model.clientFilter = self._client_format
        self._quick_copy_model.clientFilter = self._client_format

        if self._projects != proj_labels:
            self._projects = proj_labels
            self.projectsChanged.emit()

        self._set_status(status)
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
    def copySelectedSkillsToClipboard(self):
        paths = self.skillModel.getSelectedPaths()
        if not paths:
            self._set_status("No skills selected")
            return

        references = []
        for path in paths:
            skill = next((s for s in self.skillModel._all_skills if s.get("local_path") == path), None)
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
    def toggleCurrentSkillEssential(self):
        self.ops.toggle_essential()

    @Slot(str)
    def deleteSkill(self, path):
        if not path: return
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

    @Slot(str)
    def copySelectedSkillsToTarget(self, target_path):
        self.ops.copy_selected_to_target(target_path)


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
    def addTarget(self, url):
        self.config_mgr.add_target(url)

    @Slot(str)
    def removeTarget(self, path):
        self.config_mgr.remove_target(path)

    @Slot(str, result=str)
    def getTargetLabel(self, path):
        return self.config_mgr.get_target_label(path)

    @Slot(int)
    def removeUpdateTarget(self, index):
        if 0 <= index < len(self._targets):
            self.config_mgr.remove_target(self._targets[index])

    @Slot(str, str)
    def setTargetAlias(self, path, alias):
        self.config_mgr.set_target_alias(path, alias)

    @Slot(str, str, result=str)
    def verifyGitSource(self, url, token):
        return self.config_mgr.verify_git_source(url, token)

    @Slot(str)
    def addUpdateSource(self, package_name):
        if not package_name:
            return
        # Basic NPM-style source
        new_source = {
            "name": package_name,
            "source_type": "npm",
            "package_name": package_name,
            "last_updated": "Never",
            "is_updating": False
        }
        self._update_sources.append(new_source)
        self._config.set("skills", self._update_sources)
        self.updateSourcesChanged.emit()
        self._set_status(f"Added update source: {package_name}")

    @Slot(dict)
    def addSkillSource(self, data):
        if not data:
            return
        from skill_manager.core.skill_sources import (
            check_skill_source_versions,
            normalize_skill_source_config,
        )
        new_source = normalize_skill_source_config(data)
        new_source["is_updating"] = False
        new_source["last_updated"] = "Never"

        # Immediate version check
        new_source = check_skill_source_versions(new_source)

        self._update_sources.append(new_source)
        self._config.set("skills", self._update_sources)
        self.updateSourcesChanged.emit()
        self._set_status(f"Added skill source: {new_source.get('name')}")
        capture_event("skill_source_added", {"source_type": new_source.get("source_type", "unknown")})

    @Slot(int, dict)
    def updateUpdateSource(self, index, data):
        if 0 <= index < len(self._update_sources):
            # Preserve internal state
            is_updating = self._update_sources[index].get("is_updating", False)

            # Use core logic to normalize and detect fields
            from skill_manager.core.skill_sources import (
                check_skill_source_versions,
                normalize_skill_source_config,
            )
            updated_source = normalize_skill_source_config(data)
            updated_source["is_updating"] = is_updating

            # Refresh versions
            updated_source = check_skill_source_versions(updated_source)

            self._update_sources[index] = updated_source
            self._config.set("skills", self._update_sources)
            self.updateSourcesChanged.emit()
            self._set_status(f"Updated skill source: {updated_source.get('name')}")

    @Slot(int)
    def removeUpdateSource(self, index):
        if 0 <= index < len(self._update_sources):
            source = self._update_sources.pop(index)
            self._config.set("skills", self._update_sources)
            self.updateSourcesChanged.emit()
            self._set_status(f"Removed update source: {source.get('name')}")
            capture_event("skill_source_removed", {"source_type": source.get("source_type", "unknown")})

    @Slot(int)
    def clearJustFinished(self, index):
        if 0 <= index < len(self._update_sources):
            self._update_sources[index]["just_finished"] = False
            # Force refresh
            self._update_sources[index] = dict(self._update_sources[index])
            self.updateSourcesChanged.emit()

    @Slot(str, str, result=str)
    def verifyGitSource(self, url, token=None):
        """Verify a git source and return the latest version tag/hash."""
        try:
            from skill_manager.core.skill_sources import get_git_tag
            tag = get_git_tag(url, is_remote=True, token=token)
            return tag if tag else ""
        except Exception as e:
            print(f"Verify failed: {e}")
            return ""

    @Slot(int)
    def runUpdate(self, index):
        if 0 <= index < len(self._update_sources):
            source = self._update_sources[index]
            source["is_updating"] = True
            source["just_finished"] = False
            self.updateSourcesChanged.emit()
            self._set_status(f"Updating {source.get('name')}...")

            def run():
                from skill_manager.core.skill_sources import run_skill_source_update
                try:
                    # If local_path is empty and we have master sources, use the first one as default destination
                    if not source.get("local_path") and self._sources:
                        source["local_path"] = self._sources[0]

                    # Pass a callback that also updates the status bar
                    def log_callback(msg):
                        QTimer.singleShot(0, self, lambda: self._set_status(msg))

                    source.get("local_path")
                    updated_source = run_skill_source_update(source, log_callback)
                    source.update(updated_source)

                    # Update timestamp
                    source["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                    print(f"[UPDATE] Success: {source.get('name')}")
                    capture_event("skill_source_updated", {"source_type": source.get("source_type", "unknown"), "success": True})
                except Exception as e:
                    print(f"[UPDATE] Failed: {source.get('name')} - Error: {e}")
                    import traceback
                    traceback.print_exc()
                    error_msg = str(e)
                    capture_event("skill_source_updated", {"source_type": source.get("source_type", "unknown"), "success": False})
                    capture_exception(e)
                    QTimer.singleShot(0, self, lambda: self._set_status(f"Update failed for {source.get('name')}: {error_msg}"))
                finally:

                    def finalize_ui():
                        try:
                            source["is_updating"] = False
                            source["just_finished"] = True

                            # Replace dict in list to force QML to see the change
                            self._update_sources[index] = dict(source)
                            self.updateSourcesChanged.emit()

                            self._set_status(f"Update finished for {source.get('name')}")
                            # Refresh skill library from all sources (background thread)
                            self.load_initial_data()

                            # Save state
                            self._config.set("skills", self._update_sources)
                        except Exception as e:
                            print(f"[ERROR] Error in finalize_ui for {source.get('name')}: {e}")
                            import traceback
                            traceback.print_exc()
                            self._set_status(f"Error finishing update: {e}")

                    QTimer.singleShot(0, self, finalize_ui)

            threading.Thread(target=run, daemon=True).start()

    def _save_archive(self):
        save_archive(self._archive_paths)

    def _save_essentials(self):
        save_essentials(self._essential_paths)

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
            print(f"[CACHE] Saving {len(slim_data.get('skills', []))} skills to {SKILL_LIBRARY_CACHE_FILE}...")
            with open(SKILL_LIBRARY_CACHE_FILE, 'w', encoding='utf-8') as f:
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
            with open(cache_path, encoding='utf-8') as f:
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
            self.load_initial_data() # Refresh UI
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
        """Creates a new Custom Command .md file in the project's manuals/ directory."""
        if not name:
            self._set_status("Error: Command name is required")
            return

        if not project_label or project_label == "All Projects":
            self._set_status("Error: Please select a specific Project")
            return

        target_path = None
        # Map project label to path
        from skill_manager.core.quick_copy import project_label as get_label
        for t in self._targets:
            tp = Path(t)
            if get_label(tp) == project_label:
                target_path = tp
                break

        if not target_path:
            self._set_status(f"Error: Could not find target for {project_label}")
            return

        # Create manuals/ directory
        manuals_dir = target_path / "manuals"
        manuals_dir.mkdir(parents=True, exist_ok=True)

        # Sanitize filename: NAME.CLIENT.md
        safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', name)
        filename = f"{safe_name}.{client}.md"
        file_path = manuals_dir / filename

        if file_path.exists():
            self._set_status(f"Error: Command {filename} already exists")
            return

        # Content with frontmatter
        content = f"---\nname: {name}\nclient: {client}\ncategory: {category}\ntype: command\ndate: {datetime.now().strftime('%Y-%m-%d')}\n---\n\n{body}"

        try:
            file_path.write_text(content, encoding='utf-8')
            self._set_status(f"Created command: {filename}")
            self.refreshSkills()
        except Exception as e:
            self._set_status(f"Error creating command: {e}")

    @Slot(str, str)
    def setViewFilter(self, filter_type, value):
        """
        Sets a specific filter on the skill models.
        Note: We no longer clear filters when switching views (library/quick_copy).
        Filters are now additive and synced across models.
        """
        if filter_type == "category":
            self._library_model.categoryFilter = value
            self._quick_copy_model.categoryFilter = value
            if value:
                capture_event("skill_searched", {"filter_type": "category"})
        elif filter_type == "collection":
            if not value:
                self._library_model.collectionFilter = False
                self._quick_copy_model.collectionFilter = False
            elif value == "true":
                self._library_model.collectionFilter = True
                self._quick_copy_model.collectionFilter = True
            else:
                # Custom collection name - handled via applyCollectionSelection usually,
                # but we keep the filter property in sync.
                self._library_model.collectionFilter = False
                self._quick_copy_model.collectionFilter = False
        elif filter_type == "project":
            self._library_model.projectFilter = value
            self._quick_copy_model.projectFilter = value
        elif filter_type == "clear":
            # Explicit clear requested for both models
            for model in [self._library_model, self._quick_copy_model]:
                model.filterText = ""
                model.categoryFilter = ""
                model.collectionFilter = False
                model.projectFilter = ""
        # We ignore "library" and "quick_copy" here as they are handled by currentView setter

        self._set_status(f"Filter applied: {filter_type} = {value if value else 'All'}")


    @Slot(str)
    def syncProject(self, path):
        if path not in self._targets:
            return

        self._set_status(f"Updating {self.getTargetLabel(path)}...")
        if path not in self._syncing_targets:
            self._syncing_targets.append(path)
            self.targetsChanged.emit()

        def run_sync():
            try:
                # Re-scan sources
                projects = discover_project_skills(
                    targets=self._sources,
                    parse_skill_md=parse_skill_md,
                    categorize_skill=categorize_skill,
                    build_search_text=build_skill_search_text
                )
                all_raw_skills = []
                for p in projects:
                    all_raw_skills.extend(p.get("skills", []))

                # Sync only to this target, update only
                from skill_manager.core.copier import copy_skill_folders_to_targets
                result = copy_skill_folders_to_targets(all_raw_skills, [path], update_only=True)

                msg = f"Update complete for {self.getTargetLabel(path)}: {result['merged']} updated, {result['failed']} failed"
                QTimer.singleShot(0, self, lambda: self._set_status(msg))
            except Exception:
                QTimer.singleShot(0, self, lambda: self._set_status(f"Update failed for {path}: {e}"))
            finally:
                if path in self._syncing_targets:
                    self._syncing_targets.remove(path)
                QTimer.singleShot(0, self, self.targetsChanged.emit)

        threading.Thread(target=run_sync, daemon=True).start()

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
    def updateSkillInTarget(self, skill_name, target_project_name):
        self.updates.update_skill_in_target(skill_name, target_project_name)


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
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

def main():
    # Set style to Basic to avoid issues with platform themes during debug
    QQuickStyle.setStyle("Basic")

    app = QGuiApplication(sys.argv)
    app.setWindowIcon(QIcon(resource_path("assets/logo/logo.png")))

    controller = AppController()

    # Register singletons - 6 arguments required: (Type, URI, Major, Minor, Name, Instance)
    qmlRegisterSingletonInstance(AppController, "App", 1, 0, "AppController", controller)

    app.aboutToQuit.connect(controller.on_quit)

    engine = QQmlApplicationEngine()

    # Add context property for compatibility
    engine.rootContext().setContextProperty("appController", controller)

    # Listen to warnings
    engine.warnings.connect(lambda msg: print(f"QML Warning: {msg}"))

    # Setup paths
    if getattr(sys, 'frozen', False):
        # Running as a bundle (PyInstaller)
        # In the spec file we map src/skill_manager/SkillManagerComponents to skill_manager/SkillManagerComponents
        # PyInstaller 6+ places data in _internal folder when using directory mode
        base_internal = Path(sys._MEIPASS) / "_internal"
        if base_internal.exists():
            qml_dir = base_internal / "skill_manager" / "SkillManagerComponents"
        else:
            qml_dir = Path(sys._MEIPASS) / "skill_manager" / "SkillManagerComponents"
    else:
        # Running in normal Python environment
        qml_dir = Path(__file__).resolve().parent / "SkillManagerComponents"

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
                            4
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

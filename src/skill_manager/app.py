"""
Purpose: Main entry point for Skill Manager (PySide6 version).
Usage: python run.py
"""
import sys
import os
import json
import threading
import re
import ctypes
from datetime import datetime
from pathlib import Path
from PySide6.QtCore import QObject, Signal, Slot, Property, QTimer, Qt
from PySide6.QtGui import QGuiApplication, QIcon, QClipboard
from PySide6.QtQml import QQmlApplicationEngine, qmlRegisterSingletonInstance
from PySide6.QtQuickControls2 import QQuickStyle

# Try to import pywinstyles for Mica/Acrylic
try:
    import pywinstyles
    HAS_PYWINSTYLES = True
except ImportError:
    HAS_PYWINSTYLES = False

from skill_manager.core.models import SkillModel
from skill_manager.core.config import ConfigManager, SKILL_LIBRARY_ARCHIVE_FILE, SKILL_LIBRARY_ESSENTIALS_FILE
from skill_manager.core.parsing import parse_skill_md, categorize_skill, build_skill_search_text, parse_command_md, parse_frontmatter
from skill_manager.core.quick_copy import discover_project_skills, discover_source_skills, format_project_skill_reference, CLIENT_FORMATS, delete_project_skill_folders
from skill_manager.core.copier import copy_skill_folders_to_targets
from skill_manager.core.analytics import capture_event, capture_exception, shutdown as posthog_shutdown

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
        # Initialize models
        self._config = ConfigManager()
        self._library_model = SkillModel(config=self._config)
        self._quick_copy_model = SkillModel(config=self._config)
        
        # Initial model configuration
        self._library_model.showCommands = False
        self._library_model.isSourceOnly = True
        self._library_model.showEssentials = True
        
        self._quick_copy_model.showCommands = True
        self._quick_copy_model.isSourceOnly = False
        self._quick_copy_model.showEssentials = True
        
        self._selected_skill = {}
        self._is_loading = False
        self._status_message = ""
        self._sources = []
        self._targets = []
        self._syncing_targets = [] # List of paths currently syncing
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
        
        # Updates state
        self._stats_up_to_date = 0
        self._stats_outdated = 0
        self._stats_missing = 0
        self._update_results = []
        
        # UI state
        ui_state = self._config.get("ui_state", {})
        self._current_view = ui_state.get("current_view", "Library")
        
        # Normalize old values to fix case mismatch warnings
        if self._current_view == "library":
            self._current_view = "Library"
        elif self._current_view == "quick-copy":
            self._current_view = "QuickCopy"
            
        self._window_width = max(1050, ui_state.get("window_width", 1300))
        self._window_height = max(650, ui_state.get("window_height", 650))
        self._window_x = ui_state.get("window_x", 100)
        self._window_y = ui_state.get("window_y", 100)
        self._dark_mode = ui_state.get("dark_mode", False)

        # Initial view config based on loaded state
        if self._current_view == "Library":
            # Models are already configured in __init__
            pass
        elif self._current_view in ["QuickCopy", "Quick Copy"]:
            # Sync any filters if needed, though they are mostly independent now
            pass

        # Load archive and essentials
        self._archive_paths = []
        self._essential_paths = []
        try:
            if os.path.exists(SKILL_LIBRARY_ARCHIVE_FILE):
                with open(SKILL_LIBRARY_ARCHIVE_FILE, 'r') as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        self._archive_paths = data.get("archived_skills", [])
                    else:
                        self._archive_paths = data or []
            if os.path.exists(SKILL_LIBRARY_ESSENTIALS_FILE):
                with open(SKILL_LIBRARY_ESSENTIALS_FILE, 'r') as f:
                    self._essential_paths = json.load(f) or []
        except Exception as e:
            print(f"Error loading persistence: {e}")
        
        # Debounce timer for UI state saves
        self._save_timer = QTimer()
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self._save_ui_state)

        # Connect to quit signal to ensure final save
        from PySide6.QtCore import QCoreApplication
        app = QCoreApplication.instance()
        if app:
            app.aboutToQuit.connect(self._save_ui_state)

        # Load initial data
        QTimer.singleShot(100, self.load_initial_data)

    # --- Properties ---

    @Property(QObject, notify=skillModelChanged)
    def skillModel(self):
        if self._current_view == "Library":
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
        return sorted(list(CLIENT_FORMATS))

    @Property(list, notify=customCollectionsChanged)
    def customCollections(self):
        return sorted(list(self._custom_collections.keys()))

    @Property(str, notify=currentViewChanged)
    def currentView(self):
        return self._current_view

    @Property(list, notify=updateSourcesChanged)
    def updateSources(self):
        return self._update_sources

    @Property(str, notify=clientFormatChanged)
    def logoSource(self):
        fmt = self._client_format.lower()
        if "antigravity" in fmt:
            return self._get_asset_uri("client-logo/antigravity-color.svg")
        elif "gemini" in fmt:
            return self._get_asset_uri("client-logo/geminicli-color.svg")
        elif "codex" in fmt:
            return self._get_asset_uri("client-logo/codex-color.svg")
        elif "plain" in fmt:
            return self._get_asset_uri("client-logo/plaintext-color.svg")
        
        return self._get_asset_uri("logo/logo.png")

    @Slot(str, result=str)
    def getLogoSource(self, fmt):
        fmt_lower = fmt.lower()
        if "antigravity" in fmt_lower:
            return self._get_asset_uri("client-logo/antigravity-color.svg")
        elif "gemini" in fmt_lower:
            return self._get_asset_uri("client-logo/geminicli-color.svg")
        elif "codex" in fmt_lower:
            return self._get_asset_uri("client-logo/codex-color.svg")
        elif "plain" in fmt_lower:
            return self._get_asset_uri("client-logo/plaintext-color.svg")
        
        return self._get_asset_uri("logo/logo.png")

    @Slot(str, result=str)
    def getAssetUri(self, path):
        """Returns the absolute URI for an asset path."""
        if getattr(sys, 'frozen', False):
            # In frozen app, assets are bundled relative to sys._MEIPASS
            base = Path(sys._MEIPASS) / "assets"
        else:
            # In source, assets are in the root assets folder
            base = Path(__file__).resolve().parent.parent.parent / "assets"
            
        full_path = base / path
        if not full_path.exists():
            # Fallback to default logo if missing
            if "logo/" in path:
                full_path = base / "logo" / "logo.png"
                
        return full_path.as_uri()

    def _get_asset_uri(self, path):
        return self.getAssetUri(path)


    @Property(dict, notify=targetsChanged)
    def targetAliases(self):
        return self._target_aliases

    @currentView.setter
    def currentView(self, value):
        if self._current_view != value:
            self._current_view = value
            
            # Persist state
            self._save_ui_state()
            self.currentViewChanged.emit()
            self.skillModelChanged.emit() # Notify QML that the active model changed

    @Property(int, notify=windowWidthChanged)
    def windowWidth(self):
        return self._window_width

    @windowWidth.setter
    def windowWidth(self, value):
        if self._window_width != value and value >= 1050:
            self._window_width = value
            self._trigger_save()
            self.windowWidthChanged.emit()

    @Property(int, notify=windowHeightChanged)
    def windowHeight(self):
        return self._window_height

    @windowHeight.setter
    def windowHeight(self, value):
        if self._window_height != value and value >= 650:
            self._window_height = value
            self._trigger_save()
            self.windowHeightChanged.emit()

    @Property(int, notify=windowXChanged)
    def windowX(self):
        return self._window_x

    @windowX.setter
    def windowX(self, value):
        if self._window_x != value:
            self._window_x = value
            self._trigger_save()
            self.windowXChanged.emit()

    @Property(int, notify=windowYChanged)
    def windowY(self):
        return self._window_y

    @windowY.setter
    def windowY(self, value):
        if self._window_y != value:
            self._window_y = value
            self._trigger_save()
            self.windowYChanged.emit()

    @Property(bool, notify=darkModeChanged)
    def darkMode(self):
        return self._dark_mode

    @darkMode.setter
    def darkMode(self, value):
        if self._dark_mode != value:
            self._dark_mode = value
            self._trigger_save()
            self.darkModeChanged.emit()


    # --- Methods / Slots ---

    def load_initial_data(self):
        """Initial scan of skills on application startup in a background thread."""
        self._is_loading = True
        self.isLoadingChanged.emit()
        self._set_status("Scanning skills...")
        
        def run_discovery():
            try:
                # 1. Try to load from cache for instant startup (in background thread)
                cached_data = self._load_cache()
                if cached_data:
                    print(f"[CACHE] Loading {len(cached_data.get('skills', []))} skills from cache...")
                    QTimer.singleShot(0, self, lambda: self._finalize_loading(
                        cached_data.get("skills", []),
                        cached_data.get("projects", []),
                        cached_data.get("categories", []),
                        cached_data.get("project_labels", []),
                        f"Loaded {len(cached_data.get('skills', []))} skills from cache (Refreshing...)"
                    ))
                
                # 2a. Discover skills from master source folders for the Library view.
                source_skills_raw = discover_source_skills(
                    sources=self._sources,
                    parse_skill_md=parse_skill_md,
                    categorize_skill=categorize_skill,
                    build_search_text=build_skill_search_text,
                )

                all_skills = []
                for skill in source_skills_raw:
                    metadata = skill.get("metadata", {})
                    skill_data = {
                        "id": str(skill.get("local_path", "")),
                        "name": skill.get("name", "Unknown"),
                        "category": skill.get("category", "Uncategorized"),
                        "description": skill.get("description", ""),
                        "local_path": skill.get("local_path", ""),
                        "project_label": skill.get("project_label", "Master Library"),
                        "project_root": skill.get("project_root", ""),
                        "target_path": skill.get("target_path", ""),
                        "is_essential": metadata.get("essential", False) or skill.get("local_path") in self._essential_paths,
                        "is_bundle": skill.get("is_bundle", False),
                        "manuals": skill.get("manuals", []),
                        "is_selected": False,
                        "is_archived": skill.get("local_path") in self._archive_paths,
                        "search_text": skill.get("search_text", ""),
                        "raw_content": skill.get("raw_content", ""),
                        "body_content": skill.get("body_content", ""),
                        "risk": metadata.get("risk", "Unknown"),
                        "source": metadata.get("source", "Unknown"),
                        "date": str(metadata.get("date_added") or metadata.get("date", "Unknown")),
                        "is_source": True,
                    }
                    all_skills.append(skill_data)

                # 2b. Discover project-level skills from targets (for QuickCopy only).
                projects = discover_project_skills(
                    targets=self._targets,
                    parse_skill_md=parse_skill_md,
                    categorize_skill=categorize_skill,
                    build_search_text=build_skill_search_text,
                    target_aliases=self._target_aliases
                )

                for p in projects:
                    for skill in p.get("skills", []):
                        metadata = skill.get("metadata", {})
                        skill_data = {
                            "id": str(skill.get("local_path", "")),
                            "name": skill.get("name", "Unknown"),
                            "category": skill.get("category", "Uncategorized"),
                            "description": skill.get("description", ""),
                            "local_path": skill.get("local_path", ""),
                            "project_label": skill.get("project_label", p.get("project_label", "Unknown Project")),
                            "project_root": skill.get("project_root", p.get("project_root", "")),
                            "target_path": skill.get("target_path", p.get("target_path", "")),
                            "is_essential": metadata.get("essential", False) or skill.get("local_path") in self._essential_paths,
                            "is_bundle": skill.get("is_bundle", False),
                            "manuals": skill.get("manuals", []),
                            "is_selected": False,
                            "is_archived": skill.get("local_path") in self._archive_paths,
                            "search_text": skill.get("search_text", ""),
                            "raw_content": skill.get("raw_content", ""),
                            "body_content": skill.get("body_content", ""),
                            "risk": metadata.get("risk", "Unknown"),
                            "source": metadata.get("source", "Unknown"),
                            "date": str(metadata.get("date_added") or metadata.get("date", "Unknown")),
                            "is_source": False,
                            "skill_base_relative": skill.get("skill_base_relative", ""),
                            "folder_name": skill.get("folder_name", ""),
                            "skill_md_path": skill.get("skill_md_path", "")
                        }
                        all_skills.append(skill_data)
                    
                    # Also discover commands in manuals/ subdir
                    target_path = Path(p["target_path"])
                    manuals_dir = target_path / "manuals"
                    if manuals_dir.is_dir():
                        for cmd_file in manuals_dir.glob("*.md"):
                            cmd_data_raw = parse_command_md(str(cmd_file))
                            if not cmd_data_raw:
                                continue
                            
                            cmd_skill_data = {
                                "id": str(cmd_file),
                                "name": cmd_data_raw.get("name") or cmd_file.stem,
                                "category": cmd_data_raw.get("category") or "Custom Commands",
                                "description": cmd_data_raw.get("description", ""),
                                "local_path": str(cmd_file),
                                "project_label": p.get("project_label", "Unknown Project"),
                                "project_root": p.get("project_root", ""),
                                "target_path": p.get("target_path", ""),
                                "is_essential": False,
                                "is_bundle": False,
                                "manuals": [],
                                "is_selected": False,
                                "is_archived": False,
                                "raw_content": cmd_data_raw.get("raw_content", ""),
                                "body_content": cmd_data_raw.get("body_content", ""),
                                "risk": "Low",
                                "source": "Custom",
                                "date": str(cmd_data_raw.get("metadata", {}).get("date", "Unknown")),
                                "is_source": False,
                                "is_command": True,
                                "client": cmd_data_raw.get("client", "")
                            }
                            cmd_skill_data["search_text"] = build_skill_search_text(cmd_skill_data)
                            all_skills.append(cmd_skill_data)

                # Pre-compute data for main thread
                cats = sorted(list(set(s["category"] for s in all_skills if s["category"])))
                proj_labels = sorted(list(set(p["project_label"] for p in projects)))
                status = f"Found {len(all_skills)} skills in master library ({len(projects)} project targets)"
                
                # Save to cache
                self._save_cache({
                    "skills": all_skills,
                    "projects": projects,
                    "categories": cats,
                    "project_labels": proj_labels
                })
                
                # Signal completion back to main thread
                QTimer.singleShot(0, self, lambda: self._finalize_loading(all_skills, projects, cats, proj_labels, status))
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
        if not self._selected_skill:
            return
        
        path = self._selected_skill.get("local_path")
        if not path:
            return
            
        is_archived = self._selected_skill.get("is_archived", False)
        new_state = not is_archived
        
        self._selected_skill["is_archived"] = new_state
        
        if new_state:
            if path not in self._archive_paths:
                self._archive_paths.append(path)
        else:
            if path in self._archive_paths:
                self._archive_paths.remove(path)
            
        self._save_archive()
            
        self.selectedSkillChanged.emit()
        self._library_model._apply_filter()
        self._quick_copy_model._apply_filter()
        
        status = "archived" if new_state else "restored"
        self._set_status(f"Skill {status}")
        capture_event("skill_archived", {"action": status})

    @Slot()
    def toggleCurrentSkillEssential(self):
        if not self._selected_skill:
            return
        
        path = self._selected_skill.get("local_path")
        if not path:
            return
            
        is_essential = self._selected_skill.get("is_essential", False)
        new_state = not is_essential
        
        self._selected_skill["is_essential"] = new_state
        
        if new_state:
            if path not in self._essential_paths:
                self._essential_paths.append(path)
        else:
            if path in self._essential_paths:
                self._essential_paths.remove(path)
            
        self._save_essentials()
            
        self.selectedSkillChanged.emit()
        self._library_model._apply_filter()
        self._quick_copy_model._apply_filter()
        
        status = "added to essentials" if new_state else "removed from essentials"
        self._set_status(f"Skill {status}")

    @Slot(str)
    def deleteSkill(self, path: str):
        """Delete a single skill (dir) or command (file) by its local_path.

        Uses optimistic UI: removes from the model instantly, then performs
        filesystem deletion and cache patch in a background thread.
        """
        if not path:
            return

        skill = next((s for s in self.skillModel._all_skills if s.get("local_path") == path), None)
        if not skill:
            self._set_status(f"Cannot delete: skill not found for path {path}")
            return

        self._optimistic_delete([skill])

    @Slot()
    def deleteSelectedSkills(self):
        """Delete all currently selected skills/commands.

        Uses optimistic UI: removes from the model instantly, then performs
        filesystem deletion and cache patch in a background thread.
        """
        selected_paths = self.skillModel.getSelectedPaths()
        selected = [s for s in self.skillModel._all_skills if s.get("local_path") in selected_paths]
        if not selected:
            self._set_status("No skills selected for deletion")
            return
        self._optimistic_delete(selected)

    @Slot(str)
    def copySelectedSkillsToTarget(self, target_path):
        if not target_path:
            self._set_status("No target project selected")
            return
            
        selected_paths = self.skillModel.getSelectedPaths()
        if not selected_paths:
            self._set_status("No skills selected to copy")
            return
            
        # Get full skill objects for copier
        selected_skills = [s for s in self.skillModel._all_skills if s.get("local_path") in selected_paths]
        
        self._set_status(f"Copying {len(selected_skills)} skills to {self.getTargetLabel(target_path)}...")
        
        def run_copy():
            try:
                from skill_manager.core.copier import copy_skill_folders_to_targets
                result = copy_skill_folders_to_targets(selected_skills, [target_path])
                
                parts = []
                if result['copied']: parts.append(f"{result['copied']} new")
                if result['merged']: parts.append(f"{result['merged']} updated")
                if result['failed']: parts.append(f"{result['failed']} failed")
                
                msg = f"Copy complete: {', '.join(parts) or 'nothing copied'}"
                capture_event("skill_copied_to_project", {
                    "skills_copied": result["copied"],
                    "skills_merged": result["merged"],
                    "skills_failed": result["failed"],
                    "skills_count": len(selected_skills),
                })
                QTimer.singleShot(0, self, lambda: self._set_status(msg))
                # Refresh to show new skills in the project
                QTimer.singleShot(0, self, self.refreshSkills)
                # Clear selection after copy
                QTimer.singleShot(0, self, self.skillModel.clearSelection)
            except Exception as e:
                import traceback
                traceback.print_exc()
                QTimer.singleShot(0, self, lambda: self._set_status(f"Copy failed: {e}"))
                
        threading.Thread(target=run_copy, daemon=True).start()

    def _optimistic_delete(self, items: list):
        """Core optimistic-delete handler.

        1. Removes items from the in-memory SkillModel immediately (instant UI).
        2. Spawns a background thread to do disk deletion + surgical cache patch.
        3. Reports final status on the main thread via QTimer.
        """
        # Snapshot data needed by the background thread before model mutation.
        paths_to_remove = [s.get("local_path", "") for s in items]
        skill_items = [s for s in items if not s.get("is_command", False)]
        command_items = [s for s in items if s.get("is_command", False)]
        count = len(items)

        # ── Step 1: Instant visual removal ──────────────────────────────────
        self._library_model.removeSkillsByPath(paths_to_remove)
        self._quick_copy_model.removeSkillsByPath(paths_to_remove)
        self._set_status(f"Deleting {count} item{'s' if count != 1 else ''}…")
        capture_event("skills_deleted", {"count": count})

        # ── Step 2: Background disk + cache work ─────────────────────────────
        def _background_delete():
            deleted, failed = 0, 0

            # Delete directory-based skills with path validation.
            if skill_items:
                result = delete_project_skill_folders(skill_items)
                deleted += result.get("deleted", 0)
                failed += result.get("failed", 0)
                for detail in result.get("details", []):
                    if detail.get("status") != "deleted":
                        print(f"[DELETE] {detail.get('status', 'SKIP').upper()}: "
                              f"{detail.get('skill')} — {detail.get('message')}")

            # Delete command files (plain .md, no dir validation needed).
            for cmd in command_items:
                p = Path(cmd.get("local_path", ""))
                try:
                    if p.is_file():
                        p.unlink()
                        deleted += 1
                    else:
                        print(f"[DELETE] SKIPPED (not a file): {p}")
                except Exception as exc:
                    print(f"[DELETE] FAILED {p}: {exc}")
                    failed += 1

            # Patch cache: surgically remove entries instead of full rescan.
            self._patch_cache_remove(paths_to_remove)

            # ── Step 3: Report back on main thread ───────────────────────────
            parts = [f"{deleted} deleted"] if deleted else []
            if failed:
                parts.append(f"{failed} failed")
            status = f"Deletion complete: {', '.join(parts) or 'nothing happened'}"
            QTimer.singleShot(0, self, lambda: self._set_status(status))

        threading.Thread(target=_background_delete, daemon=True).start()

    def _patch_cache_remove(self, paths_to_remove: list):
        """Remove entries from the on-disk cache JSON without a full rescan."""
        try:
            from skill_manager.core.config import SKILL_LIBRARY_CACHE_FILE
            cache_path = Path(SKILL_LIBRARY_CACHE_FILE)
            if not cache_path.exists():
                return

            path_set = set(paths_to_remove)
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            original_count = len(data.get("skills", []))
            data["skills"] = [s for s in data.get("skills", []) if s.get("local_path") not in path_set]
            removed = original_count - len(data["skills"])

            if removed == 0:
                return  # Nothing to write.

            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)

            print(f"[CACHE] Patched: removed {removed} entries.")
        except Exception as exc:
            print(f"[CACHE] Patch failed (non-critical): {exc}")

    @Slot(str)
    def launchSkill(self, path):
        self._set_status(f"Launching skill: {path}")
        capture_event("skill_launched")
        self.openPath(path)

    @Slot(str)
    def openPath(self, path):
        """Opens a file or folder using system default application."""
        if not path:
            return
        try:
            if sys.platform == 'win32':
                os.startfile(path)
            elif sys.platform == 'darwin':
                import subprocess
                subprocess.run(['open', path])
            else:
                import subprocess
                subprocess.run(['xdg-open', path])
            self._set_status(f"Opened: {os.path.basename(path)}")
        except Exception as e:
            self._set_status(f"Failed to open {path}: {e}")

    @Slot(str)
    def addSource(self, url):
        path = url.replace("file:///", "").replace("/", "\\") if url.startswith("file://") else url
        if path not in self._sources:
            self._sources.append(path)
            self._config.set("sources", self._sources)
            self.sourcesChanged.emit()
            self._set_status(f"Added source: {path}")

    @Slot(str)
    def removeSource(self, path):
        if path in self._sources:
            self._sources.remove(path)
            self._config.set("sources", self._sources)
            self.sourcesChanged.emit()
            self._set_status(f"Removed source: {path}")

    @Slot(int)
    def removeSourceByIndex(self, index):
        if 0 <= index < len(self._sources):
            path = self._sources.pop(index)
            self._config.set("sources", self._sources)
            self.sourcesChanged.emit()
            self._set_status(f"Removed source: {path}")

    @Slot(str)
    def addTarget(self, url):
        path = url.replace("file:///", "").replace("/", "\\") if url.startswith("file://") else url
        if path not in self._targets:
            self._targets.append(path)
            self._config.set("targets", self._targets)
            self.targetsChanged.emit()
            self._set_status(f"Added target: {path}")
            capture_event("project_target_added", {"target_count": len(self._targets)})

    @Slot(str)
    def removeTarget(self, path):
        if path in self._targets:
            self._targets.remove(path)
            if path in self._syncing_targets:
                self._syncing_targets.remove(path)
            # Also remove alias if it exists
            if path in self._target_aliases:
                del self._target_aliases[path]
                self._config.set("target_aliases", self._target_aliases)
            self._config.set("targets", self._targets)
            self.targetsChanged.emit()
            self._set_status(f"Removed target: {path}")

    @Slot(str, result=str)
    def getTargetLabel(self, path):
        if not path: return ""
        # Normalize path for lookup
        norm_path = path.replace("\\", "/")
        label = self._target_aliases.get(path) or self._target_aliases.get(norm_path)
        if not label:
            # Fallback to folder name
            label = os.path.basename(path)
        return label

    @Slot(int)
    def removeUpdateTarget(self, index):
        if 0 <= index < len(self._targets):
            path = self._targets.pop(index)
            if path in self._syncing_targets:
                self._syncing_targets.remove(path)
            self._config.set("targets", self._targets)
            self.targetsChanged.emit()
            self._set_status(f"Removed target: {path}")

    @Slot()
    def syncNow(self):
        self.updateNow()

    @Slot(str, str)
    def setTargetAlias(self, path, alias):
        if not path:
            return
        if not alias:
            if path in self._target_aliases:
                del self._target_aliases[path]
        else:
            self._target_aliases[path] = alias
        
        self._config.set("target_aliases", self._target_aliases)
        self.targetsChanged.emit()
        self.refreshSkills() # Refresh to update project labels in library
        self._set_status(f"Renamed project to: {alias or 'Default'}")

    @Slot(str, str, result=str)
    def verifyGitSource(self, url, token):
        if not url: return ""
        from skill_manager.core.skill_sources import get_git_tag
        self._set_status(f"Verifying repository: {url}")
        tag = get_git_tag(url, is_remote=True, token=token)
        if tag:
            self._set_status(f"Repository verified. Latest version: {tag}")
        else:
            self._set_status(f"Verification failed for: {url}")
        return tag

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
        from skill_manager.core.skill_sources import normalize_skill_source_config, check_skill_source_versions
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
            from skill_manager.core.skill_sources import normalize_skill_source_config, check_skill_source_versions
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
                    
                    local_path = source.get("local_path")
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
        try:
            with open(SKILL_LIBRARY_ARCHIVE_FILE, 'w') as f:
                json.dump(self._archive_paths, f, indent=4)
        except Exception as e:
            print(f"Error saving archive: {e}")

    def _save_essentials(self):
        try:
            with open(SKILL_LIBRARY_ESSENTIALS_FILE, 'w') as f:
                json.dump(self._essential_paths, f, indent=4)
        except Exception as e:
            print(f"Error saving essentials: {e}")

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
            with open(cache_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError, OSError) as e:
            print(f"[CACHE] Corrupted cache deleted ({e}). Will rebuild on next scan.")
            try:
                cache_path.unlink(missing_ok=True)
            except OSError:
                pass
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
            self._skill_model.clearSelection()
            self._skill_model.selectByPaths(paths)
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
        """Sets the active filter on the skill model.
        Note: We no longer clear filters when switching views (library/quick_copy).
        Filters are now additive.
        """
        if filter_type == "category":
            self._skill_model.categoryFilter = value
            if value:
                capture_event("skill_searched", {"filter_type": "category"})
        elif filter_type == "collection":
            if not value:
                self._skill_model.collectionFilter = False
            elif value == "true":
                self._skill_model.collectionFilter = True
            else:
                # Custom collection name - we don't filter by name in the model yet,
                # we just use it to trigger selection changes in applyCollectionSelection
                self._skill_model.collectionFilter = False
        elif filter_type == "project":
            self._skill_model.projectFilter = value
        elif filter_type == "clear":
            # Explicit clear requested
            self._skill_model.filterText = ""
            self._skill_model.categoryFilter = ""
            self._skill_model.collectionFilter = False
            self._skill_model.projectFilter = ""
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
            except Exception as e:
                QTimer.singleShot(0, self, lambda: self._set_status(f"Update failed for {path}: {e}"))
            finally:
                if path in self._syncing_targets:
                    self._syncing_targets.remove(path)
                QTimer.singleShot(0, self, self.targetsChanged.emit)

        threading.Thread(target=run_sync, daemon=True).start()

    @Slot()
    def updateNow(self):
        self._set_status("Starting global update...")
        # Mark targets as syncing
        for t in self._targets:
            if t not in self._syncing_targets:
                self._syncing_targets.append(t)
        self.targetsChanged.emit()
        
        # Mark sources as updating
        for s in self._update_sources:
            s["is_updating"] = True
            s["just_finished"] = False
        self.updateSourcesChanged.emit()
        
        def run_full_sync():
            try:
                from skill_manager.core.skill_sources import run_skill_source_update
                from skill_manager.core.quick_copy import delete_project_skill_folders
                
                # Phase 1: Update skill sources
                self._set_status("Phase 1/2: Updating skill sources...")
                all_removed_folders = []
                for i in range(len(self._update_sources)):
                    source = self._update_sources[i]
                    try:
                        if not source.get("local_path") and self._sources:
                            source["local_path"] = self._sources[0]

                        def log_callback(msg):
                            QTimer.singleShot(0, self, lambda: self._set_status(msg))
                        
                        # run_skill_source_update handles version detection and returns updated source
                        updated_source = run_skill_source_update(source, log_callback)
                        updated_source["is_updating"] = False
                        updated_source["just_finished"] = True
                        
                        # Collect removed folders for project-wide cleanup
                        if updated_source.get("removed_folders"):
                            all_removed_folders.extend(updated_source["removed_folders"])
                        
                        # Update model and config
                        def update_item(idx, data):
                            self._update_sources[idx] = data
                            self.updateSourcesChanged.emit()
                        QTimer.singleShot(0, self, lambda idx=i, s=dict(updated_source): update_item(idx, s))
                    except Exception as e:
                        print(f"[UPDATE] Source failed: {source.get('name')} - {e}")
                        source["is_updating"] = False
                        QTimer.singleShot(0, self, self.updateSourcesChanged.emit)

                # Phase 2: Update project folders
                self._set_status("Phase 2/2: Updating project folders...")
                
                # Cleanup removed folders from targets first
                if all_removed_folders:
                    self._set_status(f"Cleaning up {len(all_removed_folders)} removed skills from projects...")
                    # Discover what's currently in targets to find instances to delete
                    target_projects_state = discover_project_skills(
                        targets=self._targets,
                        parse_skill_md=parse_skill_md,
                        categorize_skill=categorize_skill,
                        build_search_text=build_skill_search_text
                    )
                    removed_set = set(all_removed_folders)
                    skills_to_delete = []
                    for p in target_projects_state:
                        for s in p.get("skills", []):
                            if s.get("folder_name") in removed_set:
                                skills_to_delete.append(s)
                    
                    if skills_to_delete:
                        delete_project_skill_folders(skills_to_delete)

                projects = discover_project_skills(
                    targets=self._sources,
                    parse_skill_md=parse_skill_md,
                    categorize_skill=categorize_skill,
                    build_search_text=build_skill_search_text
                )
                
                all_raw_skills = []
                for p in projects:
                    all_raw_skills.extend(p.get("skills", []))
                
                from skill_manager.core.copier import copy_skill_folders_to_targets
                result = copy_skill_folders_to_targets(all_raw_skills, self._targets, update_only=True)
                
                # Final Refresh
                self._set_status("Finalizing: Refreshing library...")
                self.load_initial_data()
                
                msg = f"Global update complete: {result['merged']} updated, {result['failed']} failed"
                QTimer.singleShot(0, self, lambda: self._set_status(msg))
                
                # Save config
                self._config.set("skills", self._update_sources)
                
            except Exception as e:
                QTimer.singleShot(0, self, lambda: self._set_status(f"Global update failed: {e}"))
                import traceback
                traceback.print_exc()
            finally:
                self._syncing_targets = []
                QTimer.singleShot(0, self, self.targetsChanged.emit)
                
        threading.Thread(target=run_full_sync, daemon=True).start()


    @Slot()
    def scanForUpdates(self):
        self._set_status("Scanning for updates...")
        self._is_loading = True
        self.isLoadingChanged.emit()

        def run_scan():
            try:
                # 1. Discover skills in sources
                source_skills = discover_source_skills(
                    sources=self._sources,
                    parse_skill_md=parse_skill_md,
                    categorize_skill=categorize_skill,
                    build_search_text=build_skill_search_text,
                )
                
                # 2. Discover skills in targets
                target_projects = discover_project_skills(
                    targets=self._targets,
                    parse_skill_md=parse_skill_md,
                    categorize_skill=categorize_skill,
                    build_search_text=build_skill_search_text,
                    target_aliases=self._target_aliases
                )
                
                # 3. Check versions of all providers (sources)
                from skill_manager.core.skill_sources import check_skill_source_versions
                for i in range(len(self._update_sources)):
                    try:
                        updated_source = check_skill_source_versions(self._update_sources[i])
                        self._update_sources[i] = updated_source
                    except Exception as e:
                        print(f"[ERROR] Failed to check versions for {self._update_sources[i].get('name')}: {e}")

                # 4. Compare skills across targets
                results = []
                
                # We'll build a map of source skills by name/folder
                source_map = {s["folder_name"]: s for s in source_skills}
                
                # Pre-index target skills for faster lookup
                target_skill_maps = []
                for p in target_projects:
                    target_skill_maps.append({
                        "project_label": p["project_label"],
                        "skills_map": {s["folder_name"]: s for s in p["skills"]}
                    })

                # For each source skill, check its status in each target
                for folder_name, source_skill in source_map.items():
                    item_targets = []
                    item_status = "up_to_date"
                    
                    for tm in target_skill_maps:
                        target_skill = tm["skills_map"].get(folder_name)
                        if target_skill:
                            item_targets.append({
                                "name": tm["project_label"],
                                "status": "up_to_date"
                            })
                        else:
                            item_status = "missing"
                            item_targets.append({
                                "name": tm["project_label"],
                                "status": "missing"
                            })
                    
                    results.append({
                        "name": source_skill["name"],
                        "folder_name": folder_name,
                        "status": item_status,
                        "status_text": item_status.replace("_", " ").title(),
                        "targets": item_targets
                    })
                
                def finalize():
                    self._update_results = results
                    self._recalculate_stats()
                    self._is_loading = False
                    self.isLoadingChanged.emit()
                    self.updateSourcesChanged.emit() # Refresh source version labels
                    self._set_status(f"Scan complete: {len(results)} skills processed")

                QTimer.singleShot(0, self, finalize)
            except Exception as e:
                import traceback
                traceback.print_exc()
                QTimer.singleShot(0, self, lambda: self._set_status(f"Scan failed: {e}"))
                QTimer.singleShot(0, self, lambda: setattr(self, "_is_loading", False))
                QTimer.singleShot(0, self, self.isLoadingChanged.emit)

        threading.Thread(target=run_scan, daemon=True).start()

    @Slot()
    def updateAllOutdated(self):
        self.updateNow()

    @Slot(str, str)
    def updateSkillInTarget(self, skill_name, target_project_name):
        self._set_status(f"Updating {skill_name} in {target_project_name}...")
        
        def run_surgical_sync():
            try:
                # 1. Find source skill
                # We look in the model first
                source_skill = next((s for s in self._skill_model._all_skills 
                                    if s.get("is_source") and s.get("name") == skill_name), None)
                if not source_skill:
                    self._set_status(f"Error: Could not find source skill {skill_name}")
                    return

                # 2. Find target project
                target_path = next((t for t in self._targets if self.getTargetLabel(t) == target_project_name), None)
                if not target_path:
                    self._set_status(f"Error: Could not find target project {target_project_name}")
                    return

                # 3. Perform copy
                from skill_manager.core.copier import copy_skill_folders_to_targets
                result = copy_skill_folders_to_targets([source_skill], [target_path], update_only=True)
                
                msg = f"Updated {skill_name} in {target_project_name}"
                if result["failed"] > 0:
                    msg = f"Failed to update {skill_name} in {target_project_name}"
                
                QTimer.singleShot(0, self, lambda: self._set_status(msg))
                # Refresh local project data
                QTimer.singleShot(500, self, self.scanForUpdates)
                
            except Exception as e:
                QTimer.singleShot(0, self, lambda: self._set_status(f"Surgical update failed: {e}"))

        threading.Thread(target=run_surgical_sync, daemon=True).start()

    def _update_item_status(self, skill_name, target_project_name, new_status):
        updated = False
        for item in self._update_results:
            if item["name"] == skill_name or item["folder_name"] == skill_name:
                for target in item["targets"]:
                    if target["name"] == target_project_name:
                        target["status"] = new_status
                        updated = True
                
                # Recalculate item overall status
                statuses = [t["status"] for t in item["targets"]]
                if all(s == "up_to_date" for s in statuses):
                    item["status"] = "up_to_date"
                elif "missing" in statuses:
                    item["status"] = "missing"
                else:
                    item["status"] = "outdated"
                item["status_text"] = item["status"].replace("_", " ").title()
        
        if updated:
            self._recalculate_stats()
            self.updateResultsChanged.emit()

    def _recalculate_stats(self):
        up_to_date = 0
        outdated = 0
        missing = 0
        for item in self._update_results:
            if item["status"] == "up_to_date": up_to_date += 1
            elif item["status"] == "outdated": outdated += 1
            elif item["status"] == "missing": missing += 1
        
        self._stats_up_to_date = up_to_date
        self._stats_outdated = outdated
        self._stats_missing = missing
        self.statsChanged.emit()

    def _trigger_save(self):
        """Starts the debounce timer for saving UI state."""
        self._save_timer.start(1000) # Save 1 second after last update

    def _save_ui_state(self):
        ui_state = {
            "current_view": self._current_view,
            "window_width": self._window_width,
            "window_height": self._window_height,
            "window_x": self._window_x,
            "window_y": self._window_y,
            "dark_mode": self._dark_mode,
        }
        self._config.set("ui_state", ui_state)

    def _set_status(self, msg):
        self._status_message = msg
        self.statusMessageChanged.emit()
        print(f"Status: {msg}")

    def on_quit(self):
        """Ensures all pending state is saved before exit."""
        if self._save_timer.isActive():
            self._save_timer.stop()
            self._save_ui_state()
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
                    DWMWA_USE_IMMERSIVE_DARK_MODE = 20
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

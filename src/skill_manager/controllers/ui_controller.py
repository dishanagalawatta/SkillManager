"""
Purpose: Manages UI state, window geometry, themes, and system shell actions.
Usage: Accessed via AppController.ui
"""

import os
import sys
from pathlib import Path

from PySide6.QtCore import Property, QTimer, Signal, Slot

from skill_manager.controllers.base import BaseController
from skill_manager.core.analytics import capture_event, capture_exception
from skill_manager.core.resources import logo_asset_for_client


class UIController(BaseController):
    """Controller for UI and Window management."""

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

    def __init__(self, app):
        super().__init__(app)

        ui_state = self.config.get("ui_state", {})
        self._window_width = max(1050, ui_state.get("window_width", 1300))
        self._window_height = max(650, ui_state.get("window_height", 650))
        self._window_x = ui_state.get("window_x", 100)
        self._window_y = ui_state.get("window_y", 100)
        self._dark_mode = ui_state.get("dark_mode", False)
        self._current_view = ui_state.get("current_view", "Library")
        self._startup_view = ui_state.get("startup_view", self._current_view)
        self._remember_filters = ui_state.get("remember_filters", True)
        self._default_project_filter = ui_state.get("default_project_filter", "last")
        self._reduced_motion = ui_state.get("reduced_motion", False)
        self._compact_list_rows = ui_state.get("compact_list_rows", False)

        # Normalize view names
        self._startup_view = self._normalizeViewName(self._startup_view)
        self._current_view = self._startup_view

        # Debounce timer for UI state saves
        self._save_timer = QTimer()
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self.saveUiState)

    @Property(str, notify=currentViewChanged)
    def currentView(self):
        return self._current_view

    @currentView.setter
    def currentView(self, value):
        normalized = self._normalizeViewName(value)
        if self._current_view != normalized:
            self._current_view = normalized
            self.saveUiState()
            self.currentViewChanged.emit()
            self.app.skillModelChanged.emit()

    @Property(int, notify=windowWidthChanged)
    def windowWidth(self):
        return self._window_width

    @windowWidth.setter
    def windowWidth(self, value):
        if self._window_width != value and value >= 1050:
            self._window_width = value
            self.triggerSave()
            self.windowWidthChanged.emit()

    @Property(int, notify=windowHeightChanged)
    def windowHeight(self):
        return self._window_height

    @windowHeight.setter
    def windowHeight(self, value):
        if self._window_height != value and value >= 650:
            self._window_height = value
            self.triggerSave()
            self.windowHeightChanged.emit()

    @Property(int, notify=windowXChanged)
    def windowX(self):
        return self._window_x

    @windowX.setter
    def windowX(self, value):
        if self._window_x != value:
            self._window_x = value
            self.triggerSave()
            self.windowXChanged.emit()

    @Property(int, notify=windowYChanged)
    def windowY(self):
        return self._window_y

    @windowY.setter
    def windowY(self, value):
        if self._window_y != value:
            self._window_y = value
            self.triggerSave()
            self.windowYChanged.emit()

    @Property(bool, notify=darkModeChanged)
    def darkMode(self):
        return self._dark_mode

    @darkMode.setter
    def darkMode(self, value):
        if self._dark_mode != value:
            self._dark_mode = value
            self.triggerSave()
            self.darkModeChanged.emit()

    @Property(str, notify=startupViewChanged)
    def startupView(self):
        return self._startup_view

    @startupView.setter
    def startupView(self, value):
        normalized = self._normalizeViewName(value)
        if self._startup_view != normalized:
            self._startup_view = normalized
            self.triggerSave()
            self.startupViewChanged.emit()

    @Property(bool, notify=rememberFiltersChanged)
    def rememberFilters(self):
        return self._remember_filters

    @rememberFilters.setter
    def rememberFilters(self, value):
        if self._remember_filters != value:
            self._remember_filters = value
            if not value:
                self.clearViewFilters()
            self.triggerSave()
            self.rememberFiltersChanged.emit()

    @Property(str, notify=defaultProjectFilterChanged)
    def defaultProjectFilter(self):
        return self._default_project_filter

    @defaultProjectFilter.setter
    def defaultProjectFilter(self, value):
        normalized = value if value in {"last", "all"} else "last"
        if self._default_project_filter != normalized:
            self._default_project_filter = normalized
            if normalized == "all":
                self.setViewFilterForView("QuickCopy", "project", "")
            self.triggerSave()
            self.defaultProjectFilterChanged.emit()

    @Property(bool, notify=reducedMotionChanged)
    def reducedMotion(self):
        return self._reduced_motion

    @reducedMotion.setter
    def reducedMotion(self, value):
        if self._reduced_motion != value:
            self._reduced_motion = value
            self.triggerSave()
            self.reducedMotionChanged.emit()

    @Property(bool, notify=compactListRowsChanged)
    def compactListRows(self):
        return self._compact_list_rows

    @compactListRows.setter
    def compactListRows(self, value):
        if self._compact_list_rows != value:
            self._compact_list_rows = value
            self.triggerSave()
            self.compactListRowsChanged.emit()

    @Property(str, notify=currentViewChanged)
    def logoSource(self):
        return self.getAssetUri(logo_asset_for_client(self.app.clientFormat))

    @Slot(str, result=str)
    def getLogoSource(self, fmt):
        return self.getAssetUri(logo_asset_for_client(fmt))

    @Slot(str)
    def setClientFormat(self, f):
        if self.app._client_format != f:
            self.app._client_format = f
            self.app.clientFormatChanged.emit()
            self.currentViewChanged.emit() # Logo depends on it
            self.triggerSave()

    @Slot(str)
    def setStartupView(self, v):
        self.startupView = v

    @Slot(bool)
    def setRememberFilters(self, b):
        self.rememberFilters = b

    @Slot(str)
    def setDefaultProjectFilter(self, f):
        self.defaultProjectFilter = f

    @Slot(bool)
    def setReducedMotion(self, b):
        self.reducedMotion = b

    @Slot(bool)
    def setCompactListRows(self, b):
        self.compactListRows = b

    @Slot()
    def triggerSave(self):
        """Triggers a debounced save of the UI state."""
        if not self._save_timer.isActive():
            self._save_timer.start(2000)

    def saveUiState(self):
        """Saves current window geometry and UI preferences to config."""
        ui_state = self.config.get("ui_state", {})
        ui_state.update(
            {
                "window_width": self._window_width,
                "window_height": self._window_height,
                "window_x": self._window_x,
                "window_y": self._window_y,
                "dark_mode": self._dark_mode,
                "current_view": self._current_view,
                "startup_view": self._startup_view,
                "remember_filters": self._remember_filters,
                "default_project_filter": self._default_project_filter,
                "reduced_motion": self._reduced_motion,
                "compact_list_rows": self._compact_list_rows,
            }
        )
        self.config.set("ui_state", ui_state)

    @Slot()
    def resetUiState(self):
        """Restores UI preferences and geometry to stable defaults."""
        self._window_width = 1300
        self._window_height = 650
        self._window_x = 100
        self._window_y = 100
        self._current_view = "Library"
        self._startup_view = "Library"
        self._remember_filters = True
        self._default_project_filter = "last"
        self._reduced_motion = False
        self._compact_list_rows = False
        self._clearAllViewFilters()
        self.saveUiState()
        # Emit all relevant signals
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

    @staticmethod
    def _normalizeViewName(value: str) -> str:
        view = str(value or "").replace(" ", "").replace("-", "")
        view_map = {
            "quickcopy": "QuickCopy",
            "library": "Library",
            "updates": "Updates",
            "settings": "Settings",
        }
        return view_map.get(view.lower(), "Library")

    @Slot(str, result=str)
    def getAssetUri(self, path: str) -> str:
        """Returns the absolute URI for an asset path."""
        if getattr(sys, "frozen", False):
            base = Path(sys._MEIPASS) / "assets"
        else:
            base = Path(__file__).resolve().parent.parent.parent.parent / "assets"

        full_path = base / path
        if not full_path.exists() and ("brand/" in path or "logo" in path):
            return self.getAssetUri("brand/logo.png")

        return full_path.as_uri()

    @Slot(str)
    def openPath(self, path: str):
        """Opens a file or folder using system default application."""
        if not path:
            return
        try:
            if sys.platform == "win32":
                os.startfile(path)
            elif sys.platform == "darwin":
                import subprocess
                subprocess.run(["open", "--", path], check=True)
            else:
                import subprocess
                # xdg-open doesn't support '--' reliably; prevent argument injection
                # by making sure paths starting with '-' become relative or absolute.
                safe_path = path
                if safe_path.startswith("-"):
                    safe_path = f"./{safe_path}"
                subprocess.run(["xdg-open", safe_path], check=True)
            self.app._set_status(f"Opened: {os.path.basename(path)}")
        except Exception as e:
            self.app._set_status(f"Failed to open {path}: {e}")
            capture_exception(e)

    @Slot(str)
    def launchSkill(self, path: str):
        """Launches a skill by opening its path."""
        self.app._set_status(f"Launching skill: {path}")
        capture_event("skill_launched")
        self.openPath(path)

    @Slot(int)
    def selectSkill(self, index: int):
        """Sets the selected skill based on model index."""
        if index == -1:
            self.app._selected_skill = {}
        else:
            self.app._selected_skill = self.app.skillModel.get_skill_at(index)
        self.app.selectedSkillChanged.emit()

    @Slot()
    def selectAllVisibleSkills(self):
        """Selects all skills currently visible in the active model."""
        self.app.skillModel.selectAll()
        self.app._set_status(f"Selected {self.app.skillModel.selectedCount} visible skills")

    @Slot()
    def clearVisibleSelection(self):
        """Clears selection in the active model."""
        self.app.skillModel.clearSelection()
        self.app._set_status("Selection cleared")

    @Slot()
    def toggleAllVisibleCategories(self):
        """Toggles collapse/expand for all categories."""
        self.app.skillModel.toggleAll()
        state = "expanded" if self.app.skillModel.isAllExpanded else "collapsed"
        self.app._set_status(f"All categories {state}")

    @Slot(str, str)
    def setViewFilter(self, filter_type: str, value: str):
        """Applies a filter to the current model."""
        self._setViewFilterForModel(self.app.skillModel, filter_type, value)

    @Slot(str, str, str)
    def setViewFilterForView(self, view: str, filter_type: str, value: str):
        """Applies a filter to a specific model by view name."""
        self._setViewFilterForModel(self._modelForView(view), filter_type, value)

    def _modelForView(self, view: str):
        """Internal helper to resolve model by view name."""
        normalized = self._normalizeViewName(view)
        return self.app._library_model if normalized == "Library" else self.app._quick_copy_model

    def _setViewFilterForModel(self, model, filter_type: str, value: str):
        """Core filtering logic shared across views."""
        if not self._remember_filters:
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
            if model is self.app._quick_copy_model:
                model.projectFilter = value
        elif filter_type == "clear":
            model.filterText = ""
            model.categoryFilter = ""
            model.collectionFilter = False
            model.projectFilter = ""

        self.app._set_status(f"Filter applied: {filter_type} = {value if value else 'All'}")

    @Slot()
    def clearViewFilters(self):
        """Clears all filters from the current model."""
        model = self.app.skillModel
        model.filterText = ""
        model.categoryFilter = ""
        model.collectionFilter = False
        model.projectFilter = ""
        self.app._set_status("Filters cleared")

    def _clearAllViewFilters(self):
        """Clears filters for all models."""
        for model in [self.app._library_model, self.app._quick_copy_model]:
            model.filterText = ""
            model.categoryFilter = ""
            model.collectionFilter = False
            model.projectFilter = ""

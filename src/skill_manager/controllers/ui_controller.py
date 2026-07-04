"""
Purpose: Manages UI state, window geometry, themes, and system shell actions.
Usage: Accessed via AppController.ui
"""

import logging
import os
import sys
from pathlib import Path

from PySide6.QtCore import Property, QTimer, Signal, Slot

from skill_manager.controllers.base import BaseController
from skill_manager.core.analytics import capture_event, capture_exception
from skill_manager.core.resources import logo_asset_for_client
from skill_manager.core.schemas import UIStateRecord

logger = logging.getLogger(__name__)


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
    reducedMotionChanged = Signal()
    compactListRowsChanged = Signal()
    inspectorWidthChanged = Signal()

    def __init__(self, app):
        super().__init__(app)

        # Initialize state using Pydantic for strict validation
        raw_state = self.config.get("ui_state", {})
        try:
            # If current_view is provided but startup_view is not,
            # make startup_view match it (legacy behavior parity)
            if "current_view" in raw_state and "startup_view" not in raw_state:
                raw_state["startup_view"] = raw_state["current_view"]

            self.state = UIStateRecord.model_validate(raw_state)
        except Exception as e:
            logger.warning("Invalid UI state in config, using defaults. Error: %s", e)
            self.state = UIStateRecord()

        # Normalize view names in the record
        if self.state.startup_view == "Last Selected":
            # If "Last Selected", we don't normalize it, and we keep current_view as is
            self.state.current_view = self._normalizeViewName(self.state.current_view)
        else:
            self.state.startup_view = self._normalizeViewName(self.state.startup_view)
            self.state.current_view = self.state.startup_view

        # Debounce timer for UI state saves
        self._save_timer = QTimer()
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self.saveUiState)

    @Property(str, notify=currentViewChanged)
    def currentView(self):  # type: ignore[reportRedeclaration]
        return self.state.current_view

    @currentView.setter  # type: ignore[func-attr]
    def currentView(self, value):
        normalized = self._normalizeViewName(value)
        if self.state.current_view != normalized:
            self.state.current_view = normalized
            self.saveUiState()
            self.currentViewChanged.emit()
            self.app.skillModelChanged.emit()

    @Property(int, notify=windowWidthChanged)
    def windowWidth(self):  # type: ignore[reportRedeclaration]
        return self.state.window_width

    @windowWidth.setter  # type: ignore[func-attr]
    def windowWidth(self, value):
        if self.state.window_width != value:
            # Pydantic validation will handle bounds in a real setter,
            # but here we update the record and let it validate.
            try:
                # We create a temporary copy to validate the single field update
                update = self.state.model_dump()
                update["window_width"] = value
                self.state = UIStateRecord.model_validate(update)
                self.triggerSave()
                self.windowWidthChanged.emit()
            except Exception:
                pass

    @Property(int, notify=windowHeightChanged)
    def windowHeight(self):  # type: ignore[reportRedeclaration]
        return self.state.window_height

    @windowHeight.setter  # type: ignore[func-attr]
    def windowHeight(self, value):
        if self.state.window_height != value:
            try:
                update = self.state.model_dump()
                update["window_height"] = value
                self.state = UIStateRecord.model_validate(update)
                self.triggerSave()
                self.windowHeightChanged.emit()
            except Exception:
                pass

    @Property(int, notify=windowXChanged)
    def windowX(self):  # type: ignore[reportRedeclaration]
        return self.state.window_x

    @windowX.setter  # type: ignore[func-attr]
    def windowX(self, value):
        if self.state.window_x != value:
            self.state.window_x = value
            self.triggerSave()
            self.windowXChanged.emit()

    @Property(int, notify=windowYChanged)
    def windowY(self):  # type: ignore[reportRedeclaration]
        return self.state.window_y

    @windowY.setter  # type: ignore[func-attr]
    def windowY(self, value):
        if self.state.window_y != value:
            self.state.window_y = value
            self.triggerSave()
            self.windowYChanged.emit()

    @Property(bool, notify=darkModeChanged)
    def darkMode(self):  # type: ignore[reportRedeclaration]
        return self.state.dark_mode

    @darkMode.setter  # type: ignore[func-attr]
    def darkMode(self, value):
        if self.state.dark_mode != value:
            self.state.dark_mode = value
            self.triggerSave()
            self.darkModeChanged.emit()

    @Property(str, notify=startupViewChanged)
    def startupView(self):  # type: ignore[reportRedeclaration]
        return self.state.startup_view

    @startupView.setter  # type: ignore[func-attr]
    def startupView(self, value):
        normalized = self._normalizeViewName(value)
        if self.state.startup_view != normalized:
            self.state.startup_view = normalized
            self.triggerSave()
            self.startupViewChanged.emit()

    @Property(bool, notify=rememberFiltersChanged)
    def rememberFilters(self):  # type: ignore[reportRedeclaration]
        return self.state.remember_filters

    @rememberFilters.setter  # type: ignore[func-attr]
    def rememberFilters(self, value):
        if self.state.remember_filters != value:
            self.state.remember_filters = value
            if not value:
                self.clearViewFilters()
            self.triggerSave()
            self.rememberFiltersChanged.emit()

    @Property(bool, notify=reducedMotionChanged)
    def reducedMotion(self):  # type: ignore[reportRedeclaration]
        return self.state.reduced_motion

    @reducedMotion.setter  # type: ignore[func-attr]
    def reducedMotion(self, value):
        if self.state.reduced_motion != value:
            self.state.reduced_motion = value
            self.triggerSave()
            self.reducedMotionChanged.emit()

    @Property(bool, notify=compactListRowsChanged)
    def compactListRows(self):  # type: ignore[reportRedeclaration]
        return self.state.compact_list_rows

    @compactListRows.setter  # type: ignore[func-attr]
    def compactListRows(self, value):
        if self.state.compact_list_rows != value:
            self.state.compact_list_rows = value
            self.triggerSave()
            self.compactListRowsChanged.emit()

    @Property(int, notify=inspectorWidthChanged)
    def inspectorWidth(self):  # type: ignore[reportRedeclaration]
        return self.state.inspector_width

    @inspectorWidth.setter  # type: ignore[func-attr]
    def inspectorWidth(self, value):
        value = int(value)
        if self.state.inspector_width != value:
            try:
                update = self.state.model_dump()
                update["inspector_width"] = value
                self.state = UIStateRecord.model_validate(update)
                self.triggerSave()
                self.inspectorWidthChanged.emit()
            except Exception:
                pass

    @Slot(int)
    def setInspectorWidth(self, value):
        self.inspectorWidth = value

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
            self.currentViewChanged.emit()  # Logo depends on it
            self.config.set("client_format", f)
            self.triggerSave()

    @Slot(str)
    def setStartupView(self, v):
        self.startupView = v

    @Slot(bool)
    def setRememberFilters(self, b):
        self.rememberFilters = b

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
        self.config.set("ui_state", self.state.model_dump())

    @Slot()
    def resetUiState(self):
        """Restores UI preferences and geometry to stable defaults."""
        self.blockSignals(True)
        try:
            self.state = UIStateRecord()
            self._clearAllViewFilters()
            self.saveUiState()
        finally:
            self.blockSignals(False)
        # Re-emit after unblocking so QML bindings update
        self.currentViewChanged.emit()
        self.windowWidthChanged.emit()
        self.windowHeightChanged.emit()
        self.windowXChanged.emit()
        self.windowYChanged.emit()
        self.startupViewChanged.emit()
        self.rememberFiltersChanged.emit()
        self.reducedMotionChanged.emit()
        self.compactListRowsChanged.emit()
        self.inspectorWidthChanged.emit()

    @staticmethod
    def _normalizeViewName(value: str) -> str:
        view = str(value or "").replace(" ", "").replace("-", "")
        view_map = {
            "quickcopy": "QuickCopy",
            "library": "Library",
            "updates": "Updates",
            "settings": "Settings",
            "lastselected": "Last Selected",
        }
        return view_map.get(view.lower(), "Library")

    @Slot(str, result=str)
    def getAssetUri(self, path: str) -> str:
        """Returns the absolute URI for an asset path."""
        if getattr(sys, "frozen", False):
            # PyInstaller sets ``sys._MEIPASS`` at runtime; the type-checker
            # stub doesn't know about it, so guard the attribute access the
            # same way we guard ``sys.frozen`` above.
            meipass = getattr(sys, "_MEIPASS", "")
            base = Path(meipass) / "assets"
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
            os.startfile(path)
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
            self.app.set_selected_skill({})
        else:
            self.app.set_selected_skill(self.app.skillModel.get_skill_at(index))

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
        if not self.state.remember_filters:
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
        model._begin_batch()
        try:
            model.filterText = ""
            model.categoryFilter = ""
            model.collectionFilter = False
            model.projectFilter = ""
        finally:
            model._end_batch()
        self.app._set_status("Filters cleared")

    def _clearAllViewFilters(self):
        """Clears filters for all models."""
        for model in [self.app._library_model, self.app._quick_copy_model]:
            model._begin_batch()
            try:
                model.filterText = ""
                model.categoryFilter = ""
                model.collectionFilter = False
                model.projectFilter = ""
            finally:
                model._end_batch()

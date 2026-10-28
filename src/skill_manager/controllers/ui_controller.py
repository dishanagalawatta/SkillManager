"""
Purpose: Manages UI state, window geometry, themes, and system shell actions.
Usage: Accessed via AppController.ui
"""

import contextlib
import logging
import os
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import Property, QTimer, Signal, Slot

from skill_manager.controllers.base import BaseController
from skill_manager.core.analytics import (
    capture_event,
    capture_exception,
    set_enabled as set_telemetry_enabled,
)
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
    windowMaximizedChanged = Signal()
    darkModeChanged = Signal()
    startupViewChanged = Signal()
    rememberFiltersChanged = Signal()
    reducedMotionChanged = Signal()
    telemetryEnabledChanged = Signal()
    tasksPanelOpenChanged = Signal()
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

        # Headless observers (the MCP server) disable persistence so rendering
        # Main.qml offscreen never overwrites the user's saved UI state.
        self._state_persistence_enabled = True

    def disable_state_persistence(self) -> None:
        """Stop this controller from writing ``ui_state`` to the user's config.

        Used by the headless MCP server: it loads ``Main.qml`` offscreen to
        inspect the UI, and that offscreen window would otherwise report its own
        geometry back through ``Main.qml``'s ``onXChanged``/``onWidthChanged``
        handlers (persisting e.g. ``window_x = 0`` over the user's real window
        position).
        """
        self._state_persistence_enabled = False
        with contextlib.suppress(Exception):
            self._save_timer.stop()

    @Property(str, notify=currentViewChanged)
    def currentView(self):  # type: ignore[reportRedeclaration]
        return self.state.current_view

    @currentView.setter  # type: ignore[func-attr]
    def currentView(self, value):
        normalized = self._normalizeViewName(value)
        if self.state.current_view != normalized:
            self.state.current_view = normalized
            self.app.set_selected_skill({})
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
            except Exception as exc:
                # The value is rejected (the record enforces the bounds),
                # but it must not vanish silently: an unsignalled property
                # leaves the QML binding and the model out of sync with no
                # way to tell why.
                logger.warning("Rejected window width %r: %s", value, exc)

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
            except Exception as exc:
                logger.warning("Rejected window height %r: %s", value, exc)

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

    @Property(bool, notify=windowMaximizedChanged)
    def windowMaximized(self):  # type: ignore[reportRedeclaration]
        return self.state.window_maximized

    @windowMaximized.setter  # type: ignore[func-attr]
    def windowMaximized(self, value):
        value = bool(value)
        if self.state.window_maximized != value:
            self.state.window_maximized = value
            self.triggerSave()
            self.windowMaximizedChanged.emit()

    @Property(bool, constant=True)
    def honorsWindowPosition(self):
        """Whether the window manager lets the app place its own window.

        Wayland does not: the compositor positions top-levels, ``setX``/``setY``
        are ignored and every window reports (0, 0). Persisting that would
        overwrite a real position saved during an X11/Windows session with a
        meaningless zero, so QML skips the position write-back there. Size and
        the maximized flag are still client-controlled and are always restored.
        """
        from PySide6.QtGui import QGuiApplication

        return not QGuiApplication.platformName().startswith("wayland")

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

    @Property(bool, notify=telemetryEnabledChanged)
    def telemetryEnabled(self):  # type: ignore[reportRedeclaration]
        return self.state.telemetry_enabled

    @Property(bool, notify=tasksPanelOpenChanged)
    def tasksPanelOpen(self):  # type: ignore[reportRedeclaration]
        """Whether the Quick Copy task panel is expanded."""
        return self.state.tasks_panel_open

    @tasksPanelOpen.setter  # type: ignore[func-attr]
    def tasksPanelOpen(self, value):
        value = bool(value)
        if self.state.tasks_panel_open != value:
            self.state.tasks_panel_open = value
            self.triggerSave()
            self.tasksPanelOpenChanged.emit()

    @telemetryEnabled.setter  # type: ignore[func-attr]
    def telemetryEnabled(self, value):
        value = bool(value)
        if self.state.telemetry_enabled != value:
            self.state.telemetry_enabled = value
            self.triggerSave()
            self.telemetryEnabledChanged.emit()
            # Apply immediately so disabling stops sending without a restart.
            set_telemetry_enabled(value)

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
            except Exception as exc:
                logger.warning("Rejected inspector width %r: %s", value, exc)

    @Slot(int)
    def setInspectorWidth(self, value):
        self.inspectorWidth = value

    @Slot(str, result=int)
    def getPanelWidth(self, key):
        """Persisted width for a named side panel, 0 when never resized."""
        return int(self.state.panel_widths.get(str(key), 0))

    @Slot(str, int)
    def setPanelWidth(self, key, value):
        """Persist a named side panel's width.

        ``0`` (and anything below it) means "no override": the key is dropped
        so the panel falls back to its own preferred width. Everything else is
        clamped to a range a panel can actually use.
        """
        key = str(key or "")
        if not key:
            return
        try:
            value = max(0, min(4096, int(value)))
        except (TypeError, ValueError) as exc:
            logger.warning("Rejected panel width %r=%r: %s", key, value, exc)
            return
        if self.state.panel_widths.get(key, 0) == value:
            return
        try:
            update = self.state.model_dump()
            widths = dict(update.get("panel_widths") or {})
            if value < 1:
                widths.pop(key, None)
            else:
                widths[key] = value
            update["panel_widths"] = widths
            self.state = UIStateRecord.model_validate(update)
            self.triggerSave()
        except Exception as exc:
            logger.warning("Rejected panel width %r=%r: %s", key, value, exc)

    @Property(str, notify=currentViewChanged)
    def logoSource(self):
        return self.getAssetUri(logo_asset_for_client(self.app.clientFormat))

    @Slot(str, result=str)
    def getLogoSource(self, fmt):
        return self.getAssetUri(logo_asset_for_client(fmt))

    @Slot(str, result=bool)
    def isMonochromeLogo(self, fmt: str) -> bool:
        """Returns True if the client format uses a single-color (monochrome) logo requiring Theme.label colorization."""
        fmt_lower = str(fmt or "").lower().strip()
        return fmt_lower in ("opencode", "plain text", "plaintext", "plain")

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
    def setTelemetryEnabled(self, b):
        self.telemetryEnabled = b

    @Slot(bool)
    def setTasksPanelOpen(self, b):
        self.tasksPanelOpen = b

    @Slot()
    def triggerSave(self):
        """Triggers a debounced save of the UI state."""
        if not self._state_persistence_enabled:
            return
        self._save_timer.start(1000)

    @Slot()
    def saveUiState(self):
        """Saves current window geometry and UI preferences to config."""
        if not self._state_persistence_enabled:
            return
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
        self.telemetryEnabledChanged.emit()
        self.tasksPanelOpenChanged.emit()
        self.inspectorWidthChanged.emit()
        # Defaults restore telemetry to on; keep the live client in step.
        set_telemetry_enabled(self.state.telemetry_enabled)

    @staticmethod
    def _normalizeViewName(value: str) -> str:
        view = str(value or "").replace(" ", "").replace("-", "")
        view_map = {
            "quickcopy": "QuickCopy",
            "library": "Library",
            "updates": "Updates",
            # The view is labelled "Packages" in the UI; the key stayed
            # "Updates" so existing configs keep working.
            "packages": "Updates",
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
        """Opens a file or folder using the system default application.

        SECURITY: system open commands on macOS/Linux are susceptible to
        argument injection when the path begins with a hyphen (e.g. ``--help``
        or tool-specific flags). We isolate the path as a positional argument:
        ``open -- <path>`` on macOS and ``./<path>`` prefix on Linux.
        Windows ``os.startfile`` does not parse a command line and is safe.
        """
        if not path:
            return
        try:
            if sys.platform == "win32":
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.run(["open", "--", path], check=True)
            else:
                safe_path = f"./{path}" if path.startswith("-") else path
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
            self.app.set_selected_skill({})
        else:
            self.app.set_selected_skill(self.app.skillModel.get_skill_at(index))

    @Slot()
    def selectAllVisibleSkills(self):
        """Selects all skills currently visible in the active model."""
        self.app.skillModel.selectAll()
        # ``selectAll`` skips rows hidden behind collapsed headers, so report
        # the collapse-aware count rather than the filtered one.
        count = getattr(
            self.app.skillModel, "visibleSelectedCount", self.app.skillModel.selectedCount
        )
        self.app._set_status(f"Selected {count} visible skills")

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

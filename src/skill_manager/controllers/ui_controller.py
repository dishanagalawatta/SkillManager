"""
Purpose: Manages UI state, window geometry, themes, and system shell actions.
Usage: Accessed via AppController.ui
"""

import os
import sys
from pathlib import Path

from PySide6.QtCore import QTimer

from skill_manager.controllers.base import BaseController
from skill_manager.core.analytics import capture_event


class UIController(BaseController):
    """Controller for UI and Window management."""

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

        # Normalize old values
        if self._current_view == "library":
            self._current_view = "Library"
        elif self._current_view == "quick-copy":
            self._current_view = "QuickCopy"
        self._startup_view = self._normalize_view_name(self._startup_view)
        self._current_view = self._startup_view

        # Debounce timer for UI state saves
        self._save_timer = QTimer()
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self.save_ui_state)

    def trigger_save(self):
        """Triggers a debounced save of the UI state."""
        if not self._save_timer.isActive():
            self._save_timer.start(2000)  # Save after 2s of inactivity

    def save_ui_state(self):
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

    def reset_ui_state(self):
        """Restores speed-focused UI preferences to stable defaults."""
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
        self.save_ui_state()

    @staticmethod
    def _normalize_view_name(value: str) -> str:
        view = str(value or "").replace(" ", "").replace("-", "")
        view_map = {
            "quickcopy": "QuickCopy",
            "library": "Library",
            "updates": "Updates",
            "settings": "Settings",
        }
        return view_map.get(view.lower(), "Library")

    def get_asset_uri(self, path: str) -> str:
        """Returns the absolute URI for an asset path."""
        if getattr(sys, "frozen", False):
            base = Path(sys._MEIPASS) / "assets"
        else:
            base = Path(__file__).resolve().parent.parent.parent.parent / "assets"

        full_path = base / path
        if not full_path.exists() and ("brand/" in path or "logo" in path):
            return self.get_asset_uri("brand/logo.png")

        return full_path.as_uri()

    def open_path(self, path: str):
        """Opens a file or folder using system default application."""
        if not path:
            return
        try:
            if sys.platform == "win32":
                os.startfile(path)
            elif sys.platform == "darwin":
                import subprocess

                subprocess.run(["open", path])
            else:
                import subprocess

                subprocess.run(["xdg-open", path])
            self.app._set_status(f"Opened: {os.path.basename(path)}")
        except Exception as e:
            self.app._set_status(f"Failed to open {path}: {e}")

    def launch_skill(self, path: str):
        """Launches a skill by opening its path."""
        self.app._set_status(f"Launching skill: {path}")
        capture_event("skill_launched")
        self.open_path(path)

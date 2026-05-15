"""
Purpose: Manages UI state, window geometry, themes, and system shell actions.
Usage: Accessed via AppController.ui
"""
import os
import sys
from pathlib import Path
from PySide6.QtCore import QTimer, Slot
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

        # Normalize old values
        if self._current_view == "library":
            self._current_view = "Library"
        elif self._current_view == "quick-copy":
            self._current_view = "QuickCopy"

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
        ui_state.update({
            "window_width": self._window_width,
            "window_height": self._window_height,
            "window_x": self._window_x,
            "window_y": self._window_y,
            "dark_mode": self._dark_mode,
            "current_view": self._current_view
        })
        self.config.set("ui_state", ui_state)

    def get_asset_uri(self, path: str) -> str:
        """Returns the absolute URI for an asset path."""
        if getattr(sys, 'frozen', False):
            base = Path(sys._MEIPASS) / "assets"
        else:
            base = Path(__file__).resolve().parent.parent.parent.parent / "assets"

        full_path = base / path
        if not full_path.exists():
            if "logo/" in path:
                full_path = base / "logo" / "logo.png"

        return full_path.as_uri()

    def open_path(self, path: str):
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
            self.app._set_status(f"Opened: {os.path.basename(path)}")
        except Exception as e:
            self.app._set_status(f"Failed to open {path}: {e}")

    def launch_skill(self, path: str):
        """Launches a skill by opening its path."""
        self.app._set_status(f"Launching skill: {path}")
        capture_event("skill_launched")
        self.open_path(path)

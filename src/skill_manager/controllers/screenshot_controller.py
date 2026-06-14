import datetime
import logging
import os
from pathlib import Path

from PySide6.QtCore import Property, QObject, QRect, Signal, Slot
from PySide6.QtGui import QColor, QGuiApplication, QPainter

logger = logging.getLogger(__name__)


class ScreenshotController(QObject):
    """Manages the screenshot capture and processing workflow."""

    showOverlay = Signal()
    captureFinished = Signal(str)  # Path to saved file
    minimizeRequested = Signal()
    captureCancelled = Signal()
    screenshotVersionChanged = Signal()

    @Slot()
    def cancelCapture(self):
        """Cancels the current screenshot and restores the application window."""
        try:
            self.captureCancelled.emit()
        except Exception:
            logger.warning("Exception during captureCancelled signal emission", exc_info=True)
        self._current_full_pixmap = None
        logger.info("Screenshot capture cancelled by user.")

    def __init__(self, app_controller):
        super().__init__()
        self.app = app_controller
        self._current_full_pixmap = None
        self._screenshot_version = 0

    @Property(int, notify=screenshotVersionChanged)
    def screenshotVersion(self):
        return self._screenshot_version

    @Slot()
    def takeScreenshot(self):
        """Captures the primary screen and signals QML to show the overlay."""
        logger.info(
            "takeScreenshot called, autoMinimize=%s",
            self.app.config_controller.autoMinimizeOnScreenshot,
        )
        if self.app.config_controller.autoMinimizeOnScreenshot:
            self.minimizeRequested.emit()
            logger.info("Auto-minimize enabled, requesting window minimize.")
            return

        screen = QGuiApplication.primaryScreen()
        if not screen:
            logger.error("No primary screen detected for screenshot.")
            return

        self._current_full_pixmap = screen.grabWindow(0)
        self.app.screenshot_provider.set_pixmap(self._current_full_pixmap)
        self._screenshot_version += 1
        self.screenshotVersionChanged.emit()
        self.showOverlay.emit()
        logger.info("Screenshot capture initiated, overlay requested.")

    @Slot()
    def captureScreen(self):
        """Captures the primary screen and shows the overlay."""
        screen = QGuiApplication.primaryScreen()
        if not screen:
            logger.error("No primary screen detected for screenshot.")
            return
        logger.info(
            "captureScreen: screen=%s, geometry=%s",
            screen.name(),
            screen.geometry(),
        )
        self._current_full_pixmap = screen.grabWindow(0)
        logger.info(
            "captureScreen: grabbed %dx%d pixmap",
            self._current_full_pixmap.width(),
            self._current_full_pixmap.height(),
        )
        self.app.screenshot_provider.set_pixmap(self._current_full_pixmap)
        self._screenshot_version += 1
        self.screenshotVersionChanged.emit()
        self.showOverlay.emit()
        logger.info("Screenshot capture initiated via captureScreen().")

    @Slot(QRect, list)
    def saveScreenshot(self, crop_rect: QRect, redactions: list):
        """Crops the image, applies redactions, saves to disk, and copies to clipboard."""
        if self._current_full_pixmap is None or self._current_full_pixmap.isNull():
            logger.error("No pixmap available to save.")
            return

        # 1. Create a copy and crop
        # Note: crop_rect comes from QML, coordinates should match the screen capture
        final_image = self._current_full_pixmap.copy(crop_rect)

        # 2. Draw redactions
        painter = QPainter(final_image)
        painter.setBrush(QColor("black"))
        painter.setPen(QColor("black"))

        for r in redactions:
            # redactions list of dicts: {'x': ..., 'y': ..., 'width': ..., 'height': ...}
            # coordinates are relative to the crop_rect
            rect = QRect(r["x"], r["y"], r["width"], r["height"])
            painter.drawRect(rect)

        painter.end()

        # 3. Determine save path
        project_label_or_path = self.app.quickCopyModel.projectFilter
        project_path = None
        matched_project = None

        # Match project label to absolute path
        from skill_manager.core.quick_copy import _project_root_for_project, project_label

        aliases = self.app.config_controller.project_aliases

        if project_label_or_path:
            for p in self.app.projects:
                if (
                    project_label(p, aliases, p) == project_label_or_path
                    or str(p) == project_label_or_path
                ):
                    project_path = str(_project_root_for_project(Path(p)))
                    matched_project = p
                    break

        if not project_path and self.app.projects:
            matched_project = self.app.projects[0]
            project_path = str(_project_root_for_project(Path(matched_project)))

        if not project_path:
            logger.warning("No active project found, cannot save screenshot.")
            self.app._set_status("No project selected to save screenshot.")
            return

        save_dir = os.path.join(project_path, ".agents", "screenshots")
        os.makedirs(save_dir, exist_ok=True)

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"Screenshot_{timestamp}.png"
        filepath = os.path.join(save_dir, filename)

        # 4. Save and Copy to Clipboard
        if final_image.save(filepath, "PNG"):
            if self.app.config_controller.temporaryScreenshots:
                from skill_manager.core.persistence import (
                    load_temp_screenshots_registry,
                    save_temp_screenshots_registry,
                )

                existing = load_temp_screenshots_registry()
                updated = list(set(existing + [filepath]))
                save_temp_screenshots_registry(updated)

            client_format = self.app.clientFormat
            if client_format == "Gemini CLI":
                # For Gemini CLI, copy the relative path reference
                ref = f"@.agents/screenshots/{filename}"
                QGuiApplication.clipboard().setText(ref)
                self.app._set_status(f"Screenshot saved. Path copied: {ref}")
            else:
                QGuiApplication.clipboard().setPixmap(final_image)
                self.app._set_status(f"Screenshot saved to {filename} and copied to clipboard.")

            self.captureFinished.emit(filepath)

            # Create a virtual skill for the new screenshot to avoid a full library refresh
            skill_data = {
                "name": filename,
                "folder_name": ".agents/screenshots",
                "local_path": filepath,
                "skill_md_path": filepath,
                "project_key": str(matched_project),
                "project_path": str(matched_project),
                "project_root": project_path,
                "project_label": project_label(matched_project, aliases, str(matched_project)),
                "main_category": "Special",
                "category": "Screenshots",
                "search_text": f"screenshot capture {filename}",
                "is_screenshot": True,
                "metadata": {"category": "Capture"},
            }

            self.app._library_model.addOrUpdateSkills([skill_data])
            self.app._quick_copy_model.addOrUpdateSkills([skill_data])

            if "Screenshots" not in set(self.app._categories):
                self.app._categories = sorted(set(self.app._categories) | {"Screenshots"})
                self.app.categoriesChanged.emit()
        else:
            logger.error("Failed to save screenshot to %s", filepath)
            self.app._set_status("Failed to save screenshot.")

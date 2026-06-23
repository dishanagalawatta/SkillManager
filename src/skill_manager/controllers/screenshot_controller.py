import datetime
import logging
import os
from pathlib import Path

from PySide6.QtCore import Property, QObject, QRect, Signal, Slot
from PySide6.QtGui import QGuiApplication

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
        self.current_full_pixmap = None
        logger.info("Screenshot capture cancelled by user.")

    def __init__(self, app_controller):
        super().__init__()
        self.app = app_controller
        self.current_full_pixmap = None
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

        self.current_full_pixmap = screen.grabWindow(0)
        self.app.screenshot_provider.set_pixmap(self.current_full_pixmap)
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
        self.current_full_pixmap = screen.grabWindow(0)
        logger.info(
            "captureScreen: grabbed %dx%d pixmap",
            self.current_full_pixmap.width(),
            self.current_full_pixmap.height(),
        )
        self.app.screenshot_provider.set_pixmap(self.current_full_pixmap)
        self._screenshot_version += 1
        self.screenshotVersionChanged.emit()
        self.showOverlay.emit()
        logger.info("Screenshot capture initiated via captureScreen().")

    @Slot(QRect, list)
    def saveScreenshot(self, crop_rect: QRect, raw_redactions: list):
        """Crops the image, applies redactions, saves to disk, and copies to clipboard."""
        from skill_manager.core.image_processing import ImageProcessor
        from skill_manager.core.schemas import ScreenshotParams

        if self.current_full_pixmap is None or self.current_full_pixmap.isNull():
            logger.error("No pixmap available to save.")
            return

        # 1. Validate inputs via Pydantic
        try:
            params = ScreenshotParams(
                crop_x=crop_rect.x(),
                crop_y=crop_rect.y(),
                crop_width=crop_rect.width(),
                crop_height=crop_rect.height(),
                redactions=raw_redactions,
            )
        except Exception as e:
            logger.error("Validation failed for screenshot parameters: %s", e)
            self.app._set_status("Failed to save: invalid crop or redaction parameters.")
            return

        validated_crop_rect = QRect(
            params.crop_x, params.crop_y, params.crop_width, params.crop_height
        )

        # 2. Process image
        try:
            final_image = ImageProcessor.crop_and_redact(
                self.current_full_pixmap, validated_crop_rect, params.redactions
            )
        except ValueError as e:
            logger.error("Image processing failed: %s", e)
            return

        # 3. Determine save path
        project_label_or_path = self.app.quickCopyModel.projectFilter
        project_path = None
        matched_project = None

        # Match project label to absolute path
        from skill_manager.core.quick_copy import project_label, project_root_for_project

        aliases = self.app.config_controller.project_aliases

        if project_label_or_path:
            for p in self.app.projects:
                if (
                    project_label(p, aliases, p) == project_label_or_path
                    or str(p) == project_label_or_path
                ):
                    candidate = str(project_root_for_project(Path(p)))
                    if Path(candidate).is_dir():
                        project_path = candidate
                        matched_project = p
                        break
                    logger.warning(
                        "Matched project root does not exist: %s (from %s)",
                        candidate,
                        p,
                    )

        if not project_path and self.app.projects:
            for p in self.app.projects:
                candidate = str(project_root_for_project(Path(p)))
                if Path(candidate).is_dir():
                    matched_project = p
                    project_path = candidate
                    break

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

            # Remove any stale screenshot entries before adding the new one
            self._cleanup_stale_screenshot_skills()

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
            self.app.ops._refresh_selected_skill(filepath)

            if "Screenshots" not in set(self.app._categories):
                self.app._categories = sorted(set(self.app._categories) | {"Screenshots"})
                self.app.categoriesChanged.emit()
        else:
            logger.error("Failed to save screenshot to %s", filepath)
            self.app._set_status("Failed to save screenshot.")

    def _cleanup_stale_screenshot_skills(self):
        """Remove skill entries whose screenshot files no longer exist on disk."""
        for model in (self.app._library_model, self.app._quick_copy_model):
            stale_paths = [
                s.local_path
                for s in model._all_skills
                if s.is_screenshot and s.local_path and not Path(s.local_path).exists()
            ]
            if stale_paths:
                logger.info("Removing %d stale screenshot entries", len(stale_paths))
                model.removeSkillsByPath(stale_paths)

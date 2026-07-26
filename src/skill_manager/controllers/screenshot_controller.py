import datetime
import logging
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from PySide6.QtCore import Property, QObject, QRect, Signal, Slot
from PySide6.QtGui import QGuiApplication, QPixmap

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Wayland capture helpers (subprocess-based)
# ---------------------------------------------------------------------------
# On Wayland, QScreen.grabWindow(0) always returns null because the
# compositor controls buffer access. We fall back to the FreeDesktop
# Portal Screenshot API via a standalone subprocess script, then to
# gnome-screenshot if the portal is unavailable.


def _portal_capture(output_path: str | None = None) -> str | None:
    """Capture the full screen via the FreeDesktop Portal Screenshot API.

    Runs ``portal_capture.py`` as a subprocess using the system Python
    (``/usr/bin/python3``) which has ``dbus-python`` and ``PyGObject``
    installed as system packages.  The portal API is called with
    ``interactive: False`` -- silent full-screen capture, no system UI.

    Returns the path to the saved PNG, or ``None`` on failure.
    """
    if output_path is None:
        output_path = tempfile.mktemp(suffix=".png")

    # Locate the helper script relative to this file
    script = Path(__file__).resolve().parent.parent / "utils" / "portal_capture.py"
    if not script.is_file():
        logger.error("Portal capture script not found: %s", script)
        return None

    try:
        proc = subprocess.run(
            ["/usr/bin/python3", str(script), output_path],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        logger.error("Portal capture subprocess timed out after 30s")
        return None

    if proc.returncode != 0:
        detail = proc.stderr.strip()[:200]
        logger.warning("Portal capture failed (rc=%d): %s", proc.returncode, detail)
        return None

    path = proc.stdout.strip()
    if path and os.path.isfile(path):
        return path

    logger.warning("Portal capture returned no valid output path")
    return None


def _gnome_screenshot_capture(output_path: str | None = None) -> str | None:
    """Fallback: full-screen capture via the ``gnome-screenshot`` CLI.

    Runs ``gnome-screenshot -f <path>`` silently (no UI).
    Returns the path or ``None`` on failure.
    """
    if output_path is None:
        output_path = tempfile.mktemp(suffix=".png")

    try:
        proc = subprocess.run(
            ["gnome-screenshot", "-f", output_path],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except FileNotFoundError:
        logger.warning("gnome-screenshot not found on PATH")
        return None
    except subprocess.TimeoutExpired:
        logger.warning("gnome-screenshot timed out after 15s")
        return None

    if proc.returncode == 0 and os.path.isfile(output_path):
        return output_path

    detail = proc.stderr.strip()[:200]
    logger.warning("gnome-screenshot failed (rc=%d): %s", proc.returncode, detail)
    return None


def _capture_strategies():
    """Yield ``(name, callable)`` pairs tried in order on Wayland.

    Implemented as a generator so unit tests can patch the individual
    strategy functions.
    """
    yield "Portal", _portal_capture
    yield "gnome-screenshot", _gnome_screenshot_capture


# ---------------------------------------------------------------------------
# ScreenshotController
# ---------------------------------------------------------------------------


class ScreenshotController(QObject):
    showOverlay = Signal()
    captureFinished = Signal(str)
    minimizeRequested = Signal()
    captureCancelled = Signal()
    screenshotVersionChanged = Signal()

    def __init__(self, app_controller):
        super().__init__()
        self.app = app_controller
        self.current_full_pixmap = None
        self._screenshot_version = 0
        self._wayland_deferred = False

    @Property(int, notify=screenshotVersionChanged)
    def screenshotVersion(self):
        return self._screenshot_version

    @Property(bool, notify=showOverlay)
    def screenshotValid(self):
        return self.current_full_pixmap is not None and not self.current_full_pixmap.isNull()

    @Slot()
    def cancelCapture(self):
        try:
            self.captureCancelled.emit()
        except Exception:
            logger.warning("Exception during captureCancelled signal emission", exc_info=True)
        self.current_full_pixmap = None
        self._wayland_deferred = False
        logger.info("Screenshot capture cancelled.")

    # ------------------------------------------------------------------
    # Capture entry-points
    # ------------------------------------------------------------------

    @Slot()
    def takeScreenshot(self):
        logger.info(
            "takeScreenshot called, autoMinimize=%s",
            self.app.config_controller.autoMinimizeOnScreenshot,
        )
        if self.app.config_controller.autoMinimizeOnScreenshot:
            self.minimizeRequested.emit()
            logger.info("Auto-minimize enabled, requesting window minimize.")
            return

        self._initiate_capture()

    @Slot()
    def captureScreen(self):
        self._initiate_capture()

    # ------------------------------------------------------------------
    # Core capture logic
    # ------------------------------------------------------------------

    def _initiate_capture(self):
        screen = QGuiApplication.primaryScreen()
        if not screen:
            logger.error("No primary screen detected for screenshot.")
            return

        self._wayland_deferred = False
        self.current_full_pixmap = screen.grabWindow(0)
        if self.current_full_pixmap is not None and not self.current_full_pixmap.isNull():
            self._show_captured_pixmap()
            return

        if sys.platform == "linux":
            logger.info("grabWindow(0) returned null; deferred Wayland capture")
            self._wayland_deferred = True
            self._show_captured_pixmap()
            return

        self._fail_capture("Screen capture not available on this display server.")

    def _show_captured_pixmap(self):
        if self.current_full_pixmap is not None and not self.current_full_pixmap.isNull():
            self.app.screenshot_provider.set_pixmap(self.current_full_pixmap)
            self._screenshot_version += 1
            self.screenshotVersionChanged.emit()
        self.showOverlay.emit()
        logger.info("Screenshot overlay shown.")

    def _fail_capture(self, message: str):
        self.current_full_pixmap = None
        self._wayland_deferred = False
        self.app._set_status(f"Screenshot failed: {message}")
        self.captureCancelled.emit()

    # ------------------------------------------------------------------
    # Wayland deferred capture (called from saveScreenshot)
    # ------------------------------------------------------------------

    def _capture_full_screen(self) -> QPixmap | None:
        self.app._set_status("Capturing screen...")
        for name, strategy in _capture_strategies():
            filepath = strategy()
            if filepath:
                pixmap = QPixmap(filepath)
                if not pixmap.isNull():
                    logger.info(
                        "Deferred capture via %s succeeded: %s (%dx%d)",
                        name,
                        filepath,
                        pixmap.width(),
                        pixmap.height(),
                    )
                    return pixmap
                logger.error("%s returned unreadable file: %s", name, filepath)
            else:
                logger.info("Capture via %s returned no file", name)
        return None

    # ------------------------------------------------------------------
    # Save processed screenshot
    # ------------------------------------------------------------------

    @Slot(QRect, list)
    def saveScreenshot(self, crop_rect: QRect, raw_redactions: list):
        from skill_manager.core.image_processing import ImageProcessor
        from skill_manager.core.schemas import ScreenshotParams

        finished = False
        try:
            if self._wayland_deferred:
                captured = self._capture_full_screen()
                if captured is None:
                    self._wayland_deferred = False
                    self.app._set_status(
                        "Screenshot failed: Unable to capture screen on Wayland. "
                        "Install xdg-desktop-portal or gnome-screenshot."
                    )
                    return
                self.current_full_pixmap = captured
                self._wayland_deferred = False

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

            # 3. Determine save path -- relative to the selected project root
            project_label_or_path = self.app.quickCopyModel.projectFilter
            project_path = None
            matched_project = None

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
                cwd = os.getcwd()
                project_path = cwd
                matched_project = cwd
                logger.warning(
                    "No project matched, falling back to CWD: %s/.agents/screenshots/", cwd
                )

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
                    ref = f"@.agents/screenshots/{filename}"
                    QGuiApplication.clipboard().setText(ref)
                    self.app._set_status(f"Screenshot saved. Path copied: {ref}")
                else:
                    QGuiApplication.clipboard().setPixmap(final_image)
                    self.app._set_status(f"Screenshot saved to {filename} and copied to clipboard.")

                finished = True
                self.captureFinished.emit(filepath)

                self._cleanup_stale_screenshot_skills()

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
        finally:
            if not finished:
                self.captureCancelled.emit()

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

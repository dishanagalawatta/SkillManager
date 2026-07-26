import datetime
import logging
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from PySide6.QtCore import Property, QObject, QRect, Signal, Slot
from PySide6.QtDBus import QDBus, QDBusConnection, QDBusInterface
from PySide6.QtGui import QGuiApplication, QPixmap

from skill_manager.core.image_processing import ImageProcessor
from skill_manager.core.persistence import (
    load_temp_screenshots_registry,
    save_temp_screenshots_registry,
)
from skill_manager.core.quick_copy import project_label, project_root_for_project
from skill_manager.core.schemas import ScreenshotParams

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Wayland capture helpers (Portal, gnome-screenshot)
# ---------------------------------------------------------------------------
# On Wayland, QScreen.grabWindow(0) always returns null because the
# compositor controls buffer access.  We try two strategies in order:
#
#   1. FreeDesktop Portal        — subprocess-based GLib DBus call.
#      Before spawning, pre-authorises via PermissionStore so the portal
#      skips the dialog when the app has a desktop-file association.
#      *Known issue*: on GNOME 50 the portal's Screenshot method returns
#      a request handle but never emits the Response signal.
#
#   2. gnome-screenshot CLI       — last resort fallback (needs the
#      binary installed).


def _pre_authorize_portal(bus: QDBusConnection | None = None) -> None:
    """Pre-authorize the screenshot portal via PermissionStore.

    Sets a ``['yes']`` entry in the ``screenshot`` permission table for
    the desktop-file app ID ``skill-manager``.  When SkillManager is
    launched from the desktop (associated ``.desktop`` file), the portal
    backend uses ``g_desktop_app_info_get_from_pid()`` to determine the
    caller's app ID and finds this entry — skipping the permission dialog.

    This is harmless if the app is launched from a terminal (no desktop-file
    association): the portal simply won't find the entry and falls through
    to the dialog.
    """
    if bus is None:
        bus = QDBusConnection.sessionBus()
    if not bus or not bus.isConnected():
        return

    store = QDBusInterface(
        "org.freedesktop.impl.portal.PermissionStore",
        "/org/freedesktop/impl/portal/PermissionStore",
        "org.freedesktop.impl.portal.PermissionStore",
        bus,
    )
    if not store.isValid():
        logger.warning("Pre-authorize: PermissionStore interface not available")
        return

    app_id = "skill-manager"
    store.callWithArgumentList(
        QDBus.AutoDetect,
        "SetPermission",
        ["screenshot", True, app_id, app_id, ["yes"]],
    )
    logger.info("Pre-authorized screenshot portal for app_id=%s", app_id)


def _find_portal_python() -> str | None:
    """Find a Python interpreter with ``dbus`` and ``gi.repository`` available.

    Priority order (deduplicated):
    1. ``/usr/bin/python3`` — system Python (has ``python3-dbus`` /
       ``python3-gi`` on standard GNOME installs).
    2. ``sys.executable`` — current venv Python.
    3. Any ``python3`` on ``PATH``.
    """
    seen: set[str] = set()
    for candidate in ("/usr/bin/python3", sys.executable, "python3"):
        if candidate in seen:
            continue
        seen.add(candidate)
        if not os.path.isfile(candidate):
            continue
        try:
            result = subprocess.run(
                [candidate, "-c", "import dbus, gi.repository; print('ok')"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return candidate
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    return None


def _portal_capture(output_path: str | None = None) -> str | None:
    """Capture the full screen via the FreeDesktop Portal Screenshot API.

    Spawns ``portal_capture.py`` as a subprocess so the GLib mainloop it
    requires does not conflict with PySide6's event loop.  The permission
    store is pre-authorised in-process first (persistent storage) so the
    portal backend skips the dialog when the app has a desktop-file
    association.

    Returns the path to the saved PNG, or ``None`` on failure.
    """
    if output_path is None:
        output_path = tempfile.mktemp(suffix=".png")

    # Pre-authorise via PermissionStore (persistent — benefits the
    # subprocess even though it has a different PID).
    _pre_authorize_portal()

    # Locate the helper script relative to this file
    script = Path(__file__).resolve().parent.parent / "utils" / "portal_capture.py"
    if not script.is_file():
        logger.error("Portal capture script not found: %s", script)
        return None

    python_cmd = _find_portal_python()
    if python_cmd is None:
        logger.warning("Portal capture: no Python interpreter with dbus-python found")
        return None

    logger.info("Portal capture: spawning subprocess with %s ...", python_cmd)
    try:
        proc = subprocess.run(
            [python_cmd, str(script), output_path],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except FileNotFoundError:
        logger.error("Portal capture: Python interpreter not found: %s", python_cmd)
        return None
    except subprocess.TimeoutExpired:
        logger.warning("Portal capture subprocess timed out after 30s")
        return None

    if proc.returncode != 0:
        detail = proc.stderr.strip()[:500]
        logger.warning("Portal capture failed (rc=%d): %s", proc.returncode, detail)
        return None

    path = proc.stdout.strip()
    if path and os.path.isfile(path):
        logger.info("Portal capture succeeded: %s", path)
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

    1. **Portal** — xdg-desktop-portal Screenshot API (primary).
       Pre-authorises via PermissionStore so the dialog is skipped when
       the app has a desktop-file association.

    2. **gnome-screenshot** — CLI fallback (last resort).

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
            logger.info("Deferred capture: trying strategy '%s'...", name)
            try:
                filepath = strategy()
            except Exception as e:
                logger.error(
                    "Deferred capture: strategy '%s' raised exception: %s",
                    name,
                    e,
                    exc_info=True,
                )
                continue
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
                logger.warning("Capture via %s returned no file", name)
        logger.error("All capture strategies failed!")
        return None

    # ------------------------------------------------------------------
    # Save processed screenshot
    # ------------------------------------------------------------------

    def _resolve_save_path(self, project_label_or_path: str | None) -> tuple[str, str, str]:
        """Resolve ``(project_path, matched_project, label)`` from current project filter.

        Falls back to ``os.getcwd()`` for all three fields when no project
        is configured or none of the registered projects match.
        """
        if not project_label_or_path or not self.app.projects:
            cwd = os.getcwd()
            return cwd, cwd, cwd

        aliases = self.app.config_controller.project_aliases

        # First pass: match by label or path
        for p in self.app.projects:
            if (
                project_label(p, aliases, p) == project_label_or_path
                or str(p) == project_label_or_path
            ):
                candidate = str(project_root_for_project(Path(p)))
                if Path(candidate).is_dir():
                    return candidate, str(p), project_label(p, aliases, p)
                logger.warning(
                    "Matched project root does not exist: %s (from %s)",
                    candidate,
                    p,
                )

        # Second pass: first project with an existing root directory
        for p in self.app.projects:
            candidate = str(project_root_for_project(Path(p)))
            if Path(candidate).is_dir():
                return candidate, str(p), project_label(p, aliases, p)

        cwd = os.getcwd()
        logger.warning("No project matched, falling back to CWD: %s/.agents/screenshots/", cwd)
        return cwd, cwd, cwd

    def _save_and_register(
        self,
        final_image: QPixmap,
        project_path: str,
        matched_project: str,
        project_label_text: str,
    ) -> str | None:
        """Persist ``final_image`` to disk, update clipboard + library.

        Builds the target path ``<project_path>/.agents/screenshots/Screenshot_<ts>.png``,
        saves the file, copies a reference to the clipboard, and registers
        the screenshot as a skill entry in both library models.

        Returns the absolute filepath on success, or ``None`` on failure.
        """
        save_dir = os.path.join(project_path, ".agents", "screenshots")
        os.makedirs(save_dir, exist_ok=True)

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"Screenshot_{timestamp}.png"
        filepath = os.path.join(save_dir, filename)

        if not final_image.save(filepath, "PNG"):
            logger.error("Failed to save screenshot to %s", filepath)
            self.app._set_status("Failed to save screenshot.")
            return None

        # -- Temporary screenshots registry --
        if self.app.config_controller.temporaryScreenshots:
            existing = load_temp_screenshots_registry()
            updated = list(set(existing + [filepath]))
            save_temp_screenshots_registry(updated)

        # -- Clipboard --
        client_format = self.app.clientFormat
        if client_format == "Gemini CLI":
            ref = f"@.agents/screenshots/{filename}"
            QGuiApplication.clipboard().setText(ref)
            self.app._set_status(f"Screenshot saved. Path copied: {ref}")
        else:
            QGuiApplication.clipboard().setPixmap(final_image)
            self.app._set_status(f"Screenshot saved to {filename} and copied to clipboard.")

        # -- Library registration --
        self._cleanup_stale_screenshot_skills()

        skill_data = {
            "name": filename,
            "folder_name": ".agents/screenshots",
            "local_path": filepath,
            "skill_md_path": filepath,
            "project_key": matched_project,
            "project_path": matched_project,
            "project_root": project_path,
            "project_label": project_label_text,
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

        return filepath

    @Slot(QRect, list)
    def saveScreenshot(self, crop_rect: QRect, raw_redactions: list):
        """Orchestrate the screenshot save flow.

        1. If capture was deferred on Wayland, try portal / gnome-screenshot.
        2. Validate crop + redaction parameters via Pydantic.
        3. Crop / redact the pixmap.
        4. Resolve the project save path.
        5. Persist to disk, update clipboard, register in skill library.
        """
        # ---- Phase 1: Wayland deferred capture ----
        if self._wayland_deferred:
            captured = self._capture_full_screen()
            if captured is None:
                self._wayland_deferred = False
                logger.warning(
                    "All Wayland capture strategies failed — this is likely a "
                    "portal-gnome 50.0 server-side bug (journal shows "
                    "'InteractiveScreenshot didn't return a file').  "
                    "Use PrtSc / Shift+PrtSc as a workaround."
                )
                self.app._set_status(
                    "Screenshot unavailable on this GNOME version. "
                    "Use PrtSc or Super+Shift+S as a workaround."
                )
                self.captureCancelled.emit()
                return
            self.current_full_pixmap = captured
            self._wayland_deferred = False

        if self.current_full_pixmap is None or self.current_full_pixmap.isNull():
            logger.error("No pixmap available to save.")
            self.captureCancelled.emit()
            return

        # ---- Phase 2: Validate ----
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
            self.captureCancelled.emit()
            return

        validated_crop_rect = QRect(
            params.crop_x, params.crop_y, params.crop_width, params.crop_height
        )

        # ---- Phase 3: Process ----
        try:
            final_image = ImageProcessor.crop_and_redact(
                self.current_full_pixmap, validated_crop_rect, params.redactions
            )
        except ValueError as e:
            logger.error("Image processing failed: %s", e)
            self.captureCancelled.emit()
            return

        # ---- Phase 4: Resolve path ----
        project_path, matched_project, label = self._resolve_save_path(
            self.app.quickCopyModel.projectFilter
        )

        # ---- Phase 5: Persist + register ----
        filepath = self._save_and_register(final_image, project_path, matched_project, label)
        if filepath is None:
            self.captureCancelled.emit()
            return

        self.captureFinished.emit(filepath)

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

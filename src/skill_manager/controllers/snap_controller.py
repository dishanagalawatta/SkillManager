import datetime
import logging
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from PySide6.QtCore import Property, QObject, QRect, Signal, Slot
from PySide6.QtDBus import QDBus, QDBusConnection, QDBusInterface
from PySide6.QtGui import QGuiApplication, QPixmap

from skill_manager.core import quick_copy
from skill_manager.core.image_processing import ImageProcessor
from skill_manager.core.persistence import (
    load_temp_snaps_registry,
    save_temp_snaps_registry,
)
from skill_manager.core.schemas import SnapParams
from skill_manager.utils.notifications import close_notification, send_notification

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Wayland capture helpers (Portal, gnome-screenshot)
# ---------------------------------------------------------------------------
# On Wayland, QScreen.grabWindow(0) always returns null because the
# compositor controls buffer access.  We try two strategies in order:
#
#   1. FreeDesktop Portal        — subprocess-based GLib DBus call.
#      Before spawning, pre-authorises via PermissionStore so the portal
#      skips the dialog entirely (GNOME refuses the dialog for unfocused
#      apps, so pre-authorisation is what makes minimized captures work).
#
#   2. gnome-screenshot CLI — last resort fallback (needs the
#      binary installed).


#: Permissions IDs the xdg-desktop-portal daemon (>= 1.21, incl. Ubuntu
#: snap patches) resolves for SkillManager.  The daemon looks up the
#: caller's *permissions ID* — derived from the systemd user unit
#: (``sd_pid_get_user_unit``) or snap metadata — as the key in the
#: ``screenshot`` permission table (permission ID ``screenshot``):
#: ``""`` = terminal/ptyxis launch (no ``app-`` scope), ``skill-manager`` =
#: desktop-file launch, ``skill-manager.desktop`` = legacy key.
_PORTAL_PERMISSION_IDS: tuple[str, ...] = (
    "",
    "skill-manager",
    "skill-manager.desktop",
)


def _pre_authorize_portal(bus: QDBusConnection | None = None) -> None:
    """Pre-authorize the snap portal via PermissionStore.

    xdg-desktop-portal resolves the calling process's *permissions ID*
    (not the desktop-file app ID) and looks it up in the ``snap``
    permission table under the permission ID ``screenshot``.  Only when
    that key is missing does the portal show the interactive access dialog
    — which GNOME 50 refuses for unfocused apps ("Only the focused app is
    allowed to show a system access dialog").

    We therefore write a ``['yes']`` entry for every permissions ID the
    app can resolve to (terminal launch → ``""``, desktop launch →
    ``skill-manager``) so the dialog is skipped regardless of how the app
    was started or whether it is focused/minimized.
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

    for permission_id in _PORTAL_PERMISSION_IDS:
        store.callWithArgumentList(
            QDBus.AutoDetect,
            "SetPermission",
            ["screenshot", True, "screenshot", permission_id, ["yes"]],
        )
        logger.info("Pre-authorized snap portal for permission_id=%r", permission_id)


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
    """Capture the full screen via the FreeDesktop Portal Snap API.

    Spawns ``portal_capture.py`` as a subprocess so the GLib mainloop it
    requires does not conflict with PySide6's event loop.  The permission
    store is pre-authorised in-process first (persistent storage) so the
    portal backend skips the dialog when the app has a desktop-file
    association.

    Returns the path to the saved PNG, or ``None`` on failure.
    """
    if output_path is None:
        # SECURITY: Use mkstemp instead of mktemp to prevent TOCTOU race conditions
        fd, output_path = tempfile.mkstemp(suffix=".png")
        os.close(fd)

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


def _gnome_snap_capture(output_path: str | None = None) -> str | None:
    """Fallback: full-screen capture via the ``gnome-screenshot`` CLI.

    Runs ``gnome-screenshot -f <path>`` silently (no UI).
    Returns the path or ``None`` on failure.
    """
    if output_path is None:
        # SECURITY: Use mkstemp instead of mktemp to prevent TOCTOU race conditions
        fd, output_path = tempfile.mkstemp(suffix=".png")
        os.close(fd)

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

    1. **Portal** — xdg-desktop-portal Snap API (primary).
       Pre-authorises via PermissionStore so the dialog is skipped when
       the app has a desktop-file association.

    2. **gnome-screenshot** — CLI fallback (last resort).

    Implemented as a generator so unit tests can patch the individual
    strategy functions.
    """
    yield "Portal", _portal_capture
    yield "gnome-snap", _gnome_snap_capture


# ---------------------------------------------------------------------------
# SnapController
# ---------------------------------------------------------------------------


class SnapController(QObject):
    showOverlay = Signal()
    captureFinished = Signal(str)
    minimizeRequested = Signal()
    captureCancelled = Signal()
    snapVersionChanged = Signal()

    def __init__(self, app_controller):
        super().__init__()
        self.app = app_controller
        self.current_full_pixmap = None
        self._snap_version = 0
        self._wayland_deferred = False
        self._last_snap_time = 0.0

    @Property(int, notify=snapVersionChanged)
    def snapVersion(self):
        return self._snap_version

    @Property(bool, notify=showOverlay)
    def snapValid(self):
        return self.current_full_pixmap is not None and not self.current_full_pixmap.isNull()

    @Slot()
    def cancelCapture(self):
        try:
            self.captureCancelled.emit()
        except Exception:
            logger.warning("Exception during captureCancelled signal emission", exc_info=True)
        self.current_full_pixmap = None
        self._wayland_deferred = False
        logger.info("Snap capture cancelled.")

    @Slot()
    def notifyCapturePending(self):
        """Show a notification inviting the user to activate the capture.

        Called by Main.qml when the overlay cannot be raised because the app
        is not the active window (GNOME Wayland stacks inactive windows
        below).  Clicking the notification makes the app active, which lets
        the overlay map on top.
        """
        logger.info(
            "Capture overlay deferred: app window not active — "
            "activation notification sent (one click/activation required)"
        )
        send_notification("Skill Manager", "Capture is ready — click to start selecting")

    @Slot()
    def notifyCaptureActivation(self):
        """Dismiss the 'activation pending' notification once the app is active.

        Called by Main.qml when the capture-activation gate completes (the
        user clicked the notification or the taskbar entry, making the app
        active again).  The notification is closed so it does not linger.
        """
        logger.info("Capture overlay activation complete — mapping overlay now")
        close_notification()

    # ------------------------------------------------------------------
    # Capture entry-points
    # ------------------------------------------------------------------

    @Slot()
    def takeSnap(self):
        now = time.time()
        if now - self._last_snap_time < 0.5:
            logger.info("takeSnap ignored — duplicate call within 500ms")
            return
        self._last_snap_time = now

        logger.info(
            "takeSnap called, autoMinimize=%s",
            self.app.config_controller.autoMinimizeOnSnap,
        )
        if self.app.config_controller.autoMinimizeOnSnap:
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
            logger.error("No primary screen detected for snap.")
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
            self.app.snap_provider.set_pixmap(self.current_full_pixmap)
            self._snap_version += 1
            self.snapVersionChanged.emit()
        self.showOverlay.emit()
        logger.info("showOverlay signal emitted — QML decides how the overlay is mapped")

    def _fail_capture(self, message: str):
        self.current_full_pixmap = None
        self._wayland_deferred = False
        self.app._set_status(f"Snap failed: {message}")
        self.captureCancelled.emit()

    # ------------------------------------------------------------------
    # Wayland deferred capture (called from saveSnap)
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
    # Save processed snap
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
            lbl = quick_copy.project_label(p, aliases, p)
            if lbl == project_label_or_path or str(p) == project_label_or_path:
                candidate = str(quick_copy.project_root_for_project(Path(p)))
                if Path(candidate).is_dir():
                    return candidate, str(p), lbl
                logger.warning(
                    "Matched project root does not exist: %s (from %s)",
                    candidate,
                    p,
                )

        # Second pass: first project with an existing root directory
        for p in self.app.projects:
            candidate = str(quick_copy.project_root_for_project(Path(p)))
            if Path(candidate).is_dir():
                return candidate, str(p), quick_copy.project_label(p, aliases, p)

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
        the snap as a skill entry in both library models.

        Returns the absolute filepath on success, or ``None`` on failure.
        """
        save_dir = os.path.join(project_path, ".agents", "screenshots")
        os.makedirs(save_dir, exist_ok=True)

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"Screenshot_{timestamp}.png"
        filepath = os.path.join(save_dir, filename)

        if not final_image.save(filepath, "PNG"):
            logger.error("Failed to save snap to %s", filepath)
            self.app._set_status("Failed to save snap.")
            return None

        # -- Temporary screenshots registry --
        if self.app.config_controller.temporarySnaps:
            existing = load_temp_snaps_registry()
            updated = list(set(existing + [filepath]))
            save_temp_snaps_registry(updated)

        # -- Clipboard --
        client_format = self.app.clientFormat
        auto_copy_client_format = self.app.config_controller.autoCopySnapClientFormat
        if auto_copy_client_format or client_format == "Gemini CLI":
            from skill_manager.core.quick_copy import format_project_skill_reference

            temp_skill = {
                "name": filename,
                "folder_name": ".agents/screenshots",
                "local_path": filepath,
                "project_root": project_path,
                "is_snap": True,
            }
            ref = format_project_skill_reference(temp_skill, client_format)
            QGuiApplication.clipboard().setText(ref)
            self.app._set_status(f"Snap saved. Path copied: {ref}")
        else:
            QGuiApplication.clipboard().setPixmap(final_image)
            self.app._set_status(f"Snap saved to {filename} and copied to clipboard.")

        # -- Library registration --
        self._cleanup_stale_snap_skills()

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
            "category": "Snaps",
            "search_text": f"snap capture {filename}",
            "is_snap": True,
            "metadata": {"category": "Capture"},
        }

        self.app._library_model.addOrUpdateSkills([skill_data])
        self.app._quick_copy_model.addOrUpdateSkills([skill_data])
        self.app.ops._refresh_selected_skill(filepath)

        if "Snaps" not in set(self.app._categories):
            self.app._categories = sorted(set(self.app._categories) | {"Snaps"})
            self.app.categoriesChanged.emit()

        # -- Auto-select in Quick Copy --
        if self.app.config_controller.autoSelectSnapInQuickCopy:
            self.app.ui_controller.currentView = "QuickCopy"
            self.app._quick_copy_model.selectByPaths([filepath])
            self.app.set_selected_skill(skill_data)

        return filepath

    @Slot(QRect, list)
    def saveSnap(self, crop_rect: QRect, raw_redactions: list):
        """Orchestrate the snap save flow.

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
                    "Snap unavailable on this GNOME version. "
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
            params = SnapParams(
                crop_x=crop_rect.x(),
                crop_y=crop_rect.y(),
                crop_width=crop_rect.width(),
                crop_height=crop_rect.height(),
                redactions=raw_redactions,
            )
        except Exception as e:
            logger.error("Validation failed for snap parameters: %s", e)
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

    def _cleanup_stale_snap_skills(self):
        """Remove skill entries whose snap files no longer exist on disk."""
        for model in (self.app._library_model, self.app._quick_copy_model):
            stale_paths = [
                s.local_path
                for s in model._all_skills
                if s.is_snap and s.local_path and not Path(s.local_path).exists()
            ]
            if stale_paths:
                logger.info("Removing %d stale snap entries", len(stale_paths))
                model.removeSkillsByPath(stale_paths)

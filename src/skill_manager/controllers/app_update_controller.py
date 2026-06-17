"""
Purpose: Controller for application updates, delegating to AppUpdateService.
Refactored to use Pydantic for state management and decoupled service logic.
"""

import logging
import sys

from PySide6.QtCore import Property, Signal, Slot

import skill_manager
from skill_manager.controllers.base import BaseController
from skill_manager.core.config import get_app_data_dir
from skill_manager.core.diagnostics import (
    CATEGORY_APP_UPDATE_APPLIED,
    CATEGORY_APP_UPDATE_AVAILABLE,
    CATEGORY_APP_UPDATE_CHECK,
    CATEGORY_APP_UPDATE_FAILED,
    CATEGORY_APP_UPDATE_SKIPPED_DEV,
    CATEGORY_APP_UPDATE_UP_TO_DATE,
    get_diagnostic_logger,
)
from skill_manager.core.schemas import AppUpdateState
from skill_manager.core.update_service import AppUpdateService

logger = logging.getLogger(__name__)


class AppUpdateController(BaseController):
    """Controller for application updates."""

    # QML Signals
    updateStateChanged = Signal()
    updateProgressChanged = Signal(float)

    # Legacy signals for QML compatibility
    updateAvailableChanged = Signal()
    latestVersionChanged = Signal()
    isUpdatingChanged = Signal()
    isCheckingForUpdatesChanged = Signal()

    def __init__(self, app):
        super().__init__(app)
        self._diag = get_diagnostic_logger()

        # Initialize State
        self._state = AppUpdateState(
            current_version=skill_manager.__version__, latest_version=skill_manager.__version__
        )

        # Initialize Service
        tuf_dir = get_app_data_dir() / "tuf"
        target_dir = get_app_data_dir() / "updates"
        self._service = AppUpdateService(tuf_dir, target_dir)

    # --- Properties ---

    @Property(bool, notify=updateAvailableChanged)
    def updateAvailable(self):
        return self._state.update_available

    @Property(str, notify=latestVersionChanged)
    def latestVersion(self):
        return self._state.latest_version

    @Property(str, constant=True)
    def currentVersion(self):
        return self._state.current_version

    @Property(str, constant=True)
    def downloadUrl(self):
        # This is primarily for manual downloads if auto fails
        return "https://github.com/dishanagalawatta/SkillManager/releases/latest"

    @Property(bool, notify=isUpdatingChanged)
    def isUpdating(self):
        return self._state.is_updating

    @Property(float, notify=updateProgressChanged)
    def updateProgress(self):
        return self._state.progress

    @Property(bool, notify=isCheckingForUpdatesChanged)
    def isCheckingForUpdates(self):
        return self._state.is_checking

    @Property(bool, notify=updateStateChanged)
    def hasCheckedForUpdates(self):
        return self._state.has_checked

    # --- Slots ---

    @Slot()
    @Slot(bool)
    def checkForUpdates(self, manual=False):
        """Checks for updates asynchronously using the service."""
        if self._state.is_updating or self._state.is_checking:
            return

        # Skip check in development mode unless manual
        if not getattr(sys, "frozen", False) and not manual:
            self._state.has_checked = True
            self._diag.log_event(
                "INFO",
                CATEGORY_APP_UPDATE_SKIPPED_DEV,
                "Update check skipped in dev mode",
                current_version=self._state.current_version,
            )
            self.updateStateChanged.emit()
            return

        self._state.is_checking = True
        self.isCheckingForUpdatesChanged.emit()

        self._diag.log_event(
            "INFO",
            CATEGORY_APP_UPDATE_CHECK,
            "Update check initiated",
            manual=manual,
            current_version=self._state.current_version,
            frozen=getattr(sys, "frozen", False),
        )

        if manual:
            self.app._set_status("Checking for app updates...")

        if hasattr(self.app, "task_runner"):
            # Wrap callback to handle results
            def on_checked(result):
                new_version, error = result
                self._on_updates_checked(new_version, manual, error)

            self.app.task_runner.submit(self._service.check_for_updates, on_checked)
        else:
            logger.warning("No task_runner found to check for updates.")
            self._state.is_checking = False
            self.isCheckingForUpdatesChanged.emit()

    def _on_updates_checked(self, new_version, manual=False, error=None):
        self._state.is_checking = False
        self._state.has_checked = True
        self._state.error = error

        if error:
            logger.info("Update check failed: %s", error)
            self._state.update_available = False
            self._diag.log_event(
                "ERROR",
                CATEGORY_APP_UPDATE_FAILED,
                "Update check failed",
                error=error,
                current_version=self._state.current_version,
            )
            if manual:
                self.app._set_status(f"Update check failed: {error}")
        elif new_version:
            logger.info("Update available: %s", new_version)
            self._state.latest_version = new_version
            self._state.update_available = True
            self._diag.log_event(
                "INFO",
                CATEGORY_APP_UPDATE_AVAILABLE,
                "Update available",
                latest_version=new_version,
                current_version=self._state.current_version,
            )
            if manual:
                self.app._set_status(f"Update available: v{new_version}")
        else:
            logger.info("SkillManager is up to date.")
            self._state.update_available = False
            self._diag.log_event(
                "INFO",
                CATEGORY_APP_UPDATE_UP_TO_DATE,
                "SkillManager is up to date",
                current_version=self._state.current_version,
            )
            if manual:
                self.app._set_status("SkillManager is up to date.")

        # Emit all related signals
        self.isCheckingForUpdatesChanged.emit()
        self.updateAvailableChanged.emit()
        self.latestVersionChanged.emit()
        self.updateStateChanged.emit()

    @Slot()
    def downloadAndApplyUpdate(self):
        """Downloads and applies the update via the service."""
        if self._state.is_updating or not self._state.update_available:
            return

        self._state.is_updating = True
        self._state.progress = 0.0
        self.isUpdatingChanged.emit()
        self.updateProgressChanged.emit(0.0)

        if hasattr(self.app, "task_runner"):
            self.app.task_runner.run(self._apply_update_sync)
        else:
            logger.warning("No task_runner found to apply update.")
            self._state.is_updating = False
            self.isUpdatingChanged.emit()

    def _apply_update_sync(self):
        """Sync wrapper for service call in background thread."""
        try:

            def progress_callback(p):
                self._state.progress = p
                self.updateProgressChanged.emit(p)

            success = self._service.apply_update(progress_callback=progress_callback)

            if success:
                logger.info("Update applied. Restart recommended.")
                self._diag.log_event(
                    "INFO",
                    CATEGORY_APP_UPDATE_APPLIED,
                    "Update applied successfully",
                    latest_version=self._state.latest_version,
                    current_version=self._state.current_version,
                )
                self.app._set_status("Update applied. Please restart SkillManager.")
            else:
                self._diag.log_event(
                    "ERROR",
                    CATEGORY_APP_UPDATE_FAILED,
                    "Update apply returned False",
                    latest_version=self._state.latest_version,
                    current_version=self._state.current_version,
                )
                self.app._set_status("Update failed.")
        except Exception as e:
            logger.error("Apply update failed: %s", e)
            self._diag.log_event(
                "ERROR",
                CATEGORY_APP_UPDATE_FAILED,
                "Update apply raised exception",
                error=str(e),
                latest_version=self._state.latest_version,
                current_version=self._state.current_version,
            )
            self.app._set_status(f"Update error: {e}")
        finally:
            self._state.is_updating = False
            self.isUpdatingChanged.emit()
            self.updateStateChanged.emit()

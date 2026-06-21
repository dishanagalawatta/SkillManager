"""
Purpose: Controller for checking if a newer SkillManager release exists
on GitHub. No in-app download or install — opens the releases page.
"""

import logging
import sys

from packaging.version import InvalidVersion, Version
from PySide6.QtCore import Property, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices

import skill_manager
from skill_manager.controllers.base import BaseController
from skill_manager.core.diagnostics import (
    CATEGORY_APP_UPDATE_AVAILABLE,
    CATEGORY_APP_UPDATE_CHECK,
    CATEGORY_APP_UPDATE_FAILED,
    CATEGORY_APP_UPDATE_SKIPPED_DEV,
    CATEGORY_APP_UPDATE_UP_TO_DATE,
    get_diagnostic_logger,
)
from skill_manager.core.release_check_service import RELEASES_PAGE, check_latest_release
from skill_manager.core.schemas import AppUpdateState

logger = logging.getLogger(__name__)


class AppUpdateController(BaseController):
    """Controller for checking application updates via GitHub Releases API."""

    updateAvailableChanged = Signal()
    latestVersionChanged = Signal()
    isCheckingForUpdatesChanged = Signal()
    updateStateChanged = Signal()

    def __init__(self, app):
        super().__init__(app)
        self._diag = get_diagnostic_logger()
        self.state = AppUpdateState(
            current_version=skill_manager.__version__,
            latest_version=skill_manager.__version__,
        )

    # --- Properties ---

    @Property(bool, notify=updateAvailableChanged)
    def updateAvailable(self):
        return self.state.update_available

    @Property(str, notify=latestVersionChanged)
    def latestVersion(self):
        return self.state.latest_version

    @Property(str, constant=True)
    def currentVersion(self):
        return self.state.current_version

    @Property(str, constant=True)
    def releaseUrl(self):
        return RELEASES_PAGE

    @Property(bool, notify=isCheckingForUpdatesChanged)
    def isCheckingForUpdates(self):
        return self.state.is_checking

    @Property(bool, notify=updateStateChanged)
    def hasCheckedForUpdates(self):
        return self.state.has_checked

    # --- Slots ---

    @Slot()
    @Slot(bool)
    def checkForUpdates(self, manual=False):
        """Checks for updates via GitHub Releases API."""
        if self.state.is_checking:
            return

        if not getattr(sys, "frozen", False) and not manual:
            self.state.has_checked = True
            self._diag.log_event(
                "INFO",
                CATEGORY_APP_UPDATE_SKIPPED_DEV,
                "Update check skipped in dev mode",
                data={"current_version": self.state.current_version},
            )
            self.updateStateChanged.emit()
            return

        self.state.is_checking = True
        self.isCheckingForUpdatesChanged.emit()

        self._diag.log_event(
            "INFO",
            CATEGORY_APP_UPDATE_CHECK,
            "Update check initiated",
            data={
                "manual": manual,
                "current_version": self.state.current_version,
                "frozen": getattr(sys, "frozen", False),
            },
        )

        if manual:
            self.app._set_status("Checking for app updates...")

        if hasattr(self.app, "task_runner"):

            def on_checked(result):
                new_version, error = result
                self.on_updates_checked(new_version, manual, error)

            self.app.task_runner.submit(check_latest_release, on_checked)
        else:
            logger.warning("No task_runner found to check for updates.")
            self.state.is_checking = False
            self.isCheckingForUpdatesChanged.emit()

    def on_updates_checked(self, new_version, manual=False, error=None):
        self.state.is_checking = False
        self.state.has_checked = True
        self.state.error = error

        if error:
            logger.info("Update check failed: %s", error)
            self.state.update_available = False
            self._diag.log_event(
                "ERROR",
                CATEGORY_APP_UPDATE_FAILED,
                "Update check failed",
                data={"error": error, "current_version": self.state.current_version},
            )
            if manual:
                self.app._set_status(f"Update check failed: {error}")
        elif new_version:
            self.state.latest_version = new_version
            try:
                is_newer = Version(new_version) > Version(self.state.current_version)
            except InvalidVersion:
                logger.warning(
                    "Could not parse version strings for comparison: %s vs %s",
                    new_version,
                    self.state.current_version,
                )
                is_newer = False

            if is_newer:
                logger.info("Update available: %s", new_version)
                self.state.update_available = True
                self._diag.log_event(
                    "INFO",
                    CATEGORY_APP_UPDATE_AVAILABLE,
                    "Update available",
                    data={
                        "latest_version": new_version,
                        "current_version": self.state.current_version,
                    },
                )
                if manual:
                    self.app._set_status(f"Update available: v{new_version}")
            else:
                logger.info("SkillManager is up to date.")
                self.state.update_available = False
                self._diag.log_event(
                    "INFO",
                    CATEGORY_APP_UPDATE_UP_TO_DATE,
                    "SkillManager is up to date",
                    data={
                        "latest_version": new_version,
                        "current_version": self.state.current_version,
                    },
                )
                if manual:
                    self.app._set_status("SkillManager is up to date.")
        else:
            logger.info("SkillManager is up to date.")
            self.state.update_available = False
            self._diag.log_event(
                "INFO",
                CATEGORY_APP_UPDATE_UP_TO_DATE,
                "SkillManager is up to date",
                data={"current_version": self.state.current_version},
            )
            if manual:
                self.app._set_status("SkillManager is up to date.")

        self.isCheckingForUpdatesChanged.emit()
        self.updateAvailableChanged.emit()
        self.latestVersionChanged.emit()
        self.updateStateChanged.emit()

    @Slot()
    def openReleasesPage(self):
        """Opens the GitHub Releases page in the default browser."""
        QDesktopServices.openUrl(QUrl(RELEASES_PAGE))

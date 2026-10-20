"""
Purpose: Controller for checking if a newer SkillManager release exists
on GitHub. No in-app download or install — opens the releases page.

Checks run automatically shortly after launch and then daily, and notify the
UI (`appUpdateAvailable`) so the user hears about a release without opening
Settings. Development runs (``sys.frozen`` false) skip the automatic check;
the Settings button still forces one on demand.
"""

import logging
import sys

from packaging.version import InvalidVersion, Version
from PySide6.QtCore import Property, QTimer, QUrl, Signal, Slot
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

# Give the window time to render and the task runner to start before the
# first release check, then re-check once a day while the app stays open.
AUTO_CHECK_DELAY_MS = 4000
AUTO_CHECK_INTERVAL_MS = 24 * 60 * 60 * 1000


class AppUpdateController(BaseController):
    """Controller for checking application updates via GitHub Releases API."""

    updateAvailableChanged = Signal()
    latestVersionChanged = Signal()
    isCheckingForUpdatesChanged = Signal()
    updateStateChanged = Signal()
    # Version string of a newer release, emitted after a successful check so
    # Main.qml can raise the update toast without the user opening Settings.
    appUpdateAvailable = Signal(str)

    def __init__(self, app):
        super().__init__(app)
        self._diag = get_diagnostic_logger()
        self._auto_check_timer: QTimer | None = None
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
    def startAutoCheck(self):
        """Schedule the automatic release checks (launch + daily).

        Called once from AppController after startup. Idempotent so a second
        call (tests, reloads) cannot stack timers.
        """
        if self._auto_check_timer is not None:
            return
        self._auto_check_timer = QTimer(self)
        self._auto_check_timer.setInterval(AUTO_CHECK_INTERVAL_MS)
        self._auto_check_timer.timeout.connect(lambda: self.checkForUpdates(False))
        self._auto_check_timer.start()
        QTimer.singleShot(AUTO_CHECK_DELAY_MS, lambda: self.checkForUpdates(False))

    @Slot()
    @Slot(bool)
    def checkForUpdates(self, manual=False):
        """Checks for updates via GitHub Releases API."""
        if self.state.is_checking:
            return

        if not getattr(sys, "frozen", False) and not manual:
            # Development build: skip silently, and do not mark the check as
            # done — Settings would otherwise claim "Up to Date" without ever
            # having asked GitHub.
            self._diag.log_event(
                "INFO",
                CATEGORY_APP_UPDATE_SKIPPED_DEV,
                "Update check skipped in dev mode",
                data={"current_version": self.state.current_version},
            )
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
        # A failed check proves nothing about the installed version. The
        # Settings button renders "Up to Date" and disables itself once
        # has_checked is set, so marking it here would turn a timeout or a
        # GitHub rate limit into a permanent, untruthful "up to date" state
        # with no way to retry until the app restarts.
        self.state.has_checked = error is None
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
                    self.app._set_status(
                        f"SkillManager v{new_version} is available - open Settings to update."
                    )
                self.appUpdateAvailable.emit(new_version)
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

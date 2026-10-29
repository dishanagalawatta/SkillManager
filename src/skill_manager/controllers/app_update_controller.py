"""
Purpose: Controller for checking, downloading and installing SkillManager
application releases from GitHub.

Checks run automatically shortly after launch and then daily, and notify the
UI (`appUpdateAvailable`) so the user hears about a release without opening
Settings. Development runs (``sys.frozen`` false) skip the automatic check;
the Settings button still forces one on demand.

The download/install half is explicit: a user click starts a background
download, the artifact is verified against the release checksum, and only then
is the platform installer handed the file. Nothing downloads in the background
without consent.
"""

import logging
import os
import sys
from threading import Event

from packaging.version import InvalidVersion, Version
from PySide6.QtCore import Property, QProcess, QThread, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices, QGuiApplication

import skill_manager
from skill_manager.controllers.base import BaseController
from skill_manager.core.app_update_service import (
    InstallContext,
    InstallKind,
    UpdateCancelledError,
    UpdateDownloadError,
    apply_update,
    detect_install_context,
    download_asset,
    download_destination,
    expected_checksum,
)
from skill_manager.core.diagnostics import (
    CATEGORY_APP_UPDATE_AVAILABLE,
    CATEGORY_APP_UPDATE_CHECK,
    CATEGORY_APP_UPDATE_FAILED,
    CATEGORY_APP_UPDATE_SKIPPED_DEV,
    CATEGORY_APP_UPDATE_UP_TO_DATE,
    get_diagnostic_logger,
)
from skill_manager.core.release_check_service import (
    RELEASES_PAGE,
    ReleaseInfo,
    fetch_latest_release,
    select_update_asset,
)
from skill_manager.core.schemas import AppUpdateState
from skill_manager.utils.external_url import open_external_url
from skill_manager.utils.qt_threading import schedule_on_ui_thread

logger = logging.getLogger(__name__)

# Give the window time to render and the task runner to start before the
# first release check, then re-check once a day while the app stays open.
AUTO_CHECK_DELAY_MS = 4000
AUTO_CHECK_INTERVAL_MS = 24 * 60 * 60 * 1000
QUIT_BEFORE_INSTALL_MS = 500


class AppUpdateController(BaseController):
    """Controller for checking application updates via GitHub Releases API."""

    updateAvailableChanged = Signal()
    latestVersionChanged = Signal()
    isCheckingForUpdatesChanged = Signal()
    updateStateChanged = Signal()
    downloadStateChanged = Signal()
    installStateChanged = Signal()
    # Version string of a newer release, emitted after a successful check so
    # Main.qml can raise the update toast without the user opening Settings.
    appUpdateAvailable = Signal(str)

    def __init__(self, app):
        super().__init__(app)
        self._diag = get_diagnostic_logger()
        self._auto_check_timer: QTimer | None = None
        self._release: ReleaseInfo | None = None
        self._context: InstallContext = detect_install_context()
        self._cancel = Event()
        self._download_generation = 0
        self._last_status_percent = -1
        self.state = AppUpdateState(
            current_version=skill_manager.__version__,
            latest_version=skill_manager.__version__,
            install_kind=self._context.kind.value,
            self_update_supported=self._context.supported,
            self_update_reason=self._context.reason,
        )
        logger.debug(
            "App update install context: kind=%s supported=%s reason=%s",
            self._context.kind.value,
            self._context.supported,
            self._context.reason,
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

    @Property(bool, notify=downloadStateChanged)
    def isDownloading(self):
        return self.state.is_downloading

    @Property(int, notify=downloadStateChanged)
    def downloadProgress(self):
        return self.state.download_progress

    @Property(int, notify=downloadStateChanged)
    def downloadedBytes(self):
        return self.state.downloaded_bytes

    @Property(int, notify=downloadStateChanged)
    def downloadTotalBytes(self):
        return self.state.download_total_bytes

    @Property(str, notify=installStateChanged)
    def installError(self):
        return self.state.install_error or ""

    @Property(bool, notify=installStateChanged)
    def installInProgress(self):
        return self.state.install_in_progress

    @Property(bool, constant=True)
    def selfUpdateSupported(self):
        return self._context.supported

    @Property(str, constant=True)
    def selfUpdateReason(self):
        return self._context.reason

    @Property(str, constant=True)
    def installKind(self):
        return self._context.kind.value

    @Property(str, constant=True)
    def installKindLabel(self):
        return self._context.label

    @Property(bool, notify=updateStateChanged)
    def canInstallUpdate(self):
        return bool(
            self.state.update_available
            and self._context.supported
            and not self.state.is_downloading
            and not self.state.install_in_progress
        )

    # --- Check lifecycle ---

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
        if self.state.is_checking or self.state.is_downloading:
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
                release, error = result
                version = release.version if release else None
                self._on_ui_thread(
                    lambda: self.on_updates_checked(version, manual, error, release=release)
                )

            self.app.task_runner.submit(fetch_latest_release, on_checked)
        else:
            logger.warning("No task_runner found to check for updates.")
            self.state.is_checking = False
            self.isCheckingForUpdatesChanged.emit()

    def on_updates_checked(self, new_version, manual=False, error=None, release=None):
        self.state.is_checking = False
        # A failed check proves nothing about the installed version. The
        # Settings button renders "Up to Date" and disables itself once
        # has_checked is set, so marking it here would turn a timeout or a
        # GitHub rate limit into a permanent, untruthful "up to date" state
        # with no way to retry until the app restarts.
        self.state.has_checked = error is None
        self.state.error = error
        if release is not None:
            self._release = release

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
                        "install_kind": self._context.kind.value,
                        "self_update_supported": self._context.supported,
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

    # --- Download & install lifecycle ---

    @Slot()
    def downloadAndInstallUpdate(self):
        """Download the verified release artifact and start the installer."""
        if self.state.is_downloading or self.state.install_in_progress:
            return
        if not self.state.update_available:
            self.app._set_status("No SkillManager update is available.")
            return
        if not self._context.supported:
            self._set_install_error(self._context.reason or "This build cannot self-update.")
            return

        task_runner = getattr(self.app, "task_runner", None)
        if task_runner is None:
            self._set_install_error("Background task runner is unavailable.")
            return

        self.state.install_error = None
        self.state.downloaded_bytes = 0
        self.state.download_total_bytes = 0
        self.state.download_progress = 0
        self.state.is_downloading = True
        self._last_status_percent = -1
        self._cancel = Event()
        self._download_generation += 1
        generation = self._download_generation
        self.downloadStateChanged.emit()
        self.installStateChanged.emit()
        self.updateStateChanged.emit()
        self.app._set_status(
            f"Downloading SkillManager v{self.state.latest_version} ({self._context.label})..."
        )
        self._diag.log_event(
            "INFO",
            "app_update_download",
            "Update download started",
            data={
                "latest_version": self.state.latest_version,
                "install_kind": self._context.kind.value,
            },
        )
        task_runner.submit(
            lambda: self._download_worker(generation),
            lambda result: self._on_ui_thread(lambda: self._finish_download(generation, result)),
        )

    def _download_worker(self, generation: int):
        """Background half of :meth:`downloadAndInstallUpdate`."""
        try:
            release = self._release
            if release is None:
                release, error = fetch_latest_release()
                if error or release is None:
                    raise UpdateDownloadError(error or "Could not resolve the latest release.")
                self._on_ui_thread(lambda: self._adopt_release(release))

            asset = select_update_asset(release, self._context.kind.value)
            if asset is None:
                raise UpdateDownloadError(
                    f"No {self._context.label} asset is published for this release."
                )
            sha256 = expected_checksum(release, asset)
            destination = download_destination(asset, self._context)

            def progress(done: int, total: int) -> None:
                if generation != self._download_generation:
                    return
                self._on_ui_thread(lambda: self._set_download_progress(done, total))

            path = download_asset(
                asset,
                destination,
                sha256,
                progress=progress,
                cancel=self._cancel,
            )
            return path, None
        except UpdateCancelledError:
            return None, "cancelled"
        except Exception as exc:  # noqa: BLE001 - surfaced to the UI
            logger.warning("SkillManager update download failed: %s", exc)
            return None, str(exc)

    def _finish_download(self, generation: int, result) -> None:
        if generation != self._download_generation:
            return
        path, error = result
        self.state.is_downloading = False
        self.downloadStateChanged.emit()

        if error:
            if error == "cancelled":
                self.state.install_error = None
                self.app._set_status("Update download cancelled.")
                self._diag.log_event(
                    "INFO", "app_update_download_cancelled", "Update download cancelled"
                )
            else:
                self.state.install_error = error
                self.app._set_status(f"Update download failed: {error}")
                self._diag.log_event(
                    "ERROR",
                    "app_update_download_failed",
                    "Update download failed",
                    data={"error": error},
                )
            self.installStateChanged.emit()
            self.updateStateChanged.emit()
            return

        self.state.downloaded_path = str(path)
        self.state.download_progress = 100
        self.state.install_error = None
        self.downloadStateChanged.emit()
        self.installStateChanged.emit()
        self.app._set_status("Installing update — SkillManager will restart...")
        self._diag.log_event(
            "INFO",
            "app_update_download_complete",
            "Update downloaded and verified",
            data={"path": str(path), "install_kind": self._context.kind.value},
        )
        self._install_downloaded(path)

    def _install_downloaded(self, path) -> None:
        result = apply_update(self._context, path, pid=os.getpid())
        if not result.ok:
            self._set_install_error(result.error)
            self._diag.log_event(
                "ERROR",
                "app_update_install_failed",
                "Update install failed",
                data={"error": result.error},
            )
            return

        self.state.install_in_progress = True
        self.installStateChanged.emit()
        self.updateStateChanged.emit()
        self._diag.log_event(
            "INFO",
            "app_update_install_started",
            "Handing the verified update to the platform installer",
            data={
                "install_kind": self._context.kind.value,
                "quit_required": result.quit_required,
            },
        )

        # The AppImage is already replaced in place, so it is safe (and
        # necessary) to relaunch it now. The .deb and Windows helpers wait
        # for this process to exit and start the new build themselves.
        if self._context.kind is InstallKind.APPIMAGE and result.relaunch_argv:
            QProcess.startDetached(result.relaunch_argv[0], list(result.relaunch_argv[1:]))

        if result.quit_required:
            QTimer.singleShot(QUIT_BEFORE_INSTALL_MS, self._quit_for_update)

    def _quit_for_update(self) -> None:
        app = QGuiApplication.instance()
        if app is not None:
            app.quit()

    @Slot()
    def cancelUpdateDownload(self):
        """Cancel an in-flight update download."""
        if not self.state.is_downloading:
            return
        self._download_generation += 1
        self._cancel.set()
        self.state.is_downloading = False
        self.state.download_progress = 0
        self.state.downloaded_bytes = 0
        self.downloadStateChanged.emit()
        self.updateStateChanged.emit()
        self.app._set_status("Update download cancelled.")
        self._diag.log_event("INFO", "app_update_download_cancelled", "Update download cancelled")

    def _set_download_progress(self, done: int, total: int) -> None:
        if not self.state.is_downloading:
            return
        self.state.downloaded_bytes = max(done, 0)
        self.state.download_total_bytes = max(total, 0)
        percent = int(done * 100 / total) if total > 0 else 0
        percent = max(0, min(100, percent))
        changed = percent != self.state.download_progress
        self.state.download_progress = percent
        if changed:
            self.downloadStateChanged.emit()
        # Throttle the status line to ten-percent steps; every chunk would
        # spam the top bar and the diagnostics log.
        if percent >= self._last_status_percent + 10 or percent == 100:
            self._last_status_percent = percent
            if total > 0:
                self.app._set_status(
                    f"Downloading SkillManager update... {percent}% "
                    f"({done / (1024 * 1024):.0f}/{total / (1024 * 1024):.0f} MB)"
                )
            else:
                self.app._set_status(
                    f"Downloading SkillManager update... {done / (1024 * 1024):.0f} MB"
                )

    def _set_install_error(self, message: str) -> None:
        self.state.install_error = message
        self.state.is_downloading = False
        self.installStateChanged.emit()
        self.downloadStateChanged.emit()
        self.updateStateChanged.emit()
        self.app._set_status(f"Update failed: {message}")

    def _adopt_release(self, release: ReleaseInfo) -> None:
        self._release = release
        if release.version:
            self.state.latest_version = release.version
            self.latestVersionChanged.emit()

    def _on_ui_thread(self, callback) -> None:
        """Run *callback* on the controller's thread, immediately when already there."""
        if QThread.currentThread() == self.thread():
            callback()
        else:
            schedule_on_ui_thread(self, callback)

    # --- Release page ---

    @Slot(result=bool)
    def openReleasesPage(self) -> bool:
        """Open the GitHub Releases page in the default browser.

        Uses a sanitized environment so packaged builds are not broken by the
        bundled ``LD_LIBRARY_PATH`` (see ``utils.external_url``). When the host
        opener fails, fall back to Qt's platform service and report the failure
        instead of doing nothing.
        """
        url = self._release.page_url if self._release else RELEASES_PAGE
        self._diag.log_event(
            "INFO", "app_update_release_page", "Opening the release page", data={"url": url}
        )
        ok, reason = open_external_url(url)
        if ok:
            return True

        logger.info("Host URL opener failed (%s); falling back to QDesktopServices", reason)
        if QDesktopServices.openUrl(QUrl(url)):
            return True

        message = f"Could not open the release page: {reason or 'no browser available'}"
        logger.warning(message)
        self.app._set_status(message)
        self._diag.log_event(
            "ERROR",
            "app_update_release_page_failed",
            "Could not open the release page",
            data={"url": url, "error": reason},
        )
        return False

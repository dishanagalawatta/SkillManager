"""
Purpose: Checks for application updates from GitHub Pages (TUF repository) using tufup.
"""

import asyncio
import logging
import sys
from pathlib import Path

from PySide6.QtCore import Property, Signal, Slot
from tufup.client import Client

import skill_manager
from skill_manager.controllers.base import BaseController
from skill_manager.core.config import get_app_data_dir

logger = logging.getLogger(__name__)

# TUF Repository Configuration
# These will be hosted on GitHub Pages
TUF_METADATA_URL = (
    "https://raw.githubusercontent.com/dishanagalawatta/SkillManager/gh-pages/metadata/"
)
TUF_TARGETS_URL = (
    "https://raw.githubusercontent.com/dishanagalawatta/SkillManager/gh-pages/targets/"
)


class AppUpdateController(BaseController):
    updateAvailableChanged = Signal()
    latestVersionChanged = Signal()
    downloadUrlChanged = Signal()
    isUpdatingChanged = Signal()
    updateProgressChanged = Signal(float)
    isCheckingForUpdatesChanged = Signal()

    def __init__(self, app):
        super().__init__(app)
        self._update_available = False
        self._latest_version = ""
        self._download_url = "https://github.com/dishanagalawatta/SkillManager/releases/latest"
        self._is_updating = False
        self._update_progress = 0.0
        self._is_checking_for_updates = False
        self._has_checked_for_updates = False

        # tufup Client initialization
        # Use the app data directory for TUF metadata storage
        self._tuf_dir = get_app_data_dir() / "tuf"
        self._tuf_dir.mkdir(parents=True, exist_ok=True)
        self._target_dir = get_app_data_dir() / "updates"
        self._target_dir.mkdir(parents=True, exist_ok=True)

        # Seed the metadata_dir with bundled root.json if it doesn't exist
        tuf_root_dest = self._tuf_dir / "root.json"
        if not tuf_root_dest.exists():
            import shutil

            if getattr(sys, "frozen", False):
                bundled_root = Path(sys._MEIPASS) / "skill_manager" / "assets" / "tuf" / "root.json"
            else:
                bundled_root = Path(__file__).parent.parent / "assets" / "tuf" / "root.json"

            if bundled_root.exists():
                shutil.copy(bundled_root, tuf_root_dest)
            else:
                logger.warning("Bundled root.json not found at %s", bundled_root)

        # In a real app, the public key should be embedded
        # For now, we'll assume it's in the app bundle or handled by the publish script
        logger.debug("Initializing tufup Client...")
        try:
            self._client = Client(
                app_name="SkillManager",
                app_install_dir=str(
                    Path(sys.executable).parent if getattr(sys, "frozen", False) else Path.cwd()
                ),
                current_version=skill_manager.__version__,
                metadata_base_url=TUF_METADATA_URL,
                target_base_url=TUF_TARGETS_URL,
                metadata_dir=str(self._tuf_dir),
                target_dir=str(self._target_dir),
            )
            logger.debug("tufup Client initialized successfully.")
        except Exception as e:
            logger.warning("Failed to initialize TUF client (updates will be unavailable): %s", e)
            self._client = None

    @Property(bool, notify=updateAvailableChanged)
    def updateAvailable(self):
        return self._update_available

    @Property(str, notify=latestVersionChanged)
    def latestVersion(self):
        return self._latest_version

    @Property(str, constant=True)
    def currentVersion(self):
        return skill_manager.__version__

    @Property(str, notify=downloadUrlChanged)
    def downloadUrl(self):
        return self._download_url

    @Property(bool, notify=isUpdatingChanged)
    def isUpdating(self):
        return self._is_updating

    @Property(float, notify=updateProgressChanged)
    def updateProgress(self):
        return self._update_progress

    @Property(bool, notify=isCheckingForUpdatesChanged)
    def isCheckingForUpdates(self):
        return self._is_checking_for_updates

    @Property(bool, constant=True)
    def hasCheckedForUpdates(self):
        return self._has_checked_for_updates

    @Slot()
    @Slot(bool)
    def checkForUpdates(self, manual=False):
        """Checks for updates asynchronously using tufup."""
        logger.debug(
            "checkForUpdates called (manual=%s). is_updating=%s", manual, self._is_updating
        )
        if self._is_updating:
            return

        self._is_checking_for_updates = True
        self.isCheckingForUpdatesChanged.emit()

        # Skip update check in development mode (not frozen)
        if not getattr(sys, "frozen", False):
            logger.info("Running in development mode; skipping auto-update check.")
            if manual:
                self.app._set_status("Update check skipped in development mode.")
            self._update_available = False
            self.updateAvailableChanged.emit()
            self._is_checking_for_updates = False
            self._has_checked_for_updates = True
            self.isCheckingForUpdatesChanged.emit()
            return

        if manual:
            self.app._set_status("Checking for app updates...")

        # We need a BackgroundTaskRunner for threading, not asyncio.create_task
        # since PySide6 app doesn't have an asyncio loop running by default.
        if hasattr(self.app, "task_runner"):
            logger.debug("Submitting update check to task runner.")

            # Wrap callback to handle manual feedback
            def on_checked(result):
                if isinstance(result, tuple):
                    new_version, error = result
                else:
                    new_version, error = result, None
                self._on_updates_checked(new_version, manual, error)

            self.app.task_runner.submit(self._sync_check_updates, on_checked)
        else:
            logger.warning("No task_runner found on app to check for updates.")
            self._is_checking_for_updates = False
            self.isCheckingForUpdatesChanged.emit()

    def _sync_check_updates(self):
        logger.debug("_sync_check_updates running in thread.")
        if not self._client:
            return None, "Update client not initialized."

        pool = None
        try:
            import concurrent.futures

            pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
            future = pool.submit(self._client.check_for_updates)
            return future.result(timeout=15), None
        except concurrent.futures.TimeoutError:
            logger.warning("Update check timed out after 15 seconds.")
            return None, "Update check timed out."
        except Exception as e:
            logger.warning("Update check failed: %s", e)
            return None, str(e)
        finally:
            if pool:
                # wait=False ensures we don't block the background thread if the task hangs
                pool.shutdown(wait=False, cancel_futures=True)

    def _on_updates_checked(self, new_version, manual=False, error=None):
        logger.debug("_on_updates_checked received version: %s, error: %s", new_version, error)
        self._is_checking_for_updates = False
        self._has_checked_for_updates = True
        self.isCheckingForUpdatesChanged.emit()

        if error:
            logger.info("Update check returned error: %s", error)
            self._update_available = False
            self.updateAvailableChanged.emit()
            if manual:
                self.app._set_status(f"Update check failed: {error}")
            return

        if new_version:
            logger.info("Update available: %s", new_version)
            self._latest_version = str(new_version)
            self._update_available = True
            self.updateAvailableChanged.emit()
            self.latestVersionChanged.emit()
            if manual:
                self.app._set_status(f"Update available: v{new_version}")
        else:
            logger.info("No updates available.")
            self._update_available = False
            self.updateAvailableChanged.emit()
            if manual:
                self.app._set_status("SkillManager is up to date.")

    async def _check_tuf_updates(self):
        if not self._client:
            return
        try:
            # Running synchronous tufup calls in a thread pool to avoid blocking
            loop = asyncio.get_running_loop()
            new_version = await loop.run_in_executor(None, self._client.check_for_updates)

            if new_version:
                logger.info("Update available: %s", new_version)
                self._latest_version = str(new_version)
                self._update_available = True
                self.updateAvailableChanged.emit()
                self.latestVersionChanged.emit()
            else:
                logger.info("No updates available.")
                self._update_available = False
                self.updateAvailableChanged.emit()

        except Exception as e:
            logger.warning("Failed to check for app updates via tufup: %s", e)

    @Slot()
    def downloadAndApplyUpdate(self):
        """Downloads and applies the update."""
        if not self._client or self._is_updating or not self._update_available:
            return
        self._is_updating = True
        self.isUpdatingChanged.emit()

        if hasattr(self.app, "task_runner"):
            self.app.task_runner.run(self._sync_apply_update)
        else:
            logger.warning("No task_runner found on app to apply update.")
            self._is_updating = False
            self.isUpdatingChanged.emit()

    def _sync_apply_update(self):
        """Synchronous version of _apply_update for background thread execution."""
        try:

            def progress_hook(bytes_downloaded, total_bytes):
                if total_bytes > 0:
                    self._update_progress = bytes_downloaded / total_bytes
                    self.updateProgressChanged.emit(self._update_progress)

            import subprocess

            original_popen = subprocess.Popen

            # Monkey-patch Popen to always use CREATE_NO_WINDOW during update
            class NoWindowPopen(original_popen):
                def __init__(self, *args, **kwargs):
                    if sys.platform == "win32":
                        kwargs["creationflags"] = (
                            kwargs.get("creationflags", 0) | subprocess.CREATE_NO_WINDOW
                        )
                    super().__init__(*args, **kwargs)

            subprocess.Popen = NoWindowPopen
            try:
                success = self._client.download_and_apply_update(
                    progress_hook=progress_hook,
                )
            finally:
                subprocess.Popen = original_popen

            if success:
                logger.info("Update applied successfully. Application should be restarted.")
                self.app._set_status("Update applied. Please restart SkillManager.")
            else:
                logger.warning("Update failed or was cancelled.")
                self.app._set_status("Update failed.")

        except Exception as e:
            logger.error("Failed to apply update: %s", e)
            self.app._set_status(f"Update error: {e}")
        finally:
            self._is_updating = False
            self.isUpdatingChanged.emit()

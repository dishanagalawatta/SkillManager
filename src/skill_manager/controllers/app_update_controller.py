"""
Purpose: Checks for application updates from GitHub Releases.
"""

import json
import urllib.error
import urllib.request

from packaging.version import parse as parse_version
from PySide6.QtCore import Property, Signal, Slot

import skill_manager
from skill_manager.controllers.base import BaseController


class AppUpdateController(BaseController):
    updateAvailableChanged = Signal()
    latestVersionChanged = Signal()
    downloadUrlChanged = Signal()

    def __init__(self, app):
        super().__init__(app)
        self._update_available = False
        self._latest_version = ""
        self._download_url = "https://github.com/dishanagalawatta/SkillManager/releases/latest"

    @Property(bool, notify=updateAvailableChanged)
    def updateAvailable(self):
        return self._update_available

    @Property(str, notify=latestVersionChanged)
    def latestVersion(self):
        return self._latest_version

    @Property(str, notify=downloadUrlChanged)
    def downloadUrl(self):
        return self._download_url

    @Slot()
    def checkForUpdates(self):
        self.app.task_runner.submit(self._fetch_latest_release, self._on_release_fetched)

    def _fetch_latest_release(self):
        url = "https://api.github.com/repos/dishanagalawatta/SkillManager/releases/latest"
        req = urllib.request.Request(url, headers={'User-Agent': 'SkillManager-AppUpdateChecker'})
        try:
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode('utf-8'))
                return {
                    "version": data.get("tag_name", "").lstrip("v"),
                    "url": data.get("html_url", "")
                }
        except Exception as e:
            print(f"Failed to check for app updates: {e}")
            return None

    def _on_release_fetched(self, result):
        if not result:
            return

        latest_ver_str = result["version"]
        download_url = result["url"]

        try:
            current_ver = parse_version(skill_manager.__version__)
            latest_ver = parse_version(latest_ver_str)

            if latest_ver > current_ver:
                self._latest_version = latest_ver_str
                self._download_url = download_url
                self._update_available = True
                self.updateAvailableChanged.emit()
                self.latestVersionChanged.emit()
                self.downloadUrlChanged.emit()
        except Exception as e:
            print(f"Error parsing versions: {e}")

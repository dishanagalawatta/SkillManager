"""
Purpose: Checks for application updates from GitHub Releases.
"""

import asyncio
import json
import logging

import httpx
from packaging.version import parse as parse_version
from PySide6.QtCore import Property, Signal, Slot
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

import skill_manager
from skill_manager.controllers.base import BaseController

logger = logging.getLogger(__name__)


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
        asyncio.create_task(self._fetch_latest_release())

    async def _fetch_latest_release(self):
        url = "https://api.github.com/repos/dishanagalawatta/SkillManager/releases/latest"
        try:
            data = await self._get_release_json(url)
            result = {
                "version": data.get("tag_name", "").lstrip("v"),
                "url": data.get("html_url", "")
            }
            self._on_release_fetched(result)
        except Exception as e:
            logger.warning("Failed to check for app updates: %s", e)

    @retry(
        retry=retry_if_exception_type((httpx.HTTPError, json.JSONDecodeError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.2, max=2),
        reraise=True,
    )
    async def _get_release_json(self, url: str) -> dict:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(5.0),
            headers={"User-Agent": "SkillManager-AppUpdateChecker"},
            follow_redirects=True,
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()

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
            logger.warning("Error parsing versions: %s", e)

"""
Purpose: Check GitHub Releases API for the latest SkillManager version.
"""

import logging
from typing import Any

import httpx
from packaging.version import Version

logger = logging.getLogger(__name__)

GITHUB_REPO = "dishanagalawatta/SkillManager"
RELEASES_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
RELEASES_PAGE = f"https://github.com/{GITHUB_REPO}/releases"
_REQUEST_TIMEOUT = 10.0
_HEADERS = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "SkillManager",
}


def check_latest_release() -> tuple[str | None, str | None]:
    """Check GitHub Releases API for the latest version.

    Returns:
        (latest_version, None) on success; (None, error_message) on failure.
    """
    try:
        response = httpx.get(
            RELEASES_URL,
            timeout=_REQUEST_TIMEOUT,
            headers=_HEADERS,
        )
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        tag_name = data.get("tag_name", "")
        if not tag_name:
            return None, "No tag_name in response"

        # Strip leading "v" if present
        version_str = tag_name.lstrip("v")
        # Validate it parses as a version
        Version(version_str)
        return version_str, None

    except httpx.TimeoutException:
        logger.warning("GitHub Releases API timed out")
        return None, "Connection timed out"
    except httpx.HTTPStatusError as exc:
        logger.warning("GitHub Releases API returned HTTP %d", exc.response.status_code)
        return None, f"HTTP {exc.response.status_code}"
    except Exception as exc:
        logger.warning("GitHub Releases API check failed: %s", exc)
        return None, str(exc)

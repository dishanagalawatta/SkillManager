"""
Purpose: Check GitHub Releases API for the latest SkillManager version and the
per-platform assets needed to download it.

The service is deliberately Qt-free so it can run on any task runner and be
unit-tested without an event loop.
"""

from __future__ import annotations

import logging
import platform
import re
from dataclasses import dataclass, field
from typing import Any

import httpx
from packaging.version import InvalidVersion, Version

logger = logging.getLogger(__name__)

GITHUB_REPO = "dishanagalawatta/SkillManager"
RELEASES_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
RELEASES_PAGE = f"https://github.com/{GITHUB_REPO}/releases"
CHECKSUMS_ASSET_NAME = "SHA256SUMS"
_REQUEST_TIMEOUT = 10.0
_HEADERS = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "SkillManager",
}

# GitHub serves release assets from github.com and redirects to a signed
# storage host. Anything outside this allowlist is refused before a download
# starts, so a compromised API response cannot redirect the updater elsewhere.
ALLOWED_DOWNLOAD_HOSTS = frozenset(
    {
        "github.com",
        "objects.githubusercontent.com",
        "release-assets.githubusercontent.com",
    }
)

# Architecture tokens used in the published asset filenames.
_ARCH_TOKENS = {
    "x86_64": ("x86_64", "amd64", "x64"),
    "amd64": ("x86_64", "amd64", "x64"),
    "aarch64": ("aarch64", "arm64"),
    "arm64": ("aarch64", "arm64"),
}


class ReleaseAssetError(ValueError):
    """Raised when a release cannot be mapped to a safe download asset."""


@dataclass(frozen=True)
class ReleaseAsset:
    """A downloadable file attached to a GitHub release."""

    name: str
    url: str
    size: int = 0
    content_type: str = ""


@dataclass(frozen=True)
class ReleaseInfo:
    """The subset of a GitHub release the updater needs."""

    version: str
    tag_name: str
    page_url: str
    notes: str = ""
    published_at: str = ""
    assets: tuple[ReleaseAsset, ...] = field(default_factory=tuple)

    def asset_named(self, name: str) -> ReleaseAsset | None:
        wanted = name.strip().lower()
        for asset in self.assets:
            if asset.name.strip().lower() == wanted:
                return asset
        return None

    @property
    def checksums(self) -> ReleaseAsset | None:
        return self.asset_named(CHECKSUMS_ASSET_NAME)


def _as_asset(raw: dict[str, Any]) -> ReleaseAsset | None:
    name = str(raw.get("name") or "").strip()
    url = str(raw.get("browser_download_url") or "").strip()
    if not name or not url:
        return None
    try:
        size = int(raw.get("size") or 0)
    except (TypeError, ValueError):
        size = 0
    return ReleaseAsset(
        name=name,
        url=url,
        size=max(size, 0),
        content_type=str(raw.get("content_type") or ""),
    )


def parse_release_payload(data: dict[str, Any]) -> ReleaseInfo:
    """Build a :class:`ReleaseInfo` from a GitHub ``/releases/latest`` payload.

    Raises:
        ReleaseAssetError: when the tag is missing or not a valid version.
    """
    tag_name = str(data.get("tag_name") or "").strip()
    if not tag_name:
        raise ReleaseAssetError("No tag_name in response")

    version_str = tag_name.lstrip("vV")
    try:
        Version(version_str)
    except InvalidVersion as exc:
        raise ReleaseAssetError(f"Invalid release tag: {tag_name}") from exc

    assets = tuple(
        asset for asset in (_as_asset(item) for item in data.get("assets") or []) if asset
    )
    return ReleaseInfo(
        version=version_str,
        tag_name=tag_name,
        page_url=str(data.get("html_url") or RELEASES_PAGE),
        notes=str(data.get("body") or ""),
        published_at=str(data.get("published_at") or ""),
        assets=assets,
    )


def fetch_latest_release() -> tuple[ReleaseInfo | None, str | None]:
    """Fetch the latest release with its assets.

    Returns:
        ``(release, None)`` on success; ``(None, error_message)`` on failure.
    """
    try:
        response = httpx.get(
            RELEASES_URL,
            timeout=_REQUEST_TIMEOUT,
            headers=_HEADERS,
        )
        response.raise_for_status()
        data: dict[str, Any] = response.json()
    except httpx.TimeoutException:
        logger.warning("GitHub Releases API timed out")
        return None, "Connection timed out"
    except httpx.HTTPStatusError as exc:
        logger.warning("GitHub Releases API returned HTTP %d", exc.response.status_code)
        return None, f"HTTP {exc.response.status_code}"
    except Exception as exc:  # noqa: BLE001 - surfaced to the UI verbatim
        logger.warning("GitHub Releases API check failed: %s", exc)
        return None, str(exc)

    try:
        return parse_release_payload(data), None
    except ReleaseAssetError as exc:
        logger.warning("GitHub release payload invalid: %s", exc)
        return None, str(exc)


def check_latest_release() -> tuple[str | None, str | None]:
    """Backward-compatible version-only check.

    Returns:
        (latest_version, None) on success; (None, error_message) on failure.
    """
    release, error = fetch_latest_release()
    if error:
        return None, error
    return (release.version if release else None), None


def _arch_tokens(machine: str | None = None) -> tuple[str, ...]:
    token = (machine or platform.machine() or "").strip().lower()
    return _ARCH_TOKENS.get(token, (token,) if token else ())


def select_update_asset(
    release: ReleaseInfo | None,
    install_kind: str,
    *,
    machine: str | None = None,
) -> ReleaseAsset | None:
    """Pick the release asset that matches *install_kind* and this CPU.

    ``install_kind`` is one of ``appimage``, ``deb``, ``windows``. Unknown
    kinds return ``None``. Architecture tokens are matched first; when the
    filename has no recognizable token, the only candidate is still returned
    so a future naming change degrades to "the platform asset" instead of
    breaking the updater.
    """
    if release is None:
        return None

    kind = install_kind.strip().lower()
    if kind == "appimage":
        candidates = [a for a in release.assets if a.name.lower().endswith(".appimage")]
    elif kind == "deb":
        candidates = [a for a in release.assets if a.name.lower().endswith(".deb")]
    elif kind == "windows":
        candidates = [
            a
            for a in release.assets
            if a.name.lower().endswith(".exe") and "setup" in a.name.lower()
        ]
        if not candidates:
            candidates = [a for a in release.assets if a.name.lower().endswith(".exe")]
    else:
        return None

    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]

    tokens = _arch_tokens(machine)
    for token in tokens:
        for asset in candidates:
            if token in asset.name.lower():
                return asset
    return candidates[0]


def is_allowed_download_url(url: str) -> bool:
    """Return ``True`` only for HTTPS GitHub release asset URLs."""
    try:
        parsed = httpx.URL(url)
    except Exception:  # noqa: BLE001 - malformed URL is simply not allowed
        return False
    return parsed.scheme == "https" and (parsed.host or "").lower() in ALLOWED_DOWNLOAD_HOSTS


def parse_sha256sums(text: str) -> dict[str, str]:
    """Parse a ``SHA256SUMS`` manifest into ``{basename: lowercase hex}``.

    Accepts the GNU coreutils format (``<hash>  dist/<name>``) and the
    binary-mode ``*`` prefix some tools emit.
    """
    sums: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        match = re.match(r"^([0-9a-fA-F]{64})\s+\*?(.+)$", line)
        if not match:
            continue
        digest, raw_name = match.groups()
        key = raw_name.strip().replace("\\", "/").rsplit("/", 1)[-1]
        if key:
            sums[key] = digest.lower()
    return sums


def fetch_sha256sums(release: ReleaseInfo | None) -> tuple[dict[str, str], str | None]:
    """Fetch and parse the release ``SHA256SUMS`` manifest."""
    asset = release.checksums if release else None
    if asset is None:
        return {}, "Release does not publish a SHA256SUMS manifest"
    if not is_allowed_download_url(asset.url):
        return {}, "SHA256SUMS URL is not a trusted GitHub release URL"
    try:
        response = httpx.get(
            asset.url,
            timeout=_REQUEST_TIMEOUT,
            headers=_HEADERS,
            # Release assets redirect to objects.githubusercontent.com; without
            # this the manifest read fails with HTTP 302 on every install.
            follow_redirects=True,
        )
        response.raise_for_status()
        if not is_allowed_download_url(str(response.url)):
            return {}, "Checksum URL redirected to an untrusted host"
        text = response.text
    except httpx.TimeoutException:
        return {}, "Checksum download timed out"
    except httpx.HTTPStatusError as exc:
        return {}, f"Checksum download failed: HTTP {exc.response.status_code}"
    except Exception as exc:  # noqa: BLE001
        return {}, f"Checksum download failed: {exc}"

    sums = parse_sha256sums(text)
    if not sums:
        return {}, "SHA256SUMS manifest is empty or malformed"
    return sums, None

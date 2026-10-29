"""
Purpose: Download, verify and install a SkillManager release from inside the app.

Supported install kinds:

* ``appimage``  — atomically replace the running AppImage, then relaunch it.
* ``deb``       — install the downloaded package through a detached helper that
                  waits for this process to exit and uses ``pkexec`` (polkit)
                  for the single privileged step.
* ``windows``   — run the downloaded Inno Setup installer silently from a
                  detached helper after this process exits, then relaunch.

A source checkout is intentionally not self-updatable: ``git pull``/``uv sync``
is outside the scope of a release artifact and must stay a developer action.

Security: every download must come from an allow-listed GitHub host and must
match the release's published ``SHA256SUMS`` entry. A missing manifest is a
hard failure for self-install (the shell installer only warns; an in-app
installer must not run unverified bytes).
"""

from __future__ import annotations

import contextlib
import hashlib
import logging
import os
import shlex
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from threading import Event

import httpx

from skill_manager.core.release_check_service import (
    ReleaseAsset,
    ReleaseInfo,
    fetch_sha256sums,
    is_allowed_download_url,
)
from skill_manager.utils.linux import find_system_binary, get_clean_env

logger = logging.getLogger(__name__)

MAX_DOWNLOAD_BYTES = 2 * 1024 * 1024 * 1024  # 2 GiB
_CHUNK_SIZE = 1024 * 256
_HTTP_TIMEOUT = httpx.Timeout(30.0, read=120.0)
_DOWNLOAD_HEADERS = {"User-Agent": "SkillManager", "Accept": "application/octet-stream"}

ProgressCallback = Callable[[int, int], None]


class InstallKind(StrEnum):
    APPIMAGE = "appimage"
    DEB = "deb"
    WINDOWS_INSTALLER = "windows"
    SOURCE = "source"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True)
class InstallContext:
    """Where and how this copy of SkillManager can update itself."""

    kind: InstallKind
    target: Path | None = None
    executable: Path | None = None
    supported: bool = False
    reason: str = ""

    @property
    def label(self) -> str:
        return {
            InstallKind.APPIMAGE: "AppImage",
            InstallKind.DEB: "Debian package",
            InstallKind.WINDOWS_INSTALLER: "Windows installer",
            InstallKind.SOURCE: "source checkout",
            InstallKind.UNSUPPORTED: "unsupported build",
        }.get(self.kind, "unsupported build")


@dataclass(frozen=True)
class InstallResult:
    """Outcome of handing the verified artifact to the platform installer."""

    ok: bool
    error: str = ""
    quit_required: bool = False
    relaunch_argv: tuple[str, ...] = ()


class UpdateDownloadError(RuntimeError):
    """A download failed for a reason worth showing to the user."""


class UpdateCancelledError(UpdateDownloadError):
    """The user cancelled an in-flight download."""


class ChecksumMismatchError(UpdateDownloadError):
    """The downloaded bytes do not match the release checksum."""


def _platform() -> str:
    return sys.platform


def detect_install_context(
    *,
    frozen: bool | None = None,
    platform_name: str | None = None,
    env: dict[str, str] | None = None,
    executable: str | None = None,
    is_file: Callable[[str], bool] = os.path.isfile,
    is_writable: Callable[[str, int], bool] = os.access,
    find_binary: Callable[[str], str | None] = find_system_binary,
) -> InstallContext:
    """Classify the running build and whether it can install its own update."""
    frozen = getattr(sys, "frozen", False) if frozen is None else frozen
    platform_name = platform_name or _platform()
    env = dict(os.environ) if env is None else env
    exe = Path(executable or sys.executable)

    if platform_name == "win32":
        if not frozen:
            return InstallContext(
                InstallKind.SOURCE,
                executable=exe,
                reason="Source checkout — run the release installer or use View Release.",
            )
        return InstallContext(
            InstallKind.WINDOWS_INSTALLER,
            target=exe,
            executable=exe,
            supported=True,
        )

    if not platform_name.startswith("linux"):
        return InstallContext(
            InstallKind.UNSUPPORTED,
            executable=exe,
            reason=f"In-app updates are not available on {platform_name}.",
        )

    appimage = (env.get("APPIMAGE") or "").strip()
    if appimage and is_file(appimage):
        target = Path(appimage)
        parent = target.parent
        if not is_writable(str(parent), os.W_OK):
            return InstallContext(
                InstallKind.APPIMAGE,
                target=target,
                executable=target,
                supported=False,
                reason=f"No write permission for {parent}.",
            )
        return InstallContext(
            InstallKind.APPIMAGE,
            target=target,
            executable=target,
            supported=True,
        )

    if not frozen:
        return InstallContext(
            InstallKind.SOURCE,
            executable=exe,
            reason="Source checkout — use scripts/update-local.sh or View Release.",
        )

    pkexec = find_binary("pkexec")
    package_tool = find_binary("apt-get") or find_binary("dpkg")
    if not pkexec or not package_tool:
        missing = "pkexec" if not pkexec else "apt-get/dpkg"
        return InstallContext(
            InstallKind.DEB,
            target=exe,
            executable=exe,
            supported=False,
            reason=(
                f"{missing} is not available, so the .deb cannot be installed automatically. "
                "Use View Release or run the install script with --update."
            ),
        )
    return InstallContext(
        InstallKind.DEB,
        target=exe,
        executable=exe,
        supported=True,
    )


def download_destination(
    asset: ReleaseAsset,
    context: InstallContext,
    *,
    temp_root: Path | None = None,
) -> Path:
    """Choose a destination that keeps the final replace atomic.

    An AppImage is downloaded next to its target so ``os.replace`` stays on the
    same filesystem. Installers go to a private temp directory.
    """
    if context.kind is InstallKind.APPIMAGE and context.target is not None:
        return context.target.with_name(f".{context.target.name}.{asset.name}.new")
    root = temp_root or Path(tempfile.gettempdir()) / "SkillManager-updates"
    return root / asset.name.replace("/", "_")


def expected_checksum(release: ReleaseInfo | None, asset: ReleaseAsset) -> str:
    """Return the SHA256 for *asset*, raising when the release is unverifiable."""
    sums, error = fetch_sha256sums(release)
    if error:
        raise UpdateDownloadError(f"Cannot verify the update: {error}")
    digest = sums.get(asset.name)
    if not digest:
        raise UpdateDownloadError(
            f"Release manifest has no checksum for {asset.name}; refusing to install."
        )
    return digest


def download_asset(
    asset: ReleaseAsset,
    destination: Path,
    sha256: str,
    *,
    progress: ProgressCallback | None = None,
    cancel: Event | None = None,
    max_bytes: int = MAX_DOWNLOAD_BYTES,
) -> Path:
    """Stream *asset* to *destination*, verifying its SHA256.

    The file is written to ``<destination>.part`` and only moved into place
    after the checksum matches, so an interrupted download never looks like a
    valid installer.
    """
    if not is_allowed_download_url(asset.url):
        raise UpdateDownloadError("The update URL is not a trusted GitHub release URL.")

    destination.parent.mkdir(parents=True, exist_ok=True)
    part = destination.with_name(destination.name + ".part")
    digest = hashlib.sha256()
    written = 0
    total = max(asset.size, 0)
    last_report = 0.0

    try:
        with httpx.stream(
            "GET",
            asset.url,
            headers=_DOWNLOAD_HEADERS,
            follow_redirects=True,
            timeout=_HTTP_TIMEOUT,
        ) as response:
            response.raise_for_status()
            final_url = str(response.url)
            if not is_allowed_download_url(final_url):
                raise UpdateDownloadError("The update download redirected to an untrusted host.")
            with contextlib.suppress(TypeError, ValueError):
                total = int(response.headers.get("content-length") or total or 0)
            if total and total > max_bytes:
                raise UpdateDownloadError("The update is larger than the allowed download size.")

            with open(part, "wb") as handle:
                for chunk in response.iter_bytes(_CHUNK_SIZE):
                    if cancel is not None and cancel.is_set():
                        raise UpdateCancelledError("Update download cancelled.")
                    if not chunk:
                        continue
                    written += len(chunk)
                    if written > max_bytes:
                        raise UpdateDownloadError(
                            "The update is larger than the allowed download size."
                        )
                    handle.write(chunk)
                    digest.update(chunk)
                    now = time.monotonic()
                    if progress is not None and (now - last_report >= 0.2 or written == total):
                        last_report = now
                        progress(written, total)
                handle.flush()
                os.fsync(handle.fileno())

        if written == 0:
            raise UpdateDownloadError("The downloaded update was empty.")
        actual = digest.hexdigest()
        if actual.lower() != sha256.strip().lower():
            raise ChecksumMismatchError(
                "Checksum mismatch — the downloaded update is corrupt or was tampered with."
            )
        os.replace(part, destination)
        if progress is not None:
            progress(written, total or written)
        return destination
    except BaseException:
        part.unlink(missing_ok=True)
        raise


def _update_log_path() -> Path:
    try:
        from skill_manager.core.config import get_app_data_dir

        base = get_app_data_dir()
    except Exception:  # noqa: BLE001 - logging must never break an install
        base = Path.home() / ".local" / "share" / "SkillManager"
    return base / "update-install.log"


def _sh_path(path: Path | str) -> str:
    """Quote a path for a POSIX shell script.

    The helpers this module generates are ``/bin/sh`` and ``cmd.exe`` scripts,
    and the build that produces them can differ from the one that runs them
    (tests exercise the ``sh`` helpers on Windows CI). ``as_posix`` keeps the
    emitted script valid POSIX even when the generating host is Windows, where
    ``str(Path('/opt/x'))`` would become ``\\opt\\x``.
    """
    return shlex.quote(Path(path).as_posix())


def _script_header(log_path: Path) -> str:
    return (
        "#!/bin/sh\n"
        f"LOG={_sh_path(log_path)}\n"
        'mkdir -p "$(dirname "$LOG")" 2>/dev/null || true\n'
        'log() { echo "$(date -Is 2>/dev/null) $*" >> "$LOG" 2>/dev/null || true; }\n'
    )


def build_deb_helper_script(
    *,
    deb_path: Path,
    pid: int,
    executable: Path,
    pkexec: str,
    package_tool: str,
    log_path: Path | None = None,
) -> str:
    """Build the detached shell helper that installs a .deb after app exit."""
    log_path = log_path or _update_log_path()
    if Path(package_tool).name.startswith("apt"):
        install_cmd = (
            f"{_sh_path(pkexec)} env DEBIAN_FRONTEND=noninteractive "
            f"{_sh_path(package_tool)} install -y --allow-downgrades {_sh_path(deb_path)}"
        )
    else:
        install_cmd = f"{_sh_path(pkexec)} {_sh_path(package_tool)} -i {_sh_path(deb_path)}"

    return (
        _script_header(log_path)
        + f"log 'Waiting for SkillManager (pid {int(pid)}) to exit'\n"
        + "i=0\n"
        + f"while kill -0 {int(pid)} 2>/dev/null; do\n"
        + "  i=$((i+1))\n"
        + "  [ $i -gt 200 ] && break\n"
        + "  sleep 0.3\n"
        + "done\n"
        + f"log Installing {_sh_path(deb_path.name)}\n"
        + f'{install_cmd} >> "$LOG" 2>&1\n'
        + "rc=$?\n"
        + 'log "Installer exit code: $rc"\n'
        + f"if [ -x {_sh_path(executable)} ]; then\n"
        + f'  nohup {_sh_path(executable)} >> "$LOG" 2>&1 &\n'
        + "fi\n"
        + "exit $rc\n"
    )


def build_windows_helper_script(
    *,
    installer_path: Path,
    pid: int,
    executable: Path,
) -> str:
    """Build the detached cmd helper that runs the Inno Setup installer."""
    return (
        "@echo off\r\n"
        "setlocal\r\n"
        ":wait_for_exit\r\n"
        f'tasklist /FI "PID eq {int(pid)}" 2>nul | find "{int(pid)}" >nul\r\n'
        "if not errorlevel 1 (\r\n"
        "  timeout /t 1 /nobreak >nul\r\n"
        "  goto wait_for_exit\r\n"
        ")\r\n"
        f'start "" /wait "{installer_path}" /SILENT /SUPPRESSMSGBOXES /NORESTART '
        "/CLOSEAPPLICATIONS\r\n"
        f'if exist "{executable}" start "" "{executable}"\r\n'
        "endlocal\r\n"
    )


def _write_helper(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="")
    if not sys.platform.startswith("win"):
        path.chmod(0o700)
    return path


def apply_update(
    context: InstallContext,
    downloaded: Path,
    *,
    pid: int,
    temp_root: Path | None = None,
) -> InstallResult:
    """Install a verified artifact according to *context*.

    AppImage replacement happens in-process (atomic rename). The .deb and
    Windows paths only spawn a detached helper; the caller is responsible for
    quitting the app so the helper can proceed.
    """
    if not context.supported:
        return InstallResult(False, context.reason or "This build cannot self-update.")
    if not downloaded.is_file():
        return InstallResult(False, f"Downloaded update not found: {downloaded}")

    try:
        if context.kind is InstallKind.APPIMAGE:
            if context.target is None:
                return InstallResult(False, "AppImage path is unknown.")
            downloaded.chmod(downloaded.stat().st_mode | 0o111)
            os.replace(downloaded, context.target)
            context.target.chmod(0o755)
            return InstallResult(
                True,
                quit_required=True,
                relaunch_argv=(str(context.target),),
            )

        if context.kind is InstallKind.DEB:
            pkexec = find_system_binary("pkexec")
            package_tool = find_system_binary("apt-get") or find_system_binary("dpkg")
            if not pkexec or not package_tool:
                return InstallResult(False, context.reason or "pkexec/apt-get is unavailable.")
            executable = context.executable or Path(sys.executable)
            script = build_deb_helper_script(
                deb_path=downloaded,
                pid=pid,
                executable=executable,
                pkexec=pkexec,
                package_tool=package_tool,
            )
            script_path = _write_helper(
                (temp_root or Path(tempfile.gettempdir()) / "SkillManager-updates")
                / "install-update.sh",
                script,
            )
            subprocess.Popen(
                ["/bin/sh", str(script_path)],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env=get_clean_env(),
                start_new_session=True,
                close_fds=True,
            )
            return InstallResult(True, quit_required=True, relaunch_argv=(str(executable),))

        if context.kind is InstallKind.WINDOWS_INSTALLER:
            executable = context.executable or Path(sys.executable)
            script = build_windows_helper_script(
                installer_path=downloaded,
                pid=pid,
                executable=executable,
            )
            script_path = _write_helper(
                (temp_root or Path(tempfile.gettempdir()) / "SkillManager-updates")
                / "install-update.cmd",
                script,
            )
            creationflags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(
                subprocess, "CREATE_NEW_PROCESS_GROUP", 0
            )
            subprocess.Popen(
                ["cmd.exe", "/c", str(script_path)],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=creationflags,
                close_fds=True,
            )
            return InstallResult(True, quit_required=True, relaunch_argv=(str(executable),))

        return InstallResult(False, f"Unsupported install kind: {context.kind.value}")
    except Exception as exc:  # noqa: BLE001 - surfaced to the UI
        logger.exception("Applying the SkillManager update failed")
        return InstallResult(False, str(exc))

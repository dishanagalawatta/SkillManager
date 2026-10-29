"""Tests for the download / verify / install half of app self-updates."""

import hashlib
import os
from pathlib import Path
from threading import Event
from unittest.mock import MagicMock, patch

import pytest

from skill_manager.core.app_update_service import (
    ChecksumMismatchError,
    InstallContext,
    InstallKind,
    UpdateCancelledError,
    UpdateDownloadError,
    apply_update,
    build_deb_helper_script,
    build_windows_helper_script,
    detect_install_context,
    download_asset,
    download_destination,
    expected_checksum,
)
from skill_manager.core.release_check_service import ReleaseAsset, ReleaseInfo

ASSET_URL = "https://github.com/dishanagalawatta/SkillManager/releases/download/v9.9.9/app.AppImage"


def _asset(name="app.AppImage", url=ASSET_URL, size=0):
    return ReleaseAsset(name=name, url=url, size=size)


def _release(**kwargs):
    return ReleaseInfo(
        version="9.9.9", tag_name="v9.9.9", page_url="https://example.test", **kwargs
    )


class FakeStreamResponse:
    def __init__(self, chunks, url=ASSET_URL, content_length=None):
        self._chunks = chunks
        self.url = url
        self.headers = {} if content_length is None else {"content-length": str(content_length)}
        self.status_code = 200

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def raise_for_status(self):
        return None

    def iter_bytes(self, _size):
        yield from self._chunks


class TestDetectInstallContext:
    def test_windows_frozen(self):
        context = detect_install_context(
            frozen=True, platform_name="win32", executable="C:/Apps/SkillManager.exe"
        )
        assert context.kind is InstallKind.WINDOWS_INSTALLER
        assert context.supported is True
        assert context.executable == Path("C:/Apps/SkillManager.exe")

    def test_windows_source(self):
        context = detect_install_context(frozen=False, platform_name="win32")
        assert context.kind is InstallKind.SOURCE
        assert context.supported is False

    def test_linux_source_mentions_update_local(self):
        context = detect_install_context(frozen=False, platform_name="linux", env={})
        assert context.kind is InstallKind.SOURCE
        assert context.supported is False
        assert "update-local" in context.reason

    def test_linux_appimage_is_supported(self, tmp_path):
        appimage = tmp_path / "SkillManager.AppImage"
        appimage.write_text("old", encoding="utf-8")
        context = detect_install_context(
            frozen=True,
            platform_name="linux",
            env={"APPIMAGE": str(appimage)},
            is_writable=lambda _p, _m: True,
        )
        assert context.kind is InstallKind.APPIMAGE
        assert context.supported is True
        assert context.target == appimage

    def test_linux_appimage_readonly_dir_is_unsupported(self, tmp_path):
        appimage = tmp_path / "SkillManager.AppImage"
        appimage.write_text("old", encoding="utf-8")
        context = detect_install_context(
            frozen=True,
            platform_name="linux",
            env={"APPIMAGE": str(appimage)},
            is_writable=lambda _p, _m: False,
        )
        assert context.kind is InstallKind.APPIMAGE
        assert context.supported is False
        assert "permission" in context.reason.lower()

    def test_linux_deb_supported_with_pkexec(self):
        context = detect_install_context(
            frozen=True,
            platform_name="linux",
            env={},
            find_binary=lambda name: f"/usr/bin/{name}" if name in {"pkexec", "apt-get"} else None,
        )
        assert context.kind is InstallKind.DEB
        assert context.supported is True

    def test_linux_deb_without_pkexec_is_unsupported(self):
        context = detect_install_context(
            frozen=True,
            platform_name="linux",
            env={},
            find_binary=lambda name: "/usr/bin/dpkg" if name == "dpkg" else None,
        )
        assert context.kind is InstallKind.DEB
        assert context.supported is False
        assert "pkexec" in context.reason

    def test_other_platforms_are_unsupported(self):
        context = detect_install_context(frozen=True, platform_name="darwin")
        assert context.kind is InstallKind.UNSUPPORTED
        assert context.supported is False


class TestDownloadDestination:
    def test_appimage_stays_next_to_target(self, tmp_path):
        target = tmp_path / "skill-manager"
        context = InstallContext(InstallKind.APPIMAGE, target=target, supported=True)
        dest = download_destination(_asset(), context)
        assert dest.parent == tmp_path
        assert dest.name.startswith(".skill-manager")

    def test_installer_uses_private_temp_dir(self, tmp_path):
        context = InstallContext(InstallKind.DEB, supported=True)
        dest = download_destination(_asset(), context, temp_root=tmp_path)
        assert dest == tmp_path / "app.AppImage"


class TestExpectedChecksum:
    def test_returns_digest(self):
        with patch(
            "skill_manager.core.app_update_service.fetch_sha256sums",
            return_value=({"app.AppImage": "a" * 64}, None),
        ):
            assert expected_checksum(_release(), _asset()) == "a" * 64

    def test_missing_manifest_refuses_install(self):
        with (
            patch(
                "skill_manager.core.app_update_service.fetch_sha256sums",
                return_value=({}, "Release does not publish a SHA256SUMS manifest"),
            ),
            pytest.raises(UpdateDownloadError, match="Cannot verify"),
        ):
            expected_checksum(_release(), _asset())

    def test_missing_asset_entry_refuses_install(self):
        with (
            patch(
                "skill_manager.core.app_update_service.fetch_sha256sums",
                return_value=({"other.deb": "b" * 64}, None),
            ),
            pytest.raises(UpdateDownloadError, match="no checksum"),
        ):
            expected_checksum(_release(), _asset())


class TestDownloadAsset:
    def test_success_verifies_and_moves_into_place(self, tmp_path):
        payload = b"new-version-bytes"
        digest = hashlib.sha256(payload).hexdigest()
        progress = MagicMock()
        destination = tmp_path / "app.AppImage"

        with patch(
            "skill_manager.core.app_update_service.httpx.stream",
            return_value=FakeStreamResponse([payload], content_length=len(payload)),
        ):
            result = download_asset(
                _asset(size=len(payload)), destination, digest, progress=progress
            )

        assert result == destination
        assert destination.read_bytes() == payload
        assert not destination.with_name(destination.name + ".part").exists()
        # Final progress reports 100% (done == total).
        assert progress.call_args_list[-1][0][0] == len(payload)
        assert progress.call_args_list[-1][0][1] == len(payload)

    def test_checksum_mismatch_deletes_partial_file(self, tmp_path):
        destination = tmp_path / "app.AppImage"
        with (
            patch(
                "skill_manager.core.app_update_service.httpx.stream",
                return_value=FakeStreamResponse([b"tampered"]),
            ),
            pytest.raises(ChecksumMismatchError),
        ):
            download_asset(_asset(), destination, "0" * 64)

        assert not destination.exists()
        assert not destination.with_name(destination.name + ".part").exists()

    def test_cancel_stops_and_cleans_up(self, tmp_path):
        destination = tmp_path / "app.AppImage"
        cancel = Event()

        def first_chunk_free_progress(_done, _total):
            cancel.set()

        with (
            patch(
                "skill_manager.core.app_update_service.httpx.stream",
                return_value=FakeStreamResponse([b"one", b"two"]),
            ),
            pytest.raises(UpdateCancelledError),
        ):
            download_asset(
                _asset(),
                destination,
                hashlib.sha256(b"onetwo").hexdigest(),
                progress=first_chunk_free_progress,
                cancel=cancel,
            )

        assert not destination.exists()
        assert not destination.with_name(destination.name + ".part").exists()

    def test_untrusted_url_is_refused_before_network(self, tmp_path):
        with (
            patch("skill_manager.core.app_update_service.httpx.stream") as stream,
            pytest.raises(UpdateDownloadError, match="trusted"),
        ):
            download_asset(
                _asset(url="https://evil.example/app.AppImage"),
                tmp_path / "app.AppImage",
                "0" * 64,
            )
        stream.assert_not_called()

    def test_redirect_to_untrusted_host_is_refused(self, tmp_path):
        response = FakeStreamResponse([b"bytes"], url="https://evil.example/payload")
        with (
            patch("skill_manager.core.app_update_service.httpx.stream", return_value=response),
            pytest.raises(UpdateDownloadError, match="untrusted host"),
        ):
            download_asset(_asset(), tmp_path / "app.AppImage", "0" * 64)

    def test_empty_download_is_rejected(self, tmp_path):
        with (
            patch(
                "skill_manager.core.app_update_service.httpx.stream",
                return_value=FakeStreamResponse([]),
            ),
            pytest.raises(UpdateDownloadError, match="empty"),
        ):
            download_asset(_asset(), tmp_path / "app.AppImage", "0" * 64)

    def test_oversized_download_is_rejected(self, tmp_path):
        with (
            patch(
                "skill_manager.core.app_update_service.httpx.stream",
                return_value=FakeStreamResponse([b"x" * 32]),
            ),
            pytest.raises(UpdateDownloadError, match="larger"),
        ):
            download_asset(_asset(), tmp_path / "app.AppImage", "0" * 64, max_bytes=8)


class TestInstallerScripts:
    def test_deb_helper_waits_for_pid_and_quotes_paths(self, tmp_path):
        script = build_deb_helper_script(
            deb_path=Path("/tmp/updates/skill manager;rm -rf.deb"),
            pid=4321,
            executable=Path("/opt/SkillManager/SkillManager"),
            pkexec="/usr/bin/pkexec",
            package_tool="/usr/bin/apt-get",
            log_path=tmp_path / "update.log",
        )
        assert "kill -0 4321" in script
        assert "/usr/bin/pkexec" in script
        assert "apt-get install -y --allow-downgrades" in script
        assert "'/tmp/updates/skill manager;rm -rf.deb'" in script
        assert "[ -x /opt/SkillManager/SkillManager ]" in script
        assert "nohup /opt/SkillManager/SkillManager" in script

    def test_deb_helper_emits_posix_paths_only(self):
        """A /bin/sh script must never carry host-specific backslashes."""
        script = build_deb_helper_script(
            deb_path=Path("/tmp/updates/skill manager.deb"),
            pid=4321,
            executable=Path("/opt/SkillManager/SkillManager"),
            pkexec="/usr/bin/pkexec",
            package_tool="/usr/bin/apt-get",
            log_path=Path("/tmp/update.log"),
        )
        assert "\\" not in script
        assert "'/tmp/updates/skill manager.deb'" in script
        assert "/opt/SkillManager/SkillManager" in script

    def test_deb_helper_uses_dpkg_when_apt_is_absent(self, tmp_path):
        script = build_deb_helper_script(
            deb_path=tmp_path / "app.deb",
            pid=1,
            executable=Path("/opt/SkillManager/SkillManager"),
            pkexec="/usr/bin/pkexec",
            package_tool="/usr/bin/dpkg",
            log_path=tmp_path / "update.log",
        )
        assert "/usr/bin/pkexec /usr/bin/dpkg -i" in script

    def test_windows_helper_has_silent_upgrade_flags(self):
        script = build_windows_helper_script(
            installer_path=Path(r"C:\Temp\SkillManager_Setup.exe"),
            pid=777,
            executable=Path(r"C:\Program Files\SkillManager\SkillManager.exe"),
        )
        assert "PID eq 777" in script
        assert "/SILENT" in script
        assert "/SUPPRESSMSGBOXES" in script
        assert "/NORESTART" in script
        assert 'start "" "C:\\Program Files\\SkillManager\\SkillManager.exe"' in script


class TestApplyUpdate:
    def test_appimage_is_replaced_atomically_and_relaunched(self, tmp_path):
        target = tmp_path / "skill-manager"
        target.write_text("old", encoding="utf-8")
        downloaded = tmp_path / ".skill-manager.new"
        downloaded.write_text("new", encoding="utf-8")
        context = InstallContext(
            InstallKind.APPIMAGE, target=target, executable=target, supported=True
        )

        result = apply_update(context, downloaded, pid=1)

        assert result.ok is True
        assert result.quit_required is True
        assert result.relaunch_argv == (str(target),)
        assert target.read_text(encoding="utf-8") == "new"
        if os.name != "nt":
            # Windows reports every regular file as 0o666; the exec bit is POSIX-only.
            assert target.stat().st_mode & 0o111
        assert not downloaded.exists()

    def test_unsupported_context_refuses(self, tmp_path):
        downloaded = tmp_path / "app.deb"
        downloaded.write_text("x", encoding="utf-8")
        result = apply_update(
            InstallContext(InstallKind.DEB, supported=False, reason="no pkexec"),
            downloaded,
            pid=1,
        )
        assert result.ok is False
        assert "no pkexec" in result.error

    def test_missing_download_refuses(self, tmp_path):
        result = apply_update(
            InstallContext(InstallKind.APPIMAGE, target=tmp_path / "x", supported=True),
            tmp_path / "missing",
            pid=1,
        )
        assert result.ok is False

    def test_deb_spawns_detached_helper(self, tmp_path):
        downloaded = tmp_path / "app.deb"
        downloaded.write_text("deb", encoding="utf-8")
        context = InstallContext(
            InstallKind.DEB, executable=Path("/opt/SkillManager/SkillManager"), supported=True
        )
        with (
            patch(
                "skill_manager.core.app_update_service.find_system_binary",
                side_effect=lambda name: (
                    f"/usr/bin/{name}" if name in {"pkexec", "apt-get"} else None
                ),
            ),
            patch("skill_manager.core.app_update_service.subprocess.Popen") as popen,
        ):
            result = apply_update(context, downloaded, pid=5, temp_root=tmp_path)

        assert result.ok is True
        assert result.quit_required is True
        popen.assert_called_once()
        script_path = Path(popen.call_args[0][0][-1])
        assert script_path.exists()
        script = script_path.read_text(encoding="utf-8")
        assert "kill -0 5" in script
        assert "pkexec" in script

    def test_windows_spawns_detached_helper(self, tmp_path):
        downloaded = tmp_path / "SkillManager_Setup.exe"
        downloaded.write_text("exe", encoding="utf-8")
        context = InstallContext(
            InstallKind.WINDOWS_INSTALLER,
            executable=Path(r"C:\Apps\SkillManager.exe"),
            supported=True,
        )
        with patch("skill_manager.core.app_update_service.subprocess.Popen") as popen:
            result = apply_update(context, downloaded, pid=9, temp_root=tmp_path)

        assert result.ok is True
        popen.assert_called_once()
        script = Path(popen.call_args[0][0][-1]).read_text(encoding="utf-8")
        assert "PID eq 9" in script
        assert "/SILENT" in script

    def test_helper_spawn_failure_is_reported(self, tmp_path):
        downloaded = tmp_path / "app.deb"
        downloaded.write_text("deb", encoding="utf-8")
        context = InstallContext(InstallKind.DEB, supported=True)
        with (
            patch(
                "skill_manager.core.app_update_service.find_system_binary",
                return_value="/usr/bin/pkexec",
            ),
            patch(
                "skill_manager.core.app_update_service.subprocess.Popen",
                side_effect=OSError("denied"),
            ),
        ):
            result = apply_update(context, downloaded, pid=1, temp_root=tmp_path)

        assert result.ok is False
        assert "denied" in result.error

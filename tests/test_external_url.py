"""Tests for the environment-sanitized external URL opener."""

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from skill_manager.utils.external_url import is_safe_external_url, open_external_url

URL = "https://github.com/dishanagalawatta/SkillManager/releases"


class TestIsSafeExternalUrl:
    @pytest.mark.parametrize(
        "url",
        [
            "https://github.com/dishanagalawatta/SkillManager/releases",
            "http://example.test/release?id=1",
        ],
    )
    def test_web_urls_are_allowed(self, url):
        assert is_safe_external_url(url) is True

    @pytest.mark.parametrize(
        "url",
        [
            "",
            "   ",
            "github.com/releases",
            "/relative/path",
            "file:///etc/passwd",
            "javascript:alert(1)",
            "--help",
            " -oops",
            "https://",
        ],
    )
    def test_unsafe_or_relative_urls_are_refused(self, url):
        assert is_safe_external_url(url) is False


def _completed(returncode=0, stderr=b""):
    proc = MagicMock()
    proc.returncode = returncode
    proc.stderr = stderr
    return proc


class TestOpenLinux:
    def test_uses_gio_open_with_clean_env(self):
        with (
            patch(
                "skill_manager.utils.external_url.find_system_binary",
                side_effect=lambda name: "/usr/bin/gio" if name == "gio" else None,
            ),
            patch("skill_manager.utils.external_url.get_clean_env", return_value={"X": "1"}),
            patch(
                "skill_manager.utils.external_url.subprocess.run", return_value=_completed()
            ) as run,
        ):
            ok, reason = open_external_url(URL)

        assert ok is True
        assert reason == ""
        run.assert_called_once()
        argv = run.call_args[0][0]
        assert argv == ["/usr/bin/gio", "open", URL]
        assert run.call_args.kwargs["env"] == {"X": "1"}
        assert 0 < run.call_args.kwargs["timeout"] <= 3.0

    def test_falls_through_openers_after_a_failure(self):
        results = [_completed(1, b"symbol lookup error"), _completed(0)]
        with (
            patch(
                "skill_manager.utils.external_url.find_system_binary",
                side_effect=lambda name: f"/usr/bin/{name}",
            ),
            patch("skill_manager.utils.external_url.get_clean_env", return_value={}),
            patch("skill_manager.utils.external_url.subprocess.run", side_effect=results) as run,
        ):
            ok, _ = open_external_url(URL)

        assert ok is True
        assert [call[0][0][0] for call in run.call_args_list] == [
            "/usr/bin/gio",
            "/usr/bin/xdg-open",
        ]
        assert run.call_args_list[1][0][0] == ["/usr/bin/xdg-open", URL]

    def test_reports_every_opener_failure(self):
        with (
            patch(
                "skill_manager.utils.external_url.find_system_binary",
                side_effect=lambda name: "/usr/bin/gio" if name == "gio" else None,
            ),
            patch("skill_manager.utils.external_url.get_clean_env", return_value={}),
            patch(
                "skill_manager.utils.external_url.subprocess.run",
                return_value=_completed(1, b"undefined symbol: g_unix_mount_entry_get_options"),
            ),
        ):
            ok, reason = open_external_url(URL)

        assert ok is False
        assert "gio" in reason
        assert "g_unix_mount_entry_get_options" in reason

    def test_missing_every_opener(self):
        with (
            patch("skill_manager.utils.external_url.find_system_binary", return_value=None),
            patch("skill_manager.utils.external_url.get_clean_env", return_value={}),
        ):
            ok, reason = open_external_url(URL)

        assert ok is False
        assert "No URL opener found" in reason

    def test_os_error_continues_to_the_next_opener(self):
        with (
            patch(
                "skill_manager.utils.external_url.find_system_binary",
                side_effect=lambda name: f"/usr/bin/{name}",
            ),
            patch("skill_manager.utils.external_url.get_clean_env", return_value={}),
            patch(
                "skill_manager.utils.external_url.subprocess.run",
                side_effect=[OSError("denied"), _completed(0)],
            ) as run,
        ):
            ok, _ = open_external_url(URL)

        assert ok is True
        assert run.call_count == 2

    def test_timeout_stops_the_chain_instead_of_trying_every_opener(self):
        with (
            patch(
                "skill_manager.utils.external_url.find_system_binary",
                side_effect=lambda name: f"/usr/bin/{name}",
            ),
            patch("skill_manager.utils.external_url.get_clean_env", return_value={}),
            patch(
                "skill_manager.utils.external_url.subprocess.run",
                side_effect=subprocess.TimeoutExpired(cmd="gio", timeout=3),
            ) as run,
        ):
            ok, reason = open_external_url(URL)

        assert ok is False
        assert "timed out" in reason
        assert run.call_count == 1


class TestOpenOtherPlatforms:
    def test_refuses_unsafe_url_before_launching(self):
        with patch("skill_manager.utils.external_url.subprocess.run") as run:
            ok, reason = open_external_url("file:///etc/passwd")

        assert ok is False
        assert "unsafe" in reason
        run.assert_not_called()

    def test_windows_uses_startfile(self):
        with (
            patch("skill_manager.utils.external_url.sys.platform", "win32"),
            patch("skill_manager.utils.external_url.os.startfile", create=True) as startfile,
        ):
            ok, _ = open_external_url(URL)

        assert ok is True
        startfile.assert_called_once_with(URL)

    def test_macos_uses_open(self):
        with (
            patch("skill_manager.utils.external_url.sys.platform", "darwin"),
            patch(
                "skill_manager.utils.external_url.subprocess.run", return_value=_completed()
            ) as run,
        ):
            ok, _ = open_external_url(URL)

        assert ok is True
        assert run.call_args[0][0] == ["open", "--", URL]

    def test_unsupported_platform_is_reported(self):
        with patch("skill_manager.utils.external_url.sys.platform", "freebsd14"):
            ok, reason = open_external_url(URL)

        assert ok is False
        assert "Unsupported platform" in reason

    def test_macos_launch_failure_is_reported(self):
        with (
            patch("skill_manager.utils.external_url.sys.platform", "darwin"),
            patch(
                "skill_manager.utils.external_url.subprocess.run",
                side_effect=subprocess.SubprocessError("boom"),
            ),
        ):
            ok, reason = open_external_url(URL)

        assert ok is False
        assert "boom" in reason

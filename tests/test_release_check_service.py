"""
Tests for the GitHub Releases API version check service.
"""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from skill_manager.core.release_check_service import (
    RELEASES_URL,
    ReleaseAssetError,
    check_latest_release,
    parse_release_payload,
)


class TestCheckLatestRelease:
    """Tests for check_latest_release()."""

    @patch("skill_manager.core.release_check_service.httpx.get")
    def test_success_with_v_prefix(self, mock_get: MagicMock):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"tag_name": "v1.6.0", "name": "Release 1.6.0"}
        mock_get.return_value = mock_resp

        version, error = check_latest_release()

        assert version == "1.6.0"
        assert error is None
        mock_get.assert_called_once_with(
            RELEASES_URL,
            timeout=10.0,
            headers={"Accept": "application/vnd.github+json", "User-Agent": "SkillManager"},
        )

    @patch("skill_manager.core.release_check_service.httpx.get")
    def test_success_without_v_prefix(self, mock_get: MagicMock):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"tag_name": "2.0.0"}
        mock_get.return_value = mock_resp

        version, error = check_latest_release()

        assert version == "2.0.0"
        assert error is None

    @patch("skill_manager.core.release_check_service.httpx.get")
    def test_no_tag_name(self, mock_get: MagicMock):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"name": "Draft"}
        mock_get.return_value = mock_resp

        version, error = check_latest_release()

        assert version is None
        assert error is not None
        assert "No tag_name" in error

    @patch("skill_manager.core.release_check_service.httpx.get")
    def test_invalid_version_string(self, mock_get: MagicMock):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"tag_name": "not-a-version"}
        mock_get.return_value = mock_resp

        version, error = check_latest_release()

        assert version is None
        assert error is not None

    @patch("skill_manager.core.release_check_service.httpx.get")
    def test_timeout(self, mock_get: MagicMock):
        mock_get.side_effect = httpx.TimeoutException("connect timed out")

        version, error = check_latest_release()

        assert version is None
        assert error is not None
        assert "timed out" in error

    @patch("skill_manager.core.release_check_service.httpx.get")
    def test_http_404(self, mock_get: MagicMock):
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found", request=MagicMock(), response=mock_resp
        )
        mock_get.return_value = mock_resp

        version, error = check_latest_release()

        assert version is None
        assert error is not None
        assert "404" in error

    @patch("skill_manager.core.release_check_service.httpx.get")
    def test_http_500(self, mock_get: MagicMock):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Internal Server Error", request=MagicMock(), response=mock_resp
        )
        mock_get.return_value = mock_resp

        version, error = check_latest_release()

        assert version is None
        assert error is not None
        assert "500" in error

    @patch("skill_manager.core.release_check_service.httpx.get")
    def test_network_error(self, mock_get: MagicMock):
        mock_get.side_effect = httpx.ConnectError("Connection refused")

        version, error = check_latest_release()

        assert version is None
        assert error is not None
        assert "Connection refused" in error

    @patch("skill_manager.core.release_check_service.httpx.get")
    def test_malformed_json(self, mock_get: MagicMock):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.side_effect = ValueError("Invalid JSON")
        mock_get.return_value = mock_resp

        version, error = check_latest_release()

        assert version is None
        assert error is not None
        assert "Invalid JSON" in error


# --- Release metadata, asset selection and checksum manifest ---


from skill_manager.core.release_check_service import (  # noqa: E402
    ReleaseAsset,
    ReleaseInfo,
    fetch_latest_release,
    fetch_sha256sums,
    is_allowed_download_url,
    parse_sha256sums,
    select_update_asset,
)


def _info(assets=()):
    return ReleaseInfo(
        version="9.9.9",
        tag_name="v9.9.9",
        page_url="https://github.com/dishanagalawatta/SkillManager/releases/tag/v9.9.9",
        assets=tuple(assets),
    )


def _asset(name):
    return ReleaseAsset(
        name=name,
        url=f"https://github.com/dishanagalawatta/SkillManager/releases/download/v9.9.9/{name}",
    )


class TestReleasePayload:
    def test_parses_version_page_and_assets(self):
        release = parse_release_payload(
            {
                "tag_name": "v9.9.9",
                "html_url": "https://example.test/release",
                "body": "notes",
                "published_at": "2026-10-29T00:00:00Z",
                "assets": [
                    {
                        "name": "SHA256SUMS",
                        "browser_download_url": "https://github.com/x/y/SHA256SUMS",
                        "size": 10,
                    },
                    {
                        "name": "SkillManager-9.9.9-x86_64.AppImage",
                        "browser_download_url": "https://github.com/x/y/app.AppImage",
                        "size": 100,
                    },
                    {"name": "ignored", "browser_download_url": ""},
                ],
            }
        )
        assert release.version == "9.9.9"
        assert release.tag_name == "v9.9.9"
        assert release.page_url == "https://example.test/release"
        assert [a.name for a in release.assets] == [
            "SHA256SUMS",
            "SkillManager-9.9.9-x86_64.AppImage",
        ]
        assert release.checksums is not None
        assert release.checksums.name == "SHA256SUMS"

    def test_invalid_tag_is_an_error(self):
        with pytest.raises(ReleaseAssetError):
            parse_release_payload({"tag_name": "not-a-version"})

    def test_fetch_latest_release_returns_metadata(self):
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "tag_name": "v9.9.9",
            "html_url": "https://example.test/release",
            "assets": [
                {
                    "name": "SHA256SUMS",
                    "browser_download_url": "https://github.com/x/y/SHA256SUMS",
                }
            ],
        }
        with patch("skill_manager.core.release_check_service.httpx.get", return_value=mock_resp):
            release, error = fetch_latest_release()
        assert error is None
        assert release is not None
        assert release.version == "9.9.9"
        assert release.checksums is not None


class TestSelectUpdateAsset:
    def test_appimage_matches(self):
        asset = select_update_asset(
            _info([_asset("other.deb"), _asset("SkillManager-9.9.9-x86_64.AppImage")]),
            "appimage",
        )
        assert asset is not None
        assert asset.name.endswith(".AppImage")

    def test_deb_prefers_matching_architecture(self):
        asset = select_update_asset(
            _info(
                [
                    _asset("skill-manager_9.9.9_arm64.deb"),
                    _asset("skill-manager_9.9.9_amd64.deb"),
                ]
            ),
            "deb",
            machine="x86_64",
        )
        assert asset is not None
        assert "amd64" in asset.name

    def test_windows_requires_setup_exe(self):
        asset = select_update_asset(
            _info([_asset("portable.exe"), _asset("SkillManager_Setup.exe")]), "windows"
        )
        assert asset is not None
        assert asset.name == "SkillManager_Setup.exe"

    def test_missing_platform_asset_returns_none(self):
        assert select_update_asset(_info([_asset("x.deb")]), "appimage") is None
        assert select_update_asset(None, "appimage") is None
        assert select_update_asset(_info([_asset("x.deb")]), "unknown") is None


class TestChecksums:
    def test_parse_manifest_accepts_dist_paths_and_star_mode(self):
        text = (
            "a" * 64
            + "  dist/SkillManager-9.9.9-x86_64.AppImage\n"
            + "b" * 64
            + " *skill-manager_9.9.9_amd64.deb\n"
            + "not a checksum line\n"
        )
        sums = parse_sha256sums(text)
        assert sums["SkillManager-9.9.9-x86_64.AppImage"] == "a" * 64
        assert sums["skill-manager_9.9.9_amd64.deb"] == "b" * 64

    def test_fetch_sha256sums(self):
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.url = "https://objects.githubusercontent.com/checksums?token=1"
        mock_resp.text = "a" * 64 + "  app.AppImage\n"
        with patch(
            "skill_manager.core.release_check_service.httpx.get", return_value=mock_resp
        ) as get:
            sums, error = fetch_sha256sums(_info([_asset("SHA256SUMS")]))
        assert error is None
        assert sums["app.AppImage"] == "a" * 64
        # GitHub release assets answer with a 302 to objects.githubusercontent.com.
        assert get.call_args.kwargs["follow_redirects"] is True

    def test_manifest_redirect_to_untrusted_host_is_refused(self):
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.url = "https://evil.example/SHA256SUMS"
        mock_resp.text = "a" * 64 + "  app.AppImage\n"
        with patch("skill_manager.core.release_check_service.httpx.get", return_value=mock_resp):
            sums, error = fetch_sha256sums(_info([_asset("SHA256SUMS")]))
        assert sums == {}
        assert "untrusted host" in error

    def test_missing_manifest_is_an_error(self):
        sums, error = fetch_sha256sums(_info([_asset("app.AppImage")]))
        assert sums == {}
        assert "SHA256SUMS" in error

    def test_malformed_manifest_is_an_error(self):
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.url = (
            "https://github.com/dishanagalawatta/SkillManager/releases/download/v9.9.9/SHA256SUMS"
        )
        mock_resp.text = "garbage"
        with patch("skill_manager.core.release_check_service.httpx.get", return_value=mock_resp):
            sums, error = fetch_sha256sums(_info([_asset("SHA256SUMS")]))
        assert sums == {}
        assert "malformed" in error


class TestDownloadUrlAllowlist:
    @pytest.mark.parametrize(
        "url,allowed",
        [
            (
                "https://github.com/dishanagalawatta/SkillManager/releases/download/v1/a.deb",
                True,
            ),
            ("https://objects.githubusercontent.com/x?token=1", True),
            ("http://github.com/x/y", False),
            ("https://evil.example/x", False),
            ("file:///etc/passwd", False),
            ("", False),
        ],
    )
    def test_allowlist(self, url, allowed):
        assert is_allowed_download_url(url) is allowed

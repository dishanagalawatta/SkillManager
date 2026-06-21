"""
Tests for the GitHub Releases API version check service.
"""

from unittest.mock import MagicMock, patch

import httpx

from skill_manager.core.release_check_service import (
    RELEASES_URL,
    check_latest_release,
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

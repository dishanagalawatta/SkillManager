import asyncio
from unittest.mock import MagicMock, patch

import httpx
import pytest

from skill_manager.controllers.app_update_controller import AppUpdateController


@pytest.mark.asyncio
async def test_fetch_latest_release_uses_httpx_response():
    controller = AppUpdateController(MagicMock())
    controller._on_release_fetched = MagicMock()

    mock_response = MagicMock()
    mock_response.json.return_value = {"tag_name": "v9.9.9", "html_url": "https://example.test/release"}
    mock_response.raise_for_status.return_value = None

    with patch("httpx.AsyncClient.get", return_value=mock_response):
        await controller._fetch_latest_release()

    controller._on_release_fetched.assert_called_once_with(
        {"version": "9.9.9", "url": "https://example.test/release"}
    )


@pytest.mark.asyncio
async def test_fetch_latest_release_handles_retry_exhaustion():
    controller = AppUpdateController(MagicMock())
    controller._on_release_fetched = MagicMock()

    with patch(
        "httpx.AsyncClient.get",
        side_effect=httpx.HTTPError("timeout"),
    ) as mock_get:
        await controller._fetch_latest_release()

    assert mock_get.call_count == 3
    controller._on_release_fetched.assert_not_called()

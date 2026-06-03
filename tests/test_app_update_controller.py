from unittest.mock import MagicMock

import pytest

from skill_manager.controllers.app_update_controller import AppUpdateController


@pytest.mark.asyncio
async def test_check_tuf_updates_success():
    mock_app = MagicMock()
    controller = AppUpdateController(mock_app)

    # Mock the client and its check_for_updates method
    mock_client = MagicMock()
    mock_client.check_for_updates.return_value = "2.0.0"
    controller._client = mock_client

    # Mock the signals
    controller.updateAvailableChanged = MagicMock()
    controller.latestVersionChanged = MagicMock()

    await controller._check_tuf_updates()

    assert controller.updateAvailable is True
    assert controller.latestVersion == "2.0.0"
    controller.updateAvailableChanged.emit.assert_called()
    controller.latestVersionChanged.emit.assert_called()

@pytest.mark.asyncio
async def test_check_tuf_updates_no_update():
    mock_app = MagicMock()
    controller = AppUpdateController(mock_app)

    mock_client = MagicMock()
    mock_client.check_for_updates.return_value = None
    controller._client = mock_client

    controller.updateAvailableChanged = MagicMock()

    await controller._check_tuf_updates()

    assert controller.updateAvailable is False
    controller.updateAvailableChanged.emit.assert_called()

@pytest.mark.asyncio
async def test_check_tuf_updates_failure():
    mock_app = MagicMock()
    controller = AppUpdateController(mock_app)

    mock_client = MagicMock()
    mock_client.check_for_updates.side_effect = Exception("Network error")
    controller._client = mock_client

    # Should not raise exception but log it (guarded by try-except)
    await controller._check_tuf_updates()
    assert controller.updateAvailable is False

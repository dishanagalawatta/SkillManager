"""Progress hook signature tests for AppUpdateService.apply_update.

Verifies the progress callback works across different tufup signature variants.
"""

from unittest.mock import patch

import pytest

from skill_manager.core.update_service import AppUpdateService


@pytest.fixture
def service(tmp_path):
    tuf_dir = tmp_path / "tuf"
    target_dir = tmp_path / "updates"
    with patch("skill_manager.core.update_service.TUFClient") as mock_client:
        svc = AppUpdateService(tuf_dir, target_dir)
        svc._client = mock_client.return_value
        return svc


class TestProgressHookTwoArg:
    def test_normal_two_arg(self, service):
        service._client.download_and_apply_update.side_effect = lambda progress_hook=None: (
            (progress_hook(50, 100) if progress_hook else None) or True
        )

        captured = []
        result = service.apply_update(progress_callback=captured.append)
        assert result is True
        assert 0.5 in captured

    def test_zero_total(self, service):
        service._client.download_and_apply_update.side_effect = lambda progress_hook=None: (
            (progress_hook(50, 0) if progress_hook else None) or True
        )

        captured = []
        result = service.apply_update(progress_callback=captured.append)
        assert result is True
        assert len(captured) == 0


class TestProgressHookOneArg:
    def test_one_arg_float(self, service):
        service._client.download_and_apply_update.side_effect = lambda progress_hook=None: (
            (progress_hook(0.75) if progress_hook else None) or True
        )

        captured = []
        result = service.apply_update(progress_callback=captured.append)
        assert result is True
        assert 0.75 in captured


class TestProgressHookEdge:
    def test_no_callback(self, service):
        service._client.download_and_apply_update.return_value = True
        result = service.apply_update(progress_callback=None)
        assert result is True

    def test_callback_exception(self, service):
        def bad_callback(p):
            raise RuntimeError("callback broke")

        service._client.download_and_apply_update.side_effect = lambda progress_hook=None: (
            (progress_hook(50, 100) if progress_hook else None) or True
        )

        # Callback exception is caught by apply_update's try/except
        result = service.apply_update(progress_callback=bad_callback)
        assert result is False

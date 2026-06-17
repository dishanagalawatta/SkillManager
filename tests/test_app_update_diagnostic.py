"""Diagnostic logging tests for app update flow.

Verifies structured diagnostic events are emitted at each branch in
AppUpdateController and AppUpdateService.
"""

from unittest.mock import MagicMock, patch

import pytest

from skill_manager.controllers.app_update_controller import AppUpdateController
from skill_manager.core.diagnostics import (
    CATEGORY_APP_UPDATE_APPLIED,
    CATEGORY_APP_UPDATE_AVAILABLE,
    CATEGORY_APP_UPDATE_CHECK,
    CATEGORY_APP_UPDATE_FAILED,
    CATEGORY_APP_UPDATE_SKIPPED_DEV,
    CATEGORY_APP_UPDATE_UP_TO_DATE,
    CATEGORY_TUF_CLIENT_INIT,
    get_diagnostic_logger,
)
from skill_manager.core.update_service import AppUpdateService


@pytest.fixture
def mock_app():
    app = MagicMock()
    app.task_runner = MagicMock()
    app._set_status = MagicMock()
    return app


@pytest.fixture
def diag_log(tmp_path):
    """Provides a diagnostic logger writing to a temp file."""
    logger = get_diagnostic_logger()
    log_file = tmp_path / "diagnostic.log"
    with patch.object(logger, "_log_file", log_file):
        yield logger, log_file


@pytest.fixture
def service(tmp_path):
    tuf_dir = tmp_path / "tuf"
    target_dir = tmp_path / "updates"
    with patch("skill_manager.core.update_service.TUFClient") as mock_client:
        svc = AppUpdateService(tuf_dir, target_dir)
        svc._client = mock_client.return_value
        return svc


@pytest.fixture
def controller(mock_app, service):
    with patch(
        "skill_manager.controllers.app_update_controller.AppUpdateService",
        return_value=service,
    ):
        return AppUpdateController(mock_app)


class TestDiagnosticCheckEvents:
    def test_check_emits_event(self, controller, service, diag_log):
        diag, _ = diag_log
        service._client.check_for_updates.return_value = "1.5.0"

        def mock_submit(fn, callback):
            callback(fn())

        controller.app.task_runner.submit.side_effect = mock_submit
        with patch.object(diag, "log_event") as mock_emit:
            controller.checkForUpdates(manual=True)
            calls = {c.args[1] for c in mock_emit.call_args_list}
            assert CATEGORY_APP_UPDATE_CHECK in calls

    def test_dev_skip_emits_event(self, controller, diag_log):
        diag, _ = diag_log
        with patch("skill_manager.controllers.app_update_controller.sys") as mock_sys:
            mock_sys.frozen = False
            with patch.object(diag, "log_event") as mock_emit:
                controller.checkForUpdates(manual=False)
                calls = {c.args[1] for c in mock_emit.call_args_list}
                assert CATEGORY_APP_UPDATE_SKIPPED_DEV in calls

    def test_available_emits_event(self, controller, service, diag_log):
        diag, _ = diag_log
        service._client.check_for_updates.return_value = "2.0.0"

        def mock_submit(fn, callback):
            callback(fn())

        controller.app.task_runner.submit.side_effect = mock_submit
        with patch.object(diag, "log_event") as mock_emit:
            controller.checkForUpdates(manual=True)
            calls = {c.args[1] for c in mock_emit.call_args_list}
            assert CATEGORY_APP_UPDATE_AVAILABLE in calls

    def test_up_to_date_emits_event(self, controller, service, diag_log):
        diag, _ = diag_log
        service._client.check_for_updates.return_value = None

        def mock_submit(fn, callback):
            callback(fn())

        controller.app.task_runner.submit.side_effect = mock_submit
        with patch.object(diag, "log_event") as mock_emit:
            controller.checkForUpdates(manual=True)
            calls = {c.args[1] for c in mock_emit.call_args_list}
            assert CATEGORY_APP_UPDATE_UP_TO_DATE in calls

    def test_failed_emits_event(self, controller, service, diag_log):
        diag, _ = diag_log
        service._client.check_for_updates.side_effect = Exception("Network down")

        def mock_submit(fn, callback):
            callback(fn())

        controller.app.task_runner.submit.side_effect = mock_submit
        with patch.object(diag, "log_event") as mock_emit:
            controller.checkForUpdates(manual=True)
            calls = {c.args[1] for c in mock_emit.call_args_list}
            assert CATEGORY_APP_UPDATE_FAILED in calls


class TestDiagnosticApplyEvents:
    def test_apply_emits_event(self, controller, service, diag_log):
        diag, _ = diag_log
        controller._state.update_available = True
        service._client.download_and_apply_update.return_value = True

        def mock_run(fn):
            fn()

        controller.app.task_runner.run.side_effect = mock_run
        with patch.object(diag, "log_event") as mock_emit:
            controller.downloadAndApplyUpdate()
            calls = {c.args[1] for c in mock_emit.call_args_list}
            assert CATEGORY_APP_UPDATE_APPLIED in calls

    def test_apply_fail_emits_event(self, controller, service, diag_log):
        diag, _ = diag_log
        controller._state.update_available = True
        service._client.download_and_apply_update.return_value = False

        def mock_run(fn):
            fn()

        controller.app.task_runner.run.side_effect = mock_run
        with patch.object(diag, "log_event") as mock_emit:
            controller.downloadAndApplyUpdate()
            calls = {c.args[1] for c in mock_emit.call_args_list}
            assert CATEGORY_APP_UPDATE_FAILED in calls

    def test_apply_exception_emits_event(self, controller, service, diag_log):
        diag, _ = diag_log
        controller._state.update_available = True
        service._client.download_and_apply_update.side_effect = Exception("Download error")

        def mock_run(fn):
            fn()

        controller.app.task_runner.run.side_effect = mock_run
        with patch.object(diag, "log_event") as mock_emit:
            controller.downloadAndApplyUpdate()
            calls = {c.args[1] for c in mock_emit.call_args_list}
            assert CATEGORY_APP_UPDATE_FAILED in calls


class TestDiagnosticTUFEvents:
    def test_tuf_init_success(self, diag_log):
        diag, _ = diag_log
        tuf_dir, target_dir = diag_log[0]._log_file.parent, diag_log[0]._log_file.parent
        with (
            patch("skill_manager.core.update_service.TUFClient"),
            patch.object(diag, "log_event") as mock_emit,
        ):
            AppUpdateService(tuf_dir, target_dir)
            calls = {c.args[1] for c in mock_emit.call_args_list}
            assert CATEGORY_TUF_CLIENT_INIT in calls

    def test_tuf_init_failure(self, tmp_path):
        tuf_dir = tmp_path / "tuf"
        target_dir = tmp_path / "updates"
        with (
            patch(
                "skill_manager.core.update_service.TUFClient",
                side_effect=RuntimeError("key invalid"),
            ),
            patch("skill_manager.core.update_service.get_diagnostic_logger") as mock_diag,
        ):
            mock_log = MagicMock()
            mock_diag.return_value = mock_log
            AppUpdateService(tuf_dir, target_dir)
            emit_calls = {c.args[1] for c in mock_log.log_event.call_args_list}
            assert CATEGORY_TUF_CLIENT_INIT in emit_calls

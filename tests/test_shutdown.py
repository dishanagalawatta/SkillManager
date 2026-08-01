"""Tests for clean shutdown: watchdog exit, idempotent stop, task runner join."""

import time
from unittest.mock import patch

from skill_manager.core.global_hotkey import GlobalHotkeyManager
from skill_manager.utils.task_runner import BackgroundTaskRunner


class TestGlobalHotkeyManagerShutdown:
    """GlobalHotkeyManager must shut down cleanly without blocking."""

    def test_stop_is_idempotent(self, qapp):
        """Calling stop() twice must not double-log or deadlock."""
        mgr = GlobalHotkeyManager()
        # stop() on a manager with no hotkeys/listener
        mgr.stop()
        mgr.stop()  # must not raise or log twice
        assert mgr._cleaned_up is True

    def test_stop_sets_cleaned_up_flag(self, qapp):
        """stop() sets _cleaned_up so __del__ would be a no-op."""
        mgr = GlobalHotkeyManager()
        mgr.stop()
        assert mgr._cleaned_up is True

    def test_del_does_not_call_stop(self, qapp):
        """__del__ should not be defined — cleanup is explicit."""
        # Verify __del__ is not defined (it was removed)
        assert "__del__" not in GlobalHotkeyManager.__dict__


class TestBackgroundTaskRunnerShutdown:
    """BackgroundTaskRunner must join threads within timeout."""

    def test_run_tracks_threads(self):
        """run() records threads for later shutdown."""
        runner = BackgroundTaskRunner()
        runner.run(lambda: None)
        time.sleep(0.01)  # let thread start
        assert len(runner._threads) == 1

    def test_shutdown_joins_all_threads(self):
        """shutdown() joins threads that finish quickly."""
        runner = BackgroundTaskRunner()
        results = []

        def work():
            results.append("done")

        runner.run(work)
        runner.shutdown(timeout=2.0)
        assert results == ["done"]

    def test_shutdown_timeout_does_not_block(self):
        """shutdown() returns within timeout even for slow threads."""
        runner = BackgroundTaskRunner()
        runner.run(lambda: time.sleep(10))  # hangs for 10s

        t0 = time.monotonic()
        runner.shutdown(timeout=0.2)
        elapsed = time.monotonic() - t0

        assert elapsed < 1.0

    def test_shutdown_clears_thread_list(self):
        """shutdown() clears the tracked thread list."""
        runner = BackgroundTaskRunner()
        runner.run(lambda: None)
        time.sleep(0.01)
        runner.shutdown(timeout=1.0)
        assert len(runner._threads) == 0


class TestDumpDiagnostics:
    """dump_diagnostics must be env-gated and write to DATA_DIR, not CWD."""

    def test_noop_without_diag_env(self, tmp_path, monkeypatch):
        """Without SKILL_MANAGER_DIAG=1 the function must not create a log."""
        from skill_manager.utils.shutdown import dump_diagnostics

        monkeypatch.delenv("SKILL_MANAGER_DIAG", raising=False)
        with patch("skill_manager.utils.shutdown.DIAG_FILE", tmp_path / "shutdown_diag.log"):
            dump_diagnostics("no-gate test")
        assert not (tmp_path / "shutdown_diag.log").exists()

    def test_writes_log_when_env_set(self, tmp_path, monkeypatch):
        """With SKILL_MANAGER_DIAG=1 the function must append a diagnostic entry."""
        from skill_manager.utils.shutdown import dump_diagnostics

        monkeypatch.setenv("SKILL_MANAGER_DIAG", "1")
        diag_file = tmp_path / "shutdown_diag.log"
        with patch("skill_manager.utils.shutdown.DIAG_FILE", diag_file):
            dump_diagnostics("gated test")
        content = diag_file.read_text(encoding="utf-8")
        assert "gated test" in content
        assert "THREAD LIST" in content


class TestWatchdogExit:
    """The watchdog exit function must force-kill after timeout."""

    def test_watchdog_exit_fires_os_exit(self):
        """watchdog_exit calls os._exit after the timeout."""
        from skill_manager.utils.shutdown import watchdog_exit

        with patch("skill_manager.utils.shutdown.os._exit") as mock_exit:
            t = watchdog_exit(42, timeout=0.1)
            t.join(timeout=1.0)
            mock_exit.assert_called_once_with(42)

    def test_watchdog_exit_uses_daemon_thread(self):
        """The watchdog thread must be a daemon so it doesn't block exit."""
        from skill_manager.utils.shutdown import watchdog_exit

        with patch("skill_manager.utils.shutdown.os._exit"):
            t = watchdog_exit(0, timeout=0.1)
            assert t.daemon is True
            t.join(timeout=1.0)


class TestCleanupBounded:
    """Controller cleanup must complete within a bounded time."""

    def test_cleanup_completes_within_2s(self, app_controller):
        """cleanup() must finish even if PostHog is slow."""
        t0 = time.monotonic()
        app_controller.cleanup()
        elapsed = time.monotonic() - t0
        assert elapsed < 2.0, f"cleanup() took {elapsed:.1f}s — expected < 2.0s"

    def test_cleanup_does_not_block_on_posthog(self, app_controller):
        """cleanup() must not join the PostHog thread (fire-and-forget)."""
        with patch("skill_manager.app.posthog_shutdown") as mock_shutdown:
            mock_shutdown.side_effect = lambda: time.sleep(10)  # simulate slow shutdown
            t0 = time.monotonic()
            app_controller.cleanup()
            elapsed = time.monotonic() - t0
            # Should complete in < 1s even though posthog would take 10s
            assert elapsed < 1.0, f"cleanup() took {elapsed:.1f}s — blocked on posthog"

    def test_cleanup_flushes_sentry(self, app_controller):
        """cleanup() calls sentry_sdk.flush with 0.5s timeout."""
        with patch("skill_manager.app.sentry_sdk") as mock_sdk:
            app_controller.cleanup()
            mock_sdk.flush.assert_called_once_with(timeout=0.5)


class TestMainExitStrategy:
    """_shutdown_sequence (ex main() shutdown tail) must terminate cleanly.

    The shutdown tail moved from ``app.main()`` to ``bootstrap._shutdown_sequence``
    during the Phase 1 decomposition; these tests pin the ordering invariants on
    their new home.
    """

    def test_shutdown_uses_os_kill_or_os_exit(self):
        """The shutdown flow must call os.kill or os._exit to bypass loader lock deadlocks."""
        import inspect

        from skill_manager.bootstrap import _shutdown_sequence

        source = inspect.getsource(_shutdown_sequence)
        assert "os.kill(" in source or "os._exit(" in source, (
            "shutdown sequence should call os.kill or os._exit"
        )

    def test_shutdown_drains_qt_events_before_cleanup(self):
        """_shutdown_sequence must call processEvents() to drain Qt events."""
        import inspect

        from skill_manager.bootstrap import _shutdown_sequence

        source = inspect.getsource(_shutdown_sequence)
        assert "processEvents()" in source, "shutdown sequence should call processEvents()"

    def test_shutdown_uses_psutil_to_kill_children(self):
        """_shutdown_sequence must use psutil to kill child processes recursively bottom-up."""
        import inspect

        from skill_manager.bootstrap import _shutdown_sequence

        source = inspect.getsource(_shutdown_sequence)
        assert "psutil" in source, "shutdown sequence should use psutil"
        assert "child.kill()" in source, "shutdown sequence should kill children"

    def test_shutdown_calls_cleanup_before_termination(self):
        """cleanup() must be called before final process termination."""
        import inspect

        from skill_manager.bootstrap import _shutdown_sequence

        source = inspect.getsource(_shutdown_sequence)
        cleanup_pos = source.index("controller.cleanup()")
        term_pos = source.rindex("os.kill(")
        assert cleanup_pos < term_pos, "cleanup() must be called before os.kill()"

    def test_shutdown_drains_events_before_cleanup(self):
        """processEvents() must be called before cleanup()."""
        import inspect

        from skill_manager.bootstrap import _shutdown_sequence

        source = inspect.getsource(_shutdown_sequence)
        process_pos = source.index("processEvents()")
        cleanup_pos = source.index("controller.cleanup()")
        assert process_pos < cleanup_pos, "processEvents() must be called before cleanup()"

    def test_shutdown_clears_component_cache_before_cleanup(self):
        """engine.clearComponentCache() must run before controller.cleanup()."""
        import inspect

        from skill_manager.bootstrap import _shutdown_sequence

        source = inspect.getsource(_shutdown_sequence)
        cache_pos = source.index("engine.clearComponentCache()")
        cleanup_pos = source.index("controller.cleanup()")
        assert cache_pos < cleanup_pos, "component cache must be cleared before cleanup()"

    def test_watchdog_still_uses_os_exit(self):
        """Watchdog must still use os._exit as the failsafe."""
        import inspect

        from skill_manager.utils.shutdown import watchdog_exit

        source = inspect.getsource(watchdog_exit)
        assert "os._exit(" in source, "watchdog should use os._exit as failsafe"

    def test_cleanup_posthog_is_daemon_thread(self):
        """cleanup() must start posthog in a daemon thread (no join)."""
        import inspect

        from skill_manager.app import AppController

        source = inspect.getsource(AppController.cleanup)
        assert "daemon=True" in source, "posthog thread should be daemon"
        assert "posthog_shutdown" in source, "cleanup should call posthog_shutdown"

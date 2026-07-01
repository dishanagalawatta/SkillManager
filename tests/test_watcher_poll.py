"""Tests for per-directory watchdog (Fix 4) and stat-polling safety net (Fix 5).

Covers:
- SkillFolderWatcher schedules non-recursive watches
- add_path / remove_path methods
- _poll_known_paths detects missing paths and triggers refresh
- _poll_known_paths is no-op when all paths exist
- _poll_known_paths handles empty model gracefully
- _poll_known_paths handles exceptions gracefully
"""
from __future__ import annotations

import os
import tempfile
from unittest.mock import MagicMock, patch

from skill_manager.core.file_watch import SkillFolderWatcher


class TestPerDirectoryWatcher:
    """SkillFolderWatcher should schedule non-recursive watches."""

    def test_start_schedules_non_recursive(self):
        cb = MagicMock()
        with patch("watchdog.observers.Observer") as mock_obs:
            obs = mock_obs.return_value
            with tempfile.TemporaryDirectory() as td:
                sub = os.path.join(td, "skills")
                os.makedirs(sub)
                w = SkillFolderWatcher(paths=[sub], callback=cb)
                w.start()
                assert w.started
                calls = obs.schedule.call_args_list
                assert len(calls) == 1
                _, kwargs = calls[0]
                assert kwargs.get("recursive") is False
                w.stop()

    def test_start_skips_nonexistent_paths(self):
        cb = MagicMock()
        with patch("watchdog.observers.Observer") as mock_obs:
            obs = mock_obs.return_value
            w = SkillFolderWatcher(paths=["/nonexistent/path/xyz"], callback=cb)
            w.start()
            obs.schedule.assert_not_called()
            w.stop()

    def test_add_path_registers_new_dir(self):
        cb = MagicMock()
        with patch("watchdog.observers.Observer") as mock_obs:
            obs = mock_obs.return_value
            with tempfile.TemporaryDirectory() as td:
                w = SkillFolderWatcher(paths=[], callback=cb)
                w.start()
                sub = os.path.join(td, "new-skill")
                os.makedirs(sub)
                w.add_path(sub)
                obs.schedule.assert_called()
                w.stop()

    def test_add_path_noop_when_not_started(self):
        cb = MagicMock()
        with patch("watchdog.observers.Observer") as mock_obs:
            obs = mock_obs.return_value
            w = SkillFolderWatcher(paths=[], callback=cb)
            # Don't start — add_path should be a no-op
            w.add_path("/some/path")
            obs.schedule.assert_not_called()

    def test_remove_path_logs_best_effort(self):
        cb = MagicMock()
        w = SkillFolderWatcher(paths=[], callback=cb)
        w.started = True
        # Should not raise
        w.remove_path("/some/path")
        w.started = False

    def test_stop_cancels_handler(self):
        cb = MagicMock()
        with patch("watchdog.observers.Observer"), \
             tempfile.TemporaryDirectory() as td:
            w = SkillFolderWatcher(paths=[td], callback=cb)
            w.start()
            assert w.started
            w.stop()
            assert not w.started
            assert w._handler._timer is None


class TestPollKnownPaths:
    """_poll_known_paths detects missing skill directories."""

    def _make_app_with_model(self, known_paths):
        """Create a minimal mock app with _quick_copy_model.get_known_paths."""
        app = MagicMock()
        app._quick_copy_model.get_known_paths.return_value = known_paths
        app.refreshSkills = MagicMock()
        app._last_poll_ts = 0.0
        return app

    def test_triggers_refresh_when_path_missing(self):
        # Import first to avoid dotenv issues during patching
        from skill_manager.app import AppController
        app = self._make_app_with_model(["/existent", "/missing-skill"])
        with patch("os.path.exists", side_effect=lambda p: p == "/existent"):
            AppController._poll_known_paths(app)
        app.refreshSkills.assert_called_once_with("stat-poll", True)

    def test_no_refresh_when_all_exist(self):
        from skill_manager.app import AppController
        app = self._make_app_with_model(["/path/a", "/path/b"])
        with patch("os.path.exists", return_value=True):
            AppController._poll_known_paths(app)
        app.refreshSkills.assert_not_called()

    def test_no_refresh_when_model_empty(self):
        from skill_manager.app import AppController
        app = self._make_app_with_model([])
        AppController._poll_known_paths(app)
        app.refreshSkills.assert_not_called()

    def test_handles_exception_gracefully(self):
        from skill_manager.app import AppController
        app = MagicMock()
        app._last_poll_ts = 0.0
        app._quick_copy_model.get_known_paths.side_effect = RuntimeError("boom")
        # Should not raise
        AppController._poll_known_paths(app)
        app.refreshSkills.assert_not_called()

    def test_logs_missing_paths(self):
        from skill_manager.app import AppController
        app = self._make_app_with_model(["/a", "/b", "/c"])
        with patch("os.path.exists", side_effect=lambda p: p != "/b"), \
             patch("skill_manager.app.logger") as mock_logger:
            AppController._poll_known_paths(app)
            mock_logger.info.assert_called()
            call_args = mock_logger.info.call_args
            # call_args[0] is the format string tuple, check it mentions missing
            assert "missing" in call_args[0][0].lower()


class TestGetKnownPaths:
    """get_known_paths returns local_path values from the model."""

    def test_returns_paths(self):
        from skill_manager.core.models.qt_model import SkillModel
        model = SkillModel.__new__(SkillModel)
        model._all_skills = [
            MagicMock(local_path="/path/a"),
            MagicMock(local_path="/path/b"),
            MagicMock(local_path=""),
        ]
        result = model.get_known_paths()
        assert result == ["/path/a", "/path/b"]

    def test_empty_model(self):
        from skill_manager.core.models.qt_model import SkillModel
        model = SkillModel.__new__(SkillModel)
        model._all_skills = []
        result = model.get_known_paths()
        assert result == []

"""Tests that stat-poll triggers force_full_scan when paths are missing."""
from __future__ import annotations

from unittest.mock import MagicMock, patch


class TestPollTriggersFullScan:
    """Tests that stat-poll correctly triggers full scan when paths disappear."""

    def test_missing_path_triggers_force_scan(self) -> None:
        """Missing path in model triggers refreshSkills with force_full_scan=True."""
        from skill_manager.app import AppController

        app = MagicMock(spec=AppController)
        app._last_poll_ts = 0.0
        app._quick_copy_model = MagicMock()
        app._quick_copy_model.get_known_paths.return_value = [
            "/existing/path",
            "/nonexistent/path",
        ]
        app.refreshSkills = MagicMock()

        with patch("os.path.exists", side_effect=lambda p: p == "/existing/path"):
            AppController._poll_known_paths(app)

        app.refreshSkills.assert_called_once_with("stat-poll", True)

    def test_no_missing_paths_skips_refresh(self) -> None:
        """When all paths exist, no refresh is triggered."""
        from skill_manager.app import AppController

        app = MagicMock(spec=AppController)
        app._last_poll_ts = 0.0
        app._quick_copy_model = MagicMock()
        app._quick_copy_model.get_known_paths.return_value = [
            "/path1",
            "/path2",
        ]
        app.refreshSkills = MagicMock()

        with patch("os.path.exists", return_value=True):
            AppController._poll_known_paths(app)

        app.refreshSkills.assert_not_called()

    def test_empty_known_paths_skips_refresh(self) -> None:
        """When no known paths, no refresh is triggered."""
        from skill_manager.app import AppController

        app = MagicMock(spec=AppController)
        app._last_poll_ts = 0.0
        app._quick_copy_model = MagicMock()
        app._quick_copy_model.get_known_paths.return_value = []
        app.refreshSkills = MagicMock()

        AppController._poll_known_paths(app)

        app.refreshSkills.assert_not_called()

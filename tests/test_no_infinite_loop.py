"""Regression tests: stat-poll must not trigger infinite refresh loops."""

from __future__ import annotations

import time
from unittest.mock import MagicMock


class TestNoInfiniteLoop:
    """Tests that prevent the stat-poll infinite loop regression."""

    def test_consecutive_polls_with_debounce(self) -> None:
        """10 consecutive polls with missing paths trigger at most 1 refresh (debounce)."""
        from skill_manager.app import AppController

        app = MagicMock(spec=AppController)
        app._last_poll_ts = 0.0
        app._quick_copy_model = MagicMock()
        app._quick_copy_model.get_known_paths.return_value = ["/nonexistent/skill"]
        app.refreshSkills = MagicMock()

        # Simulate 10 rapid polls (all within 5s window)
        for _ in range(10):
            AppController._poll_known_paths(app)

        # Only the first should trigger refresh (debounce suppresses rest)
        assert app.refreshSkills.call_count == 1
        app.refreshSkills.assert_called_with("stat-poll", True)

    def test_poll_after_debounce_window_triggers_again(self) -> None:
        """After 5s debounce window, next poll triggers refresh."""
        from skill_manager.app import AppController

        app = MagicMock(spec=AppController)
        app._last_poll_ts = 0.0
        app._quick_copy_model = MagicMock()
        app._quick_copy_model.get_known_paths.return_value = ["/nonexistent/skill"]
        app.refreshSkills = MagicMock()

        # First poll triggers
        AppController._poll_known_paths(app)
        assert app.refreshSkills.call_count == 1

        # Simulate time passing (>5s)
        app._last_poll_ts = time.monotonic() - 6.0

        # Second poll should trigger
        AppController._poll_known_paths(app)
        assert app.refreshSkills.call_count == 2

    def test_poll_exception_does_not_crash(self) -> None:
        """Exception during poll is caught and does not crash."""
        from skill_manager.app import AppController

        app = MagicMock(spec=AppController)
        app._last_poll_ts = 0.0
        app._quick_copy_model = MagicMock()
        app._quick_copy_model.get_known_paths.side_effect = RuntimeError("test error")
        app.refreshSkills = MagicMock()

        # Should not raise
        AppController._poll_known_paths(app)
        app.refreshSkills.assert_not_called()

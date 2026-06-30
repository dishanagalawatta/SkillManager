"""Tests for 5-second debounce on stat-poll."""
from __future__ import annotations

import time
from unittest.mock import MagicMock


class TestPollDebounce:
    """Tests that stat-poll respects 5-second debounce window."""

    def test_first_poll_triggers_refresh(self) -> None:
        """First poll within no prior history triggers refresh."""
        from skill_manager.app import AppController

        app = MagicMock(spec=AppController)
        app._last_poll_ts = 0.0
        app._quick_copy_model = MagicMock()
        app._quick_copy_model.get_known_paths.return_value = ["/nonexistent/skill"]
        app.refreshSkills = MagicMock()

        AppController._poll_known_paths(app)

        app.refreshSkills.assert_called_once_with("stat-poll", True)
        assert app._last_poll_ts > 0.0

    def test_second_poll_within_5s_suppressed(self) -> None:
        """Second poll within 5 seconds is suppressed."""
        from skill_manager.app import AppController

        app = MagicMock(spec=AppController)
        app._last_poll_ts = time.monotonic()  # Just triggered
        app._quick_copy_model = MagicMock()
        app._quick_copy_model.get_known_paths.return_value = ["/nonexistent/skill"]
        app.refreshSkills = MagicMock()

        AppController._poll_known_paths(app)

        app.refreshSkills.assert_not_called()

    def test_poll_after_5s_triggers_refresh(self) -> None:
        """Poll after 5 seconds triggers refresh again."""
        from skill_manager.app import AppController

        app = MagicMock(spec=AppController)
        app._last_poll_ts = time.monotonic() - 6.0  # 6 seconds ago
        app._quick_copy_model = MagicMock()
        app._quick_copy_model.get_known_paths.return_value = ["/nonexistent/skill"]
        app.refreshSkills = MagicMock()

        AppController._poll_known_paths(app)

        app.refreshSkills.assert_called_once_with("stat-poll", True)

from unittest.mock import MagicMock, patch

import pytest

from skill_manager.controllers.config_controller import ConfigController


@pytest.fixture
def mock_app():
    app = MagicMock()
    app._sources = []
    app._projects = []
    app._project_aliases = {}
    app._syncing_projects = []
    app._custom_collections = {}
    app._config = MagicMock()
    app._is_recording_shortcut = False
    return app


@pytest.fixture
def controller(mock_app):
    return ConfigController(mock_app)


class TestConfigControllerSDET:
    def test_scroll_speed_multiplier_validation(self, controller, mock_app):
        # Valid value
        controller.scrollSpeedMultiplier = 2.5
        mock_app._config.set.assert_called_with("scroll_speed_multiplier", 2.5)

        # Below minimum (0.1) -> should still be 0.1 or fallback (Pydantic will coerce)
        # In our schema, ge=0.1.
        mock_app._config.reset_mock()
        controller.scrollSpeedMultiplier = 0.05
        # If Pydantic validation fails in _set_config_value, it logs warning and returns False.
        # However, our _coerce_float returns 1.0 on ValueError/TypeError.
        # ge=0.1 is a validation error.
        mock_app._config.set.assert_not_called()

        # String coercion
        mock_app._config.reset_mock()
        controller.scrollSpeedMultiplier = "3.14"
        mock_app._config.set.assert_called_with("scroll_speed_multiplier", 3.14)

    def test_update_interval_validation(self, controller, mock_app):
        # Valid
        controller.updateCheckIntervalHours = 48
        mock_app._config.set.assert_called_with("update_check_interval_hours", 48)

        # Out of range (max 168)
        mock_app._config.reset_mock()
        controller.updateCheckIntervalHours = 200
        mock_app._config.set.assert_not_called()

        # Negative
        controller.updateCheckIntervalHours = -5
        mock_app._config.set.assert_not_called()

    def test_update_mode_validation(self, controller, mock_app):
        # Valid
        controller.skillPackageAutoUpdateMode = "auto"
        mock_app._config.set.assert_called_with("skill_package_auto_update_mode", "auto")

        # Invalid -> fallback to "prompt" via validator
        mock_app._config.reset_mock()
        controller.skillPackageAutoUpdateMode = "invalid_mode"
        # Our validator returns "prompt" for unknown strings
        mock_app._config.set.assert_called_with("skill_package_auto_update_mode", "prompt")

    def test_add_source_path_normalization(self, controller, mock_app):
        with patch("pathlib.Path.resolve") as mock_resolve:
            mock_resolve.return_value = "/absolute/path"
            controller.addSource("file:///relative/path")
            assert "/absolute/path" in mock_app._sources

    def test_get_project_label_robustness(self, controller, mock_app):
        # Test standard folder
        assert controller.getProjectLabel("/home/user/MyProj") == "MyProj"

        # Test .agents/skills folder
        assert controller.getProjectLabel("/home/user/MyProj/.agents/skills") == "MyProj"

        # Test custom alias
        mock_app._project_aliases = {"/path/a": "CustomName"}
        assert controller.getProjectLabel("/path/a") == "CustomName"

    def test_set_project_alias_updates_models(self, controller, mock_app):
        mock_app._library_model = MagicMock()
        mock_app._quick_copy_model = MagicMock()
        mock_app._library_model._all_skills = [
            {"name": "S1", "project_path": "/proj/1", "project_label": "Old"}
        ]

        controller.setProjectAlias("/proj/1", "New")

        assert mock_app._project_aliases["/proj/1"] == "New"
        assert mock_app._library_model._all_skills[0]["project_label"] == "New"
        mock_app._library_model._begin_batch.assert_called()
        mock_app._library_model._end_batch.assert_called()

    def test_reset_shortcuts(self, controller, mock_app):
        mock_signal = MagicMock()
        controller.shortcutsChanged.connect(mock_signal)

        controller.resetShortcuts()
        mock_app._config.set.assert_called()
        # Verify it uses DEFAULT_SHORTCUTS
        args = mock_app._config.set.call_args[0]
        assert args[0] == "shortcuts"
        assert "search" in args[1]
        mock_signal.assert_called_once()

    def test_add_source_empty(self, controller, mock_app):
        controller.addSource("")
        assert len(mock_app._sources) == 0
        mock_app._config.set.assert_not_called()

import pytest
from unittest.mock import MagicMock, patch
from skill_manager.controllers.config_controller import ConfigController

@pytest.fixture
def mock_app():
    app = MagicMock()
    app._sources = []
    app._targets = []
    app._target_aliases = {}
    app._syncing_targets = []
    app._config = MagicMock()
    return app

@pytest.fixture
def config_controller(mock_app):
    return ConfigController(mock_app)

def test_config_controller_add_source(config_controller, mock_app):
    config_controller.add_source("/path/to/source")
    assert "/path/to/source" in mock_app._sources
    mock_app._config.set.assert_called_with("sources", mock_app._sources)
    mock_app.sourcesChanged.emit.assert_called_once()

def test_config_controller_remove_source(config_controller, mock_app):
    mock_app._sources = ["/path/1"]
    config_controller.remove_source("/path/1")
    assert "/path/1" not in mock_app._sources
    mock_app.sourcesChanged.emit.assert_called_once()

def test_config_controller_add_target(config_controller, mock_app):
    config_controller.add_target("file:///C:/project")
    assert "C:\\project" in mock_app._targets
    mock_app.targetsChanged.emit.assert_called_once()

def test_config_controller_get_target_label(config_controller, mock_app):
    mock_app._target_aliases = {"C:\\project": "MyProj"}
    assert config_controller.get_target_label("C:\\project") == "MyProj"
    import sys
    if sys.platform == "win32":
        assert config_controller.get_target_label("C:\\other") == "other"
    else:
        assert config_controller.get_target_label("C:\\other") == "other"

def test_config_controller_set_target_alias(config_controller, mock_app):
    config_controller.set_target_alias("/path/p", "NewName")
    assert mock_app._target_aliases["/path/p"] == "NewName"
    mock_app.targetsChanged.emit.assert_called_once()
    mock_app.refreshSkills.assert_called_once()

def test_config_controller_remove_target(config_controller, mock_app):
    mock_app._targets = ["/path/t"]
    mock_app._target_aliases = {"/path/t": "Alias"}
    mock_app._syncing_targets = ["/path/t"]
    
    config_controller.remove_target("/path/t")
    
    assert "/path/t" not in mock_app._targets
    assert "/path/t" not in mock_app._target_aliases
    assert "/path/t" not in mock_app._syncing_targets
    mock_app.targetsChanged.emit.assert_called_once()

@patch("skill_manager.core.skill_sources.get_git_tag")
def test_config_controller_verify_git_fail(mock_tag, config_controller, mock_app):
    mock_tag.return_value = ""
    res = config_controller.verify_git_source("http://git.com")
    assert res == ""
    mock_app._set_status.assert_any_call("Verification failed for: http://git.com")

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
    app._config = MagicMock()
    return app


@pytest.fixture
def config_controller(mock_app):
    return ConfigController(mock_app)


def test_config_controller_add_source(config_controller, mock_app):
    config_controller.addSource("/path/to/source")
    # abspath will normalize path based on platform, so we normalize for the test
    import os

    expected = os.path.abspath("/path/to/source")
    assert expected in mock_app._sources
    mock_app._config.set.assert_called_with("sources", mock_app._sources)
    mock_app.sourcesChanged.emit.assert_called_once()


def test_config_controller_remove_source(config_controller, mock_app):
    mock_app._sources = ["/path/1"]
    config_controller.removeSource("/path/1")
    assert "/path/1" not in mock_app._sources
    mock_app.sourcesChanged.emit.assert_called_once()


def test_config_controller_add_project(config_controller, mock_app):
    config_controller.addProject("file:///C:/project")
    assert "C:\\project" in mock_app._projects
    mock_app.projectsChanged.emit.assert_called_once()


def test_config_controller_get_project_label(config_controller, mock_app):
    mock_app._project_aliases = {"C:\\project": "MyProj"}
    assert config_controller.getProjectLabel("C:\\project") == "MyProj"
    import sys

    if sys.platform == "win32":
        assert config_controller.getProjectLabel("C:\\other") == "other"
    else:
        assert config_controller.getProjectLabel("C:\\other") == "C:\\other"


def test_config_controller_set_project_alias(config_controller, mock_app):
    config_controller.setProjectAlias("/path/p", "NewName")
    assert mock_app._project_aliases["/path/p"] == "NewName"
    mock_app.projectsChanged.emit.assert_called_once()
    mock_app.refreshSkills.assert_called_once()


def test_config_controller_remove_project(config_controller, mock_app):
    mock_app._projects = ["/path/t"]
    mock_app._project_aliases = {"/path/t": "Alias"}
    mock_app._syncing_projects = ["/path/t"]

    config_controller.removeProject("/path/t")

    assert "/path/t" not in mock_app._projects
    assert "/path/t" not in mock_app._project_aliases
    assert "/path/t" not in mock_app._syncing_projects
    mock_app.projectsChanged.emit.assert_called_once()


def test_config_controller_add_source_invalid(config_controller, mock_app):
    config_controller.addSource("")
    mock_app.sourcesChanged.emit.assert_not_called()


def test_config_controller_add_project_invalid(config_controller, mock_app):
    config_controller.addProject("")
    mock_app.projectsChanged.emit.assert_not_called()


@patch("skill_manager.core.skill_packages.get_git_tag")
def test_config_controller_verify_git_fail(mock_tag, config_controller, mock_app):
    mock_tag.return_value = ""
    res = config_controller.verifyGitPackage("http://git.com")
    assert res == ""
    mock_app._set_status.assert_any_call("Verification failed for: http://git.com")

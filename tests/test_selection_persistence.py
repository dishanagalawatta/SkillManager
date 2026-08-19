"""Tests for selection persistence before closing and on startup."""

from unittest.mock import MagicMock, patch

from skill_manager.controllers.selected_skill_controller import SelectedSkillController
from skill_manager.core.models.entities import Skill
from skill_manager.core.models.qt_model import SkillModel


def _make_mock_config(data=None):
    """Create a mock ConfigManager storing data in a dict."""
    storage = dict(data or {})
    config = MagicMock()
    config.get = MagicMock(side_effect=lambda key, default=None: storage.get(key, default))

    def _set(key, val):
        storage[key] = val

    config.set = MagicMock(side_effect=_set)
    config._storage = storage
    return config


def test_selection_sync_current_project():
    """Toggling selection must immediately sync _selections_by_project for active project."""
    config = _make_mock_config()
    model = SkillModel(config=config)

    skill = Skill(name="Test Skill", local_path="/path/to/skill1")
    model.addOrUpdateSkills([skill])

    model.toggleSelection(0)
    assert model.getSelectedPaths() == ["/path/to/skill1"]
    assert model._selections_by_project[""] == ["/path/to/skill1"]

    model._do_save_project_selections()
    assert config._storage["project_selections"][""] == ["/path/to/skill1"]


def test_selection_restored_on_boot_default_project():
    """Selections stored under project_filter="" must be restored on boot."""
    stored_selections = {"": ["/path/to/skill1"]}
    config = _make_mock_config({"project_selections": stored_selections, "project_filter": ""})

    model = SkillModel(config=config)
    assert model.getSelectedPaths() == ["/path/to/skill1"]


def test_selection_swap_and_restore_named_project():
    """Swapping projects must preserve selections per project."""
    config = _make_mock_config()
    model = SkillModel(config=config)

    skill1 = Skill(name="Skill 1", local_path="/path/1", project_label="ProjA")
    skill2 = Skill(name="Skill 2", local_path="/path/2", project_label="ProjB")
    model.addOrUpdateSkills([skill1, skill2])

    model.projectFilter = "ProjA"
    model.selectByPaths(["/path/1"])
    assert model._selections_by_project["ProjA"] == ["/path/1"]

    model.projectFilter = "ProjB"
    assert model.getSelectedPaths() == []
    model.selectByPaths(["/path/2"])
    assert model._selections_by_project["ProjB"] == ["/path/2"]

    model.projectFilter = "ProjA"
    assert model.getSelectedPaths() == ["/path/1"]


def test_on_quit_flushes_pending_selection_timers():
    """AppController.on_quit must flush pending selection save timers."""
    from skill_manager.app import AppController

    config = _make_mock_config()

    patches = [
        patch("skill_manager.app.ConfigManager", return_value=config),
        patch("skill_manager.app.BackgroundTaskRunner"),
        patch("skill_manager.app.QtScheduler"),
        patch("skill_manager.app.load_archive", return_value=[]),
        patch("skill_manager.app.load_starred", return_value=[]),
        patch("skill_manager.app.get_diagnostic_logger"),
    ]
    for p in patches:
        p.start()

    try:
        app = AppController(skip_initial_load=True, config=config)
        skill = Skill(name="Skill 1", local_path="/path/to/skill1")
        app._library_model.addOrUpdateSkills([skill])

        app._library_model.selectByPaths(["/path/to/skill1"])
        # Verify save timer is active
        assert app._library_model._project_selections_save_timer is not None

        # Call on_quit directly
        app.on_quit()

        # Config should contain flushed selections under scoped key library.project_selections
        assert config._storage["library.project_selections"][""] == ["/path/to/skill1"]
    finally:
        for p in patches:
            p.stop()


def test_selected_skill_controller_persists_last_selected_path():
    """SelectedSkillController must save last_selected_skill_path to config."""
    config = _make_mock_config()
    mock_app = MagicMock()
    mock_app._config = config
    mock_app._library_model = MagicMock()
    mock_app._quick_copy_model = MagicMock()

    ctrl = SelectedSkillController(mock_app)
    ctrl.setSelection({"local_path": "/path/to/skill1", "name": "Skill 1"})

    assert config._storage.get("last_selected_skill_path") == "/path/to/skill1"

    ctrl.clearSelection()
    assert config._storage.get("last_selected_skill_path") == ""

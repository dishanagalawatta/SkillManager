from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from skill_manager.controllers.ops_controller import OpsController
from skill_manager.utils.task_runner import SynchronousTaskRunner


@pytest.fixture
def ops_controller(mock_app):
    with patch("skill_manager.controllers.ops_controller.QTimer.singleShot") as mock_timer:
        mock_timer.side_effect = lambda msec, receiver, functor=None: (functor() if functor is not None else receiver())
        yield OpsController(mock_app)


@pytest.fixture
def real_ops_controller(temp_dir, mock_config):
    """OpsController backed by a real AppController with real models."""
    from skill_manager.app import AppController

    controller = AppController(skip_initial_load=True, config=mock_config)
    controller.task_runner = SynchronousTaskRunner()
    controller._projects = []
    controller._sources = []
    controller._archive_paths = []
    controller._starred_paths = []
    controller._project_aliases = {}
    controller._categories = []
    return controller.ops


def test_ops_controller_toggle_archive(ops_controller, mock_app):
    mock_app._selected_skill = {"local_path": "/path/s", "is_archived": False}
    with patch("skill_manager.controllers.ops_controller.save_archive") as mock_save:
        ops_controller.toggleArchive()

        assert "/path/s" in mock_app._archive_paths
        assert mock_app._selected_skill["is_archived"] is True
        mock_app.selectedSkillChanged.emit.assert_called()
        mock_save.assert_called_with(mock_app._archive_paths)


def test_ops_controller_toggle_archive_restore(ops_controller, mock_app):
    mock_app._selected_skill = {"local_path": "/path/s", "is_archived": True}
    mock_app._archive_paths = ["/path/s"]
    with patch("skill_manager.controllers.ops_controller.save_archive") as mock_save:
        ops_controller.toggleArchive()

        assert "/path/s" not in mock_app._archive_paths
        assert mock_app._selected_skill["is_archived"] is False
        mock_save.assert_called_with(mock_app._archive_paths)


def test_ops_controller_toggle_archive_no_skill(ops_controller, mock_app):
    mock_app._selected_skill = None
    ops_controller.toggleArchive()
    mock_app.selectedSkillChanged.emit.assert_not_called()


def test_ops_controller_toggle_archive_no_path(ops_controller, mock_app):
    mock_app._selected_skill = {"name": "NoPath"}
    ops_controller.toggleArchive()
    mock_app.selectedSkillChanged.emit.assert_not_called()


def test_ops_controller_toggle_starred(ops_controller, mock_app):
    mock_app._selected_skill = {"local_path": "/path/e", "is_starred": False}
    with patch("skill_manager.controllers.ops_controller.save_starred") as mock_save:
        ops_controller.toggleStarred()

        assert "/path/e" in mock_app._starred_paths
        assert mock_app._selected_skill["is_starred"] is True
        mock_save.assert_called_with(mock_app._starred_paths)


def test_ops_controller_toggle_starred_remove(ops_controller, mock_app):
    mock_app._selected_skill = {"local_path": "/path/e", "is_starred": True}
    mock_app._starred_paths = ["/path/e"]
    with patch("skill_manager.controllers.ops_controller.save_starred") as mock_save:
        ops_controller.toggleStarred()

        assert "/path/e" not in mock_app._starred_paths
        assert mock_app._selected_skill["is_starred"] is False
        mock_save.assert_called_with(mock_app._starred_paths)


def test_ops_controller_toggle_starred_no_path(ops_controller, mock_app):
    mock_app._selected_skill = {"name": "NoPath"}
    ops_controller.toggleStarred()
    mock_app.selectedSkillChanged.emit.assert_not_called()


@patch("skill_manager.controllers.ops_controller.delete_project_skill_folders")
@patch("skill_manager.controllers.ops_controller.QTimer.singleShot")
def test_ops_controller_delete_commands(mock_timer, mock_del, ops_controller, mock_app, tmp_path):
    cmd_file = tmp_path / "test.md"
    cmd_file.write_text("content")

    items = [{"name": "Cmd", "local_path": str(cmd_file), "is_command": True}]
    with patch("skill_manager.controllers.ops_controller.patch_cache_remove") as mock_patch:
        ops_controller.deleteSkills(items)
        assert not cmd_file.exists()
        mock_patch.assert_called_with([str(cmd_file)])


@patch("skill_manager.controllers.ops_controller.delete_project_skill_folders")
@patch("skill_manager.controllers.ops_controller.QTimer.singleShot")
def test_ops_controller_delete_skills(mock_timer, mock_del, ops_controller, mock_app):
    mock_del.return_value = {
        "deleted": 1,
        "failed": 0,
        "details": [{"path": "/p1", "status": "deleted"}],
    }

    items = [{"name": "S1", "local_path": "/p1", "is_command": False}]
    with patch("skill_manager.controllers.ops_controller.patch_cache_remove") as mock_patch:
        ops_controller.deleteSkills(items)
        mock_del.assert_called_once()
        mock_patch.assert_called_with(["/p1"])


def test_ops_controller_delete_screenshots(ops_controller, tmp_path):
    screenshot = tmp_path / "Screenshot_test.png"
    screenshot.write_text("fake-image-data")

    items = [{"name": "Screenshot", "local_path": str(screenshot), "is_screenshot": True}]
    with (
        patch("skill_manager.controllers.ops_controller.patch_cache_remove") as mock_patch,
        patch("skill_manager.controllers.ops_controller.QTimer.singleShot"),
    ):
        ops_controller.deleteSkills(items)
        assert not screenshot.exists()
        mock_patch.assert_called_with([str(screenshot)])


def test_ops_controller_cleanup_temp_copies(ops_controller, tmp_path):
    temp_dir = tmp_path / "temp_skill"
    temp_dir.mkdir()
    temp_file = tmp_path / "temp_file.txt"
    temp_file.write_text("temp")

    with (
        patch(
            "skill_manager.controllers.ops_controller.load_temp_registry",
            return_value=[str(temp_dir), str(temp_file)],
        ),
        patch("skill_manager.controllers.ops_controller.save_temp_registry") as mock_save,
    ):
        ops_controller.cleanup_temp_copies()

        assert not temp_dir.exists()
        assert not temp_file.exists()
        mock_save.assert_called_with([])


def test_ops_controller_cleanup_temp_screenshots(ops_controller, tmp_path):
    screenshot = tmp_path / "Screenshot_test.png"
    screenshot.write_text("fake-image-data")
    cache_entry_path = str(screenshot)

    with (
        patch(
            "skill_manager.controllers.ops_controller.load_temp_screenshots_registry",
            return_value=[cache_entry_path],
        ),
        patch("skill_manager.controllers.ops_controller.patch_cache_remove") as mock_cache_remove,
        patch(
            "skill_manager.controllers.ops_controller.save_temp_screenshots_registry"
        ) as mock_save,
    ):
        ops_controller.cleanup_temp_screenshots()

        assert not screenshot.exists()
        mock_cache_remove.assert_called_with([cache_entry_path])
        mock_save.assert_called_with([])


def test_ops_controller_cleanup_temp_screenshots_empty(ops_controller):
    with patch(
        "skill_manager.controllers.ops_controller.load_temp_screenshots_registry",
        return_value=[],
    ):
        ops_controller.cleanup_temp_screenshots()


def test_ops_controller_cleanup_temp_screenshots_crash_recovery(ops_controller, tmp_path):
    screenshot = tmp_path / "Screenshot_test.png"
    cache_entry_path = str(screenshot)
    assert not screenshot.exists()

    with (
        patch(
            "skill_manager.controllers.ops_controller.load_temp_screenshots_registry",
            return_value=[cache_entry_path],
        ),
        patch("skill_manager.controllers.ops_controller.patch_cache_remove") as mock_cache_remove,
        patch(
            "skill_manager.controllers.ops_controller.save_temp_screenshots_registry"
        ) as mock_save,
    ):
        ops_controller.cleanup_temp_screenshots()

        mock_cache_remove.assert_called_with([cache_entry_path])
        mock_save.assert_called_with([])


@patch("skill_manager.core.copier.copy_skill_folders_to_projects")
@patch("skill_manager.controllers.ops_controller.QTimer.singleShot")
def test_ops_controller_copy_selected(mock_timer, mock_copy, ops_controller, mock_app):
    mock_copy.return_value = {"copied": 1, "merged": 0, "details": []}

    mock_app.skillModel.getSelectedPaths.return_value = ["/p1"]
    mock_app.skillModel._all_skills = [{"local_path": "/p1", "name": "S1"}]

    ops_controller.copySelectedSkillsToProject("/project")

    mock_copy.assert_called_once()
    mock_app._set_status.assert_any_call("Copying 1 skills...")


@patch("skill_manager.core.copier.copy_skill_folders_to_projects")
@patch("skill_manager.controllers.ops_controller.QTimer.singleShot")
def test_ops_controller_copy_selected_temporary(mock_timer, mock_copy, ops_controller, mock_app):
    mock_copy.return_value = {
        "copied": 1,
        "merged": 0,
        "details": [{"status": "copied", "message": "/project/S1"}],
    }

    mock_app.skillModel.getSelectedPaths.return_value = ["/p1"]
    mock_app.skillModel._all_skills = [{"local_path": "/p1", "name": "S1"}]

    with (
        patch("skill_manager.controllers.ops_controller.load_temp_registry", return_value=[]),
        patch("skill_manager.controllers.ops_controller.save_temp_registry") as mock_save,
    ):
        ops_controller.copySelectedSkillsToProject("/project", is_temporary=True)

        mock_save.assert_called_with(["/project/S1"])


def test_ops_controller_update_models_source(ops_controller, mock_app):
    mock_app._library_model.updateSkillProperty.return_value = True
    mock_app._quick_copy_model.updateSkillProperty.return_value = True

    ops_controller._updateModelsProperty("/path/s", "is_archived", True)

    mock_app._library_model.updateSkillProperty.assert_called_with("/path/s", "is_archived", True)
    mock_app._quick_copy_model.updateSkillProperty.assert_called_with(
        "/path/s", "is_archived", True
    )


def test_ops_controller_toggle_archive_updates_all_skills_list(ops_controller, mock_app):
    skill = {"local_path": "/path/s", "is_archived": False}
    mock_app._selected_skill = skill
    mock_app._library_model._all_skills = [skill]
    mock_app._quick_copy_model._all_skills = [{"local_path": "/path/s", "is_archived": False}]

    with patch("skill_manager.controllers.ops_controller.save_archive") as mock_save:
        ops_controller.toggleArchive()

        assert skill["is_archived"] is True
        mock_save.assert_called_once()


def test_ops_controller_toggle_starred_updates_all_skills_list(ops_controller, mock_app):
    skill = {"local_path": "/path/e", "is_starred": False}
    mock_app._selected_skill = skill
    mock_app._library_model._all_skills = [skill]
    mock_app._quick_copy_model._all_skills = [{"local_path": "/path/e", "is_starred": False}]

    with patch("skill_manager.controllers.ops_controller.save_starred") as mock_save:
        ops_controller.toggleStarred()

        assert skill["is_starred"] is True
        mock_save.assert_called_once()


@patch("skill_manager.core.copier.copy_skill_folders_to_projects")
@patch("skill_manager.controllers.ops_controller.QTimer.singleShot")
def test_ops_controller_copy_selected_targeted_discovery_and_dynamic_update(
    mock_timer, mock_copy, ops_controller, mock_app
):
    mock_copy.return_value = {
        "copied": 1,
        "merged": 0,
        "details": [{"status": "copied", "message": "/project/S1", "project": "/project"}],
    }

    mock_app.skillModel.getSelectedPaths.return_value = ["/p1"]
    mock_app.skillModel._all_skills = [{"local_path": "/p1", "name": "S1"}]
    mock_app._sources = []
    mock_app._projects = ["/project"]
    mock_app._archive_paths = []
    mock_app._starred_paths = []
    mock_app._project_aliases = {}
    mock_app._categories = ["General"]

    # Mock discover_single to return a mock skill dict
    mock_skill_data = {
        "local_path": "/project/S1",
        "name": "S1",
        "category": "Development",
        "project_label": "Project S1",
    }

    # Intercept QTimer.singleShot callback execution
    timer_callbacks = []

    def mock_single_shot(ms, obj, callback):
        timer_callbacks.append(callback)

    mock_timer.side_effect = mock_single_shot

    with (
        patch(
            "skill_manager.core.discovery.DiscoveryService.discover_single",
            return_value=mock_skill_data,
        ) as mock_discover,
        patch("skill_manager.controllers.ops_controller.patch_cache_add") as mock_patch_cache,
    ):
        ops_controller.copySelectedSkillsToProject("/project")

        mock_copy.assert_called_once()
        mock_discover.assert_called_once()
        mock_patch_cache.assert_called_once_with([mock_skill_data])

        # Execute singleShot callbacks to verify UI updates
        for cb in timer_callbacks:
            cb()

        # Check QML models updated surgically
        mock_app._library_model.addOrUpdateSkills.assert_called_once_with([mock_skill_data])
        mock_app._quick_copy_model.addOrUpdateSkills.assert_called_once_with([mock_skill_data])

        # Verify category update
        assert "Development" in mock_app._categories
        mock_app.categoriesChanged.emit.assert_called()


def test_ops_controller_copy_selected_no_project(ops_controller, mock_app):
    ops_controller.copySelectedSkillsToProject("")
    mock_app._set_status.assert_not_called()


def test_ops_controller_copy_selected_no_selection(ops_controller, mock_app):
    mock_app.skillModel.getSelectedPaths.return_value = []
    ops_controller.copySelectedSkillsToProject("/project")
    mock_app._set_status.assert_called_with("No skills selected to copy")


@patch("skill_manager.core.copier.copy_skill_folders_to_projects")
@patch("skill_manager.controllers.ops_controller.QTimer.singleShot")
def test_ops_controller_copy_selected_exception(mock_timer, mock_copy, ops_controller, mock_app):
    # Execute singleShot callbacks immediately
    mock_timer.side_effect = lambda ms, obj, cb: cb()

    mock_copy.side_effect = RuntimeError("Disk full")
    mock_app.skillModel.getSelectedPaths.return_value = ["/p1"]
    mock_app.skillModel._all_skills = [{"local_path": "/p1"}]

    ops_controller.copySelectedSkillsToProject("/project")

    mock_app._set_status.assert_called_with("Copy failed: Disk full")


@patch("skill_manager.controllers.ops_controller.delete_project_skill_folders")
@patch("skill_manager.controllers.ops_controller.QTimer.singleShot")
def test_ops_controller_delete_skills_partial_failure(
    mock_timer, mock_del, ops_controller, mock_app
):
    # Execute singleShot callbacks immediately
    mock_timer.side_effect = lambda ms, obj, cb: cb()

    # Simulate 1 deleted, 1 failed
    mock_del.return_value = {
        "deleted": 1,
        "failed": 1,
        "details": [{"path": "/p1", "status": "deleted"}],
    }

    items = [{"name": "S1", "local_path": "/p1"}, {"name": "S2", "local_path": "/p2"}]
    ops_controller.deleteSkills(items)

    mock_app._set_status.assert_called_with("Deletion complete: 1 deleted, 1 failed")


def test_ops_controller_aliases(ops_controller):
    with patch.object(OpsController, "toggleArchive") as mock_archive:
        ops_controller.toggleCurrentSkillArchive()
        mock_archive.assert_called_once()

    with patch.object(OpsController, "toggleStarred") as mock_starred:
        ops_controller.toggleCurrentSkillStarred()
        mock_starred.assert_called_once()


def test_ops_controller_archive_selected_skills(ops_controller, mock_app):
    mock_app.skillModel.getSelectedPaths.return_value = ["/p1", "/p2"]
    mock_app._archive_paths = ["/p1"]  # /p1 already archived
    mock_app._library_model._all_skills = []
    mock_app._quick_copy_model._all_skills = []

    with patch("skill_manager.controllers.ops_controller.save_archive") as mock_save:
        ops_controller.archiveSelectedSkills()

        assert "/p2" in mock_app._archive_paths
        mock_save.assert_called_once()
        mock_app._set_status.assert_called_with("1 skills archived")
        mock_app._library_model.updateSkillProperty.assert_called()
        mock_app._quick_copy_model.updateSkillProperty.assert_called()

    # Test already archived case
    mock_app.skillModel.getSelectedPaths.return_value = ["/p1", "/p2"]
    mock_app._archive_paths = ["/p1", "/p2"]
    ops_controller.archiveSelectedSkills()
    mock_app._set_status.assert_called_with("Selected skills are already archived")

    # Test no selection case
    mock_app.skillModel.getSelectedPaths.return_value = []
    ops_controller.archiveSelectedSkills()
    mock_app._set_status.assert_called_with("No skills selected for archiving")


def test_ops_controller_add_to_archive(ops_controller, mock_app):
    mock_app._archive_paths = []
    mock_app._library_model.updateSkillProperty.return_value = True
    mock_app._quick_copy_model.updateSkillProperty.return_value = True
    ops_controller.addToArchive("/p3")
    assert "/p3" in mock_app._archive_paths
    mock_app._library_model.updateSkillProperty.assert_called_with("/p3", "is_archived", True)
    mock_app._quick_copy_model.updateSkillProperty.assert_called_with("/p3", "is_archived", True)
    mock_app._set_status.assert_called_with("Skill archived: /p3")


def test_ops_controller_clipboard_operations(ops_controller, mock_app):
    mock_app.skillModel._all_skills = [{"local_path": "/p1", "name": "S1"}]
    mock_app._client_format = "Gemini"
    mock_app.config_controller.autoMinimizeOnQuickCopy = False
    mock_app.ui_controller.currentView = "QuickCopy"

    # Test copySkillToClipboard (skill exists)
    with patch("skill_manager.core.quick_copy.format_project_skill_reference", return_value="REF"):
        ops_controller.copySkillToClipboard("/p1")
        mock_app._clipboard.setText.assert_called_with("REF")

    # Test copySkillToClipboard (raw text)
    ops_controller.copySkillToClipboard("raw text")
    mock_app._clipboard.setText.assert_called_with("raw text")

    # Test auto-minimize signal
    mock_app.config_controller.autoMinimizeOnQuickCopy = True

    # Connect a mock to the signal
    signal_mock = MagicMock()
    ops_controller.minimizeAppRequested.connect(signal_mock)

    ops_controller.copyTextToClipboard("some text")
    assert signal_mock.called

    # Test no minimize if view is different
    signal_mock.reset_mock()
    mock_app.ui_controller.currentView = "Library"
    ops_controller.copyTextToClipboard("some text")
    assert not signal_mock.called


def test_ops_controller_copy_selection_orchestration(ops_controller, mock_app):
    # 1. Selected items
    mock_app.skillModel.selectedCount = 2
    with patch.object(ops_controller, "copySelectedSkillsToClipboard") as mock_copy:
        ops_controller.copyCurrentSelectionOrFocusedSkill()
        mock_copy.assert_called_once()

    # 2. Focused skill
    mock_app.skillModel.selectedCount = 0
    mock_app._selected_skill = {"local_path": "/focused"}
    with patch.object(ops_controller, "copySkillReference") as mock_ref:
        ops_controller.copyCurrentSelectionOrFocusedSkill()
        mock_ref.assert_called_with(mock_app._selected_skill)

    # 3. First skill
    mock_app._selected_skill = None
    mock_app.skillModel.get_skill_at.return_value = {"local_path": "/first"}
    with patch.object(ops_controller, "copySkillReference") as mock_ref:
        ops_controller.copyCurrentSelectionOrFocusedSkill()
        mock_ref.assert_called_with({"local_path": "/first"})

    # 4. Nothing
    mock_app.skillModel.get_skill_at.return_value = None
    ops_controller.copyCurrentSelectionOrFocusedSkill()
    mock_app._set_status.assert_called_with("No skill available to copy")


@patch("skill_manager.core.persistence.patch_cache_add")
@patch("skill_manager.core.discovery.DiscoveryService.discover_single")
@patch("skill_manager.core.commands.create_custom_command_file")
def test_ops_controller_create_custom_command(
    mock_create, mock_discover, mock_patch_cache, ops_controller, mock_app
):
    mock_result = MagicMock(
        ok=True, message="Created command: test.md", path=Path("/project/.agents/commands/test.md")
    )
    mock_create.return_value = mock_result
    mock_discover.return_value = {
        "local_path": "/project/.agents/commands/test.md",
        "name": "test",
        "category": "Commands",
    }
    mock_app._sources = []
    mock_app._projects = ["/project"]
    mock_app._archive_paths = []
    mock_app._starred_paths = []
    mock_app._project_aliases = {}
    mock_app._categories = []

    ops_controller.createCustomCommand("cmd", "body", ["proj"], "cat")
    mock_create.assert_called_once()
    mock_discover.assert_called_once_with(
        Path("/project/.agents/commands/test.md"), Path("/project/.agents/commands")
    )
    mock_patch_cache.assert_called_once()
    mock_app._library_model.addOrUpdateSkills.assert_called_once()
    mock_app._quick_copy_model.addOrUpdateSkills.assert_called_once()

    # Verify category update
    assert "Commands" in mock_app._categories
    mock_app.categoriesChanged.emit.assert_called()
    mock_app._set_status.assert_called_with("Created command in 1 project(s)")


def test_ops_controller_toggle_starred_none(ops_controller, mock_app):
    mock_app._selected_skill = None
    ops_controller.toggleStarred()
    mock_app.selectedSkillChanged.emit.assert_not_called()


def test_ops_controller_delete_skills_empty(ops_controller, mock_app):
    ops_controller.deleteSkills([])


def test_ops_controller_copy_text_to_clipboard(ops_controller, mock_app):
    ops_controller.copyTextToClipboard("test text")
    mock_app._clipboard.setText.assert_called_with("test text")


def test_set_project_alias_targeted_update(mock_app):
    from skill_manager.controllers.config_controller import ConfigController

    mock_app._project_aliases = {}
    mock_app._categories = ["Dev"]
    skill_library = {
        "local_path": "/src/S1",
        "project_path": "/project",
        "project_label": "OldLabel",
    }
    skill_quick = {"local_path": "/src/S1", "project_path": "/project", "project_label": "OldLabel"}
    mock_app._library_model._all_skills = [skill_library]
    mock_app._quick_copy_model._all_skills = [skill_quick]

    config_ctrl = ConfigController(mock_app)
    config_ctrl.setProjectAlias("/project", "NewLabel")

    assert skill_library["project_label"] == "NewLabel"
    assert skill_quick["project_label"] == "NewLabel"
    mock_app._set_status.assert_called_with("Renamed project to: NewLabel")


def test_set_project_alias_no_refresh(mock_app):
    from skill_manager.controllers.config_controller import ConfigController

    mock_app._project_aliases = {}
    mock_app._categories = ["Dev"]
    skill = {"local_path": "/src/S1", "project_path": "/other_project", "project_label": "Old"}
    mock_app._library_model._all_skills = [skill]
    mock_app._quick_copy_model._all_skills = []

    config_ctrl = ConfigController(mock_app)
    config_ctrl.setProjectAlias("/project", "NewLabel")

    assert skill["project_label"] == "Old"


@patch("skill_manager.core.persistence.patch_cache_add")
@patch("skill_manager.core.discovery.DiscoveryService.discover_project")
@patch("skill_manager.core.commands.update_custom_command_file_multi")
def test_update_custom_command_full(
    mock_update_multi,
    mock_discover,
    mock_patch_cache,
    ops_controller,
    mock_app,
    tmp_path,
):
    """updateCustomCommandFull updates a single command file."""
    mock_app._sources = []
    mock_app._projects = ["/project"]
    mock_app._archive_paths = []
    mock_app._starred_paths = []
    mock_app._project_aliases = {}
    mock_app._categories = []

    commands_dir = tmp_path / "commands"
    commands_dir.mkdir(parents=True, exist_ok=True)

    local_path = commands_dir / "Cmd.md"
    local_path.write_text("---\nname: Cmd\n---\nold body", encoding="utf-8")

    update_result = MagicMock(
        ok=True,
        message="Updated command: Cmd.md",
        path=local_path,
        needs_conflict_resolution=False,
        conflicting_path=None,
        suggested_rename=None,
        needs_confirm=False,
        pending_removals=[],
    )
    mock_update_multi.return_value = [update_result]

    mock_discover.return_value = [{
        "local_path": str(local_path),
        "name": "Cmd",
        "category": "Commands",
    }]

    ops_controller.updateCustomCommandFull(
        str(local_path),
        "Cmd",
        "new body",
        "NewCat",
        ["Old"],
        "",
    )

    mock_update_multi.assert_called_once_with(
        local_path=str(local_path),
        name="Cmd",
        body="new body",
        category="NewCat",
        project_labels=["Old"],
        project_paths=mock_app._projects,
        project_aliases=mock_app._project_aliases,
        on_conflict=None,
        confirmed_removals=None,
    )
    mock_discover.assert_called_once()
    mock_patch_cache.assert_called_once()
    mock_app._set_status.assert_called_with("Updated command in 1 project(s)")


@patch("skill_manager.core.persistence.patch_cache_add")
@patch("skill_manager.core.discovery.DiscoveryService.discover_project")
@patch("skill_manager.core.commands.update_custom_command_file_multi")
def test_update_custom_command_full_moves_to_new_project(
    mock_update_multi,
    mock_discover,
    mock_patch_cache,
    ops_controller,
    mock_app,
    tmp_path,
):
    """updateCustomCommandFull moves file to a new project."""
    mock_app._sources = []
    mock_app._projects = ["/projectA", "/projectB"]
    mock_app._archive_paths = []
    mock_app._starred_paths = []
    mock_app._project_aliases = {}
    mock_app._categories = []

    local_path = tmp_path / "cmd.md"
    local_path.write_text("---\nname: cmd\n---\nbody")

    new_path = tmp_path / "cmd_new.md"
    update_result = MagicMock(
        ok=True,
        message="Updated command: cmd_new.md",
        path=new_path,
        needs_conflict_resolution=False,
        conflicting_path=None,
        suggested_rename=None,
        needs_confirm=False,
        pending_removals=[],
    )
    mock_update_multi.return_value = [update_result]

    mock_discover.return_value = [{
        "local_path": str(new_path),
        "name": "cmd",
        "category": "NewCat",
    }]

    ops_controller.updateCustomCommandFull(
        str(local_path), "cmd", "new body", "NewCat", ["ProjectB"], ""
    )

    mock_update_multi.assert_called_once_with(
        local_path=str(local_path),
        name="cmd",
        body="new body",
        category="NewCat",
        project_labels=["ProjectB"],
        project_paths=mock_app._projects,
        project_aliases=mock_app._project_aliases,
        on_conflict=None,
        confirmed_removals=None,
    )
    mock_app._set_status.assert_called_with("Updated command in 1 project(s)")
    mock_patch_cache.assert_called_once()


@patch("skill_manager.core.commands.update_custom_command_file_multi")
def test_update_custom_command_full_emits_conflict_signal(
    mock_update_multi,
    ops_controller,
    mock_app,
    tmp_path,
):
    """updateCustomCommandFull emits commandUpdateConflict on conflict."""
    mock_app._sources = []
    mock_app._projects = ["/project"]
    mock_app._archive_paths = []
    mock_app._starred_paths = []
    mock_app._project_aliases = {}
    mock_app._categories = []

    local_path = tmp_path / "cmd.md"
    local_path.write_text("---\nname: cmd\n---\nbody")
    conflict_path = tmp_path / "other.md"

    update_result = MagicMock(
        ok=False,
        message="conflict",
        path=None,
        needs_conflict_resolution=True,
        conflicting_path=conflict_path,
        suggested_rename="cmd-1.md",
        needs_confirm=False,
        pending_removals=[],
    )
    mock_update_multi.return_value = [update_result]

    ops_controller.updateCustomCommandFull(str(local_path), "cmd", "new body", "NewCat", ["ProjectB"])

    # The controller calls self.app.commandUpdateConflict.emit(...)
    # With MagicMock, the attribute creates a new mock each time, so we
    # verify the call was made by checking _set_status was NOT called
    # (i.e. the controller returned early via the conflict path).
    mock_app._set_status.assert_not_called()


@patch("skill_manager.controllers.ops_controller.QTimer.singleShot")
def test_copy_collection_to_clipboard(mock_timer, ops_controller, mock_app):
    skill1 = MagicMock(local_path="/skill/a", name="SkillA")
    skill2 = MagicMock(local_path="/skill/b", name="SkillB")
    mock_app.skillModel._all_skills = [skill1, skill2]
    mock_app._client_format = "Gemini"
    mock_app._custom_collections = {
        "MyCollection": {
            "paths": ["/skill/a", "/skill/b"],
            "projects": [],
            "shortcut": "",
            "shortcut_enabled": True,
        }
    }
    mock_app.config_controller.autoMinimizeOnQuickCopy = False

    with patch("skill_manager.core.quick_copy.format_project_skill_reference") as mock_fmt:
        mock_fmt.side_effect = lambda s, fmt, all_skills: (
            "ref:SkillA" if s.local_path == "/skill/a" else "ref:SkillB"
        )
        ops_controller.copyCollectionToClipboard("MyCollection")

        assert mock_fmt.call_count == 2
        mock_app._clipboard.setText.assert_called_once_with("ref:SkillA ref:SkillB")
        mock_app._set_status.assert_called_with("Copied collection 'MyCollection' (2 skills)")
        mock_timer.assert_called_once_with(50, ops_controller._send_paste_to_focused_window)


@patch("skill_manager.controllers.ops_controller.QTimer.singleShot")
def test_copy_collection_to_clipboard_no_paths(mock_timer, ops_controller, mock_app):
    mock_app._custom_collections = {"Empty": {"paths": [], "projects": []}}
    ops_controller.copyCollectionToClipboard("Empty")
    mock_app._set_status.assert_called_with("Collection 'Empty' has no skills")
    mock_app._clipboard.setText.assert_not_called()


@patch("skill_manager.controllers.ops_controller.QTimer.singleShot")
def test_copy_collection_to_clipboard_missing_skill(mock_timer, ops_controller, mock_app):
    mock_app.skillModel._all_skills = []
    mock_app._custom_collections = {
        "Partial": {
            "paths": ["/skill/a"],
            "projects": [],
            "shortcut": "",
            "shortcut_enabled": True,
        }
    }
    mock_app.config_controller.autoMinimizeOnQuickCopy = False

    with patch("skill_manager.core.quick_copy.format_project_skill_reference") as mock_fmt:
        ops_controller.copyCollectionToClipboard("Partial")
        mock_fmt.assert_not_called()
        mock_app._clipboard.setText.assert_called_once_with("/skill/a")
        mock_timer.assert_called_once_with(50, ops_controller._send_paste_to_focused_window)


@patch("skill_manager.controllers.ops_controller.QTimer.singleShot")
def test_copy_collection_to_clipboard_non_dict_entry(mock_timer, ops_controller, mock_app):
    mock_app._custom_collections = {"Bad": "not a dict"}
    ops_controller.copyCollectionToClipboard("Bad")
    mock_app._clipboard.setText.assert_not_called()


@patch("skill_manager.controllers.ops_controller.QTimer.singleShot")
def test_copy_collection_to_clipboard_auto_minimize(mock_timer, ops_controller, mock_app):
    skill = MagicMock(local_path="/skill/a")
    mock_app.skillModel._all_skills = [skill]
    mock_app._client_format = "Gemini"
    mock_app._custom_collections = {
        "MinColl": {
            "paths": ["/skill/a"],
            "projects": [],
            "shortcut": "",
            "shortcut_enabled": True,
        }
    }
    mock_app.config_controller.autoMinimizeOnQuickCopy = True

    signal_mock = MagicMock()
    ops_controller.minimizeAppRequested.connect(signal_mock)

    with patch("skill_manager.core.quick_copy.format_project_skill_reference", return_value="ref"):
        ops_controller.copyCollectionToClipboard("MinColl")
        signal_mock.assert_called_once()
        mock_timer.assert_called_once_with(120, ops_controller._send_paste_to_focused_window)


@patch("skill_manager.utils.win32.send_paste_to_focused_window", return_value=False)
def test_send_paste_to_focused_window_failure_sets_status(mock_paste, ops_controller, mock_app):
    ops_controller._send_paste_to_focused_window()
    mock_app._set_status.assert_called_with("Copied, but could not paste automatically")


# ---------------------------------------------------------------------------
# _refresh_selected_skill tests
# ---------------------------------------------------------------------------


class TestRefreshSelectedSkill:
    """Tests for OpsController._refresh_selected_skill."""

    def test_noop_when_nothing_selected(self, ops_controller, mock_app):
        mock_app._selected_skill = {}
        ops_controller._refresh_selected_skill("/any/path")
        mock_app.selectedSkillChanged.emit.assert_not_called()

    def test_noop_when_different_path_selected(self, ops_controller, mock_app):
        from skill_manager.core.models.entities import Skill

        mock_app._selected_skill = {"local_path": "/other/path"}
        skill = Skill(name="Test", local_path="/other/path")
        mock_app.skillModel._filtered_skills = [skill]
        ops_controller._refresh_selected_skill("/target/path")
        mock_app.selectedSkillChanged.emit.assert_not_called()

    def test_refreshes_when_same_path_selected(self, ops_controller, mock_app):
        from skill_manager.core.models.entities import Skill

        mock_app._selected_skill = {"local_path": "/cmd/Cmd.md", "name": "Cmd"}
        updated_skill = Skill(name="Cmd", local_path="/cmd/Cmd.md", body_content="new body")
        mock_app.skillModel._filtered_skills = [updated_skill]
        mock_app.skillModel.get_skill_at.return_value = {
            "local_path": "/cmd/Cmd.md",
            "name": "Cmd",
            "body_content": "new body",
        }

        ops_controller._refresh_selected_skill("/cmd/Cmd.md")

        mock_app.selectedSkillChanged.emit.assert_called_once()
        mock_app.skillModel.get_skill_at.assert_called_with(0)
        assert mock_app._selected_skill["body_content"] == "new body"

    def test_rename_refreshes_with_new_path(self, ops_controller, mock_app):
        from skill_manager.core.models.entities import Skill

        mock_app._selected_skill = {"local_path": "/cmd/Old.md", "name": "Old"}
        renamed_skill = Skill(name="New", local_path="/cmd/New.md", body_content="updated")
        mock_app.skillModel._filtered_skills = [renamed_skill]
        mock_app.skillModel.get_skill_at.return_value = {
            "local_path": "/cmd/New.md",
            "name": "New",
            "body_content": "updated",
        }

        ops_controller._refresh_selected_skill("/cmd/Old.md", rename_path="/cmd/New.md")

        mock_app.selectedSkillChanged.emit.assert_called_once()
        mock_app.skillModel.get_skill_at.assert_called_with(0)
        assert mock_app._selected_skill["local_path"] == "/cmd/New.md"

    def test_not_in_view_when_path_missing_from_model(self, ops_controller, mock_app):
        mock_app._selected_skill = {"local_path": "/cmd/Missing.md"}
        mock_app.skillModel._filtered_skills = []

        ops_controller._refresh_selected_skill("/cmd/Missing.md")

        mock_app.selectedSkillChanged.emit.assert_not_called()

    def test_diagnostic_events_emitted(self, ops_controller, mock_app):

        mock_app._selected_skill = {}
        with patch("skill_manager.controllers.ops_controller.get_diagnostic_logger") as mock_diag:
            ops_controller._refresh_selected_skill("/any/path")
            mock_diag.return_value.log_event.assert_called_with(
                "INFO", "selection_refreshed", "noop: nothing selected"
            )


# ---------------------------------------------------------------------------
# Integration: createCustomCommand refreshes selection (real DiscoveryService)
# ---------------------------------------------------------------------------


def _write_command_file(path: Path, name: str, body: str, category: str = "Commands"):
    """Write a valid command file with YAML frontmatter."""
    path.parent.mkdir(parents=True, exist_ok=True)
    content = (
        f"---\nname: {name}\ncategory: {category}\ntype: command\ndate: 2026-01-01\n---\n\n{body}"
    )
    path.write_text(content, encoding="utf-8")


def _load_command_into_model(app_controller, cmd_path: Path, name: str, body: str):
    """Load a command into both models so _refresh_selected_skill can find it."""

    skill_data = {
        "local_path": str(cmd_path),
        "name": name,
        "body_content": body,
        "category": "Custom Commands",
        "main_category": "⚙️ System & Workflow",
        "is_command": True,
        "is_starred": False,
        "is_bundle": False,
        "is_archived": False,
        "is_selected": False,
        "is_package": False,
        "is_source": False,
        "project_label": "test-project",
        "source": "Custom",
        "risk": "Low",
        "description": "",
        "raw_content": "",
    }
    app_controller._library_model.addOrUpdateSkills([skill_data])
    app_controller._quick_copy_model.addOrUpdateSkills([skill_data])
    # Ensure the skill is in _filtered_skills so _refresh_selected_skill can find it
    for model in (app_controller._library_model, app_controller._quick_copy_model):
        model.showCommands = True
        model.state.is_package_only = None
        model._apply_filter()
    return skill_data


@patch("skill_manager.core.persistence.patch_cache_add")
def test_create_custom_command_refreshes_selection_real_discovery(
    mock_patch_cache,
    real_ops_controller,
    temp_dir,
):
    """createCustomCommand uses real DiscoveryService and discovers the new command.

    This test exercises the production path end-to-end: the real command file
    is written to disk, the real DiscoveryService parses it, and the controller
    merges it into the model.  On main (pre-fix), this fails
    because discover_single returns None for bare .md command files.
    """
    app = real_ops_controller.app
    project_path = temp_dir / "project"
    project_path.mkdir()
    commands_dir = project_path / ".agents" / "commands"
    commands_dir.mkdir(parents=True)

    app._projects = [str(project_path)]

    # Track signal emissions
    emissions = []
    app.selectedSkillChanged.connect(lambda: emissions.append(True))

    # Act — uses real create_custom_command_file + real DiscoveryService
    from skill_manager.core.quick_copy import project_label as compute_project_label

    label = compute_project_label(project_path)
    real_ops_controller.createCustomCommand("NewCmd", "echo world", [label], "Commands")

    # The new command was created; verify it exists on disk and discover_single works
    new_cmd_file = commands_dir / "NewCmd.md"
    assert new_cmd_file.exists(), "New command file should exist on disk"

    from skill_manager.core.discovery import DiscoveryService

    svc = DiscoveryService(
        sources=list(app._sources),
        projects=app._projects,
        archive_paths=app._archive_paths,
        starred_paths=app._starred_paths,
        project_aliases=app._project_aliases,
    )
    skill_data = svc.discover_single(new_cmd_file, new_cmd_file.parent)
    assert skill_data is not None, (
        "discover_single returned None for newly created command — "
        "the command file parser should handle bare .md files"
    )


@patch("skill_manager.core.persistence.patch_cache_add")
def test_update_custom_command_refreshes_selection_real_discovery(
    mock_patch_cache,
    real_ops_controller,
    temp_dir,
):
    """updateCustomCommandFull refreshes _selected_skill using real DiscoveryService.

    This test exercises the production path end-to-end: the real command file
    is written to disk, the real DiscoveryService parses it, and the controller
    refreshes the selected skill snapshot.  On main (pre-fix), this fails
    because discover_single returns None for bare .md command files.
    """
    app = real_ops_controller.app
    project_path = temp_dir / "project"
    project_path.mkdir()
    commands_dir = project_path / ".agents" / "commands"
    commands_dir.mkdir(parents=True)

    # Create a command file on disk
    cmd_file = commands_dir / "Cmd.md"
    _write_command_file(cmd_file, "Cmd", "old body")

    # Load into model and select
    _load_command_into_model(app, cmd_file, "Cmd", "old body")
    app._selected_skill = {"local_path": str(cmd_file), "name": "Cmd"}

    emissions = []
    app.selectedSkillChanged.connect(lambda: emissions.append(True))

    # Act — uses real update_custom_command_file + real DiscoveryService
    from skill_manager.core.quick_copy import project_label as compute_project_label

    proj_label = compute_project_label(project_path)
    real_ops_controller.app._projects = [str(project_path)]
    real_ops_controller.updateCustomCommandFull(
        str(cmd_file), "Cmd", "new body", "Commands", [proj_label]
    )

    from PySide6.QtWidgets import QApplication
    QApplication.processEvents()

    # The command was updated; verify _selected_skill reflects the new body
    assert emissions, (
        "selectedSkillChanged was not emitted after updateCustomCommandFull — "
        "discover_single likely returned None for the command file"
    )


@patch("skill_manager.core.persistence.patch_cache_add")
def test_update_custom_command_rename_refreshes_selection_real_discovery(
    mock_patch_cache,
    real_ops_controller,
    temp_dir,
):
    """updateCustomCommandFull refreshes _selected_skill after rename using real DiscoveryService."""
    app = real_ops_controller.app
    project_path = temp_dir / "project"
    project_path.mkdir()
    commands_dir = project_path / ".agents" / "commands"
    commands_dir.mkdir(parents=True)

    # Create the original command file
    old_file = commands_dir / "OldCmd.md"
    _write_command_file(old_file, "OldCmd", "old body")

    # Load into model and select using the old path
    _load_command_into_model(app, old_file, "OldCmd", "old body")
    app._selected_skill = {"local_path": str(old_file), "name": "OldCmd"}

    emissions = []
    app.selectedSkillChanged.connect(lambda: emissions.append(True))

    # Act — rename to NewCmd.md
    from skill_manager.core.quick_copy import project_label as compute_project_label

    proj_label = compute_project_label(project_path)
    real_ops_controller.app._projects = [str(project_path)]
    real_ops_controller.updateCustomCommandFull(
        str(old_file), "NewCmd", "updated body", "Commands", [proj_label]
    )

    from PySide6.QtWidgets import QApplication
    QApplication.processEvents()

    # The old file should be gone, new file should exist
    new_file = commands_dir / "NewCmd.md"
    assert new_file.exists(), "Renamed command file should exist"
    assert not old_file.exists(), "Old command file should be removed after rename"

    # _selected_skill should now point to the new path
    assert emissions, (
        "selectedSkillChanged was not emitted after rename — "
        "discover_single likely returned None for the command file"
    )
    assert app._selected_skill.get("local_path") == str(new_file), (
        f"_selected_skill should point to renamed file, got {app._selected_skill.get('local_path')}"
    )


@patch("skill_manager.core.persistence.patch_cache_add")
def test_create_custom_command_no_selection_refresh_for_different_skill_real_discovery(
    mock_patch_cache,
    real_ops_controller,
    temp_dir,
):
    """createCustomCommand does not refresh selection when a different skill is selected."""
    app = real_ops_controller.app
    project_path = temp_dir / "project"
    project_path.mkdir()

    app._projects = [str(project_path)]

    app._selected_skill = {"local_path": "/other/skill/Skill.md", "name": "Other"}

    emissions = []
    app.selectedSkillChanged.connect(lambda: emissions.append(True))

    from skill_manager.core.quick_copy import project_label as compute_project_label

    label = compute_project_label(project_path)
    real_ops_controller.createCustomCommand("NewCmd", "body", label, "cat")

    # selectedSkillChanged should NOT fire — the created command is different
    # from the currently selected skill
    assert not emissions, "selectedSkillChanged should not fire for a different skill"


# ---------------------------------------------------------------------------
# Tests 9-10: multi-project confirm flow in updateCustomCommandFull
# ---------------------------------------------------------------------------


@patch("skill_manager.core.commands.update_custom_command_file_multi")
def test_update_custom_command_full_needs_confirm_emits_signal(
    mock_multi,
    ops_controller,
    mock_app,
    tmp_path,
):
    """updateCustomCommandFull emits commandPendingRemovals when needs_confirm."""
    mock_app._sources = []
    mock_app._projects = ["/projectA", "/projectB"]
    mock_app._archive_paths = []
    mock_app._starred_paths = []
    mock_app._project_aliases = {}
    mock_app._categories = []

    local_path = tmp_path / "Cmd.md"
    local_path.write_text("---\nname: Cmd\n---\nbody", encoding="utf-8")

    # Mock multi to return needs_confirm
    confirm_result = MagicMock(
        ok=True,
        message="Confirmation required",
        needs_conflict_resolution=False,
        conflicting_path=None,
        suggested_rename=None,
        needs_confirm=True,
        pending_removals=["projB"],
    )
    mock_multi.return_value = [confirm_result]

    # Track signal emissions
    signal_payloads = []

    # In PySide6, we can't easily mock a real Signal object on an instantiated QObject.
    # Instead, we just connect a slot to capture emissions.
    ops_controller.commandPendingRemovals.connect(
        lambda path, labels: signal_payloads.append((path, labels))
    )

    ops_controller.updateCustomCommandFull(
        str(local_path),
        "Cmd",
        "new body",
        "Commands",
        ["projA", "projB"],
        "",
    )

    # Signal should be emitted
    assert len(signal_payloads) == 1
    assert signal_payloads[0][0] == str(local_path)
    assert "projB" in signal_payloads[0][1]

    # Pending update stored
    assert ops_controller._pending_command_update is not None
    assert ops_controller._pending_command_update["local_path"] == str(local_path)
    assert ops_controller._pending_command_update["name"] == "Cmd"
    assert ops_controller._pending_command_update["project_labels"] == ["projA", "projB"]


@patch("skill_manager.core.commands.update_custom_command_file_multi")
def test_confirm_command_removals_reinvokes_with_confirmed(
    mock_multi,
    ops_controller,
    mock_app,
    tmp_path,
):
    """confirmCommandRemovals re-invoke updateCustomCommandFull with confirmed labels."""
    mock_app._sources = []
    mock_app._projects = ["/projectA", "/projectB"]
    mock_app._archive_paths = []
    mock_app._starred_paths = []
    mock_app._project_aliases = {}
    mock_app._categories = []

    local_path = tmp_path / "Cmd.md"
    local_path.write_text("---\nname: Cmd\n---\nbody", encoding="utf-8")

    # Set up _pending_command_update as if confirm flow stored it
    ops_controller._pending_command_update = {
        "local_path": str(local_path),
        "name": "Cmd",
        "body": "body",
        "category": "Commands",
        "project_labels": ["projA", "projB"],
        "on_conflict": "",
    }

    # After confirm, multi returns ok=False (no rescan path) — we only
    # need to verify that confirmCommandRemovals re-invoked with the
    # right confirmed_removals.
    fail_result = MagicMock(
        ok=False,
        message="Simulated failure to stop before rescan",
        path=None,
        needs_conflict_resolution=False,
        conflicting_path=None,
        suggested_rename=None,
        needs_confirm=False,
        pending_removals=[],
    )
    mock_multi.return_value = [fail_result]

    ops_controller.confirmCommandRemovals(str(local_path), ["projB"])

    # _pending_command_update cleared
    assert ops_controller._pending_command_update is None

    # multi was re-invoked with confirmed_removals
    mock_multi.assert_called_once_with(
        local_path=str(local_path),
        name="Cmd",
        body="body",
        category="Commands",
        project_labels=["projA", "projB"],
        project_paths=mock_app._projects,
        project_aliases=mock_app._project_aliases,
        on_conflict=None,
        confirmed_removals=["projB"],
    )


def test_ops_controller_confirm_command_skills_carry(ops_controller, mock_app):
    import json
    with patch("skill_manager.core.copier.copy_commands_with_skill_carry") as mock_carry:
        mock_carry.return_value = {
            "copied": 1,
            "skills_copied": 2,
            "skills_failed": 0,
            "missing_skills": [],
        }
        ops_controller.confirmCommandSkillsCarry(
            "/proj/path",
            json.dumps(["/cmd/path"]),
            json.dumps([{"name": "Skill1"}])
        )
        mock_carry.assert_called_once_with(
            [{"local_path": "/cmd/path", "name": "path"}],
            "/proj/path",
            mock_app._library_model._all_skills,
            confirmed_skills=[{"name": "Skill1"}],
        )
        mock_app._set_status.assert_called_with(
            "Copied 1 command(s) and 2 skill(s) to project."
        )


@patch("skill_manager.core.discovery.DiscoveryService")
@patch("skill_manager.core.persistence.patch_cache_add")
def test_ops_controller_create_custom_command_emits_carry_prompt(
    mock_patch, mock_discovery, ops_controller, mock_app, tmp_path
):
    import json

    from skill_manager.core.commands import CommandCreateResult

    cmd_path = tmp_path / ".agents" / "commands" / "Cmd.md"
    results = [CommandCreateResult(ok=True, message="Success", path=cmd_path)]

    emissions = []
    ops_controller.commandSkillsCarryPrompt.connect(
        lambda cmd, proj, miss: emissions.append((cmd, proj, miss))
    )

    with (
        patch("skill_manager.core.commands.create_custom_command_files_multi", return_value=results),
        patch("skill_manager.core.copier.find_missing_skills_for_commands", return_value=[{"name": "Skill1"}]),
    ):
        ops_controller.createCustomCommand("Cmd", "body", ["projA"], "Commands")

        assert len(emissions) == 1
        cmd_json, proj_str, miss_json = emissions[0]
        assert json.loads(cmd_json) == [str(cmd_path)]
        assert Path(proj_str) == tmp_path
        assert json.loads(miss_json) == [{"name": "Skill1"}]


@patch("skill_manager.core.discovery.DiscoveryService")
@patch("skill_manager.core.persistence.patch_cache_add")
def test_ops_controller_update_custom_command_emits_carry_prompt(
    mock_patch, mock_discovery, ops_controller, mock_app, tmp_path
):
    import json

    from skill_manager.core.commands import CommandUpdateResult

    cmd_path = tmp_path / ".agents" / "commands" / "Cmd.md"
    results = [CommandUpdateResult(ok=True, message="Success", path=cmd_path)]

    emissions = []
    ops_controller.commandSkillsCarryPrompt.connect(
        lambda cmd, proj, miss: emissions.append((cmd, proj, miss))
    )

    with (
        patch("skill_manager.core.commands.update_custom_command_file_multi", return_value=results),
        patch("skill_manager.core.copier.find_missing_skills_for_commands", return_value=[{"name": "Skill1"}]),
    ):
        ops_controller.updateCustomCommandFull(str(cmd_path), "Cmd", "body", "Commands", ["projA"])

        assert len(emissions) == 1
        cmd_json, proj_str, miss_json = emissions[0]
        assert json.loads(cmd_json) == [str(cmd_path)]
        assert Path(proj_str) == tmp_path
        assert json.loads(miss_json) == [{"name": "Skill1"}]

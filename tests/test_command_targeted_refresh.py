"""Tests for targeted refresh: updateCustomCommandFull removes stale paths immediately."""

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def ops_controller(mock_app):
    with patch("skill_manager.controllers.ops_controller.QTimer.singleShot") as mock_timer:
        mock_timer.side_effect = lambda msec, functor: functor()
        from skill_manager.controllers.ops_controller import OpsController

        yield OpsController(mock_app)


def _skill_dict(name, local_path, project_path):
    """Build a minimal skill dict as returned by DiscoveryService."""
    return {
        "name": name,
        "local_path": str(local_path),
        "project_path": str(project_path),
    }


class _FakeSkill:
    """Skill-like object with attribute access, matching Skill entity interface."""

    def __init__(self, local_path, project_path):
        self.local_path = local_path
        self.project_path = project_path


def _ok_result(path):
    """Build a successful update result with all attributes explicitly set."""
    return MagicMock(
        ok=True,
        message="Updated",
        path=path,
        needs_confirm=False,
        needs_conflict_resolution=False,
        conflicting_path=None,
        suggested_rename=None,
        pending_removals=[],
    )


def _setup_models(mock_app):
    """Wire up mock models so _snapshot_affected_paths can iterate _all_skills."""
    for model in (mock_app._library_model, mock_app._quick_copy_model):
        model._all_skills = []
        model._begin_batch = MagicMock()
        model._end_batch = MagicMock()
        model.addOrUpdateSkills = MagicMock()
        model.removeSkillsByPath = MagicMock()
    return mock_app


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@patch("skill_manager.core.commands.find_project_path_by_label")
@patch("skill_manager.core.commands.find_command_holder_projects")
@patch("skill_manager.core.persistence.patch_cache_add")
@patch("skill_manager.core.discovery.DiscoveryService.discover_project")
@patch("skill_manager.core.commands.update_custom_command_file_multi")
def test_removal_drops_stale_path_immediately(
    mock_update_multi,
    mock_discover,
    mock_patch_cache,
    mock_find_holders,
    mock_find_label,
    ops_controller,
    mock_app,
    tmp_path,
):
    """Removing a command from project B (via pending_removals) should drop its stale path."""
    _setup_models(mock_app)
    mock_app._projects = ["/projectA", "/projectB"]
    mock_app._project_aliases = {}

    # Simulate existing skill entries for both projects
    path_a = tmp_path / "projA" / ".agents" / "commands" / "Cmd.md"
    path_b = tmp_path / "projB" / ".agents" / "commands" / "Cmd.md"
    path_a.parent.mkdir(parents=True, exist_ok=True)
    path_b.parent.mkdir(parents=True, exist_ok=True)
    path_a.write_text("---\nname: Cmd\n---\nold body", encoding="utf-8")
    path_b.write_text("---\nname: Cmd\n---\nold body", encoding="utf-8")

    proj_a = tmp_path / "projA"
    proj_b = tmp_path / "projB"

    # Both models have entries for both projects BEFORE the update
    for model in (mock_app._library_model, mock_app._quick_copy_model):
        model._all_skills = [
            _FakeSkill(str(path_a), str(proj_a)),
            _FakeSkill(str(path_b), str(proj_b)),
        ]

    # Mock: find_project_path_by_label resolves removal target
    mock_find_label.return_value = proj_b

    mock_update_multi.return_value = [_ok_result(path_a)]

    # After rescan of A and B: A has Cmd, B has nothing (removed)
    mock_discover.side_effect = [
        [_skill_dict("Cmd", path_a, proj_a)],  # projectA rescan
        [],  # projectB rescan — nothing found
    ]

    # updateCustomCommandFull with confirmed_removals=["projectB"]
    ops_controller.updateCustomCommandFull(
        str(path_a),
        "Cmd",
        "new body",
        "Commands",
        ["projectA"],
        "",
        confirmed_removals=["projectB"],
    )

    for model_name in ("_library_model", "_quick_copy_model"):
        model = getattr(mock_app, model_name)
        model.removeSkillsByPath.assert_called_once()
        removed = model.removeSkillsByPath.call_args[0][0]
        assert str(path_b) in removed
        assert str(path_a) not in removed


@patch("skill_manager.core.commands.find_command_holder_projects")
@patch("skill_manager.core.persistence.patch_cache_add")
@patch("skill_manager.core.discovery.DiscoveryService.discover_project")
@patch("skill_manager.core.commands.update_custom_command_file_multi")
def test_rename_removes_old_local_path(
    mock_update_multi,
    mock_discover,
    mock_patch_cache,
    mock_find_holders,
    ops_controller,
    mock_app,
    tmp_path,
):
    """Renaming a command should remove the old path and add the new one."""
    _setup_models(mock_app)
    mock_app._projects = ["/projectA"]
    mock_app._project_aliases = {}

    old_path = tmp_path / "projA" / ".agents" / "commands" / "OldCmd.md"
    new_path = tmp_path / "projA" / ".agents" / "commands" / "NewCmd.md"
    old_path.parent.mkdir(parents=True, exist_ok=True)
    old_path.write_text("---\nname: OldCmd\n---\nbody", encoding="utf-8")

    proj_a = tmp_path / "projA"

    # Model has the OLD path
    for model in (mock_app._library_model, mock_app._quick_copy_model):
        model._all_skills = [
            _FakeSkill(str(old_path), str(proj_a)),
        ]

    mock_find_holders.return_value = ["projectA"]
    mock_update_multi.return_value = [_ok_result(new_path)]

    # After rescan, only the NEW path is discovered
    mock_discover.return_value = [
        _skill_dict("NewCmd", new_path, proj_a),
    ]

    ops_controller.updateCustomCommandFull(
        str(old_path), "NewCmd", "body", "Commands", ["projectA"], ""
    )

    for model_name in ("_library_model", "_quick_copy_model"):
        model = getattr(mock_app, model_name)
        model.removeSkillsByPath.assert_called_once()
        removed = model.removeSkillsByPath.call_args[0][0]
        assert str(old_path) in removed


@patch("skill_manager.core.commands.find_command_holder_projects")
@patch("skill_manager.core.persistence.patch_cache_add")
@patch("skill_manager.core.discovery.DiscoveryService.discover_project")
@patch("skill_manager.core.commands.update_custom_command_file_multi")
def test_add_to_new_project_inserts_entry(
    mock_update_multi,
    mock_discover,
    mock_patch_cache,
    mock_find_holders,
    ops_controller,
    mock_app,
    tmp_path,
):
    """Adding a command to a new project should insert an entry, not remove anything."""
    _setup_models(mock_app)
    mock_app._projects = ["/projectA", "/projectB"]
    mock_app._project_aliases = {}

    path_a = tmp_path / "projA" / ".agents" / "commands" / "Cmd.md"
    path_a.parent.mkdir(parents=True, exist_ok=True)
    path_a.write_text("---\nname: Cmd\n---\nbody", encoding="utf-8")

    proj_a = tmp_path / "projA"
    proj_b = tmp_path / "projB"

    # Model only has projA BEFORE the update
    for model in (mock_app._library_model, mock_app._quick_copy_model):
        model._all_skills = [
            _FakeSkill(str(path_a), str(proj_a)),
        ]

    mock_find_holders.return_value = ["projectA"]
    mock_update_multi.return_value = [_ok_result(path_a)]

    # After rescan, both projects have the skill (projB now has it too)
    path_b = tmp_path / "projB" / ".agents" / "commands" / "Cmd.md"
    mock_discover.return_value = [
        _skill_dict("Cmd", path_a, proj_a),
        _skill_dict("Cmd", path_b, proj_b),
    ]

    ops_controller.updateCustomCommandFull(
        str(path_a), "Cmd", "body", "Commands", ["projectA", "projectB"], ""
    )

    for model_name in ("_library_model", "_quick_copy_model"):
        model = getattr(mock_app, model_name)
        # No stale paths — removeSkillsByPath should not have been called
        model.removeSkillsByPath.assert_not_called()
        # addOrUpdateSkills was called with both discovered entries
        model.addOrUpdateSkills.assert_called_once()
        added = model.addOrUpdateSkills.call_args[0][0]
        assert len(added) == 2


@patch("skill_manager.core.commands.find_command_holder_projects")
@patch("skill_manager.core.persistence.patch_cache_add")
@patch("skill_manager.core.discovery.DiscoveryService.discover_project")
@patch("skill_manager.core.commands.update_custom_command_file_multi")
def test_unaffected_projects_not_touched(
    mock_update_multi,
    mock_discover,
    mock_patch_cache,
    mock_find_holders,
    ops_controller,
    mock_app,
    tmp_path,
):
    """Skills in unaffected projects should not be removed."""
    _setup_models(mock_app)
    mock_app._projects = ["/projectA", "/projectB", "/projectC"]
    mock_app._project_aliases = {}

    path_a = tmp_path / "projA" / ".agents" / "commands" / "Cmd.md"
    path_c = tmp_path / "projC" / ".agents" / "commands" / "Cmd.md"
    path_a.parent.mkdir(parents=True, exist_ok=True)
    path_c.parent.mkdir(parents=True, exist_ok=True)
    path_a.write_text("---\nname: Cmd\n---\nbody", encoding="utf-8")
    path_c.write_text("---\nname: Cmd\n---\nbody", encoding="utf-8")

    proj_a = tmp_path / "projA"
    proj_b = tmp_path / "projB"
    proj_c = tmp_path / "projC"

    # Model has entries for A and C
    for model in (mock_app._library_model, mock_app._quick_copy_model):
        model._all_skills = [
            _FakeSkill(str(path_a), str(proj_a)),
            _FakeSkill(str(path_c), str(proj_c)),
        ]

    # Command is updated in projectA only — no removal needed
    mock_find_holders.return_value = ["projectA"]
    mock_update_multi.return_value = [_ok_result(path_a)]

    # After rescan of A and B, A's skill is still there
    path_b = tmp_path / "projB" / ".agents" / "commands" / "Cmd.md"
    mock_discover.side_effect = [
        [_skill_dict("Cmd", path_a, proj_a)],  # projectA rescan
        [_skill_dict("Cmd", path_b, proj_b)],  # projectB rescan
    ]

    ops_controller.updateCustomCommandFull(
        str(path_a), "Cmd", "body", "Commands", ["projectA", "projectB"], ""
    )

    for model_name in ("_library_model", "_quick_copy_model"):
        model = getattr(mock_app, model_name)
        # projC's entry should NOT be removed — it was not in the affected set
        model.removeSkillsByPath.assert_not_called()


@patch("skill_manager.core.commands.find_command_holder_projects")
@patch("skill_manager.core.persistence.patch_cache_add")
@patch("skill_manager.core.discovery.DiscoveryService.discover_project")
@patch("skill_manager.core.commands.update_custom_command_file_multi")
def test_no_stale_paths_when_command_only_renames_in_place(
    mock_update_multi,
    mock_discover,
    mock_patch_cache,
    mock_find_holders,
    ops_controller,
    mock_app,
    tmp_path,
):
    """Rename in same project: old path removed, new path added, no extra stale paths."""
    _setup_models(mock_app)
    mock_app._projects = ["/projectA"]
    mock_app._project_aliases = {}

    old_path = tmp_path / "projA" / ".agents" / "commands" / "Old.md"
    new_path = tmp_path / "projA" / ".agents" / "commands" / "New.md"
    old_path.parent.mkdir(parents=True, exist_ok=True)
    old_path.write_text("---\nname: Old\n---\nbody", encoding="utf-8")

    proj_a = tmp_path / "projA"

    # Model has only the old path
    for model in (mock_app._library_model, mock_app._quick_copy_model):
        model._all_skills = [
            _FakeSkill(str(old_path), str(proj_a)),
        ]

    mock_find_holders.return_value = ["projectA"]
    mock_update_multi.return_value = [_ok_result(new_path)]

    # After rescan, only the new path is discovered
    mock_discover.return_value = [
        _skill_dict("New", new_path, proj_a),
    ]

    ops_controller.updateCustomCommandFull(
        str(old_path), "New", "body", "Commands", ["projectA"], ""
    )

    for model_name in ("_library_model", "_quick_copy_model"):
        model = getattr(mock_app, model_name)
        # Exactly 1 stale path: the old path
        model.removeSkillsByPath.assert_called_once()
        removed = model.removeSkillsByPath.call_args[0][0]
        assert len(removed) == 1
        assert str(old_path) in removed
        # addOrUpdateSkills was called with the new entry
        model.addOrUpdateSkills.assert_called_once()


# ---------------------------------------------------------------------------
# Selection refresh: find renamed file in _all_skills even when filtered out
# ---------------------------------------------------------------------------


def test_refresh_finds_renamed_file_in_all_skills(mock_app, ops_controller):
    """When a file is renamed (moved between projects), the selection refresh
    must find it in _all_skills, not just _filtered_skills."""
    new_path = "C:/Projects/New/projA/.agents/commands/Cmd.md"
    skill = _FakeSkill(local_path=new_path, project_path="C:/Projects/New/projA")

    # Set up selected skill with the OLD path
    mock_app._selected_skill = {
        "local_path": "C:/Projects/Old/projB/.agents/commands/Cmd.md",
        "name": "Cmd",
    }

    # Model has the new path in _all_skills but NOT in _filtered_skills
    mock_app.skillModel._all_skills = [skill]
    mock_app.skillModel._filtered_skills = []  # filtered out
    # Mock get_skill_at to return the skill
    mock_app.skillModel.get_skill_at = MagicMock(return_value=skill)

    ops_controller._refresh_selected_skill(
        local_path="C:/Projects/Old/projB/.agents/commands/Cmd.md",
        rename_path=new_path,
    )

    # Selection should be updated to the new skill (even though filtered)
    mock_app.set_selected_skill.assert_called_once()
    call_arg = mock_app.set_selected_skill.call_args[0][0]
    assert call_arg["local_path"] == new_path


def test_refresh_returns_when_not_in_view(mock_app, ops_controller):
    """When the renamed path is genuinely missing from _all_skills,
    selection is unchanged and a WARNING is logged."""
    old_path = "C:/Projects/Old/projB/.agents/commands/Cmd.md"
    mock_app._selected_skill = {"local_path": old_path, "name": "Cmd"}
    mock_app.skillModel._all_skills = []
    mock_app.skillModel._filtered_skills = []

    ops_controller._refresh_selected_skill(
        local_path=old_path,
        rename_path="C:/Projects/New/projA/.agents/commands/Cmd.md",
    )

    # Selection should NOT change — the new path doesn't exist
    mock_app.set_selected_skill.assert_not_called()

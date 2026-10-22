"""Library copy flow: deploying commands that already exist in a project.

The Library is the source of truth for a command. Copying a command into a
project where the same file already exists is ambiguous, so the copy flow
detects the conflict, asks the user, and only then decides whether to
overwrite the project's file or keep it.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from skill_manager.core.copier import (
    copy_command_files_to_projects,
    find_existing_commands_in_projects,
)


def _make_project(tmp_path: Path, name: str = "proj") -> Path:
    proj = tmp_path / name
    (proj / ".agents" / "commands").mkdir(parents=True)
    return proj


def _make_command(tmp_path: Path, name: str = "cmd") -> Path:
    src = tmp_path / "source"
    src.mkdir(parents=True, exist_ok=True)
    cmd = src / f"{name}.md"
    cmd.write_text(f"---\nname: {name}\n---\nbody of {name}\n", encoding="utf-8")
    return cmd


# ── core: overwrite flag ──────────────────────────────────────────────────


def test_copy_command_files_skips_existing_by_default(tmp_path):
    """Without ``overwrite`` an existing project command is left alone."""
    proj = _make_project(tmp_path)
    cmd = _make_command(tmp_path)
    existing = proj / ".agents" / "commands" / "cmd.md"
    existing.write_text("---\nname: cmd\n---\nproject version\n", encoding="utf-8")

    result = copy_command_files_to_projects([{"local_path": str(cmd)}], [str(proj)])

    assert result["copied"] == 0
    assert result["updated"] == 0
    assert result["skipped"] == 1
    assert "project version" in existing.read_text(encoding="utf-8")


def test_copy_command_files_overwrites_when_requested(tmp_path):
    """With ``overwrite`` the project file is replaced by the Library version."""
    proj = _make_project(tmp_path)
    cmd = _make_command(tmp_path)
    existing = proj / ".agents" / "commands" / "cmd.md"
    existing.write_text("---\nname: cmd\n---\nproject version\n", encoding="utf-8")

    result = copy_command_files_to_projects([{"local_path": str(cmd)}], [str(proj)], overwrite=True)

    assert result["copied"] == 0
    assert result["updated"] == 1
    assert result["skipped"] == 0
    assert "body of cmd" in existing.read_text(encoding="utf-8")
    assert result["details"][0]["status"] == "updated"


def test_copy_command_files_copies_new_and_updates_existing(tmp_path):
    """A mixed batch copies what is new and updates what already exists."""
    proj = _make_project(tmp_path)
    new_cmd = _make_command(tmp_path, "fresh")
    old_cmd = _make_command(tmp_path, "stale")
    existing = proj / ".agents" / "commands" / "stale.md"
    existing.write_text("---\nname: stale\n---\nproject version\n", encoding="utf-8")

    result = copy_command_files_to_projects(
        [
            {"local_path": str(new_cmd)},
            {"local_path": str(old_cmd)},
        ],
        [str(proj)],
        overwrite=True,
    )

    assert result["copied"] == 1
    assert result["updated"] == 1
    assert (proj / ".agents" / "commands" / "fresh.md").exists()


def test_copy_command_into_its_own_project_is_skipped_not_failed(tmp_path):
    """Copying a command into the project it already lives in is a no-op.

    ``shutil.copy2`` raises SameFileError for identical source and
    destination, which would report the copy as a failure.
    """
    proj = _make_project(tmp_path)
    cmd = proj / ".agents" / "commands" / "cmd.md"
    cmd.write_text("---\nname: cmd\n---\nbody\n", encoding="utf-8")

    result = copy_command_files_to_projects([{"local_path": str(cmd)}], [str(proj)], overwrite=True)

    assert result["failed"] == 0
    assert result["copied"] == 0
    assert result["updated"] == 0
    assert result["skipped"] == 1
    assert "already the project's copy" in result["details"][0]["message"]


def test_find_existing_commands_in_projects_reports_pairs(tmp_path):
    """The detector reports which command already exists in which project."""
    proj_a = _make_project(tmp_path, "projA")
    proj_b = _make_project(tmp_path, "projB")
    cmd = _make_command(tmp_path)
    (proj_a / ".agents" / "commands" / "cmd.md").write_text("x", encoding="utf-8")

    existing = find_existing_commands_in_projects(
        [{"local_path": str(cmd), "name": "cmd"}], [str(proj_a), str(proj_b)]
    )

    assert len(existing) == 1
    entry = existing[0]
    assert entry["name"] == "cmd"
    assert entry["project"] == str(proj_a)
    assert entry["dest_path"].endswith("cmd.md")


# ── controller: the copy flow pauses and asks ─────────────────────────────


@pytest.fixture
def ops_controller(mock_app):
    from skill_manager.controllers.ops_controller import OpsController

    # The shared ``mock_app`` is not a QObject, so the deferred UI updates
    # are executed inline instead of being posted to the event loop.
    with patch("skill_manager.controllers.ops._helpers.QTimer.singleShot") as mock_timer:
        mock_timer.side_effect = lambda *args: args[-1]() if callable(args[-1]) else None
        yield OpsController(mock_app)


def _command_model_entry(path: str):
    return {
        "local_path": path,
        "name": Path(path).stem,
        "is_command": True,
        "project_path": "",
    }


def test_copy_selected_pauses_when_command_already_exists(ops_controller, mock_app, tmp_path):
    """A conflicting command stops the copy and asks the user."""
    proj = _make_project(tmp_path)
    cmd = _make_command(tmp_path)
    (proj / ".agents" / "commands" / "cmd.md").write_text("x", encoding="utf-8")

    mock_app.skillModel.getSelectedPaths.return_value = [str(cmd)]
    mock_app.skillModel._all_skills = [_command_model_entry(str(cmd))]

    ops_controller.copySelectedSkillsToProject(str(proj))

    # The controller emits the detection signal instead of copying.
    mock_app.commandCopyExistingDetected.emit.assert_called_once()
    project, command_paths_json, existing_json = (
        mock_app.commandCopyExistingDetected.emit.call_args[0]
    )
    assert project == str(proj)
    assert json.loads(command_paths_json) == [str(cmd)]
    existing = json.loads(existing_json)
    assert len(existing) == 1
    assert existing[0]["dest_path"].endswith("cmd.md")
    # Nothing was written yet.
    assert (proj / ".agents" / "commands" / "cmd.md").read_text(encoding="utf-8") == "x"


def test_confirm_copy_with_overwrite_replaces_existing_file(ops_controller, mock_app, tmp_path):
    """'Update Existing & Copy New' replaces the project's command file."""
    proj = _make_project(tmp_path)
    cmd = _make_command(tmp_path)
    existing = proj / ".agents" / "commands" / "cmd.md"
    existing.write_text("---\nname: cmd\n---\nproject version\n", encoding="utf-8")

    mock_app.skillModel.getSelectedPaths.return_value = [str(cmd)]
    mock_app.skillModel._all_skills = [_command_model_entry(str(cmd))]

    ops_controller.copySelectedSkillsToProject(str(proj))
    ops_controller.confirmCommandCopyWithOverwrite(str(proj), json.dumps([str(cmd)]), True)

    assert "body of cmd" in existing.read_text(encoding="utf-8")


def test_confirm_copy_without_overwrite_keeps_existing_file(ops_controller, mock_app, tmp_path):
    """'Copy Only New' leaves the project's command file untouched."""
    proj = _make_project(tmp_path)
    cmd = _make_command(tmp_path)
    existing = proj / ".agents" / "commands" / "cmd.md"
    existing.write_text("---\nname: cmd\n---\nproject version\n", encoding="utf-8")

    mock_app.skillModel.getSelectedPaths.return_value = [str(cmd)]
    mock_app.skillModel._all_skills = [_command_model_entry(str(cmd))]

    ops_controller.copySelectedSkillsToProject(str(proj))
    ops_controller.confirmCommandCopyWithOverwrite(str(proj), json.dumps([str(cmd)]), False)

    assert "project version" in existing.read_text(encoding="utf-8")


def test_confirm_copy_without_overwrite_still_copies_new_commands(
    ops_controller, mock_app, tmp_path
):
    """'Copy Only New' still deploys the commands the project does not have."""
    proj = _make_project(tmp_path)
    existing_cmd = _make_command(tmp_path, "stale")
    new_cmd = _make_command(tmp_path, "fresh")
    (proj / ".agents" / "commands" / "stale.md").write_text("x", encoding="utf-8")

    mock_app.skillModel.getSelectedPaths.return_value = [str(existing_cmd), str(new_cmd)]
    mock_app.skillModel._all_skills = [
        _command_model_entry(str(existing_cmd)),
        _command_model_entry(str(new_cmd)),
    ]

    ops_controller.copySelectedSkillsToProject(str(proj))
    ops_controller.confirmCommandCopyWithOverwrite(
        str(proj), json.dumps([str(existing_cmd), str(new_cmd)]), False
    )

    assert (proj / ".agents" / "commands" / "fresh.md").exists()
    assert (proj / ".agents" / "commands" / "stale.md").read_text(encoding="utf-8") == "x"


def test_cancel_copy_writes_nothing(ops_controller, mock_app, tmp_path):
    """'Cancel' aborts the copy without touching the project."""
    proj = _make_project(tmp_path)
    cmd = _make_command(tmp_path)
    existing = proj / ".agents" / "commands" / "cmd.md"
    existing.write_text("x", encoding="utf-8")

    mock_app.skillModel.getSelectedPaths.return_value = [str(cmd)]
    mock_app.skillModel._all_skills = [_command_model_entry(str(cmd))]

    ops_controller.copySelectedSkillsToProject(str(proj))
    ops_controller.cancelCommandCopyWithOverwrite()

    assert existing.read_text(encoding="utf-8") == "x"
    assert ops_controller._pending_command_copy is None


def test_copy_without_conflict_copies_directly(ops_controller, mock_app, tmp_path):
    """When nothing conflicts the copy runs without any prompt."""
    proj = _make_project(tmp_path)
    cmd = _make_command(tmp_path)

    mock_app.skillModel.getSelectedPaths.return_value = [str(cmd)]
    mock_app.skillModel._all_skills = [_command_model_entry(str(cmd))]

    ops_controller.copySelectedSkillsToProject(str(proj))

    mock_app.commandCopyExistingDetected.emit.assert_not_called()
    assert (proj / ".agents" / "commands" / "cmd.md").exists()


def test_deployed_command_prompts_to_carry_missing_skills(
    ops_controller, mock_app, tmp_path, qtbot
):
    """A deployed command whose skill is missing prompts the skill carry."""
    proj = _make_project(tmp_path)
    cmd = _make_command(tmp_path)

    missing = [{"local_path": "/src/helper/SKILL.md", "folder_name": "helper", "name": "helper"}]
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            "skill_manager.core.copier.find_missing_skills_for_commands",
            lambda *a, **k: missing,
        )
        emissions = []
        ops_controller.commandSkillsCarryPrompt.connect(lambda c, p, m: emissions.append((c, p, m)))
        ops_controller._prompt_missing_skills_for_commands([{"local_path": str(cmd)}], str(proj))
        qtbot.waitUntil(lambda: len(emissions) == 1, timeout=5000)

    assert len(emissions) == 1
    cmd_json, proj_str, miss_json = emissions[0]
    assert json.loads(cmd_json) == [str(cmd)]
    assert proj_str == str(proj)
    assert json.loads(miss_json) == missing


def test_partition_selection_splits_skills_and_commands(ops_controller, mock_app):
    """The selection is split into skills and commands by their path."""
    model = MagicMock()
    model._all_skills = [
        {"local_path": "/src/skill/SKILL.md", "name": "skill", "is_command": False},
        {"local_path": "/proj/.agents/commands/cmd.md", "name": "cmd", "is_command": True},
        {"local_path": "/proj/.agents/commands/plain.md", "name": "plain", "is_command": False},
    ]
    selected = {
        "/src/skill/SKILL.md",
        "/proj/.agents/commands/cmd.md",
        "/proj/.agents/commands/plain.md",
    }

    skills, commands = ops_controller._partition_selection(model, selected)

    assert [s["name"] for s in skills] == ["skill"]
    assert sorted(c["name"] for c in commands) == ["cmd", "plain"]

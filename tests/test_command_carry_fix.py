import json
from pathlib import Path
from unittest.mock import MagicMock

from skill_manager.core.copier import (
    find_missing_skills_for_commands,
    get_installed_skill_folder_names,
)
from skill_manager.core.models.entities import Skill


def test_find_missing_skills_with_skill_dataclasses(tmp_path: Path):
    """Verify find_missing_skills_for_commands converts Skill dataclasses to dicts."""
    project_dir = tmp_path / "my_project"
    project_dir.mkdir()
    skills_dir = project_dir / ".agents" / "skills"
    skills_dir.mkdir(parents=True)

    skill_path = tmp_path / "global_skills" / "my-test-skill"
    skill_path.mkdir(parents=True)
    (skill_path / "SKILL.md").write_text("# Test Skill\n")

    skill_obj = Skill(
        name="my-test-skill",
        folder_name="my-test-skill",
        local_path=str(skill_path),
    )

    cmd = {"body": "Run /my-test-skill now"}
    all_skills = [skill_obj]

    missing = find_missing_skills_for_commands([cmd], project_dir, all_skills)

    assert len(missing) == 1
    assert isinstance(missing[0], dict)
    assert missing[0]["name"] == "my-test-skill"
    assert missing[0]["folder_name"] == "my-test-skill"

    # Must be JSON serializable
    dumped = json.dumps(missing)
    assert "my-test-skill" in dumped


def test_installed_skill_folder_names_case_insensitive(tmp_path: Path):
    """Verify get_installed_skill_folder_names returns lowercased folder names."""
    project_dir = tmp_path / "project_case"
    skills_dir = project_dir / ".agents" / "skills"
    skills_dir.mkdir(parents=True)

    (skills_dir / "My-Mixed-Case-Skill").mkdir()

    installed = get_installed_skill_folder_names(project_dir)
    assert "my-mixed-case-skill" in installed


def test_ops_controller_create_command_carry_prompt_emitted(tmp_path: Path, qtbot):
    """Test ops_controller emits commandSkillsCarryPrompt on command creation when skills missing."""
    from skill_manager.controllers.ops_controller import OpsController

    app_mock = MagicMock()
    proj_a = tmp_path / "projA"
    proj_a.mkdir(parents=True)
    app_mock._projects = [str(proj_a)]

    source_dir = tmp_path / "sources" / "global"
    source_dir.mkdir(parents=True)
    app_mock._sources = [str(source_dir)]
    app_mock._archive_paths = []
    app_mock._starred_paths = []
    app_mock._project_aliases = {}

    skill_folder = source_dir / "helper-skill"
    skill_folder.mkdir()
    (skill_folder / "SKILL.md").write_text("# Helper Skill\n")

    skill_obj = Skill(
        name="helper-skill",
        folder_name="helper-skill",
        local_path=str(skill_folder),
    )
    app_mock._library_model._all_skills = [skill_obj]
    app_mock._selected_skill = skill_obj
    app_mock._quick_copy_model = MagicMock()

    ops = OpsController(app_mock)

    received_signals = []
    ops.commandSkillsCarryPrompt.connect(
        lambda cmd_json, proj_path, missing_json: received_signals.append(
            (cmd_json, proj_path, missing_json)
        )
    )

    cmd_path = ops.createCustomCommand(
        name="test-cmd",
        body="Use /helper-skill to do stuff",
        category="General",
    )

    qtbot.wait(100)

    assert cmd_path != ""
    assert len(received_signals) >= 1
    cmd_json, proj_path, missing_json = received_signals[0]
    missing = json.loads(missing_json)
    assert len(missing) == 1
    assert missing[0]["name"] == "helper-skill"


def test_ops_controller_update_command_carry_prompt_emitted(tmp_path: Path, qtbot):
    """Test ops_controller emits commandSkillsCarryPrompt on command update when skills missing."""
    from skill_manager.controllers.ops_controller import OpsController

    app_mock = MagicMock()
    proj_a = tmp_path / "projA"
    proj_a.mkdir(parents=True)
    app_mock._projects = [str(proj_a)]

    source_dir = tmp_path / "sources" / "global"
    source_dir.mkdir(parents=True)
    app_mock._sources = [str(source_dir)]
    app_mock._archive_paths = []
    app_mock._starred_paths = []
    app_mock._project_aliases = {}

    skill_folder = source_dir / "my-helper"
    skill_folder.mkdir()
    (skill_folder / "SKILL.md").write_text("# My Helper Skill\n")

    skill_obj = Skill(
        name="my-helper",
        folder_name="my-helper",
        local_path=str(skill_folder),
    )
    app_mock._library_model._all_skills = [skill_obj]
    app_mock._selected_skill = skill_obj
    app_mock._quick_copy_model = MagicMock()

    ops = OpsController(app_mock)

    # First create command without missing skills
    cmd_path = ops.createCustomCommand(
        name="my-cmd",
        body="Basic command text",
        category="General",
    )

    qtbot.wait(50)

    received_signals = []
    ops.commandSkillsCarryPrompt.connect(
        lambda cmd_json, proj_path, missing_json: received_signals.append(
            (cmd_json, proj_path, missing_json)
        )
    )

    # Now update command to reference /my-helper
    ops.updateCustomCommandFull(
        local_path=cmd_path,
        name="my-cmd",
        body="Updated text referencing /my-helper",
        category="General",
    )

    qtbot.wait(100)

    assert len(received_signals) >= 1
    cmd_json, proj_path, missing_json = received_signals[0]
    missing = json.loads(missing_json)
    assert len(missing) == 1
    assert missing[0]["name"] == "my-helper"


def test_ops_controller_copy_command_to_project_carries_skills(tmp_path: Path, qtbot):
    """Deploying a command to a project that lacks its skill offers the carry.

    The dialog no longer fans a command out to several projects, so the
    "command added to a project" path is the Library copy flow. Copying a
    command into a project that does not have the referenced skill must
    emit the skill-carry prompt for that project.
    """
    from skill_manager.controllers.ops_controller import OpsController

    app_mock = MagicMock()
    proj_a = tmp_path / "projA"
    proj_b = tmp_path / "projB"
    proj_a.mkdir(parents=True)
    proj_b.mkdir(parents=True)
    app_mock._projects = [str(proj_a), str(proj_b)]

    source_dir = tmp_path / "sources" / "global"
    source_dir.mkdir(parents=True)
    app_mock._sources = [str(source_dir)]
    app_mock._archive_paths = []
    app_mock._starred_paths = []
    app_mock._project_aliases = {}

    # The referenced skill exists in the library but in neither project.
    skill_folder_global = source_dir / "multi-helper"
    skill_folder_global.mkdir()
    (skill_folder_global / "SKILL.md").write_text("# Multi Helper Skill\n")

    skill_obj = Skill(
        name="multi-helper",
        folder_name="multi-helper",
        local_path=str(skill_folder_global),
    )
    app_mock._library_model._all_skills = [skill_obj]
    app_mock._selected_skill = skill_obj
    app_mock._quick_copyModel = MagicMock()
    app_mock._quick_copy_model = MagicMock()

    ops = OpsController(app_mock)

    # The canonical command lives in projA and references /multi-helper.
    cmd_file_a = proj_a / ".agents" / "commands" / "shared-cmd.md"
    cmd_file_a.parent.mkdir(parents=True)
    cmd_file_a.write_text(
        "---\nname: shared-cmd\n---\nUpdated body referencing /multi-helper\n",
        encoding="utf-8",
    )

    received_signals = []
    ops.commandSkillsCarryPrompt.connect(
        lambda cmd_json, proj_path, missing_json: received_signals.append(
            (cmd_json, proj_path, missing_json)
        )
    )

    ops._prompt_missing_skills_for_commands(
        [{"local_path": str(cmd_file_a), "name": "shared-cmd"}], str(proj_b)
    )

    qtbot.wait(100)

    assert len(received_signals) >= 1
    cmd_json, proj_path, missing_json = received_signals[0]
    assert json.loads(cmd_json) == [str(cmd_file_a)]
    assert proj_path == str(proj_b)
    missing = json.loads(missing_json)
    assert len(missing) == 1
    assert missing[0]["name"] == "multi-helper"

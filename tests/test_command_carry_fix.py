import json
from pathlib import Path
from unittest.mock import MagicMock

from skill_manager.core.copier import (
    find_missing_skills_for_commands,
    get_installed_skill_folder_names,
)
from skill_manager.core.models.entities import Skill
from skill_manager.core.quick_copy import project_label


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

    label_a = project_label(proj_a)
    cmd_path = ops.createCustomCommand(
        name="test-cmd",
        body="Use /helper-skill to do stuff",
        project_labels=[label_a],
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

    label_a = project_label(proj_a)
    # First create command without missing skills
    cmd_path = ops.createCustomCommand(
        name="my-cmd",
        body="Basic command text",
        project_labels=[label_a],
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
        project_labels=[label_a],
    )

    qtbot.wait(100)

    assert len(received_signals) >= 1
    cmd_json, proj_path, missing_json = received_signals[0]
    missing = json.loads(missing_json)
    assert len(missing) == 1
    assert missing[0]["name"] == "my-helper"


def test_ops_controller_update_command_multi_project_carry_prompt(tmp_path: Path, qtbot):
    """Test editing a command to add a new project prompts carry if the new project lacks skills.

    The command is initially held only in projA. Updating with project_labels=[A, B]
    adds projB as an ``add_set`` project, which triggers the fan-out write and carry check
    for projB. projB lacks the skill that projA has, so the carry prompt is emitted for projB.
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

    # Pre-install skill in projA, but NOT in projB
    skill_folder_global = source_dir / "multi-helper"
    skill_folder_global.mkdir()
    (skill_folder_global / "SKILL.md").write_text("# Multi Helper Skill\n")

    skill_folder_a = proj_a / ".agents" / "skills" / "multi-helper"
    skill_folder_a.mkdir(parents=True)
    (skill_folder_a / "SKILL.md").write_text("# Multi Helper Skill in ProjA\n")

    skill_obj = Skill(
        name="multi-helper",
        folder_name="multi-helper",
        local_path=str(skill_folder_global),
    )
    app_mock._library_model._all_skills = [skill_obj]
    app_mock._selected_skill = skill_obj
    app_mock._quick_copy_model = MagicMock()

    ops = OpsController(app_mock)

    label_a = project_label(proj_a)
    label_b = project_label(proj_b)

    # Create command in projA only (not in projB)
    cmd_path_a = ops.createCustomCommand(
        name="shared-cmd",
        body="Initial shared body",
        project_labels=[label_a],
        category="General",
    )

    qtbot.wait(50)

    received_signals = []
    ops.commandSkillsCarryPrompt.connect(
        lambda cmd_json, proj_path, missing_json: received_signals.append(
            (cmd_json, proj_path, missing_json)
        )
    )

    # Now edit command, adding reference to /multi-helper, targeting BOTH projects.
    # projB is in add_set (doesn't hold the command yet) → fan-out writes to projB → carry check runs.
    ops.updateCustomCommandFull(
        local_path=cmd_path_a,
        name="shared-cmd",
        body="Updated body referencing /multi-helper",
        category="General",
        project_labels=[label_a, label_b],
    )

    qtbot.wait(100)

    # Verify projB's command file was created by the add_set fan-out
    cmd_file_b = proj_b / ".agents" / "commands" / "shared-cmd.md"
    assert cmd_file_b.exists()
    assert "/multi-helper" in cmd_file_b.read_text()

    # Verify carry prompt was emitted for projB (which lacks the skill)
    assert len(received_signals) >= 1
    proj_b_signals = [s for s in received_signals if s[1] == str(proj_b)]
    assert len(proj_b_signals) == 1
    missing_b = json.loads(proj_b_signals[0][2])
    assert len(missing_b) == 1
    assert missing_b[0]["name"] == "multi-helper"

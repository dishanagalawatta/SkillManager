"""Tests for get_commands_dir and copy_command_files_to_projects."""

from __future__ import annotations

from skill_manager.core.copier import copy_command_files_to_projects, get_commands_dir

# --- get_commands_dir ---


def test_get_commands_dir_resolves_root(tmp_path):
    """A project root path should resolve to <root>/.agents/commands."""
    project = tmp_path / "MyProject"
    project.mkdir()
    result = get_commands_dir(project)
    assert result == project / ".agents" / "commands"


def test_get_commands_dir_handles_agents_path(tmp_path):
    """When given <root>/.agents, returns <root>/.agents/commands."""
    agents = tmp_path / "MyProject" / ".agents"
    agents.mkdir(parents=True)
    result = get_commands_dir(agents)
    assert result == agents / "commands"


def test_get_commands_dir_handles_skills_path(tmp_path):
    """When given <root>/.agents/skills, resolves to the project root's commands dir."""
    skills = tmp_path / "MyProject" / ".agents" / "skills"
    skills.mkdir(parents=True)
    result = get_commands_dir(skills)
    assert result == tmp_path / "MyProject" / ".agents" / "commands"


def test_get_commands_dir_handles_string_input(tmp_path):
    """String paths are accepted and resolved."""
    project = tmp_path / "MyProject"
    project.mkdir()
    result = get_commands_dir(str(project))
    assert result == project / ".agents" / "commands"


# --- copy_command_files_to_projects ---


def test_copy_command_files_copies_missing(tmp_path):
    """Command .md file is copied when destination does not exist."""
    src_dir = tmp_path / "source" / ".agents" / "commands"
    src_dir.mkdir(parents=True)
    (src_dir / "Deploy.md").write_text("---\nname: Deploy\n---\nDeploy body", encoding="utf-8")

    target_root = tmp_path / "target"
    target_root.mkdir()

    result = copy_command_files_to_projects(
        [{"local_path": str(src_dir / "Deploy.md"), "name": "Deploy.md"}],
        [str(target_root)],
    )

    dest = target_root / ".agents" / "commands" / "Deploy.md"
    assert dest.exists()
    assert dest.read_text(encoding="utf-8") == "---\nname: Deploy\n---\nDeploy body"
    assert result["copied"] == 1
    assert result["skipped"] == 0
    assert result["failed"] == 0


def test_copy_command_files_skips_existing(tmp_path):
    """Existing command file is not overwritten (Q1: skip-if-exists)."""
    src_dir = tmp_path / "source" / ".agents" / "commands"
    src_dir.mkdir(parents=True)
    (src_dir / "Deploy.md").write_text("---\nname: Deploy\n---\nNew content", encoding="utf-8")

    target_root = tmp_path / "target"
    target_commands = target_root / ".agents" / "commands"
    target_commands.mkdir(parents=True)
    (target_commands / "Deploy.md").write_text(
        "---\nname: Deploy\n---\nOriginal content", encoding="utf-8"
    )

    result = copy_command_files_to_projects(
        [{"local_path": str(src_dir / "Deploy.md"), "name": "Deploy.md"}],
        [str(target_root)],
    )

    dest = target_commands / "Deploy.md"
    assert dest.read_text(encoding="utf-8") == "---\nname: Deploy\n---\nOriginal content"
    assert result["copied"] == 0
    assert result["skipped"] == 1
    assert result["failed"] == 0


def test_copy_command_files_reports_missing_source(tmp_path):
    """Source file does not exist: counted as failed, no exception."""
    target_root = tmp_path / "target"
    target_root.mkdir()

    result = copy_command_files_to_projects(
        [{"local_path": str(tmp_path / "nonexistent" / "Ghost.md"), "name": "Ghost.md"}],
        [str(target_root)],
    )

    assert result["failed"] == 1
    assert result["copied"] == 0
    assert "does not exist" in result["details"][0]["message"]


def test_copy_command_files_multiple_projects(tmp_path):
    """Command is copied to multiple target projects."""
    src_dir = tmp_path / "source" / ".agents" / "commands"
    src_dir.mkdir(parents=True)
    (src_dir / "Lint.md").write_text("lint body", encoding="utf-8")

    target_a = tmp_path / "projA"
    target_b = tmp_path / "projB"
    target_a.mkdir()
    target_b.mkdir()

    result = copy_command_files_to_projects(
        [{"local_path": str(src_dir / "Lint.md"), "name": "Lint.md"}],
        [str(target_a), str(target_b)],
    )

    assert (target_a / ".agents" / "commands" / "Lint.md").exists()
    assert (target_b / ".agents" / "commands" / "Lint.md").exists()
    assert result["copied"] == 2
    assert result["skipped"] == 0


def test_copy_command_files_partial_skip(tmp_path):
    """Mixed: one project gets a copy, another already has it."""
    src_dir = tmp_path / "source" / ".agents" / "commands"
    src_dir.mkdir(parents=True)
    (src_dir / "Deploy.md").write_text("deploy body", encoding="utf-8")

    target_a = tmp_path / "projA"
    target_a.mkdir()

    target_b = tmp_path / "projB"
    target_b_commands = target_b / ".agents" / "commands"
    target_b_commands.mkdir(parents=True)
    (target_b_commands / "Deploy.md").write_text("existing", encoding="utf-8")

    result = copy_command_files_to_projects(
        [{"local_path": str(src_dir / "Deploy.md"), "name": "Deploy.md"}],
        [str(target_a), str(target_b)],
    )

    assert result["copied"] == 1
    assert result["skipped"] == 1
    assert (target_a / ".agents" / "commands" / "Deploy.md").exists()


def test_copy_command_files_empty_commands(tmp_path):
    """Empty commands list produces empty result."""
    target_root = tmp_path / "target"
    target_root.mkdir()

    result = copy_command_files_to_projects([], [str(target_root)])

    assert result == {"copied": 0, "skipped": 0, "failed": 0, "details": []}

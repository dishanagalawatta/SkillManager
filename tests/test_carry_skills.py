"""Tests for copier carry helpers — skill detection + command copy with carry."""

import textwrap
from pathlib import Path


def _make_skill(name, folder_name=None, local_path=None, **extra):
    """Factory for minimal skill dicts."""
    return {
        "name": name,
        "folder_name": folder_name or name.lower(),
        "local_path": local_path or f"/skills/{(folder_name or name).lower()}",
        "is_command": extra.pop("is_command", False),
        "is_screenshot": extra.pop("is_screenshot", False),
        **extra,
    }


def _write_command(directory: Path, name: str, body: str) -> Path:
    """Write a minimal command .md file with frontmatter."""
    directory.mkdir(parents=True, exist_ok=True)
    f = directory / f"{name}.md"
    f.write_text(
        textwrap.dedent(f"""\
            ---
            name: {name}
            category: Test
            type: command
            ---
            {body}
        """),
        encoding="utf-8",
    )
    return f


# ---------------------------------------------------------------------------
# get_installed_skill_folder_names
# ---------------------------------------------------------------------------


class TestGetInstalledSkillFolderNames:
    def test_empty_dir(self, tmp_path):
        from skill_manager.core.copier import get_installed_skill_folder_names

        # Point to a dir that has a "skills" child with nothing in it
        agents = tmp_path / ".agents" / "skills"
        agents.mkdir(parents=True)
        assert get_installed_skill_folder_names(str(tmp_path)) == set()

    def test_populated_dir(self, tmp_path):
        from skill_manager.core.copier import get_installed_skill_folder_names

        skills_dir = tmp_path / ".agents" / "skills"
        (skills_dir / "git-pr").mkdir(parents=True)
        (skills_dir / "cavecrew").mkdir(parents=True)
        (skills_dir / "SKILL.md").write_text("not a dir", encoding="utf-8")  # file, not dir
        result = get_installed_skill_folder_names(str(tmp_path))
        assert result == {"git-pr", "cavecrew"}

    def test_missing_skills_dir(self, tmp_path):
        from skill_manager.core.copier import get_installed_skill_folder_names

        # No .agents/skills dir at all → returns empty set
        assert get_installed_skill_folder_names(str(tmp_path)) == set()


# ---------------------------------------------------------------------------
# find_missing_skills_for_commands
# ---------------------------------------------------------------------------


class TestFindMissingSkillsForCommands:
    def test_no_missing(self, tmp_path):
        from skill_manager.core.copier import find_missing_skills_for_commands

        skills_dir = tmp_path / ".agents" / "skills" / "git-pr"
        skills_dir.mkdir(parents=True)
        cmd = _write_command(tmp_path, "deploy", "Use /git-pr for PRs.")
        skill = _make_skill("git-pr", folder_name="git-pr")
        result = find_missing_skills_for_commands(
            [{"local_path": str(cmd)}], str(tmp_path), [skill]
        )
        assert result == []

    def test_all_missing(self, tmp_path):
        from skill_manager.core.copier import find_missing_skills_for_commands

        cmd = _write_command(tmp_path, "deploy", "Use /git-pr and /cavecrew.")
        s1 = _make_skill("git-pr", folder_name="git-pr")
        s2 = _make_skill("cavecrew", folder_name="cavecrew")
        result = find_missing_skills_for_commands(
            [{"local_path": str(cmd)}], str(tmp_path), [s1, s2]
        )
        assert len(result) == 2
        folders = {s["folder_name"] for s in result}
        assert folders == {"git-pr", "cavecrew"}

    def test_partial_missing(self, tmp_path):
        from skill_manager.core.copier import find_missing_skills_for_commands

        # git-pr is installed, cavecrew is not
        skills_dir = tmp_path / ".agents" / "skills" / "git-pr"
        skills_dir.mkdir(parents=True)
        cmd = _write_command(tmp_path, "deploy", "Use /git-pr and /cavecrew.")
        s1 = _make_skill("git-pr", folder_name="git-pr")
        s2 = _make_skill("cavecrew", folder_name="cavecrew")
        result = find_missing_skills_for_commands(
            [{"local_path": str(cmd)}], str(tmp_path), [s1, s2]
        )
        assert len(result) == 1
        assert result[0]["folder_name"] == "cavecrew"

    def test_new_command_body(self, tmp_path):
        """Command not yet on disk — body is in the dict."""
        from skill_manager.core.copier import find_missing_skills_for_commands

        cmd_dict = {"body": "Use /git-pr for PRs.", "name": "deploy"}
        s1 = _make_skill("git-pr", folder_name="git-pr")
        result = find_missing_skills_for_commands([cmd_dict], str(tmp_path), [s1])
        assert len(result) == 1
        assert result[0]["folder_name"] == "git-pr"

    def test_dedup_across_commands(self, tmp_path):
        """Same skill referenced by two commands → appears once."""
        from skill_manager.core.copier import find_missing_skills_for_commands

        cmd1 = _write_command(tmp_path, "c1", "Use /git-pr.")
        cmd2 = _write_command(tmp_path, "c2", "Also /git-pr here.")
        s1 = _make_skill("git-pr", folder_name="git-pr")
        result = find_missing_skills_for_commands(
            [{"local_path": str(cmd1)}, {"local_path": str(cmd2)}],
            str(tmp_path),
            [s1],
        )
        assert len(result) == 1

    def test_command_with_no_refs(self, tmp_path):
        from skill_manager.core.copier import find_missing_skills_for_commands

        cmd = _write_command(tmp_path, "plain", "Just some plain text.")
        s1 = _make_skill("git-pr", folder_name="git-pr")
        result = find_missing_skills_for_commands(
            [{"local_path": str(cmd)}], str(tmp_path), [s1]
        )
        assert result == []


# ---------------------------------------------------------------------------
# copy_commands_with_skill_carry
# ---------------------------------------------------------------------------


class TestCopyCommandsWithSkillCarry:
    def test_probe_returns_missing(self, tmp_path):
        from skill_manager.core.copier import copy_commands_with_skill_carry

        source = tmp_path / "source"
        (source / ".agents" / "skills").mkdir(parents=True)
        cmd = _write_command(source / ".agents" / "commands", "deploy", "Use /git-pr.")
        s1 = _make_skill("git-pr", folder_name="git-pr")
        target = tmp_path / "target"
        (target / ".agents" / "skills").mkdir(parents=True)

        result = copy_commands_with_skill_carry(
            [{"local_path": str(cmd)}], str(target), [s1],
            confirmed_skills=None,
        )
        assert len(result["missing_skills"]) == 1
        assert result["skills_copied"] == 0

    def test_confirm_copies_skills(self, tmp_path):
        from skill_manager.core.copier import copy_commands_with_skill_carry

        # Set up a real skill folder to copy
        source = tmp_path / "source" / ".agents" / "skills" / "git-pr"
        source.mkdir(parents=True)
        (source / "SKILL.md").write_text("# git-pr", encoding="utf-8")

        cmd = _write_command(tmp_path / "source" / ".agents" / "commands", "deploy", "Use /git-pr.")
        target = tmp_path / "target"
        (target / ".agents" / "skills").mkdir(parents=True)

        skill_to_carry = _make_skill(
            "git-pr", folder_name="git-pr", local_path=str(source)
        )
        result = copy_commands_with_skill_carry(
            [{"local_path": str(cmd)}], str(target), [skill_to_carry],
            confirmed_skills=[skill_to_carry],
        )
        assert result["skills_copied"] >= 1
        assert result["skills_failed"] == 0
        assert result["missing_skills"] == []
        assert (target / ".agents" / "skills" / "git-pr" / "SKILL.md").exists()

    def test_no_missing_returns_empty_list(self, tmp_path):
        from skill_manager.core.copier import copy_commands_with_skill_carry

        # git-pr already installed
        target_skills = tmp_path / ".agents" / "skills" / "git-pr"
        target_skills.mkdir(parents=True)
        (target_skills / "SKILL.md").write_text("# git-pr", encoding="utf-8")

        cmd = _write_command(tmp_path / ".agents" / "commands", "deploy", "Use /git-pr.")
        skill = _make_skill("git-pr", folder_name="git-pr", local_path=str(target_skills))
        result = copy_commands_with_skill_carry(
            [{"local_path": str(cmd)}], str(tmp_path), [skill],
            confirmed_skills=None,
        )
        assert result["missing_skills"] == []

    def test_empty_confirmed_skills(self, tmp_path):
        from skill_manager.core.copier import copy_commands_with_skill_carry

        cmd = _write_command(tmp_path / "source" / ".agents" / "commands", "deploy", "Use /git-pr.")
        s1 = _make_skill("git-pr", folder_name="git-pr")
        target = tmp_path / "target"
        (target / ".agents" / "skills").mkdir(parents=True)

        result = copy_commands_with_skill_carry(
            [{"local_path": str(cmd)}], str(target), [s1],
            confirmed_skills=[],
        )
        assert result["missing_skills"] == []
        assert result["skills_copied"] == 0

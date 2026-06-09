from unittest.mock import patch

import pytest

from skill_manager.core.discovery import DiscoveryService


@pytest.fixture
def service():
    return DiscoveryService(
        sources=["/src1", "/src2"],
        projects=["/project1"],
        archive_paths=["/src2/archived"],
        starred_paths=["/src1/starred"],
        project_aliases={"/project1": "My Project Alias"},
    )


def test_transform_skill_source(service):
    skill = {
        "name": "Test Skill",
        "local_path": "/src1/skill1",
        "category": "Test",
        "metadata": {"risk": "High"},
    }
    transformed = service.transform_skill(skill, is_package=True)
    assert transformed["name"] == "Test Skill"
    assert transformed["is_package"] is True
    assert transformed["risk"] == "High"
    assert transformed["project_label"] == "Master Library"


def test_transform_skill_project(service):
    skill = {
        "name": "Proj Skill",
        "local_path": "/project1/skillA",
        "category": "Dev",
        "skill_base_relative": "skillA",
        "folder_name": "skillA",
    }
    transformed = service.transform_skill(skill, is_package=False, project_label="My Project")
    assert transformed["name"] == "Proj Skill"
    assert transformed["is_package"] is False
    assert transformed["project_label"] == "My Project"
    assert transformed["skill_base_relative"] == "skillA"


def test_transform_skill_archived_and_starred(service):
    # Archived
    s1 = {"local_path": "/src2/archived"}
    t1 = service.transform_skill(s1, is_package=True)
    assert t1["is_archived"] is True

    # Starred
    s2 = {"local_path": "/src1/starred"}
    t2 = service.transform_skill(s2, is_package=True)
    assert t2["is_starred"] is True


def test_process_command_file(service, temp_dir):
    cmd_file = temp_dir / "Test.Codex.md"
    cmd_file.write_text("---\nname: My Command\ncategory: Ops\n---\nBody")

    project = {"project_label": "Proj", "project_root": str(temp_dir)}
    data = service._process_command_file(cmd_file, project)

    assert data["name"] == "My Command"
    assert data["category"] == "Ops"
    assert data["is_command"] is True
    assert data["project_label"] == "Proj"


@patch("skill_manager.core.discovery.load_cache")
@patch("skill_manager.core.discovery.save_cache")
def test_discover_all_integration(mock_save, mock_load, temp_dir):
    # Setup source directory
    source_lib = temp_dir / "source_lib"
    source_lib.mkdir()
    skill1_dir = source_lib / "skill1"
    skill1_dir.mkdir()
    (skill1_dir / "SKILL.md").write_text(
        "---\nname: Skill One\ncategory: Automation\nmetadata:\n  risk: Low\n---"
    )

    # Setup project directory
    proj = temp_dir / "proj"
    proj.mkdir()
    proj_skills = proj / ".agents" / "skills"
    proj_skills.mkdir(parents=True)
    skill_a_dir = proj_skills / "skillA"
    skill_a_dir.mkdir()
    (skill_a_dir / "SKILL.md").write_text(
        "---\nname: Project Skill A\ncategory: Developer Tools\n---"
    )

    # Setup commands directory at .agents/commands/
    commands_dir = proj / ".agents" / "commands"
    commands_dir.mkdir(parents=True)
    (commands_dir / "my_cmd.Codex.md").write_text(
        "---\nname: My Custom Command\ncategory: Ops\n---"
    )

    service = DiscoveryService(
        sources=[str(source_lib)],
        projects=[str(proj_skills)],
        archive_paths=[],
        starred_paths=[],
    )

    mock_load.return_value = None

    # Run full discovery bypassing cache
    result = service.discover_all(use_cache=False)

    assert "skills" in result
    assert "categories" in result
    assert "projects" in result

    # Check discovered skills
    skills = result["skills"]
    skill_names = {s["name"] for s in skills}
    assert "Skill One" in skill_names
    assert "Project Skill A" in skill_names
    assert "My Custom Command" in skill_names

    # Check categorizations
    categories = result["categories"]
    assert "Testing" in categories
    assert "Developer Tools" in categories
    assert "Ops" in categories or "Custom Commands" in categories

    mock_save.assert_called_once_with(result)


@patch("skill_manager.core.discovery.load_cache")
@patch("skill_manager.core.discovery.save_cache")
def test_discovery_symlinks_and_hidden_dirs(mock_save, mock_load, temp_dir):
    source_lib = temp_dir / "source_lib"
    source_lib.mkdir()

    # 1. Normal skill with SKILL.md
    skill1 = source_lib / "skill1"
    skill1.mkdir()
    (skill1 / "SKILL.md").write_text("---\nname: Skill 1\ncategory: Test\n---")

    # 2. Directory without SKILL.md (should be ignored)
    ignored_dir = source_lib / "ignored_folder"
    ignored_dir.mkdir()
    (ignored_dir / "other.txt").write_text("content")

    # 3. Hidden directory starting with "." containing SKILL.md
    hidden_dir = source_lib / ".hidden_skill"
    hidden_dir.mkdir()
    (hidden_dir / "SKILL.md").write_text("---\nname: Hidden Skill\ncategory: Secret\n---")

    # 4. Symlink directory pointing to a valid skill (if OS supports it, else we fallback/mock)
    target_dir = temp_dir / "target_skill"
    target_dir.mkdir()
    (target_dir / "SKILL.md").write_text("---\nname: Symlink Skill\ncategory: Test\n---")

    symlink_dir = source_lib / "symlink_skill"
    try:
        symlink_dir.symlink_to(target_dir, target_is_directory=True)
    except (OSError, NotImplementedError):
        # Fallback for environments/Windows without symlink creation rights
        # Just create as directory to verify scan continues correctly
        symlink_dir.mkdir()
        (symlink_dir / "SKILL.md").write_text("---\nname: Symlink Skill\ncategory: Test\n---")

    service = DiscoveryService(
        sources=[str(source_lib)],
        projects=[],
        archive_paths=[],
        starred_paths=[],
    )

    mock_load.return_value = None
    result = service.discover_all(use_cache=False)
    skills = result["skills"]
    skill_names = {s["name"] for s in skills}

    assert "Skill 1" in skill_names
    assert "ignored_folder" not in skill_names
    assert "Hidden Skill" in skill_names
    assert "Symlink Skill" in skill_names


@patch("skill_manager.core.discovery.load_cache")
@patch("skill_manager.core.discovery.save_cache")
def test_discovery_respects_gitignore_patterns(mock_save, mock_load, temp_dir):
    source_lib = temp_dir / "source_lib"
    source_lib.mkdir()
    (source_lib / ".gitignore").write_text("ignored_skill/\n", encoding="utf-8")

    kept = source_lib / "kept_skill"
    kept.mkdir()
    (kept / "SKILL.md").write_text("---\nname: Kept Skill\n---", encoding="utf-8")

    ignored = source_lib / "ignored_skill"
    ignored.mkdir()
    (ignored / "SKILL.md").write_text("---\nname: Ignored Skill\n---", encoding="utf-8")

    service = DiscoveryService(
        sources=[str(source_lib)],
        projects=[],
        archive_paths=[],
        starred_paths=[],
    )

    mock_load.return_value = None
    result = service.discover_all(use_cache=False)
    names = {skill["name"] for skill in result["skills"]}

    assert "Kept Skill" in names
    assert "Ignored Skill" not in names


@patch("skill_manager.core.discovery.load_cache")
@patch("skill_manager.core.discovery.save_cache")
def test_discovery_cache_behavior(mock_save, mock_load, temp_dir):
    service = DiscoveryService(
        sources=[],
        projects=[],
        archive_paths=[],
        starred_paths=[],
    )

    # 1. Test cache hit
    cached_data = {
        "skills": [],
        "projects": [],
        "categories": [],
        "project_labels": [],
        "status": "Cached",
    }
    mock_load.return_value = cached_data

    callback_messages = []
    result = service.discover_all(use_cache=True, cache_callback=callback_messages.append)

    assert result["status"] == "Found 0 skills in master library (0 projects)"
    assert callback_messages == [cached_data]
    mock_load.assert_called_once()

    # 2. Test cache load raising error (should fallback gracefully to scanning)
    mock_load.reset_mock()
    mock_load.side_effect = Exception("Cache file corrupted")

    result_fallback = service.discover_all(use_cache=True)
    assert "skills" in result_fallback
    assert result_fallback["status"] == "Found 0 skills in master library (0 projects)"


@patch("os.walk")
def test_discovery_permission_errors(mock_walk, service):
    # Simulate permission error on one of the sources
    mock_walk.side_effect = [
        [("/src1", ["skill1"], [])],  # Success for src1
        PermissionError("Access Denied"),  # Failure for src2
    ]

    # We need to mock Path.is_file/is_dir or just let it run on real-ish paths
    # For simplicity, we'll just check it doesn't crash
    result = service.discover_all(use_cache=False)
    assert "skills" in result


def test_process_command_file_varied_names(service, temp_dir):
    # Multiple dots
    f1 = temp_dir / "test.extra.Codex.md"
    f1.write_text("# Cmd")
    p = {"project_label": "P", "project_root": str(temp_dir)}
    res1 = service._process_command_file(f1, p)
    assert res1["client"] == "Codex"

    # No client format in name
    f2 = temp_dir / "simple_cmd.md"
    f2.write_text("# Cmd")
    res2 = service._process_command_file(f2, p)
    assert res2["client"] == ""


def test_discover_single_skill(service, temp_dir):
    # Setup project directory
    proj = temp_dir / "project1"
    proj.mkdir()
    proj_skills = proj / ".agents" / "skills"
    proj_skills.mkdir(parents=True)

    # Update service aliases to match the real temp path
    service.project_aliases[str(proj_skills)] = "My Project Alias"

    skill_dir = proj_skills / "my_skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("---\nname: Targeted Skill\ncategory: Architecture\n---")

    # Call discover_single_skill
    res = service.discover_single_skill(skill_dir, proj_skills)

    assert res is not None
    assert res["name"] == "Targeted Skill"
    assert res["category"] == "Architecture"
    assert res["project_label"] == "My Project Alias"
    assert res["is_package"] is False

from unittest.mock import patch

import pytest

from skill_manager.core.copier import copy_skill_folders_to_projects


@pytest.fixture
def temp_dir(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    project = tmp_path / "project"
    project.mkdir()
    return source, project


def test_copy_skill_folders_to_projects_success(temp_dir):
    source, project = temp_dir
    skill_dir = source / "test_skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("# Test Skill")
    (skill_dir / "data.txt").write_text("data")

    skills = [{"local_path": str(skill_dir), "name": "Test Skill"}]
    projects = [str(project)]

    result = copy_skill_folders_to_projects(skills, projects)

    assert result["copied"] == 1
    assert (project / ".agents" / "skills" / "test_skill" / "SKILL.md").exists()
    assert (project / ".agents" / "skills" / "test_skill" / "data.txt").read_text() == "data"


def test_copy_skill_folders_to_projects_update_only(temp_dir):
    source, project = temp_dir
    skill_dir = source / "test_skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("# Test Skill")

    skills = [{"local_path": str(skill_dir), "name": "Test Skill"}]
    projects = [str(project)]

    # First run with update_only=True should skip because it doesn't exist in project
    result = copy_skill_folders_to_projects(skills, projects, update_only=True)
    assert result["copied"] == 0
    assert not (project / ".agents" / "skills" / "test_skill").exists()

    # Create it in project then run update_only=True
    (project / ".agents" / "skills" / "test_skill").mkdir(parents=True)
    result = copy_skill_folders_to_projects(skills, projects, update_only=True)
    assert result["merged"] == 1
    assert (project / ".agents" / "skills" / "test_skill" / "SKILL.md").exists()


def test_copy_skill_folders_to_projects_missing_skill_md(temp_dir):
    source, project = temp_dir
    skill_dir = source / "bad_skill"
    skill_dir.mkdir()
    # No SKILL.md

    skills = [{"local_path": str(skill_dir), "name": "Bad Skill"}]
    projects = [str(project)]

    result = copy_skill_folders_to_projects(skills, projects)
    assert result["skipped"] == 1
    assert "missing SKILL.md" in result["details"][0]["message"]


def test_copy_skill_folders_to_projects_invalid_project(temp_dir):
    source, project = temp_dir
    skill_dir = source / "test_skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("# Test")

    # Project is a file, not a directory
    bad_project = project / "file.txt"
    bad_project.write_text("not a dir")

    skills = [{"local_path": str(skill_dir)}]
    projects = [str(bad_project)]

    result = copy_skill_folders_to_projects(skills, projects)
    assert result["skipped"] == 1
    assert "directory is not a folder" in result["details"][0]["message"]


def test_copy_skill_folders_to_projects_permission_denied(temp_dir):
    source, project = temp_dir
    skill_dir = source / "test_skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("# Test")

    skills = [{"local_path": str(skill_dir)}]
    projects = [str(project)]

    with patch("shutil.copytree", side_effect=PermissionError("Permission Denied")):
        result = copy_skill_folders_to_projects(skills, projects)
        assert result["failed"] == 1
        assert "Permission Denied" in result["details"][0]["message"]


def test_copy_skill_folders_to_projects_mkdir_failure(temp_dir):
    source, project = temp_dir
    skill_dir = source / "test_skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("# Test")

    skills = [{"local_path": str(skill_dir)}]
    # Project root exists, so normalization appends .agents/skills before mkdir.
    project_path = project / "new_dir"
    project_path.mkdir()
    projects = [str(project_path)]

    # Mock mkdir to fail even if it passes the pre-normalization check
    with patch("pathlib.Path.mkdir", side_effect=OSError("Drive Read Only")):
        result = copy_skill_folders_to_projects(skills, projects)
        assert result["failed"] == 1
        assert "Drive Read Only" in result["details"][0]["message"]


def test_copy_skill_folders_to_projects_normalization_failure(temp_dir):
    source, project = temp_dir
    skill_dir = source / "test_skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("# Test")

    skills = [{"local_path": str(skill_dir)}]
    # Normalization fails if parent doesn't exist
    projects = [str(project / "nonexistent" / "project")]

    result = copy_skill_folders_to_projects(skills, projects)
    assert result["skipped"] == 1
    assert "Project root folder does not exist" in result["details"][0]["message"]

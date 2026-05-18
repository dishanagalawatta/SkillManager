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
    transformed = service._transform_skill(skill, is_package=True)
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
    transformed = service._transform_skill(skill, is_package=False, project_label="My Project")
    assert transformed["name"] == "Proj Skill"
    assert transformed["is_package"] is False
    assert transformed["project_label"] == "My Project"
    assert transformed["skill_base_relative"] == "skillA"


def test_transform_skill_archived_and_starred(service):
    # Archived
    s1 = {"local_path": "/src2/archived"}
    t1 = service._transform_skill(s1, is_package=True)
    assert t1["is_archived"] is True

    # Starred
    s2 = {"local_path": "/src1/starred"}
    t2 = service._transform_skill(s2, is_package=True)
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

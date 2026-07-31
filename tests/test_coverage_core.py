from unittest.mock import patch

from skill_manager.core.config import (
    DEFAULT_SHORTCUTS,
    ConfigManager,
    resolve_data_file,
)
from skill_manager.core.copier import copy_skill_folders_to_projects


def test_copy_skill_folders_invalid_paths(tmp_path, caplog):
    result = copy_skill_folders_to_projects(
        [{"name": "ghost", "local_path": str(tmp_path / "missing-skill")}],
        [str(tmp_path / "proj")],
    )
    assert result["copied"] == 0
    assert result["failed"] == 0
    assert result["skipped"] == 1
    assert "Skill folder does not exist" in result["details"][0]["message"]

    valid_src = tmp_path / "valid-skill"
    valid_src.mkdir()
    (valid_src / "SKILL.md").write_text("# skill")
    missing_parent = tmp_path / "no_such_parent" / "proj" / "skills"
    result = copy_skill_folders_to_projects(
        [{"name": "valid", "local_path": str(valid_src)}],
        [str(missing_parent)],
    )
    assert result["skipped"] == 1
    assert "Project parent folder does not exist" in result["details"][0]["message"]
    assert "parent_missing" in caplog.text


def test_copy_skill_folders_empty_inputs(tmp_path):
    assert copy_skill_folders_to_projects([], []) == {
        "copied": 0,
        "merged": 0,
        "skipped": 0,
        "failed": 0,
        "details": [],
    }

    result = copy_skill_folders_to_projects([{"name": "x"}], [str(tmp_path / "proj")])
    assert result["skipped"] == 1
    assert "no local folder path" in result["details"][0]["message"]

    valid_src = tmp_path / "valid-skill"
    valid_src.mkdir()
    (valid_src / "SKILL.md").write_text("# skill")
    result = copy_skill_folders_to_projects([{"name": "valid", "local_path": str(valid_src)}], [])
    assert result["copied"] == 0
    assert result["skipped"] == 0
    assert result["details"] == []


def test_copy_skill_folders_multi_source(tmp_path):
    source_1 = tmp_path / "source1"
    source_1.mkdir()
    (source_1 / "SKILL.md").write_text("source 1 content")
    (source_1 / "assets").mkdir()
    (source_1 / "assets" / "icon.svg").write_text("icon 1")

    source_2 = tmp_path / "source2"
    source_2.mkdir()
    (source_2 / "SKILL.md").write_text("source 2 content")

    skills_dir = tmp_path / "proj" / "skills"
    (skills_dir / "skill-a").mkdir(parents=True)
    (skills_dir / "skill-a" / "SKILL.md").write_text("old content")
    (skills_dir / "unknown-skill").mkdir()

    result = copy_skill_folders_to_projects(
        [
            {"name": "skill-a", "folder_name": "skill-a", "local_path": str(source_1)},
            {"name": "skill-b", "folder_name": "skill-b", "local_path": str(source_2)},
        ],
        [str(skills_dir)],
    )

    assert result["merged"] == 1
    assert result["copied"] == 1
    assert result["failed"] == 0
    assert result["skipped"] == 0
    assert (skills_dir / "skill-a" / "SKILL.md").read_text() == "source 1 content"
    assert (skills_dir / "skill-a" / "assets" / "icon.svg").read_text() == "icon 1"
    assert (skills_dir / "skill-b" / "SKILL.md").read_text() == "source 2 content"
    assert not (skills_dir / "unknown-skill" / "SKILL.md").exists()

    # Copier has no first-wins priority: for the same target folder the
    # LAST source wins (updater.py's priority semantics are not preserved).
    copy_skill_folders_to_projects(
        [
            {"name": "skill-a", "folder_name": "skill-a", "local_path": str(source_1)},
            {"name": "skill-a", "folder_name": "skill-a", "local_path": str(source_2)},
        ],
        [str(skills_dir)],
    )
    assert (skills_dir / "skill-a" / "SKILL.md").read_text() == "source 2 content"


def test_copy_skill_folders_error_handling(tmp_path):
    source = tmp_path / "src"
    source.mkdir()
    (source / "SKILL.md").write_text("# skill")
    skills_dir = tmp_path / "proj" / "skills"
    skills_dir.mkdir(parents=True)

    # Trigger exception in copytree → counted as failed, no crash
    with patch("shutil.copytree", side_effect=RuntimeError("Copy failed")):
        result = copy_skill_folders_to_projects(
            [{"name": "skill-a", "folder_name": "skill-a", "local_path": str(source)}],
            [str(skills_dir)],
        )

    assert result["failed"] == 1
    assert result["details"][0]["status"] == "failed"
    assert result["details"][0]["message"] == "Copy failed"


def test_resolve_data_file_copy_error(tmp_path):
    data_dir = tmp_path / "data"
    legacy_dir = tmp_path / "legacy"
    legacy_dir.mkdir()
    (legacy_dir / "test.json").write_text("{}")

    # Mock copy2 to raise OSError
    with patch("shutil.copy2", side_effect=OSError("Copy failed")):
        # Should return legacy_path instead of target_path on failure
        res = resolve_data_file("test.json", data_dir, legacy_dir)
        assert res == legacy_dir / "test.json"


def test_config_manager_migration(tmp_path):
    # Create a separate directory for app data
    app_data_dir = tmp_path / "app_data"
    app_data_dir.mkdir()

    # Create a root config in a "current working directory"
    cwd_dir = tmp_path / "cwd"
    cwd_dir.mkdir()
    root_config = cwd_dir / "config.json"
    root_config.write_text('{"targets": ["a"]}')

    # Mock get_app_data_dir to return our temp app_data_dir
    with (
        patch("skill_manager.core.config.get_app_data_dir", return_value=app_data_dir),
        patch("pathlib.Path.cwd", return_value=cwd_dir),
    ):
        # Also need to make sure resolve_data_file sees the mock
        cm = ConfigManager("config.json")
        # Should have migrated targets to projects
        assert cm.get("projects") == ["a"]
        # New config should exist in app_data_dir
        assert (app_data_dir / "config.json").exists()


def test_config_manager_shortcut_merging(tmp_path):
    config_file = tmp_path / "config.json"
    # Partial shortcuts
    config_file.write_text('{"shortcuts": {"search": "Ctrl+Shift+F"}}')

    cm = ConfigManager(str(config_file))
    shortcuts = cm.get("shortcuts")
    assert shortcuts["search"] == "Ctrl+Shift+F"  # Preserved
    assert shortcuts["copy"] == DEFAULT_SHORTCUTS["copy"]  # Merged from default


def test_config_manager_save_error(tmp_path, caplog):
    config_file = tmp_path / "config.json"
    cm = ConfigManager(str(config_file))

    with patch("builtins.open", side_effect=OSError("Permission denied")):
        cm.save()

    assert "Error saving config: Permission denied" in caplog.text

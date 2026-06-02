import os
from unittest.mock import patch

import pytest

from skill_manager.core.persistence import (
    load_archive,
    load_cache,
    load_starred,
    load_temp_registry,
    patch_cache_remove,
    save_archive,
    save_cache,
    save_starred,
    save_temp_registry,
)


@pytest.fixture
def temp_files(tmp_path):
    archive = tmp_path / "archive.json"
    starred = tmp_path / "starred.json"
    cache = tmp_path / "cache.json"
    temp_reg = tmp_path / "temp.json"
    return {
        "archive": str(archive),
        "starred": str(starred),
        "cache": str(cache),
        "temp": str(temp_reg),
    }


def patch_config(temp_files):
    return patch.multiple(
        "skill_manager.core.persistence",
        SKILL_LIBRARY_ARCHIVE_FILE=temp_files["archive"],
        SKILL_LIBRARY_STARRED_FILE=temp_files["starred"],
        SKILL_LIBRARY_CACHE_FILE=temp_files["cache"],
        TEMP_COPIES_FILE=temp_files["temp"],
    )


def test_archive_persistence(temp_files):
    paths = ["/p1", "/p2"]
    with patch_config(temp_files):
        save_archive(paths)
        loaded = load_archive()
        assert loaded == paths


def test_archive_persistence_failure(temp_files):
    with patch_config(temp_files), patch("builtins.open", side_effect=OSError("Disk Full")):
        result = save_archive(["/p1"])
        assert result is False


def test_load_archive_corrupted(temp_files):
    with patch_config(temp_files):
        with open(temp_files["archive"], "w") as f:
            f.write("invalid json")
        loaded = load_archive()
        assert loaded == []

        # Test dictionary return case
        with open(temp_files["archive"], "w") as f:
            f.write('{"archived_skills": ["/p3"]}')
        loaded_dict = load_archive()
        assert loaded_dict == ["/p3"]


def test_starred_persistence(temp_files):
    paths = ["/e1"]
    with patch_config(temp_files):
        save_starred(paths)
        loaded = load_starred()
        assert loaded == paths


def test_starred_persistence_failure(temp_files):
    with patch_config(temp_files), patch("builtins.open", side_effect=PermissionError("Denied")):
        result = save_starred(["/e1"])
        assert result is False


def test_cache_persistence(temp_files):
    data = {"skills": [{"name": "S1", "local_path": "/p1", "raw_content": "large"}]}
    with patch_config(temp_files):
        save_cache(data)
        loaded = load_cache()
        assert loaded["skills"][0]["name"] == "S1"
        assert loaded["skills"][0]["raw_content"] == ""


def test_save_cache_failure(temp_files):
    with patch_config(temp_files), patch("builtins.open", side_effect=OSError("IO Error")):
        result = save_cache({"skills": []})
        assert result is False


def test_load_cache_corrupted(temp_files):
    with patch_config(temp_files):
        with open(temp_files["cache"], "w") as f:
            f.write("{corrupted")
        loaded = load_cache()
        assert loaded is None
        assert not os.path.exists(temp_files["cache"])


def test_load_starred_corrupted(temp_files):
    with patch_config(temp_files):
        with open(temp_files["starred"], "w") as f:
            f.write("not json")
        # load_starred doesn't currently delete corrupted files, but it should return []
        assert load_starred() == []


def test_load_project_skill_ownership_corrupted(temp_files):
    from skill_manager.core.persistence import load_project_skill_ownership
    with patch_config(temp_files), patch("skill_manager.core.persistence.PROJECT_SKILL_OWNERSHIP_FILE", temp_files["cache"]):
        with open(temp_files["cache"], "w") as f:
            f.write("bad")
        assert load_project_skill_ownership() == {}

        # Non-dict JSON
        with open(temp_files["cache"], "w") as f:
            f.write("[1, 2, 3]")
        assert load_project_skill_ownership() == {}


def test_save_project_skill_ownership_failure(temp_files):
    from skill_manager.core.persistence import save_project_skill_ownership
    with patch_config(temp_files), patch("builtins.open", side_effect=OSError("denied")):
        assert save_project_skill_ownership({}) is False



def test_patch_cache_remove(temp_files):
    data = {"skills": [{"local_path": "/p1"}, {"local_path": "/p2"}]}
    with patch_config(temp_files):
        save_cache(data)
        removed_count = patch_cache_remove(["/p1"])
        assert removed_count == 1
        loaded = load_cache()
        assert len(loaded["skills"]) == 1
        assert loaded["skills"][0]["local_path"] == "/p2"


def test_patch_cache_remove_failure(temp_files):
    with patch_config(temp_files):
        save_cache({"skills": [{"local_path": "/p1"}]})
        with patch("builtins.open", side_effect=OSError("Lock Error")):
            count = patch_cache_remove(["/p1"])
            assert count == 0


def test_temp_registry_persistence(temp_files):
    paths = ["/t1"]
    with patch_config(temp_files):
        save_temp_registry(paths)
        loaded = load_temp_registry()
        assert loaded == paths


def test_temp_registry_failure(temp_files):
    with patch_config(temp_files), patch("builtins.open", side_effect=OSError("Read only")):
        save_temp_registry(["/t1"])  # Should handle exception and print
        loaded = load_temp_registry()
        assert loaded == []


def test_patch_cache_add(temp_files):
    from skill_manager.core.persistence import patch_cache_add
    data = {"skills": [{"local_path": "/p1", "category": "Cat1"}]}
    with patch_config(temp_files):
        save_cache(data)
        new_skills = [
            {"local_path": "/p1", "category": "Cat2", "raw_content": "strip-me"},
            {"local_path": "/p2", "category": "Cat3"}
        ]
        projects_state = [
            {
                "project_path": "/proj1",
                "project_label": "Proj 1",
                "skills": [{"local_path": "/p2", "category": "Cat3"}]
            }
        ]
        added_count = patch_cache_add(new_skills, projects_state)
        assert added_count == 2
        loaded = load_cache()
        assert len(loaded["skills"]) == 2
        # Check update
        s1 = next(s for s in loaded["skills"] if s["local_path"] == "/p1")
        assert s1["category"] == "Cat2"
        assert s1["raw_content"] == ""
        # Check append
        s2 = next(s for s in loaded["skills"] if s["local_path"] == "/p2")
        assert s2["category"] == "Cat3"
        # Check projects
        assert len(loaded["projects"]) == 1
        assert loaded["projects"][0]["project_path"] == "/proj1"
        assert loaded["project_labels"] == ["Proj 1"]
        assert loaded["categories"] == ["Cat2", "Cat3"]


def test_patch_cache_add_failure(temp_files):
    from skill_manager.core.persistence import patch_cache_add
    with patch_config(temp_files):
        # Cache doesn't exist
        count = patch_cache_add([{"local_path": "/p1"}])
        assert count == 0


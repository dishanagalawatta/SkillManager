import os
import json
import pytest
from unittest.mock import patch, mock_open
from skill_manager.core.persistence import (
    save_archive, load_archive,
    save_essentials, load_essentials,
    save_cache, load_cache,
    patch_cache_remove,
    save_temp_registry, load_temp_registry
)

@pytest.fixture
def temp_files(tmp_path):
    archive = tmp_path / "archive.json"
    essentials = tmp_path / "essentials.json"
    cache = tmp_path / "cache.json"
    temp_reg = tmp_path / "temp.json"
    return {
        "archive": str(archive),
        "essentials": str(essentials),
        "cache": str(cache),
        "temp": str(temp_reg)
    }

def patch_config(temp_files):
    return patch.multiple(
        "skill_manager.core.persistence",
        SKILL_LIBRARY_ARCHIVE_FILE=temp_files["archive"],
        SKILL_LIBRARY_ESSENTIALS_FILE=temp_files["essentials"],
        SKILL_LIBRARY_CACHE_FILE=temp_files["cache"],
        TEMP_COPIES_FILE=temp_files["temp"]
    )

def test_archive_persistence(temp_files):
    paths = ["/p1", "/p2"]
    with patch_config(temp_files):
        save_archive(paths)
        loaded = load_archive()
        assert loaded == paths

def test_archive_persistence_failure(temp_files):
    with patch_config(temp_files), \
         patch("builtins.open", side_effect=OSError("Disk Full")):
        result = save_archive(["/p1"])
        assert result is False

def test_load_archive_corrupted(temp_files):
    with patch_config(temp_files):
        with open(temp_files["archive"], "w") as f:
            f.write("invalid json")
        loaded = load_archive()
        assert loaded == []

def test_essentials_persistence(temp_files):
    paths = ["/e1"]
    with patch_config(temp_files):
        save_essentials(paths)
        loaded = load_essentials()
        assert loaded == paths

def test_essentials_persistence_failure(temp_files):
    with patch_config(temp_files), \
         patch("builtins.open", side_effect=PermissionError("Denied")):
        result = save_essentials(["/e1"])
        assert result is False

def test_cache_persistence(temp_files):
    data = {"skills": [{"name": "S1", "local_path": "/p1", "raw_content": "large"}]}
    with patch_config(temp_files):
        save_cache(data)
        loaded = load_cache()
        assert loaded["skills"][0]["name"] == "S1"
        assert "raw_content" not in loaded["skills"][0]

def test_save_cache_failure(temp_files):
    with patch_config(temp_files), \
         patch("builtins.open", side_effect=OSError("IO Error")):
        result = save_cache({"skills": []})
        assert result is False

def test_load_cache_corrupted(temp_files):
    with patch_config(temp_files):
        with open(temp_files["cache"], "w") as f:
            f.write("{corrupted")
        loaded = load_cache()
        assert loaded is None
        assert not os.path.exists(temp_files["cache"])

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
    with patch_config(temp_files), \
         patch("builtins.open", side_effect=OSError("Read only")):
        save_temp_registry(["/t1"]) # Should handle exception and print
        loaded = load_temp_registry()
        assert loaded == []

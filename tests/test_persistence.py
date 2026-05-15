import os
import json
import pytest
from pathlib import Path
from skill_manager.core.persistence import (
    save_archive, load_archive, save_essentials, load_essentials,
    save_cache, load_cache, patch_cache_remove
)
from skill_manager.core.config import (
    SKILL_LIBRARY_ARCHIVE_FILE,
    SKILL_LIBRARY_ESSENTIALS_FILE,
    SKILL_LIBRARY_CACHE_FILE
)

@pytest.fixture
def temp_persistence(tmp_path, monkeypatch):
    """Overrides persistence file paths for testing."""
    archive = tmp_path / "archive.json"
    essentials = tmp_path / "essentials.json"
    cache = tmp_path / "cache.json"
    
    monkeypatch.setattr("skill_manager.core.persistence.SKILL_LIBRARY_ARCHIVE_FILE", str(archive))
    monkeypatch.setattr("skill_manager.core.persistence.SKILL_LIBRARY_ESSENTIALS_FILE", str(essentials))
    monkeypatch.setattr("skill_manager.core.persistence.SKILL_LIBRARY_CACHE_FILE", str(cache))
    
    return {
        "archive": archive,
        "essentials": essentials,
        "cache": cache
    }

def test_archive_persistence(temp_persistence):
    paths = ["/path/a", "/path/b"]
    assert save_archive(paths) is True
    assert temp_persistence["archive"].exists()
    
    loaded = load_archive()
    assert loaded == paths
    
    # Test empty/missing
    temp_persistence["archive"].unlink()
    assert load_archive() == []

def test_essentials_persistence(temp_persistence):
    paths = ["/path/essential/1"]
    assert save_essentials(paths) is True
    assert temp_persistence["essentials"].exists()
    
    loaded = load_essentials()
    assert loaded == paths

def test_cache_persistence(temp_persistence):
    data = {
        "skills": [
            {"name": "Skill 1", "local_path": "/p1", "raw_content": "BIG CONTENT"},
            {"name": "Skill 2", "local_path": "/p2"}
        ],
        "categories": ["Dev"]
    }
    assert save_cache(data) is True
    
    # Verify exclusion
    with open(temp_persistence["cache"], 'r') as f:
        saved = json.load(f)
        assert "raw_content" not in saved["skills"][0]
        assert saved["skills"][0]["name"] == "Skill 1"
        assert len(saved["skills"]) == 2

    loaded = load_cache()
    assert loaded["categories"] == ["Dev"]
    assert len(loaded["skills"]) == 2

def test_patch_cache_remove(temp_persistence):
    data = {
        "skills": [
            {"local_path": "/a"},
            {"local_path": "/b"},
            {"local_path": "/c"}
        ]
    }
    save_cache(data)
    
    removed = patch_cache_remove(["/a", "/c"])
    assert removed == 2
    
    loaded = load_cache()
    assert len(loaded["skills"]) == 1
    assert loaded["skills"][0]["local_path"] == "/b"

def test_load_corrupted_cache(temp_persistence):
    temp_persistence["cache"].write_text("NOT JSON")
    assert load_cache() is None
    assert not temp_persistence["cache"].exists() # Should auto-delete

import json
from pathlib import Path
from unittest.mock import patch

from skill_manager.core.skill_packages.relocator import (
    _cleanup_empty_parents,
    _merge_and_move_lockfile,
    _relocate_path_internal,
    relocate_packages_from_output,
)


def test_cleanup_empty_parents_oserror(tmp_path):
    # Trigger OSError by mocking rmdir
    test_dir = tmp_path / "a" / "b"
    test_dir.mkdir(parents=True)
    with patch.object(Path, "rmdir", side_effect=OSError("Permission denied")):
        _cleanup_empty_parents(test_dir / "dummy")
        assert test_dir.exists()

def test_relocate_path_internal_same_path(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    dest_base = tmp_path
    # src is already at dest_base / src.name
    assert _relocate_path_internal(src, dest_base, None) is False

def test_relocate_path_internal_exception(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    dest_base = tmp_path / "dest"
    with patch("shutil.move", side_effect=RuntimeError("Move failed")):
        messages = []
        assert _relocate_path_internal(src, dest_base, messages.append) is False
        assert any("Relocation failed" in m for m in messages)

def test_merge_and_move_lockfile_no_source(tmp_path):
    source_lock = tmp_path / "missing.json"
    target_lock = tmp_path / "target.json"
    _merge_and_move_lockfile(source_lock, target_lock, None)
    assert not target_lock.exists()

def test_merge_and_move_lockfile_json_errors(tmp_path):
    source_lock = tmp_path / "source.json"
    target_lock = tmp_path / "target.json"
    source_lock.write_text("invalid json")
    target_lock.write_text("invalid json")
    messages = []
    # Should handle decode errors and treat as empty dict
    _merge_and_move_lockfile(source_lock, target_lock, messages.append)
    assert target_lock.exists()
    assert json.loads(target_lock.read_text()) == {}

def test_merge_and_move_lockfile_malformed_target_skills(tmp_path):
    source_lock = tmp_path / "source.json"
    target_lock = tmp_path / "target.json"
    source_lock.write_text('{"skills": {"a": 1}}')
    target_lock.write_text('{"skills": "not a dict"}')
    _merge_and_move_lockfile(source_lock, target_lock, None)
    data = json.loads(target_lock.read_text())
    assert data["skills"] == {"a": 1}

def test_merge_and_move_lockfile_exception(tmp_path):
    source_lock = tmp_path / "source.json"
    source_lock.write_text("{}")
    target_lock = tmp_path / "target.json"
    target_lock.write_text("{}") # Ensure target exists to trigger merge logic
    with patch("json.load", side_effect=RuntimeError("Load failed")):
        messages = []
        _merge_and_move_lockfile(source_lock, target_lock, messages.append)
        assert any("Failed to merge lockfile" in m for m in messages)

def test_relocate_packages_fallback_regex(tmp_path):
    dest = tmp_path / "dest"
    dest.mkdir()
    src = tmp_path / "unusual_path"
    src.mkdir()
    # Output that doesn't match primary path_regex but might match fallback
    output = [f"Something happened at {src}"]
    result = relocate_packages_from_output(output, str(dest), None)
    assert "unusual_path" in result
    assert (dest / "unusual_path").exists()

def test_relocate_packages_manifest_move(tmp_path):
    dest = tmp_path / "dest" / "skills"
    dest.mkdir(parents=True)
    source_root = tmp_path / "source"
    source_root.mkdir()
    manifest = source_root / ".antigravity-install-manifest.json"
    manifest.write_text("manifest content")

    src_path = source_root / "skills" / "pkg"
    src_path.mkdir(parents=True)

    output = [f"at {src_path}"]
    with patch("skill_manager.core.config.DATA_DIR", tmp_path / "mock_data"):
        relocate_packages_from_output(output, str(dest), None)

    assert (dest.parent / ".antigravity-install-manifest.json").exists()

def test_relocate_packages_same_path_skips(tmp_path):
    dest = tmp_path / "dest"
    dest.mkdir()
    output = [f"at {dest}"]
    result = relocate_packages_from_output(output, str(dest), None)
    assert result == ["dest"]

def test_relocate_packages_data_dir_fallback(tmp_path):
    # Trigger line 192: if target_root.resolve() == Path.cwd().resolve()
    mock_data_dir = tmp_path / "data_dir"
    mock_data_dir.mkdir()

    dest_base = tmp_path / "skills"
    # So target_root is tmp_path

    source_root = tmp_path / "source"
    source_root.mkdir()
    (source_root / "skills" / "pkg").mkdir(parents=True)
    (source_root / "skills-lock.json").write_text("{}")

    with (
        patch("pathlib.Path.cwd", return_value=tmp_path),
        patch("skill_manager.core.config.DATA_DIR", mock_data_dir),
    ):
        relocate_packages_from_output([f"at {source_root / 'skills' / 'pkg'}"], str(dest_base), None)

    # Should have merged lockfile to mock_data_dir instead of tmp_path
    assert (mock_data_dir / "skills-lock.json").exists()

from unittest.mock import patch

from skill_manager.core.skill_packages.storage import (
    _skill_fingerprint,
    diff_package_inventory,
    inventory_removals_verified,
    normalize_storage_key,
    package_project_path_conflicts,
    promote_package_storage,
    resolve_package_storage,
    safe_package_folder_name,
    scan_package_inventory,
)


def test_normalize_storage_key(tmp_path):
    p = tmp_path / "foo"
    assert normalize_storage_key(p) == str(p.resolve()).casefold()


def test_safe_package_folder_name():
    assert (
        safe_package_folder_name({"name": "Test Package", "package_id": "pkg_123456789"})
        == "test-package-23456789"
    )
    assert (
        safe_package_folder_name({"name": "Test-Package-123456789", "package_id": "pkg_123456789"})
        == "test-package-123456789"
    )


def test_resolve_package_storage(tmp_path):
    packages = [
        {"package_id": "1", "configured_package_path": str(tmp_path / "shared"), "name": "pkg1"},
        {"package_id": "2", "configured_package_path": str(tmp_path / "shared"), "name": "pkg2"},
        {"package_id": "3", "configured_package_path": str(tmp_path / "isolated"), "name": "pkg3"},
    ]
    resolved = resolve_package_storage(packages)

    assert resolved[0]["storage_mode"] == "grouped"
    assert "pkg1" in resolved[0]["resolved_package_path"]
    assert resolved[1]["storage_mode"] == "grouped"
    assert "pkg2" in resolved[1]["resolved_package_path"]

    # Now this defaults to grouped as well
    assert resolved[2]["storage_mode"] == "grouped"
    assert resolved[2]["resolved_package_path"] != str((tmp_path / "isolated").resolve())


def test_resolve_package_storage_conflict(tmp_path):
    packages = [
        {"package_id": "1", "configured_package_path": str(tmp_path / "shared"), "name": "pkg"},
        {"package_id": "2", "configured_package_path": str(tmp_path / "shared"), "name": "pkg"},
    ]
    resolved = resolve_package_storage(packages)
    assert resolved[0]["resolved_package_path"] != resolved[1]["resolved_package_path"]
    assert "pkg-2" in resolved[1]["resolved_package_path"]


def test_resolve_package_storage_no_configured():
    packages = [{"package_id": "1", "name": "pkg1"}]
    resolved = resolve_package_storage(packages)
    assert len(resolved) == 1
    assert resolved[0]["configured_package_path"] == ""


def test_resolve_package_storage_exact_match(tmp_path):
    packages = [
        {"package_id": "1", "configured_package_path": str(tmp_path / "pkg1"), "name": "pkg1"},
    ]
    resolved = resolve_package_storage(packages)
    assert resolved[0]["storage_mode"] == "direct"
    assert resolved[0]["resolved_package_path"] == str((tmp_path / "pkg1").resolve())


@patch("skill_manager.core.copier.normalize_project_skills_path")
def test_package_project_path_conflicts(mock_normalize, tmp_path):
    mock_normalize.return_value = (str(tmp_path / "project"), None)

    packages = [
        {"resolved_package_path": str(tmp_path / "project")},
        {"package_path": str(tmp_path / "other")},
    ]
    conflicts = package_project_path_conflicts(packages, ["dummy_project"])
    assert len(conflicts) == 1
    assert conflicts[0] == str(tmp_path / "project")


def test_scan_package_inventory(tmp_path):
    pkg_dir = tmp_path / "pkg"
    pkg_dir.mkdir()
    skill_dir = pkg_dir / "skill1"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("dummy")

    package = {"resolved_package_path": str(pkg_dir), "package_id": "pkg1"}
    inventory = scan_package_inventory(package)

    assert inventory["scan_ok"] is True
    assert inventory["skill_count"] == 1
    assert "skill1" in inventory["skills"]
    assert "fingerprint" in inventory["skills"]["skill1"]


def test_scan_package_inventory_not_exist(tmp_path):
    package = {"resolved_package_path": str(tmp_path / "non_existent")}
    inventory = scan_package_inventory(package)
    assert inventory["scan_ok"] is False
    assert inventory["path_exists"] is False
    assert inventory["skill_count"] == 0


def test_scan_package_inventory_oserror(tmp_path):
    package = {"resolved_package_path": str(tmp_path)}
    with patch("pathlib.Path.iterdir", side_effect=OSError("Permission denied")):
        inventory = scan_package_inventory(package)
    assert inventory["scan_ok"] is False
    assert "Permission denied" in inventory["scan_error"]


def test_diff_package_inventory():
    prev = {
        "skills": {"a": {"fingerprint": "1"}, "b": {"fingerprint": "2"}, "c": {"fingerprint": "3"}}
    }
    curr = {
        "skills": {"b": {"fingerprint": "2"}, "c": {"fingerprint": "4"}, "d": {"fingerprint": "5"}}
    }
    diff = diff_package_inventory(prev, curr)

    assert diff["added"] == ["d"]
    assert diff["removed"] == ["a"]
    assert diff["updated"] == ["c"]
    assert diff["unchanged"] == ["b"]


def test_inventory_removals_verified():
    # If not scan_ok, should return False
    assert not inventory_removals_verified({}, {"scan_ok": False})

    # If all skills removed, return False
    assert not inventory_removals_verified({"skills": {"a": {}}}, {"scan_ok": True, "skills": {}})

    # If valid, return True
    assert inventory_removals_verified(
        {"skills": {"a": {}}}, {"scan_ok": True, "skills": {"b": {}}}
    )


def test_promote_package_storage(tmp_path):
    old_dir = tmp_path / "old"
    old_dir.mkdir()
    skill_dir = old_dir / "skill1"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("content")

    new_dir = tmp_path / "new"

    package = {
        "_previous_resolved_package_path": str(old_dir),
        "resolved_package_path": str(new_dir),
    }
    # Pass previous_inventory to authorize the move
    result = promote_package_storage(package, {"skills": {"skill1": {}}})

    assert result["moved"] == 1
    assert result["skipped"] == 0
    assert (new_dir / "skill1" / "SKILL.md").exists()
    assert not (old_dir / "skill1" / "SKILL.md").exists()


def test_promote_package_storage_skip(tmp_path):
    package = {
        "_previous_resolved_package_path": str(tmp_path),
        "resolved_package_path": str(tmp_path),
    }
    assert promote_package_storage(package, None) == {"moved": 0, "skipped": 0}

    new_dir = tmp_path / "new"
    new_dir.mkdir()
    (new_dir / "blocking").write_text("x")
    package = {
        "_previous_resolved_package_path": str(tmp_path / "old"),
        "resolved_package_path": str(new_dir),
    }

    old_dir = tmp_path / "old"
    old_dir.mkdir()
    assert promote_package_storage(package, None) == {"moved": 0, "skipped": 1}


def test_skill_fingerprint(tmp_path):
    skill_dir = tmp_path / "skill"
    skill_dir.mkdir()
    f1 = skill_dir / "SKILL.md"
    f1.write_text("abc")

    fp1 = _skill_fingerprint(skill_dir)
    assert isinstance(fp1, str)
    assert len(fp1) > 0

    f1.write_text("def")
    fp2 = _skill_fingerprint(skill_dir)
    assert fp1 != fp2


def test_skill_fingerprint_oserror(tmp_path):
    skill_dir = tmp_path / "skill"
    skill_dir.mkdir()
    f1 = skill_dir / "SKILL.md"
    f1.write_text("abc")

    with patch("pathlib.Path.stat", side_effect=OSError("Permission denied")):
        fp = _skill_fingerprint(skill_dir)

    import hashlib

    assert fp == hashlib.sha1().hexdigest()


def test_resolve_package_storage_exact_conflict(tmp_path):
    packages = [
        {"configured_package_path": str(tmp_path / "shared"), "name": "pkg"},
        {"configured_package_path": str(tmp_path / "shared"), "name": "pkg"},
    ]
    resolved = resolve_package_storage(packages)
    assert len(resolved) == 2
    assert resolved[0]["resolved_package_path"] != resolved[1]["resolved_package_path"]
    assert "-2" in resolved[1]["resolved_package_path"]


def test_promote_package_storage_no_skills(tmp_path):
    old_dir = tmp_path / "old"
    old_dir.mkdir()
    new_dir = tmp_path / "new"
    package = {
        "_previous_resolved_package_path": str(old_dir),
        "resolved_package_path": str(new_dir),
    }
    assert promote_package_storage(package, {"skills": {}}) == {"moved": 0, "skipped": 0}


def test_promote_package_storage_missing_source(tmp_path):
    old_dir = tmp_path / "old"
    old_dir.mkdir()
    new_dir = tmp_path / "new"
    package = {
        "_previous_resolved_package_path": str(old_dir),
        "resolved_package_path": str(new_dir),
    }
    # Skill is in inventory but not on disk
    assert promote_package_storage(package, {"skills": {"skill1": {}}}) == {
        "moved": 0,
        "skipped": 0,
    }


def test_promote_package_storage_destination_exists(tmp_path):
    old_dir = tmp_path / "old"
    old_dir.mkdir()
    skill_dir = old_dir / "skill1"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("content")

    new_dir = tmp_path / "new"
    new_dir.mkdir()
    (new_dir / "skill1").mkdir()  # destination already exists

    package = {
        "_previous_resolved_package_path": str(old_dir),
        "resolved_package_path": str(new_dir),
    }
    assert promote_package_storage(package, {"skills": {"skill1": {}}}) == {
        "moved": 0,
        "skipped": 1,
    }

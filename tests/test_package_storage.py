from pathlib import Path
from unittest.mock import patch

from skill_manager.core.skill_packages.storage import (
    diff_package_inventory,
    inventory_removals_verified,
    package_project_path_conflicts,
    promote_package_storage,
    resolve_package_storage,
    scan_package_inventory,
)


def test_first_package_uses_direct_path(tmp_path):
    packages = [
        {"name": "Alpha", "package_id": "pkg_alpha", "package_path": str(tmp_path / "skills")}
    ]

    resolved = resolve_package_storage(packages)

    assert resolved[0]["storage_mode"] == "direct"
    assert Path(resolved[0]["resolved_package_path"]) == (tmp_path / "skills").resolve()


def test_shared_package_path_promotes_all_packages_to_children(tmp_path):
    shared = tmp_path / "skills"
    packages = [
        {"name": "Alpha", "package_id": "pkg_alpha", "package_path": str(shared)},
        {"name": "Beta", "package_id": "pkg_beta", "package_path": str(shared)},
    ]

    resolved = resolve_package_storage(packages)

    assert {package["storage_mode"] for package in resolved} == {"grouped"}
    assert all(Path(package["resolved_package_path"]).parent == shared.resolve() for package in resolved)
    assert len({package["resolved_package_path"] for package in resolved}) == 2


def test_promote_package_storage_moves_only_owned_skill_folders(tmp_path):
    shared = tmp_path / "skills"
    shared.mkdir()
    alpha = shared / "alpha"
    alpha.mkdir()
    (alpha / "SKILL.md").write_text("alpha")
    unrelated = shared / "notes"
    unrelated.mkdir()
    (unrelated / "readme.txt").write_text("keep")

    package = {
        "name": "Alpha",
        "package_id": "pkg_alpha",
        "_previous_resolved_package_path": str(shared),
        "resolved_package_path": str(shared / "alpha-pkg"),
    }
    previous = {"skills": {"alpha": {"folder_name": "alpha"}}}

    result = promote_package_storage(package, previous)

    assert result == {"moved": 1, "skipped": 0}
    assert (shared / "alpha-pkg" / "alpha" / "SKILL.md").is_file()
    assert (shared / "notes" / "readme.txt").is_file()


def test_scan_and_diff_package_inventory(tmp_path):
    package_path = tmp_path / "pkg"
    skill = package_path / "alpha"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("v1")
    current = scan_package_inventory(
        {
            "package_id": "pkg_alpha",
            "configured_package_path": str(package_path),
            "resolved_package_path": str(package_path),
        }
    )

    previous = {"skills": {"old": {"fingerprint": "old"}, "alpha": {"fingerprint": "stale"}}}
    diff = diff_package_inventory(previous, current)

    assert diff["added"] == []
    assert diff["removed"] == ["old"]
    assert diff["updated"] == ["alpha"]


def test_missing_package_scan_does_not_verify_removals(tmp_path):
    previous = {"skills": {"alpha": {"fingerprint": "a"}, "beta": {"fingerprint": "b"}}}
    current = scan_package_inventory(
        {"package_id": "pkg_alpha", "resolved_package_path": str(tmp_path / "missing")}
    )
    diff = diff_package_inventory(previous, current)

    assert diff["removed"] == ["alpha", "beta"]
    assert current["scan_ok"] is False
    assert inventory_removals_verified(previous, current) is False


def test_empty_scan_after_non_empty_inventory_does_not_verify_removals(tmp_path):
    package_path = tmp_path / "package"
    package_path.mkdir()
    previous = {"skills": {"alpha": {"fingerprint": "a"}}}
    current = scan_package_inventory(
        {"package_id": "pkg_alpha", "resolved_package_path": str(package_path)}
    )

    assert current["scan_ok"] is True
    assert current["skill_count"] == 0
    assert inventory_removals_verified(previous, current) is False


def test_package_project_path_conflicts_detect_same_final_path(tmp_path):
    path = tmp_path / "repo" / ".agents" / "skills"
    packages = [{"resolved_package_path": str(path)}]

    assert package_project_path_conflicts(packages, [str(path)]) == [str(path)]


def test_promote_package_storage_aborts_when_destination_not_empty(tmp_path):
    shared = tmp_path / "skills"
    shared.mkdir()
    destination = shared / "alpha-pkg"
    destination.mkdir()
    (destination / "existing.txt").write_text("x")

    package = {
        "_previous_resolved_package_path": str(shared),
        "resolved_package_path": str(destination),
    }

    with patch("shutil.move") as move:
        result = promote_package_storage(package, {"skills": {"alpha": {}}})

    assert result == {"moved": 0, "skipped": 1}
    move.assert_not_called()

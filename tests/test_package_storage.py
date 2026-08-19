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


def test_first_package_uses_grouped_path(tmp_path):
    packages = [
        {"name": "Alpha", "package_id": "pkg_alpha", "package_path": str(tmp_path / "skills")}
    ]

    resolved = resolve_package_storage(packages)

    assert resolved[0]["storage_mode"] == "grouped"
    assert Path(resolved[0]["resolved_package_path"]) != (tmp_path / "skills").resolve()
    assert (tmp_path / "skills").resolve() in Path(resolved[0]["resolved_package_path"]).parents


def test_shared_package_path_promotes_all_packages_to_children(tmp_path):
    shared = tmp_path / "skills"
    packages = [
        {"name": "Alpha", "package_id": "pkg_alpha", "package_path": str(shared)},
        {"name": "Beta", "package_id": "pkg_beta", "package_path": str(shared)},
    ]

    resolved = resolve_package_storage(packages)

    assert {package["storage_mode"] for package in resolved} == {"grouped"}
    assert all(
        Path(package["resolved_package_path"]).parent == shared.resolve() for package in resolved
    )
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


def test_package_project_path_conflicts_detect_project_root(tmp_path):
    project_root = tmp_path / "repo"
    project_skills = project_root / ".agents" / "skills"
    project_skills.mkdir(parents=True)
    packages = [{"resolved_package_path": str(project_skills)}]

    assert package_project_path_conflicts(packages, [str(project_root)]) == [str(project_skills)]


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


def test_delete_package_storage_grouped(tmp_path):
    from skill_manager.core.skill_packages.storage import delete_package_storage

    shared_root = tmp_path / "skills"
    pkg_folder = shared_root / "find-skills-12345678"
    pkg_folder.mkdir(parents=True)
    skill1 = pkg_folder / "skill-a"
    skill1.mkdir()
    (skill1 / "SKILL.md").write_text("skill a")

    clone_dir = tmp_path / "clones" / "find-skills-12345678"
    clone_dir.mkdir(parents=True)
    (clone_dir / "README.md").write_text("clone content")

    lockfile = shared_root / ".find-skills-skill-lock.json"
    lockfile.write_text("{}")

    package = {
        "name": "find-skills",
        "package_id": "pkg_12345678",
        "configured_package_path": str(shared_root),
        "resolved_package_path": str(pkg_folder),
        "storage_mode": "grouped",
        "clone_path": str(clone_dir),
    }

    result = delete_package_storage(package, protected_paths=[str(shared_root)])

    assert not pkg_folder.exists()
    assert not clone_dir.exists()
    assert not lockfile.exists()
    assert str(pkg_folder.resolve()) in result["deleted_folders"]
    assert str(clone_dir.resolve()) in result["deleted_folders"]
    assert str(lockfile.resolve()) in result["deleted_files"]
    assert len(result["errors"]) == 0


def test_delete_package_storage_direct_managed_folders(tmp_path):
    from skill_manager.core.skill_packages.storage import delete_package_storage

    shared_root = tmp_path / "skills"
    shared_root.mkdir(parents=True)
    managed1 = shared_root / "managed-skill-1"
    managed1.mkdir()
    (managed1 / "SKILL.md").write_text("skill 1")

    unrelated = shared_root / "unrelated-skill"
    unrelated.mkdir()
    (unrelated / "SKILL.md").write_text("unrelated")

    package = {
        "name": "custom-package",
        "package_id": "pkg_custom",
        "configured_package_path": str(shared_root),
        "resolved_package_path": str(shared_root),
        "storage_mode": "direct",
        "managed_folders": ["managed-skill-1"],
    }

    result = delete_package_storage(package, protected_paths=[str(shared_root)])

    assert not managed1.exists()
    assert unrelated.exists()
    assert shared_root.exists()
    assert str(managed1.resolve()) in result["deleted_folders"]


def test_delete_package_storage_safety_guards(tmp_path):
    from skill_manager.core.skill_packages.storage import (
        delete_package_storage,
        is_safe_deletion_target,
    )

    project_dir = tmp_path / "my_project"
    project_dir.mkdir()

    assert not is_safe_deletion_target(Path("/"), protected_paths=[project_dir])
    assert not is_safe_deletion_target(Path.home(), protected_paths=[project_dir])
    assert not is_safe_deletion_target(Path.cwd(), protected_paths=[project_dir])
    assert not is_safe_deletion_target(project_dir, protected_paths=[project_dir])

    # Target being ancestor of protected path is unsafe
    assert not is_safe_deletion_target(tmp_path, protected_paths=[project_dir])

    # Package trying to delete project root is rejected
    package = {
        "name": "dangerous",
        "package_id": "pkg_danger",
        "resolved_package_path": str(project_dir),
        "storage_mode": "grouped",
    }
    result = delete_package_storage(package, protected_paths=[str(project_dir)])
    assert project_dir.exists()
    assert len(result["deleted_folders"]) == 0

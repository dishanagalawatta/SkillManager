from skill_manager.core.skill_packages.config import (
    detect_package_config,
    normalize_skill_package_config,
)
from skill_manager.core.skill_packages.relocator import _cleanup_empty_parents


def test_config_id_generation():
    # Same repo URL should yield same ID
    data1 = {"repository_url": "https://github.com/user/repo"}
    data2 = {"repository_url": "https://github.com/user/repo", "name": "different"}

    norm1 = normalize_skill_package_config(data1)
    norm2 = normalize_skill_package_config(data2)

    assert norm1["package_id"] == norm2["package_id"]
    assert norm1["package_id"].startswith("pkg_")

def test_detect_package_config_git_auto():
    # If no type, but has repo URL, it's NOT auto-detected as git unless explicitly set or detected by other means
    # Wait, detect_package_config logic:
    # if package_name -> npm
    # else if update_command -> check command type

    data = {"repository_url": "https://github.com/user/repo"}
    detected = detect_package_config(data)
    # Default is "auto" which becomes "auto" if no package_name or update_command
    assert detected["source_type"] == "auto"

    # If we set type to git
    data["source_type"] = "git"
    detected = detect_package_config(data)
    assert detected["source_type"] == "git"

def test_cleanup_empty_parents(tmp_path):
    # Create nested empty dirs: root/a/b/c
    c = tmp_path / "a" / "b" / "c"
    c.mkdir(parents=True)

    # Run cleanup on c/dummy
    _cleanup_empty_parents(c / "dummy", levels=3)

    # a, b, c should be gone
    assert not c.exists()
    assert not (tmp_path / "a" / "b").exists()
    assert not (tmp_path / "a").exists()
    assert tmp_path.exists()

def test_cleanup_empty_parents_stops_at_non_empty(tmp_path):
    # root/a/b/c
    # root/a/other.txt
    a = tmp_path / "a"
    b = a / "b"
    c = b / "c"
    c.mkdir(parents=True)
    (a / "other.txt").write_text("keep me")

    _cleanup_empty_parents(c / "dummy", levels=3)

    # c and b should be gone, but a should remain
    assert not c.exists()
    assert not b.exists()
    assert a.exists()
    assert (a / "other.txt").exists()

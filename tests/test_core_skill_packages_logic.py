from skill_manager.core.skill_packages.config import (
    detect_package_config,
    normalize_skill_package_config,
)


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
    # if package_name -> npx
    # else if update_command -> check command type

    data = {"repository_url": "https://github.com/user/repo"}
    detected = detect_package_config(data)
    # Default is "auto" which becomes "auto" if no package_name or update_command
    assert detected["source_type"] == "auto"

    # If we set type to git
    data["source_type"] = "git"
    detected = detect_package_config(data)
    assert detected["source_type"] == "git"

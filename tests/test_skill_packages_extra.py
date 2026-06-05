import json
from unittest.mock import patch

import pytest

from skill_manager.core.skill_packages.relocator import (
    _merge_and_move_lockfile,
    _relocate_path_internal,
    relocate_packages,
)
from skill_manager.core.skill_packages.updater import (
    _intercept_cross_platform_command,
    _run_git_package_update,
    _run_npx_update,
    run_skill_package_update,
)


def test_run_git_package_update_missing_args():
    with pytest.raises(ValueError, match="Configure a repository_url"):
        _run_git_package_update({"clone_path": "path"}, None)


def test_run_git_package_update_token(tmp_path):
    with patch("skill_manager.core.skill_packages.updater.cmd.Git") as mock_git:
        _run_git_package_update(
            {"repository_url": "url", "clone_path": str(tmp_path), "github_token": "secret"}, None
        )
        args = mock_git.return_value.execute.call_args[0][0]
        assert any("credential.helper" in arg and "secret" in arg for arg in args)


def test_run_git_package_update_not_empty(tmp_path):
    (tmp_path / "file.txt").write_text("hello")
    with pytest.raises(ValueError, match="Clone path exists but is not an empty git checkout"):
        _run_git_package_update({"repository_url": "url", "clone_path": str(tmp_path)}, None)


def test_run_git_package_update_installed_to(tmp_path):
    messages = []
    with patch("skill_manager.core.skill_packages.updater.cmd.Git"):
        _run_git_package_update(
            {
                "repository_url": "url",
                "clone_path": str(tmp_path),
                "package_path": str(tmp_path / "dest"),
            },
            messages.append,
        )
    assert any(f"Installed to {tmp_path}" in m for m in messages)


def test_run_npx_update_missing_package():
    with pytest.raises(ValueError, match="Configure an npx package name."):
        _run_npx_update({}, None)


def test_intercept_cross_platform_command_quotes(tmp_path):
    # Test path with quotes and echo with quotes
    p = tmp_path / "quoted dir"
    p.mkdir()
    messages = []

    cmd = f"test -d '{p}' && echo 'Hello World'"
    assert _intercept_cross_platform_command(cmd, messages.append) is True
    assert messages[-1] == "Hello World"

    cmd = f'test -d "{p}" && echo "Hello World"'
    assert _intercept_cross_platform_command(cmd, messages.append) is True


def test_relocate_path_internal_exceptions(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    dest = tmp_path / "dest"

    with patch("shutil.copytree", side_effect=Exception("Copy failed")):
        assert not _relocate_path_internal(src, dest, None)


def test_merge_and_move_lockfile_invalid_json(tmp_path):
    src = tmp_path / "src.json"
    dest = tmp_path / "dest.json"

    # Dest exists with invalid JSON, src has valid JSON
    src.write_text('{"version": "1.0"}')
    dest.write_text("not json")

    _merge_and_move_lockfile(src, dest, None)

    merged = json.loads(dest.read_text())
    assert merged["version"] == "1.0"

    # Src has invalid JSON
    src.write_text("not json")
    _merge_and_move_lockfile(src, dest, None)
    # Shouldn't crash


def test_relocate_packages_no_skills_folder(tmp_path):
    assert relocate_packages(str(tmp_path), str(tmp_path / "dest"), None) == []


def test_relocate_packages_failed_iteration(tmp_path):
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()

    with patch("pathlib.Path.iterdir", side_effect=OSError("Failed iter")):
        relocate_packages(str(tmp_path), str(tmp_path / "dest"), None)
    # Should not crash


def test_relocate_packages_manifest_move(tmp_path):
    dest_base = tmp_path / "dest"
    source = tmp_path / "source"
    skills = source / "skills"
    skills.mkdir(parents=True)

    manifest = source / ".antigravity-install-manifest.json"
    manifest.write_text("{}")

    relocate_packages(str(source), str(dest_base), None, "pkg")

    assert (tmp_path / ".pkg-antigravity-install-manifest.json").exists()


@patch("skill_manager.core.skill_packages.updater._run_shell_command")
def test_run_skill_package_update_verify_command(mock_shell, tmp_path):
    source = {
        "name": "pkg",
        "source_type": "custom",
        "update_command": "python -c 'print(1)'",
        "verify_command": "echo verified",
    }
    with patch(
        "skill_manager.core.skill_packages.updater.check_skill_package_versions", return_value={}
    ):
        run_skill_package_update(source)

    mock_shell.assert_called_with("echo verified", None)

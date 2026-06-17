import json
from unittest.mock import patch

import pytest

from skill_manager.core.skill_packages.relocator import (
    _is_safe_relative_to,
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


def test_is_safe_relative_to(tmp_path):
    inner = tmp_path / "inner" / "sub"
    inner.mkdir(parents=True)
    assert _is_safe_relative_to(inner, tmp_path)

    outer = tmp_path.parent / "unrelated"
    outer.mkdir(exist_ok=True)
    assert not _is_safe_relative_to(outer, tmp_path)


def test_merge_and_move_lockfile_source_missing(tmp_path):
    src = tmp_path / "missing.json"
    dest = tmp_path / "dest.json"
    _merge_and_move_lockfile(src, dest, None)
    assert not dest.exists()


def test_merge_and_move_lockfile_handles_exception(tmp_path):
    src = tmp_path / "src.json"
    src.write_text('{"skills": {"a": 1}}')
    with patch("builtins.open", side_effect=OSError("Locked")):
        _merge_and_move_lockfile(src, tmp_path / "dest.json", None)


def test_relocate_packages_from_output_no_target(tmp_path):
    from skill_manager.core.skill_packages.relocator import relocate_packages_from_output

    assert relocate_packages_from_output(["line"], "", None) is None


def test_relocate_packages_from_output_no_detected_paths(tmp_path):
    from skill_manager.core.skill_packages.relocator import relocate_packages_from_output

    dest = tmp_path / "dest"
    dest.mkdir()
    result = relocate_packages_from_output(["just some noise"], str(dest), None)
    assert result is None


def test_relocate_packages_from_output_skip_same_as_dest(tmp_path):
    from skill_manager.core.skill_packages.relocator import relocate_packages_from_output

    dest = tmp_path / "dest"
    dest.mkdir()
    skill1 = dest / "skill1"
    skill1.mkdir()
    (skill1 / "SKILL.md").write_text("content")

    result = relocate_packages_from_output([f"Installed to {dest}"], str(dest), None)
    assert result == []


def test_relocate_packages_from_output_security_rejection(tmp_path):
    from skill_manager.core.skill_packages.relocator import relocate_packages_from_output

    dest = tmp_path / "dest"
    dest.mkdir()
    malicious = tmp_path.parent / "malicious"
    malicious.mkdir(exist_ok=True)

    result = relocate_packages_from_output(
        [f"Installed to {malicious}"], str(dest), None, base_path=str(tmp_path)
    )
    assert result is None


def test_relocate_packages_from_output_fallback_regex(tmp_path):
    from skill_manager.core.skill_packages.relocator import relocate_packages_from_output

    dest = tmp_path / "dest"
    dest.mkdir()
    skills_inline = f"C:/nonesuch/{tmp_path.name}/skills"
    result = relocate_packages_from_output([f"Installed to {skills_inline}"], str(dest), None)
    assert result is None


def test_relocate_packages_from_output_standalone_skill(tmp_path):
    from skill_manager.core.skill_packages.relocator import relocate_packages_from_output

    dest = tmp_path / "dest"
    dest.mkdir()
    source = tmp_path / "source"
    source.mkdir()
    standalone = source / "standalone-skill"
    standalone.mkdir()
    (standalone / "SKILL.md").write_text("content")

    result = relocate_packages_from_output([f"Installed to {standalone}"], str(dest), None)
    assert result == ["standalone-skill"]
    assert (dest / "standalone-skill").is_dir()


def test_relocate_packages_from_output_exception_path(tmp_path):
    from skill_manager.core.skill_packages.relocator import relocate_packages_from_output

    result = relocate_packages_from_output(
        ["some output"], str(tmp_path), None, base_path=str(tmp_path)
    )
    assert result is None


def test_relocate_packages_data_dir_fallback(tmp_path):
    with patch(
        "skill_manager.core.skill_packages.relocator.Path.cwd",
        return_value=tmp_path,
    ):
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        skill1 = skills_dir / "skill1"
        skill1.mkdir()
        (skill1 / "SKILL.md").write_text("content")

        result = relocate_packages(str(tmp_path), str(tmp_path), None)
        assert result == ["skill1"]


def test_relocate_packages_from_output_container_move(tmp_path):
    from skill_manager.core.skill_packages.relocator import relocate_packages_from_output

    src_dir = tmp_path / "src_pkg"
    src_dir.mkdir()
    skills_dir = src_dir / "skills"
    skills_dir.mkdir()
    skill1 = skills_dir / "skill1"
    skill1.mkdir()
    (skill1 / "SKILL.md").write_text("content")

    dest = tmp_path / "dest"
    dest.mkdir()

    result = relocate_packages_from_output([f"Installed to {skills_dir}"], str(dest), None)
    assert result == ["skill1"]
    assert (dest / "skill1").is_dir()


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

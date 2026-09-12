import json
from unittest.mock import patch

import pytest

from skill_manager.core.skill_packages.relocator import (
    is_safe_relative_to,
    merge_and_move_lockfile,
    relocate_packages,
    relocate_path_internal,
)
from skill_manager.core.skill_packages.updater import (
    intercept_cross_platform_command,
    run_git_package_update,
    run_npx_update,
    run_skill_package_update,
)


def testrun_git_package_update_missing_args():
    with pytest.raises(ValueError, match="Configure a repository_url"):
        run_git_package_update({"clone_path": "path"}, None)


def testrun_git_package_update_token(tmp_path):
    with patch("skill_manager.core.skill_packages.updater.cmd.Git") as mock_git:
        run_git_package_update(
            {"repository_url": "url", "clone_path": str(tmp_path), "github_token": "secret"}, None
        )
        args = mock_git.return_value.execute.call_args[0][0]
        assert any("credential.helper" in arg and "secret" in arg for arg in args)


def testrun_git_package_update_not_empty(tmp_path):
    (tmp_path / "file.txt").write_text("hello")
    with pytest.raises(ValueError, match="Clone path exists but is not an empty git checkout"):
        run_git_package_update({"repository_url": "url", "clone_path": str(tmp_path)}, None)


def testrun_git_package_update_installed_to(tmp_path):
    messages = []
    with patch("skill_manager.core.skill_packages.updater.cmd.Git"):
        run_git_package_update(
            {
                "repository_url": "url",
                "clone_path": str(tmp_path),
                "package_path": str(tmp_path / "dest"),
            },
            messages.append,
        )
    assert any(f"Installed to {tmp_path}" in m for m in messages)


def testrun_npx_update_missing_package():
    with pytest.raises(ValueError, match="Configure an npx package name."):
        run_npx_update({}, None)


def testintercept_cross_platform_command_quotes(tmp_path):
    # Test path with quotes and echo with quotes
    p = tmp_path / "quoted dir"
    p.mkdir()
    messages = []

    cmd = f"test -d '{p}' && echo 'Hello World'"
    assert intercept_cross_platform_command(cmd, messages.append) is True
    assert messages[-1] == "Hello World"

    cmd = f'test -d "{p}" && echo "Hello World"'
    assert intercept_cross_platform_command(cmd, messages.append) is True


def testrelocate_path_internal_exceptions(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    dest = tmp_path / "dest"

    with patch("shutil.copytree", side_effect=Exception("Copy failed")):
        assert not relocate_path_internal(src, dest, None)


def testmerge_and_move_lockfile_invalid_json(tmp_path):
    src = tmp_path / "src.json"
    dest = tmp_path / "dest.json"

    # Dest exists with invalid JSON, src has valid JSON
    src.write_text('{"version": "1.0"}')
    dest.write_text("not json")

    merge_and_move_lockfile(src, dest, None)

    merged = json.loads(dest.read_text())
    assert merged["version"] == "1.0"

    # Src has invalid JSON
    src.write_text("not json")
    merge_and_move_lockfile(src, dest, None)
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


def testis_safe_relative_to(tmp_path):
    inner = tmp_path / "inner" / "sub"
    inner.mkdir(parents=True)
    assert is_safe_relative_to(inner, tmp_path)

    outer = tmp_path.parent / "unrelated"
    outer.mkdir(exist_ok=True)
    assert not is_safe_relative_to(outer, tmp_path)


def testmerge_and_move_lockfile_source_missing(tmp_path):
    src = tmp_path / "missing.json"
    dest = tmp_path / "dest.json"
    merge_and_move_lockfile(src, dest, None)
    assert not dest.exists()


def testmerge_and_move_lockfile_handles_exception(tmp_path):
    src = tmp_path / "src.json"
    src.write_text('{"skills": {"a": 1}}')
    with patch("builtins.open", side_effect=OSError("Locked")):
        merge_and_move_lockfile(src, tmp_path / "dest.json", None)


def test_relocate_packages_from_output_global_store_accepted(tmp_path, monkeypatch):
    """Regression: `npx skills add <repo> -g` installs to ~/.agents/skills.

    The global store sits outside the staging temp dir, so the relocation
    security gate must accept it (copy into isolated storage) instead of
    dropping it as "outside of staging directory" (archify partial-install).
    """
    from skill_manager.core.skill_packages import relocator as reloc_mod
    from skill_manager.core.skill_packages.relocator import relocate_packages_from_output

    fake_home = tmp_path / "home"
    global_store = fake_home / ".agents" / "skills"
    archify = global_store / "archify"
    archify.mkdir(parents=True)
    (archify / "SKILL.md").write_text("# archify")
    staging = tmp_path / "staging"
    staging.mkdir()
    dest = tmp_path / "dest"
    dest.mkdir()

    monkeypatch.setattr(reloc_mod, "known_global_skill_dirs", lambda: [global_store])

    messages: list[str] = []
    result = relocate_packages_from_output(
        [f"Installed to {archify}"],
        str(dest),
        messages.append,
        base_path=str(staging),
    )
    assert result == ["archify"]
    assert (dest / "archify" / "SKILL.md").is_file()
    # Global install is preserved (copy, not move).
    assert (archify / "SKILL.md").is_file()
    assert not any("outside of staging" in m for m in messages)


def test_relocate_packages_from_output_global_container_accepted(tmp_path, monkeypatch):
    """A detected global container dir is iterated like any skills container."""
    from skill_manager.core.skill_packages import relocator as reloc_mod
    from skill_manager.core.skill_packages.relocator import relocate_packages_from_output

    global_store = tmp_path / "ghost" / ".agents" / "skills"
    skill = global_store / "my-skill"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("# my-skill")
    staging = tmp_path / "staging"
    staging.mkdir()
    dest = tmp_path / "dest"
    dest.mkdir()

    monkeypatch.setattr(reloc_mod, "known_global_skill_dirs", lambda: [global_store])

    result = relocate_packages_from_output(
        [f"Installed to {global_store}"],
        str(dest),
        None,
        base_path=str(staging),
    )
    assert result == ["my-skill"]
    assert (dest / "my-skill" / "SKILL.md").is_file()


def test_verify_command_quoting_is_well_formed(tmp_path):
    """Regression: verify_command had a broken quote (`echo "Skills installed in "{path}`)."""
    from skill_manager.core.skill_packages.config import normalize_skill_package_config

    pkg = normalize_skill_package_config(
        {
            "name": "Archify",
            "source_type": "npx",
            "package_name": "skills",
            "package_args": "add tt-a1i/archify -g -y --all",
            "package_path": str(tmp_path / "archify-pkg"),
        }
    )
    cmd = pkg["verify_command"]
    assert cmd.count('"') % 2 == 0
    assert '""' not in cmd
    assert "Skills installed in " in cmd


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


@patch("skill_manager.core.skill_packages.updater.run_shell_command")
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

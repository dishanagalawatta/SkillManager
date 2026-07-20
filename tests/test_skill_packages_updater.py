from unittest.mock import MagicMock, patch

import pytest

from skill_manager.core.skill_packages.updater import (
    intercept_cross_platform_command,
    remove_package_folder,
    run_git_package_update,
    run_npx_update,
    run_shell_command,
    run_skill_package_update,
)


def test_remove_package_folder(tmp_path):
    d = tmp_path / "test"
    d.mkdir()
    assert d.exists()
    remove_package_folder(d)
    assert not d.exists()


@patch("skill_manager.core.skill_packages.updater.run_npx_update")
@patch("skill_manager.core.skill_packages.updater.relocate_packages_from_output")
@patch(
    "skill_manager.core.skill_packages.updater.check_skill_package_versions",
    return_value={"updated": True},
)
def test_run_skill_package_update_npx_full(mock_check, mock_relocate, mock_run, tmp_path):
    source = {
        "source_type": "npx",
        "package_name": "test-package",
        "name": "test-pkg",
        "package_path": str(tmp_path / "pkg"),
        "managed_folders": ["folder1"],
    }
    mock_relocate.return_value = ["folder2"]
    d = tmp_path / "pkg"
    d.mkdir()
    f1 = d / "folder1"
    f1.mkdir()
    out = run_skill_package_update(source)
    assert out["managed_folders"] == ["folder2"]
    assert out["removed_folders"] == ["folder1"]
    assert not f1.exists()


@patch("skill_manager.core.skill_packages.updater.run_git_package_update")
@patch("skill_manager.core.skill_packages.updater.relocate_packages")
@patch(
    "skill_manager.core.skill_packages.updater.check_skill_package_versions",
    return_value={"updated": True},
)
def test_run_skill_package_update_git_full(mock_check, mock_relocate, mock_run, tmp_path):
    source = {
        "source_type": "git",
        "repository_url": "fake",
        "name": "test-pkg",
        "package_path": str(tmp_path / "pkg"),
        "managed_folders": ["folder1"],
    }
    mock_relocate.return_value = ["folder2"]
    d = tmp_path / "pkg"
    d.mkdir()
    f1 = d / "folder1"
    f1.mkdir()
    out = run_skill_package_update(source)
    assert out["managed_folders"] == ["folder2"]
    assert out["removed_folders"] == ["folder1"]
    assert not f1.exists()


@patch("skill_manager.core.skill_packages.updater.run_shell_command")
@patch("skill_manager.core.skill_packages.updater.relocate_packages_from_output")
@patch("skill_manager.core.skill_packages.updater.check_skill_package_versions", return_value={})
def test_run_skill_package_update_command(mock_check, mock_relocate, mock_run, tmp_path):
    source = {
        "update_command": "echo test",
        "name": "test-pkg",
        "package_path": str(tmp_path),
        "verify_command": "echo verify",
    }
    mock_relocate.return_value = ["folder1"]
    out = run_skill_package_update(source)
    assert out["managed_folders"] == ["folder1"]


def test_intercept_cross_platform_command_basic():
    cb = MagicMock()
    assert not intercept_cross_platform_command("echo hello", cb)


def test_intercept_cross_platform_command_test_d():
    cb = MagicMock()
    with patch("pathlib.Path.is_dir", return_value=True):
        assert intercept_cross_platform_command("test -d /fake/dir", cb)


def test_intercept_cross_platform_command_test_d_quotes():
    cb = MagicMock()
    with patch("pathlib.Path.is_dir", return_value=True):
        assert intercept_cross_platform_command("test -d '/fake/dir'", cb)
        assert intercept_cross_platform_command('test -d "/fake/dir"', cb)


def test_intercept_cross_platform_command_test_d_echo():
    cb = MagicMock()
    with patch("pathlib.Path.is_dir", return_value=True):
        assert intercept_cross_platform_command("test -d /fake/dir && echo done", cb)
        cb.assert_called_with("done")


def test_intercept_cross_platform_command_test_d_fail():
    cb = MagicMock()
    with patch("pathlib.Path.is_dir", return_value=False), pytest.raises(RuntimeError):
        intercept_cross_platform_command("test -d /fake/dir", cb)


@patch("skill_manager.core.skill_packages.updater.run_process")
@patch("skill_manager.core.skill_packages.updater.shlex.split")
def test_run_shell_command_splits(mock_shlex, mock_run_process):
    mock_shlex.return_value = ["echo", "hello"]
    cb = MagicMock()
    run_shell_command("echo hello", cb, cwd="/tmp")
    mock_run_process.assert_called_once_with(["echo", "hello"], cb, shell=False, cwd="/tmp")
    mock_shlex.assert_called_once()


@patch("skill_manager.core.skill_packages.updater.cmd.Git")
@patch("skill_manager.core.skill_packages.updater.Repo")
def test_run_git_package_update_clone(mock_repo, mock_git, tmp_path):
    source = {
        "repository_url": "https://github.com/fake/repo",
        "name": "test-pkg",
        "clone_path": str(tmp_path / "repo"),
        "github_token": "fake_token",
    }
    run_git_package_update(source, None)
    mock_git.return_value.execute.assert_called_once()


@patch("skill_manager.core.skill_packages.updater.Repo")
def test_run_git_package_update_pull(mock_repo_cls, tmp_path):
    d = tmp_path / "repo"
    d.mkdir()
    (d / ".git").mkdir()
    source = {
        "repository_url": "https://github.com/fake/repo",
        "name": "test-pkg",
        "clone_path": str(d),
    }
    mock_repo_inst = MagicMock()
    mock_repo_cls.return_value = mock_repo_inst
    run_git_package_update(source, None)
    mock_repo_inst.git.execute.assert_called_once()


def test_run_npx_update_basic():
    with patch("skill_manager.core.skill_packages.updater.run_process") as mock_rp:
        run_npx_update({"package_name": "test", "package_args": "--some arg"}, None)
        mock_rp.assert_called_once()


@patch("skill_manager.core.skill_packages.updater.Repo")
def test_run_git_package_update_pull_exception(mock_repo_cls, tmp_path):
    d = tmp_path / "repo"
    d.mkdir()
    (d / ".git").mkdir()
    source = {
        "repository_url": "https://github.com/fake/repo",
        "name": "test-pkg",
        "clone_path": str(d),
    }
    mock_repo_inst = MagicMock()
    mock_repo_cls.return_value = mock_repo_inst
    mock_repo_inst.git.execute.side_effect = Exception("failed")
    with pytest.raises(Exception, match="failed"):
        run_git_package_update(source, None)


def test_run_git_package_update_no_url(tmp_path):
    with pytest.raises(ValueError, match="Configure a repository_url"):
        run_git_package_update({"clone_path": str(tmp_path)}, None)


def test_run_git_package_update_not_empty_dir(tmp_path):
    d = tmp_path / "repo"
    d.mkdir()
    (d / "somefile").write_text("hello")
    with pytest.raises(ValueError, match="not an empty git checkout"):
        run_git_package_update({"repository_url": "fake", "clone_path": str(d)}, None)


@patch("skill_manager.core.skill_packages.updater.cmd.Git")
def test_run_git_package_update_clone_exception(mock_git, tmp_path):
    source = {
        "repository_url": "https://github.com/fake/repo",
        "name": "test-pkg",
        "clone_path": str(tmp_path / "repo"),
        "github_token": "fake_token",
    }
    mock_git.return_value.execute.side_effect = Exception("failed")
    with pytest.raises(Exception, match="failed"):
        run_git_package_update(source, None)


@patch("skill_manager.core.skill_packages.updater.run_npx_update")
@patch("skill_manager.core.skill_packages.updater.relocate_packages_from_output")
@patch(
    "skill_manager.core.skill_packages.updater.check_skill_package_versions",
    return_value={"updated": True},
)
def test_run_skill_package_update_no_package_path(mock_check, mock_relocate, mock_run, tmp_path):
    source = {
        "source_type": "npx",
        "package_name": "test-package",
        "name": "test-pkg",
        "managed_folders": ["folder1"],
    }
    mock_relocate.return_value = ["folder2"]
    out = run_skill_package_update(source)
    mock_relocate.assert_not_called()
    assert out["managed_folders"] == ["folder1"]


@patch("skill_manager.core.skill_packages.updater.remove_package_folder")
@patch("skill_manager.core.skill_packages.updater.run_npx_update")
@patch("skill_manager.core.skill_packages.updater.relocate_packages_from_output")
@patch(
    "skill_manager.core.skill_packages.updater.check_skill_package_versions",
    return_value={"updated": True},
)
def test_run_skill_package_update_cleanup_exception(
    mock_check, mock_relocate, mock_run, mock_remove, tmp_path
):
    source = {
        "source_type": "npx",
        "package_name": "test-package",
        "name": "test-pkg",
        "package_path": str(tmp_path / "pkg"),
        "managed_folders": ["folder1"],
    }
    mock_relocate.return_value = ["folder2"]
    d = tmp_path / "pkg"
    d.mkdir()
    f1 = d / "folder1"
    f1.mkdir()
    mock_remove.side_effect = Exception("failed")
    out = run_skill_package_update(source)
    assert out["managed_folders"] == ["folder2"]
    assert out["removed_folders"] == []


def test_run_npx_update_no_name():
    with pytest.raises(ValueError, match="Configure an npx package name"):
        run_npx_update({}, None)


@patch("skill_manager.core.skill_packages.updater.run_git_package_update")
@patch("skill_manager.core.skill_packages.updater.relocate_packages")
@patch(
    "skill_manager.core.skill_packages.updater.check_skill_package_versions",
    return_value={"updated": True},
)
def test_run_skill_package_update_git_full_staging(mock_check, mock_relocate, mock_run, tmp_path):
    source = {
        "source_type": "git",
        "repository_url": "fake",
        "name": "test-pkg",
        "package_path": str(tmp_path / "pkg"),
        "managed_folders": ["folder1"],
    }
    mock_relocate.return_value = ["folder2"]
    d = tmp_path / "pkg"
    d.mkdir()
    f1 = d / "folder1"
    f1.mkdir()
    out = run_skill_package_update(source)
    assert out["managed_folders"] == ["folder2"]
    assert out["removed_folders"] == ["folder1"]
    assert not f1.exists()


@patch("skill_manager.core.skill_packages.updater.Repo")
def test_run_git_package_update_pull_output(mock_repo_cls, tmp_path):
    d = tmp_path / "repo"
    d.mkdir()
    (d / ".git").mkdir()
    source = {
        "repository_url": "https://github.com/fake/repo",
        "name": "test-pkg",
        "clone_path": str(d),
    }
    mock_repo_inst = MagicMock()
    mock_repo_cls.return_value = mock_repo_inst
    mock_repo_inst.git.execute.return_value = b"success"
    run_git_package_update(source, None)


@patch("skill_manager.core.skill_packages.updater.cmd.Git")
def test_run_git_package_update_clone_output(mock_git, tmp_path):
    source = {
        "repository_url": "https://github.com/fake/repo",
        "name": "test-pkg",
        "clone_path": str(tmp_path / "repo"),
    }
    mock_git.return_value.execute.return_value = b"success"
    run_git_package_update(source, None)


@patch("skill_manager.core.skill_packages.updater.run_git_package_update")
@patch("skill_manager.core.skill_packages.updater.relocate_packages")
@patch(
    "skill_manager.core.skill_packages.updater.check_skill_package_versions",
    return_value={"updated": True},
)
def test_run_skill_package_update_git_full_no_staging(
    mock_check, mock_relocate, mock_run, tmp_path
):
    source = {
        "source_type": "git",
        "repository_url": "fake",
        "name": "test-pkg",
        "package_path": str(tmp_path / "pkg"),
        "managed_folders": ["folder1"],
    }
    mock_relocate.return_value = ["folder2"]
    d = tmp_path / "pkg"
    d.mkdir()
    f1 = d / "folder1"
    f1.mkdir()
    out = run_skill_package_update(source)
    assert out["managed_folders"] == ["folder2"]
    assert out["removed_folders"] == ["folder1"]
    assert not f1.exists()


@patch("skill_manager.core.skill_packages.updater.run_git_package_update")
@patch("skill_manager.core.skill_packages.updater.relocate_packages")
@patch(
    "skill_manager.core.skill_packages.updater.check_skill_package_versions",
    return_value={"updated": True},
)
def test_run_skill_package_update_git_full_no_staging_verify(
    mock_check, mock_relocate, mock_run, tmp_path
):
    source = {
        "source_type": "git",
        "repository_url": "fake",
        "name": "test-pkg",
        "package_path": str(tmp_path / "pkg"),
        "managed_folders": ["folder1"],
        "verify_command": "echo verify",
    }
    mock_relocate.return_value = ["folder2"]
    d = tmp_path / "pkg"
    d.mkdir()
    f1 = d / "folder1"
    f1.mkdir()
    with patch("skill_manager.core.skill_packages.updater.run_shell_command") as mock_rsc:
        out = run_skill_package_update(source)
        mock_rsc.assert_called_once()
    assert out["managed_folders"] == ["folder2"]
    assert out["removed_folders"] == ["folder1"]
    assert not f1.exists()


def test_intercept_cross_platform_command_test_d_path_quotes_fixed():
    cb = MagicMock()
    with patch("pathlib.Path.is_dir", return_value=True) as mock_isdir:
        assert intercept_cross_platform_command("test -d '/fake/dir", cb)
        mock_isdir.assert_called_once()
        assert intercept_cross_platform_command('test -d "/fake/dir', cb)
        mock_isdir.assert_called_with()


@patch("skill_manager.core.skill_packages.updater.run_git_package_update")
@patch("skill_manager.core.skill_packages.updater.relocate_packages")
@patch(
    "skill_manager.core.skill_packages.updater.check_skill_package_versions",
    return_value={"updated": True},
)
def test_run_skill_package_update_git_full_no_staging_verify_2(
    mock_check, mock_relocate, mock_run, tmp_path
):
    source = {
        "source_type": "git",
        "repository_url": "fake",
        "name": "test-pkg",
        "package_path": str(tmp_path / "pkg"),
        "managed_folders": ["folder1"],
        "verify_command": "echo verify",
    }
    mock_relocate.return_value = ["folder2"]
    d = tmp_path / "pkg"
    d.mkdir()
    f1 = d / "folder1"
    f1.mkdir()
    with patch("skill_manager.core.skill_packages.updater.run_shell_command") as mock_rsc:
        out = run_skill_package_update(source)
        mock_rsc.assert_called_once()
    assert out["managed_folders"] == ["folder2"]
    assert out["removed_folders"] == ["folder1"]
    assert not f1.exists()

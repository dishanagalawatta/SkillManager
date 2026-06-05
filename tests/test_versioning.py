from unittest.mock import MagicMock, patch

import pytest

from skill_manager.core.skill_packages.versioning import (
    check_skill_package_versions,
    check_skill_package_versions_async,
    detect_git_remote,
    get_git_tag,
    run_version_command,
)


@pytest.fixture
def mock_repo():
    with patch("skill_manager.core.skill_packages.versioning.Repo") as mock:
        yield mock


def test_detect_git_remote_empty():
    assert detect_git_remote("") == ""
    assert detect_git_remote(None) == ""


def test_detect_git_remote_no_dir(tmp_path):
    assert detect_git_remote(str(tmp_path)) == ""


def test_detect_git_remote_success(tmp_path, mock_repo):
    git_dir = tmp_path / ".git"
    git_dir.mkdir()

    mock_instance = MagicMock()
    mock_instance.remotes.origin.url = "https://github.com/test/repo.git"
    mock_repo.return_value = mock_instance

    assert detect_git_remote(str(tmp_path)) == "https://github.com/test/repo.git"


def test_detect_git_remote_exception(tmp_path, mock_repo):
    git_dir = tmp_path / ".git"
    git_dir.mkdir()

    mock_repo.side_effect = Exception("Test Error")
    assert detect_git_remote(str(tmp_path)) == ""


@patch("skill_manager.core.skill_packages.versioning.subprocess.run")
def test_run_version_command_success(mock_run):
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "v1.0.0\n"
    mock_run.return_value = mock_result

    assert run_version_command("git --version") == "v1.0.0"


@patch("skill_manager.core.skill_packages.versioning.subprocess.run")
def test_run_version_command_empty(mock_run):
    assert run_version_command("") == ""


@patch("skill_manager.core.skill_packages.versioning.subprocess.run")
def test_run_version_command_failure(mock_run):
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_run.return_value = mock_result

    assert run_version_command("git fail") == ""


@patch("skill_manager.core.skill_packages.versioning.subprocess.run")
def test_run_version_command_exception(mock_run):
    import subprocess

    mock_run.side_effect = subprocess.SubprocessError("Failed")
    assert run_version_command("git err") == ""


@patch("skill_manager.core.skill_packages.versioning.cmd.Git")
def test_get_git_tag_remote_success(mock_git):
    mock_instance = MagicMock()
    # Mocking ls-remote output with tags
    mock_instance.execute.return_value = "hash1\trefs/tags/v1.0.0\nhash2\trefs/tags/v1.1.0\n"
    mock_git.return_value = mock_instance

    assert get_git_tag("url", is_remote=True) == "v1.0.0"


@patch("skill_manager.core.skill_packages.versioning.cmd.Git")
def test_get_git_tag_remote_fallback_head(mock_git):
    mock_instance = MagicMock()

    # First call throws, second call returns HEAD
    def side_effect(*args, **kwargs):
        if "HEAD" in args[0]:
            return "abcdef1234567890\tHEAD"
        raise Exception("Failed tags")

    mock_instance.execute.side_effect = side_effect
    mock_git.return_value = mock_instance

    assert get_git_tag("url", is_remote=True) == "abcdef1"


@patch("skill_manager.core.skill_packages.versioning.cmd.Git")
def test_get_git_tag_remote_token(mock_git):
    mock_instance = MagicMock()
    mock_instance.execute.return_value = "hash1\trefs/tags/v2.0.0\n"
    mock_git.return_value = mock_instance

    assert get_git_tag("url", is_remote=True, token="mytoken") == "v2.0.0"


def test_get_git_tag_local_no_git(tmp_path):
    assert get_git_tag(str(tmp_path), is_remote=False) == ""


@patch("skill_manager.core.skill_packages.versioning.Repo")
def test_get_git_tag_local_success(mock_repo, tmp_path):
    git_dir = tmp_path / ".git"
    git_dir.mkdir()

    mock_instance = MagicMock()
    mock_tag = MagicMock()
    mock_tag.name = "v3.0.0"
    mock_instance.tags = [mock_tag]
    mock_repo.return_value = mock_instance

    assert get_git_tag(str(tmp_path), is_remote=False) == "v3.0.0"


@patch("skill_manager.core.skill_packages.versioning.Repo")
def test_get_git_tag_local_fallback_commit(mock_repo, tmp_path):
    git_dir = tmp_path / ".git"
    git_dir.mkdir()

    mock_instance = MagicMock()
    mock_instance.tags = []
    mock_instance.head.commit.hexsha = "1234567890abcdef"
    mock_repo.return_value = mock_instance

    assert get_git_tag(str(tmp_path), is_remote=False) == "1234567"


@patch("skill_manager.core.skill_packages.versioning.run_version_command")
def test_check_skill_package_versions_commands(mock_run):
    def run_eff(cmd):
        if "current" in cmd:
            return "v1.0"
        if "latest" in cmd:
            return "v2.0"
        return ""

    mock_run.side_effect = run_eff

    source = {"current_version_command": "current", "latest_version_command": "latest"}
    result = check_skill_package_versions(source)
    assert result["current_version"] == "1.0"
    assert result["latest_version"] == "2.0"


@patch("skill_manager.core.skill_packages.versioning.get_git_tag")
def test_check_skill_package_versions_github(mock_get_tag):
    mock_get_tag.return_value = "v3.1.4"
    source = {"repository_url": "https://github.com/foo/bar"}
    result = check_skill_package_versions(source)
    assert result["latest_version"] == "3.1.4"


@patch("skill_manager.core.skill_packages.versioning.get_git_tag")
def test_check_skill_package_versions_git_source(mock_get_tag, tmp_path):
    git_dir = tmp_path / ".git"
    git_dir.mkdir()

    def tag_eff(url, is_remote=False, token=None):
        if is_remote:
            return "v4.0.0"
        return "v3.0.0"

    mock_get_tag.side_effect = tag_eff

    source = {
        "source_type": "git",
        "clone_path": str(tmp_path),
        "repository_url": "https://foo.com/bar.git",
    }
    result = check_skill_package_versions(source, force_refresh=True)
    assert result["current_version"] == "3.0.0"
    assert result["latest_version"] == "4.0.0"


@patch("skill_manager.core.skill_packages.versioning.run_version_command")
def test_check_skill_package_versions_npx(mock_run):
    mock_run.return_value = "5.0.0"
    source = {"source_type": "npx", "package_name": "mypkg"}
    result = check_skill_package_versions(source)
    assert result["latest_version"] == "5.0.0"


@pytest.mark.asyncio
async def test_check_skill_package_versions_async():
    source = {"package_name": "foo"}
    with patch(
        "skill_manager.core.skill_packages.versioning.check_skill_package_versions"
    ) as mock_check:
        mock_check.return_value = {"package_name": "foo", "latest_version": "1.0"}
        res = await check_skill_package_versions_async(source)
        assert res["latest_version"] == "1.0"

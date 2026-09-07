import subprocess
from unittest.mock import MagicMock, patch

from skill_manager.core.skill_packages.versioning import (
    _sync_current_to_latest_if_applicable,
    check_skill_package_versions,
    detect_git_remote,
    get_git_tag,
    run_version_command,
)


@patch("skill_manager.core.skill_packages.versioning.Repo")
def test_detect_git_remote(mock_repo_class, tmp_path):
    git_dir = tmp_path / ".git"
    git_dir.mkdir()

    mock_repo = mock_repo_class.return_value
    mock_repo.remotes.origin.url = "https://github.com/test/repo.git"

    assert detect_git_remote(str(tmp_path)) == "https://github.com/test/repo.git"


def test_detect_git_remote_empty():
    assert detect_git_remote("") == ""
    assert detect_git_remote("non_existent_path") == ""


@patch("skill_manager.core.skill_packages.versioning.Repo")
def test_detect_git_remote_exception(mock_repo_class, tmp_path):
    git_dir = tmp_path / ".git"
    git_dir.mkdir()

    mock_repo_class.side_effect = Exception("Failed")
    assert detect_git_remote(str(tmp_path)) == ""


@patch("subprocess.run")
@patch("shutil.which", return_value="/bin/cmd")
def test_run_version_command_success(mock_which, mock_run):
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "v1.2.3\n"
    mock_run.return_value = mock_result

    assert run_version_command("cmd --version") == "v1.2.3"


@patch("subprocess.run", side_effect=subprocess.SubprocessError("Failed"))
@patch("shutil.which", return_value="/bin/cmd")
def test_run_version_command_failure(mock_which, mock_run):
    assert run_version_command("cmd --version") == ""


def test_run_version_command_empty():
    assert run_version_command("") == ""


@patch("skill_manager.core.skill_packages.versioning.cmd.Git")
def test_get_git_tag_remote_success(mock_git_class):
    mock_git = mock_git_class.return_value
    mock_git.execute.return_value = "hash123\trefs/tags/v2.0.0\n"

    assert get_git_tag("https://github.com/repo", is_remote=True, token="token") == "v2.0.0"


@patch("skill_manager.core.skill_packages.versioning.cmd.Git")
def test_get_git_tag_remote_fallback_head(mock_git_class):
    mock_git = mock_git_class.return_value
    mock_git.execute.side_effect = ["", "abc123456\tHEAD\n"]

    assert get_git_tag("https://github.com/repo", is_remote=True) == "abc1234"


@patch("skill_manager.core.skill_packages.versioning.cmd.Git")
def test_get_git_tag_remote_exception(mock_git_class):
    mock_git = mock_git_class.return_value
    mock_git.execute.side_effect = Exception("Network Error")

    assert get_git_tag("https://github.com/repo", is_remote=True) == ""


@patch("skill_manager.core.skill_packages.versioning.Repo")
def test_get_git_tag_local_success(mock_repo_class, tmp_path):
    git_dir = tmp_path / ".git"
    git_dir.mkdir()

    mock_repo = mock_repo_class.return_value
    mock_tag = MagicMock()
    mock_tag.name = "v1.0.0"
    mock_tag.commit.committed_datetime = 100
    mock_repo.tags = [mock_tag]

    assert get_git_tag(str(tmp_path), is_remote=False) == "v1.0.0"


def test_get_git_tag_local_no_git(tmp_path):
    assert get_git_tag(str(tmp_path), is_remote=False) == ""


@patch("skill_manager.core.skill_packages.versioning.run_version_command")
@patch("skill_manager.core.skill_packages.versioning.get_git_tag")
def test_check_skill_package_versions_custom(mock_get_git_tag, mock_run_version):
    source = {
        "current_version_command": "echo v1.0",
        "latest_version_command": "echo v2.0",
    }
    mock_run_version.side_effect = ["v1.0", "v2.0"]

    updated = check_skill_package_versions(source)
    assert updated["current_version"] == "1.0"
    assert updated["latest_version"] == "2.0"


@patch("skill_manager.core.skill_packages.versioning.get_git_tag")
def test_check_skill_package_versions_git(mock_get_git_tag, tmp_path):
    git_dir = tmp_path / ".git"
    git_dir.mkdir()

    source = {
        "source_type": "git",
        "repository_url": "https://github.com/user/repo.git",
        "clone_path": str(tmp_path),
    }

    mock_get_git_tag.side_effect = ["v1.2", "v1.0", "v1.5"]

    updated = check_skill_package_versions(source, force_refresh=True)
    assert updated["latest_version"] == "1.5"
    assert updated["current_version"] == "1.0"


@patch("skill_manager.core.skill_packages.versioning.run_version_command")
def test_check_skill_package_versions_npx(mock_run_version):
    source = {
        "source_type": "npx",
        "package_name": "mypkg",
    }

    mock_run_version.return_value = "v3.0.0"

    updated = check_skill_package_versions(source, force_refresh=True)
    assert updated["latest_version"] == "3.0.0"
    assert updated["current_version"] == "3.0.0"  # force refresh applies latest to current


# --- sync_current_to_latest tests ---


class TestSyncCurrentToLatestHelper:
    def test_npx_without_current_version_command(self):
        """Snaps current to latest for npx source with no current_version_command."""
        source = {"source_type": "npx", "current_version_command": ""}
        result = _sync_current_to_latest_if_applicable("", "3.0.0", source)
        assert result == "3.0.0"

    def test_npx_with_current_version_command(self):
        """Does NOT snap when current_version_command is provided."""
        source = {"source_type": "npx", "current_version_command": "my-cmd"}
        result = _sync_current_to_latest_if_applicable("1.0.0", "3.0.0", source)
        assert result == "1.0.0"

    def test_git_source_with_current_set(self):
        """Does NOT snap for git source when current_version is set (local detection worked)."""
        source = {"source_type": "git", "current_version_command": ""}
        result = _sync_current_to_latest_if_applicable("1.0.0", "3.0.0", source)
        assert result == "1.0.0"

    def test_git_source_with_empty_current(self):
        """Snaps for git source when current_version is empty (local detection failed)."""
        source = {"source_type": "git", "current_version_command": ""}
        result = _sync_current_to_latest_if_applicable("", "1.9.0", source)
        assert result == "1.9.0"

    def test_git_source_with_current_version_command(self):
        """Does NOT snap for git source when current_version_command is set."""
        source = {"source_type": "git", "current_version_command": "my-cmd"}
        result = _sync_current_to_latest_if_applicable("", "3.0.0", source)
        assert result == ""

    def test_empty_latest(self):
        """Does NOT snap when latest_version is empty."""
        source = {"source_type": "npx", "current_version_command": ""}
        result = _sync_current_to_latest_if_applicable("1.0.0", "", source)
        assert result == "1.0.0"

    def test_custom_source(self):
        """Snaps for custom source without current_version_command."""
        source = {"source_type": "custom", "current_version_command": ""}
        result = _sync_current_to_latest_if_applicable("", "2.5.0", source)
        assert result == "2.5.0"


class TestCheckVersionsSyncCurrentToLatest:
    @patch("skill_manager.core.skill_packages.versioning.run_version_command")
    def test_npx_sync_on_add(self, mock_run_version):
        """sync_current_to_latest=True snaps npx current to latest."""
        source = {
            "source_type": "npx",
            "package_name": "mypkg",
            "current_version": "",
        }
        mock_run_version.return_value = "v4.0.0"

        updated = check_skill_package_versions(source, sync_current_to_latest=True)
        assert updated["latest_version"] == "4.0.0"
        assert updated["current_version"] == "4.0.0"

    @patch("skill_manager.core.skill_packages.versioning.get_git_tag")
    def test_git_source_no_sync(self, mock_get_git_tag, tmp_path):
        """sync_current_to_latest=True does NOT snap git source."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        source = {
            "source_type": "git",
            "repository_url": "https://github.com/user/repo.git",
            "clone_path": str(tmp_path),
            "current_version": "",
        }
        mock_get_git_tag.side_effect = ["v5.0.0", "v2.0.0"]

        updated = check_skill_package_versions(source, sync_current_to_latest=True)
        assert updated["latest_version"] == "5.0.0"
        assert updated["current_version"] == "2.0.0"  # local tag, not snapped

    @patch("skill_manager.core.skill_packages.versioning.run_version_command")
    def test_npx_no_sync_without_flag(self, mock_run_version):
        """Without sync_current_to_latest, current stays empty for npx."""
        source = {
            "source_type": "npx",
            "package_name": "mypkg",
            "current_version": "",
        }
        mock_run_version.return_value = "v3.0.0"

        updated = check_skill_package_versions(source, sync_current_to_latest=False)
        assert updated["latest_version"] == "3.0.0"
        assert updated.get("current_version", "") == ""  # not snapped

    @patch("skill_manager.core.skill_packages.versioning.run_version_command")
    def test_custom_with_version_commands_no_sync(self, mock_run_version):
        """sync_current_to_latest skips when current_version_command is set."""
        source = {
            "source_type": "custom",
            "current_version_command": "echo v1.0",
            "latest_version_command": "echo v2.0",
            "current_version": "",
        }
        mock_run_version.side_effect = ["v1.0", "v2.0"]

        updated = check_skill_package_versions(source, sync_current_to_latest=True)
        assert updated["current_version"] == "1.0"
        assert updated["latest_version"] == "2.0"


def test_fetch_npm_registry_version_success():
    from skill_manager.core.skill_packages.versioning import fetch_npm_registry_version

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = b'{"version": "2.4.1"}'

    with patch("urllib.request.urlopen") as mock_url:
        mock_url.return_value.__enter__.return_value = mock_resp
        ver = fetch_npm_registry_version("@scope/pkg")
        assert ver == "2.4.1"


def test_fetch_npm_registry_version_error():
    from skill_manager.core.skill_packages.versioning import fetch_npm_registry_version

    with patch("urllib.request.urlopen", side_effect=Exception("Network down")):
        ver = fetch_npm_registry_version("some-pkg")
        assert ver == ""


@patch("skill_manager.core.skill_packages.versioning.get_git_tag")
def test_check_skill_package_versions_npx_github_shorthand(mock_git_tag):
    mock_git_tag.return_value = "v1.5.0"
    source = {
        "source_type": "npx",
        "package_name": "sickn33/agentic-awesome-skills",
        "current_version": "",
    }

    updated = check_skill_package_versions(source, sync_current_to_latest=True)
    assert updated["latest_version"] == "1.5.0"
    assert updated["current_version"] == "1.5.0"
    mock_git_tag.assert_called_with(
        "https://github.com/sickn33/agentic-awesome-skills", is_remote=True, token=""
    )


class TestPostUpdatePromotion:
    """Post-update reconciliation: a successful update leaves an npx/custom
    package AT latest, but those sources cannot observe their installed
    version, so current must be promoted or the Update button never clears."""

    def _find_skills_source(self):
        return {
            "source_type": "npx",
            "name": "Find Skills",
            "package_name": "skills",
            "package_args": "add vercel-labs/skills --all -y",
            "repository_url": "https://github.com/vercel-labs/skills",
            "update_command": "npx --yes -- skills add vercel-labs/skills --all -y",
            "current_version": "1.5.23",
            "latest_version": "1.5.24",
        }

    @patch("skill_manager.core.skill_packages.versioning.run_version_command")
    @patch("skill_manager.core.skill_packages.versioning.get_git_tag")
    def test_npx_post_update_promotes_stale_current(self, mock_git_tag, mock_run_version):
        mock_git_tag.return_value = "v1.5.24"
        mock_run_version.return_value = "1.5.24"

        updated = check_skill_package_versions(
            self._find_skills_source(),
            force_refresh=True,
            promote_current_to_latest=True,
        )
        assert updated["latest_version"] == "1.5.24"
        assert updated["current_version"] == "1.5.24"

    @patch("skill_manager.core.skill_packages.versioning.run_version_command")
    @patch("skill_manager.core.skill_packages.versioning.get_git_tag")
    def test_promote_skipped_without_flag_keeps_scan_semantics(
        self, mock_git_tag, mock_run_version
    ):
        mock_git_tag.return_value = "v1.5.24"
        mock_run_version.return_value = "1.5.24"

        updated = check_skill_package_versions(self._find_skills_source(), force_refresh=True)
        assert updated["latest_version"] == "1.5.24"
        assert updated["current_version"] == "1.5.23"

    @patch("skill_manager.core.skill_packages.versioning.run_version_command")
    def test_promote_respects_explicit_current_version_command(self, mock_run_version):
        mock_run_version.side_effect = ["v1.0.0", "v2.0.0"]
        source = {
            "source_type": "custom",
            "current_version_command": "echo v1.0.0",
            "latest_version_command": "echo v2.0.0",
            "current_version": "1.0.0",
            "latest_version": "2.0.0",
        }

        updated = check_skill_package_versions(
            source, force_refresh=True, promote_current_to_latest=True
        )
        assert updated["current_version"] == "1.0.0"
        assert updated["latest_version"] == "2.0.0"

    @patch("skill_manager.core.skill_packages.versioning.get_git_tag")
    def test_promote_skips_git_with_local_detection(self, mock_git_tag, tmp_path):
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        mock_git_tag.side_effect = ["v2.0.0", "v1.5.0", "v2.0.0"]

        source = {
            "source_type": "git",
            "repository_url": "https://github.com/user/repo.git",
            "clone_path": str(tmp_path),
            "current_version": "1.0.0",
            "latest_version": "1.5.0",
        }

        updated = check_skill_package_versions(
            source, force_refresh=True, promote_current_to_latest=True
        )
        assert updated["current_version"] == "1.5.0"
        assert updated["latest_version"] == "2.0.0"


class TestNpxLatestPrecedence:
    """A bare commit hash from the git HEAD fallback must never clobber an
    npm-derived semver latest, and plain npm names must reach the registry."""

    @patch("skill_manager.core.skill_packages.versioning.run_version_command")
    @patch("skill_manager.core.skill_packages.versioning.get_git_tag")
    def test_commit_hash_never_overwrites_npm_version(self, mock_git_tag, mock_run_version):
        mock_run_version.return_value = "1.5.24"
        mock_git_tag.return_value = "abc1234"
        source = {
            "source_type": "npx",
            "name": "Find Skills",
            "package_name": "skills",
            "repository_url": "https://github.com/vercel-labs/skills",
            "current_version": "1.5.23",
            "latest_version": "",
        }

        updated = check_skill_package_versions(source, force_refresh=True)
        assert updated["latest_version"] == "1.5.24"
        assert updated["current_version"] == "1.5.23"

    @patch("skill_manager.core.skill_packages.versioning.run_version_command")
    @patch("skill_manager.core.skill_packages.versioning.fetch_npm_registry_version")
    @patch("skill_manager.core.skill_packages.versioning.get_git_tag")
    def test_hash_accepted_as_last_resort_for_untagged_repo(
        self, mock_git_tag, mock_fetch, mock_run_version
    ):
        mock_git_tag.return_value = "abc1234"
        mock_fetch.return_value = ""
        mock_run_version.return_value = ""
        source = {
            "source_type": "npx",
            "package_name": "owner/repo",
            "current_version": "",
            "latest_version": "",
        }

        updated = check_skill_package_versions(source, sync_current_to_latest=True)
        assert updated["latest_version"] == "abc1234"
        assert updated["current_version"] == "abc1234"

    @patch("skill_manager.core.skill_packages.versioning.run_version_command")
    @patch("skill_manager.core.skill_packages.versioning.fetch_npm_registry_version")
    @patch("skill_manager.core.skill_packages.versioning.get_git_tag")
    def test_plain_npm_name_reaches_registry(self, mock_git_tag, mock_fetch, mock_run_version):
        mock_git_tag.return_value = ""
        mock_fetch.return_value = "9.9.9"
        mock_run_version.return_value = ""
        source = {
            "source_type": "npx",
            "package_name": "some-plain-pkg",
            "current_version": "",
            "latest_version": "",
        }

        updated = check_skill_package_versions(source)
        assert updated["latest_version"] == "9.9.9"
        mock_fetch.assert_called_once()

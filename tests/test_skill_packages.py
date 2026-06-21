import subprocess
from unittest.mock import MagicMock, patch

import pytest

from skill_manager.core.skill_packages.config import (
    detect_command_type,
    detect_package_config,
    normalize_skill_package_config,
    parse_npx_command,
    split_args,
)
from skill_manager.core.skill_packages.process import (
    resolve_process_command,
    run_process as _run_process,
    sanitize_token,
)
from skill_manager.core.skill_packages.relocator import (
    merge_and_move_lockfile,
    relocate_packages as _relocate_packages,
    relocate_path_internal,
)
from skill_manager.core.skill_packages.updater import (
    intercept_cross_platform_command,
    run_git_package_update,
    run_npx_update,
    run_skill_package_update,
)
from skill_manager.core.skill_packages.versioning import (
    detect_git_remote,
    get_git_tag,
)


@pytest.fixture
def mock_run():
    with patch("subprocess.run") as mock:
        yield mock


def test_normalize_skill_package_config():
    data = {"package_name": "test-package"}
    normalized = normalize_skill_package_config(data)
    assert normalized["name"] == "test-package"
    assert normalized["source_type"] == "npx"
    assert normalized["package_id"].startswith("pkg_")
    assert "npx --yes -- test-package" in normalized["update_command"]


def test_normalize_skill_package_config_preserves_package_id():
    normalized = normalize_skill_package_config(
        {"package_name": "test-package", "package_id": "pkg_existing"}
    )
    assert normalized["package_id"] == "pkg_existing"


def test_sanitize_token_masks_auth_urls_and_ignores_non_string():
    assert (
        sanitize_token("https://secret@example.com/repo.git") == "https://***@example.com/repo.git"
    )
    assert sanitize_token(None) is None


def test_detect_package_config_npx():
    data = {"package_name": "npx --yes my-pkg --foo"}
    detected = detect_package_config(data)
    assert detected["source_type"] == "npx"
    assert detected["package_name"] == "my-pkg"
    assert detected["package_args"] == "--foo"


def test_detect_package_config_git():
    data = {"source_type": "git", "repository_url": "http://git.com/repo"}
    detected = detect_package_config(data)
    assert detected["source_type"] == "git"


def test_relocate_packages(temp_dir):
    project_path = temp_dir / "project_skills"
    project_path.mkdir()

    source_dir = temp_dir / "some_repo"
    skills_dir = source_dir / "skills"
    skills_dir.mkdir(parents=True)

    skill_caveman = skills_dir / "caveman"
    skill_caveman.mkdir()
    (skill_caveman / "SKILL.md").write_text("content")

    skill_invalid = skills_dir / "invalid"
    skill_invalid.mkdir()

    _relocate_packages(str(source_dir), str(project_path), None)

    # Check if it moved
    assert (project_path / "caveman").is_dir()
    assert (project_path / "caveman" / "SKILL.md").exists()
    assert not (project_path / "invalid").exists()


def test_relocate_packages_from_output_agents_subfolder(temp_dir):
    from skill_manager.core.skill_packages.relocator import relocate_packages_from_output

    project_path = temp_dir / "project_skills"
    project_path.mkdir()

    source_dir = temp_dir / "staging_area"
    agents_skills_dir = source_dir / ".agents" / "skills"
    agents_skills_dir.mkdir(parents=True)

    skill_awesome = agents_skills_dir / "awesome"
    skill_awesome.mkdir()
    (skill_awesome / "SKILL.md").write_text("content")

    skill_invalid = agents_skills_dir / "invalid"
    skill_invalid.mkdir()

    captured_output = ["Some random npx output", f"Installed to {agents_skills_dir}", "done"]

    managed = relocate_packages_from_output(captured_output, str(project_path), None)

    assert managed == ["awesome"]
    assert (project_path / "awesome").is_dir()
    assert (project_path / "awesome" / "SKILL.md").exists()
    assert not (project_path / "invalid").exists()
    assert not (project_path / ".agents").exists()
    assert not (project_path / "skills").exists()


def test_relocate_packages_no_dest_or_no_source(temp_dir):
    messages = []
    assert _relocate_packages(str(temp_dir), "", messages.append) is None

    messages.clear()
    assert _relocate_packages("non_existent_path", str(temp_dir), messages.append) is None


@patch("skill_manager.core.skill_packages.updater.run_process")
@patch("skill_manager.core.skill_packages.updater.relocate_packages_from_output")
@patch("skill_manager.core.skill_packages.updater.check_skill_package_versions")
def test_run_skill_package_update_with_relocation(
    mock_check, mock_relocate_from_output, mock_run, temp_dir
):
    package_path = temp_dir / "skills_dest"
    package_path.mkdir()
    (package_path / "old-skill").mkdir()

    source = {
        "name": "test",
        "package_path": str(package_path),
        "update_command": "python -c \"print('ok')\"",
        "managed_folders": ["old-skill"],
    }

    # Mock relocation to return a NEW list of managed folders
    mock_relocate_from_output.return_value = ["new-skill"]
    mock_check.return_value = {"current_version": "2.0.0"}

    updated = run_skill_package_update(source)

    # Should have deleted old-skill
    assert not (package_path / "old-skill").exists()
    assert updated["managed_folders"] == ["new-skill"]
    assert updated["removed_folders"] == ["old-skill"]
    assert updated["current_version"] == "2.0.0"
    assert mock_run.call_args.kwargs["cwd"]


@patch("skill_manager.core.skill_packages.updater.run_process")
@patch("skill_manager.core.skill_packages.updater.relocate_packages_from_output")
@patch("skill_manager.core.skill_packages.updater.check_skill_package_versions")
def test_run_skill_package_update_with_npx_relocation(
    mock_check, mock_relocate_from_output, mock_run, temp_dir
):
    package_path = temp_dir / "skills_dest"
    package_path.mkdir()

    source = {
        "name": "test-npx",
        "source_type": "npx",
        "package_name": "some-npx-pkg",
        "package_path": str(package_path),
        "managed_folders": [],
    }

    mock_relocate_from_output.return_value = ["new-npx-skill"]
    mock_check.return_value = {"current_version": "3.0.0"}

    updated = run_skill_package_update(source)

    assert mock_relocate_from_output.called
    assert updated["managed_folders"] == ["new-npx-skill"]
    assert mock_run.call_args.kwargs["cwd"]
    assert (
        mock_relocate_from_output.call_args.kwargs["base_path"] == mock_run.call_args.kwargs["cwd"]
    )


@patch("skill_manager.core.skill_packages.versioning.cmd.Git")
def test_get_git_tag_remote(mock_git_class, mock_run):
    mock_git = mock_git_class.return_value
    mock_git.execute.return_value = "hash123\trefs/tags/v1.2.3\n"

    tag = get_git_tag("https://github.com/repo.git", is_remote=True)
    assert tag == "v1.2.3"


@patch("skill_manager.core.skill_packages.versioning.Repo")
def test_get_git_tag_local(mock_repo_class, temp_dir):
    git_dir = temp_dir / ".git"
    git_dir.mkdir()

    mock_repo = mock_repo_class.return_value
    mock_tag = MagicMock()
    mock_tag.name = "v2.0.0"
    mock_repo.tags = [mock_tag]

    tag = get_git_tag(str(temp_dir), is_remote=False)
    assert tag == "v2.0.0"


@patch("skill_manager.core.skill_packages.updater.cmd.Git")
def testrun_git_package_update_clone(mock_git_class, temp_dir):
    clone_path = temp_dir / "repo"
    source = {
        "repository_url": "https://github.com/repo.git",
        "clone_path": str(clone_path),
        "package_path": str(clone_path),
    }

    mock_git = mock_git_class.return_value
    run_git_package_update(source, None)

    # Should call clone since path is empty/doesn't exist
    mock_git.execute.assert_called()
    assert "clone" in mock_git.execute.call_args[0][0]


@patch("skill_manager.core.skill_packages.updater.run_process")
def testrun_npx_update(mock_run):
    source = {"package_name": "my-pkg", "package_args": "--dev"}
    run_npx_update(source, None)

    mock_run.assert_called_once()
    assert mock_run.call_args[0][0] == ["npx", "--yes", "--", "my-pkg", "--dev"]


@patch("shutil.which")
@patch("subprocess.Popen")
def test_run_process_error(mock_popen, mock_which):
    mock_which.return_value = "/bin/test"
    mock_proc = MagicMock()
    mock_proc.stdout = []
    mock_proc.returncode = 1
    mock_popen.return_value = mock_proc

    with pytest.raises(subprocess.CalledProcessError):
        _run_process(["test"], None)


def testresolve_process_command_not_found():
    with patch("shutil.which") as mock_which:
        mock_which.return_value = None
        with pytest.raises(FileNotFoundError):
            resolve_process_command(["no-such-exec"])


def test_detect_package_config_auto_npx():
    # update_command starting with npx should be auto-detected as npx
    source = {"update_command": "npx --yes my-pkg"}
    detected = detect_package_config(source)
    assert detected["source_type"] == "npx"
    assert detected["package_name"] == "my-pkg"


def test_detect_package_config_custom_and_verify_command(temp_dir):
    detected = detect_package_config(
        {
            "update_command": "python install.py",
            "package_path": str(temp_dir),
        }
    )
    assert detected["source_type"] == "custom"
    assert "test -d" in detected["verify_command"]


def test_parse_npx_and_apply_package_args():
    assert parse_npx_command("npx --yes package-name --foo") == ("package-name", "--foo")
    assert parse_npx_command("python script.py") == ("", "")

    detected = detect_package_config({"source_type": "npx", "package_name": "npx --yes pkg --dev"})
    assert detected["package_name"] == "pkg"
    assert detected["package_args"] == "--dev"


def test_relocate_lock_files(temp_dir):
    project_path = temp_dir / "project_skills"
    project_path.mkdir()

    source_root = temp_dir / "source_repo"
    source_root.mkdir()
    (source_root / ".skill-lock.json").write_text("{}")

    skills_dir = source_root / "skills"
    skills_dir.mkdir()
    skill1 = skills_dir / "skill1"
    skill1.mkdir()
    (skill1 / "SKILL.md").write_text("content")

    _relocate_packages(str(source_root), str(project_path), None, package_name_prefix="test-repo")

    # Should move the lock file to project root (project_path.parent) with prefix
    assert (project_path.parent / ".test-repo-skill-lock.json").exists()


def testmerge_and_move_lockfile_merges_existing_json(tmp_path):
    source_lock = tmp_path / "source" / ".skill-lock.json"
    dest_lock = tmp_path / "dest" / ".skill-lock.json"
    source_lock.parent.mkdir()
    dest_lock.parent.mkdir()
    source_lock.write_text('{"version": "2", "skills": {"a": 1}}')
    dest_lock.write_text('{"skills": {"b": 2}}')
    messages = []

    merge_and_move_lockfile(source_lock, dest_lock, messages.append)

    merged = dest_lock.read_text()
    assert '"a": 1' in merged
    assert '"b": 2' in merged
    assert '"version": "2"' in merged


def testrelocate_path_internal_cleanup(temp_dir):
    dest_base = temp_dir / "dest"
    dest_base.mkdir()

    # Existing directory in destination
    src = temp_dir / "src"
    src.mkdir()
    (dest_base / "src").mkdir()
    (dest_base / "src" / "old.txt").write_text("old")

    relocate_path_internal(src, dest_base, None)
    assert (dest_base / "src").is_dir()
    assert not (dest_base / "src" / "old.txt").exists()

    # Existing file in destination
    src2 = temp_dir / "src2"
    src2.mkdir()
    (dest_base / "src2").write_text("blocking file")

    relocate_path_internal(src2, dest_base, None)
    assert (dest_base / "src2").is_dir()


def testsplit_args():
    assert split_args("  a   b  c  ") == ["a", "b", "c"]
    assert split_args(None) == []


def test_intercept_cross_platform_success(temp_dir):
    # test -d should succeed for existing dir
    assert intercept_cross_platform_command(f"test -d {temp_dir}", None)


def test_intercept_cross_platform_quoted_path_with_apostrophe(temp_dir):
    # Create a directory with an apostrophe in its name
    dir_with_apostrophe = temp_dir / "a'b"
    dir_with_apostrophe.mkdir()

    import shlex

    quoted_path = shlex.quote(str(dir_with_apostrophe))

    messages = []
    # This should succeed without raising a Verification failed exception
    assert intercept_cross_platform_command(
        f'test -d {quoted_path} && echo "Skills installed in "{quoted_path}', messages.append
    )
    assert messages[-1] == f"Skills installed in {dir_with_apostrophe}"


def test_intercept_cross_platform_echo_and_tilde_typo(temp_dir, monkeypatch):
    home = temp_dir / "home"
    target = home / ".agents"
    target.mkdir(parents=True)
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.setenv("HOME", str(home))
    messages = []

    assert intercept_cross_platform_command('test -d "~.agents" && echo "ok"', messages.append)
    assert messages[-1] == "ok"


def test_intercept_cross_platform_unsupported_test_command():
    assert intercept_cross_platform_command("test -f file.txt", None) is False


def test_intercept_cross_platform_fail():
    with pytest.raises(RuntimeError):
        intercept_cross_platform_command("test -d /non_existent_dir_random_path_123", None)


def test_intercept_cross_platform_invalid():
    # Command not starting with test
    assert intercept_cross_platform_command("echo hi", None) is False


@patch("subprocess.run")
def test_detect_git_remote_failures(mock_run, temp_dir):
    # Not a directory
    assert detect_git_remote("/non/existent") == ""

    # Not a git repo
    empty_dir = temp_dir / "empty"
    empty_dir.mkdir()
    assert detect_git_remote(str(empty_dir)) == ""

    # Subprocess error
    git_dir = temp_dir / "git-fail"
    git_dir.mkdir()
    (git_dir / ".git").mkdir()
    mock_run.side_effect = subprocess.SubprocessError()
    assert detect_git_remote(str(git_dir)) == ""


def test_fallback_package_name():
    # Git URL fallback
    assert (
        normalize_skill_package_config({"repository_url": "https://github.com/user/my-repo.git"})[
            "name"
        ]
        == "my-repo"
    )
    # Package path fallback
    assert (
        normalize_skill_package_config({"package_path": "/home/user/skills-dir"})["name"]
        == "skills-dir"
    )
    # Default
    assert normalize_skill_package_config({})["name"] == "Unnamed Package"


@patch("skill_manager.core.skill_packages.versioning.cmd.Git")
def test_get_git_tag_remote_falls_back_to_head(mock_git_class, mock_run):
    mock_git = mock_git_class.return_value
    # First call (tags) returns empty, second call (HEAD) returns hash
    mock_git.execute.side_effect = ["", "abcdef123456\tHEAD\n"]

    assert get_git_tag("https://github.com/repo.git", is_remote=True, token="secret") == "abcdef1"


@patch("skill_manager.core.skill_packages.versioning.Repo")
def test_get_git_tag_local_falls_back_to_hash(mock_repo_class, temp_dir):
    git_dir = temp_dir / ".git"
    git_dir.mkdir()

    mock_repo = mock_repo_class.return_value
    mock_repo.tags = []
    mock_repo.head.commit.hexsha = "1234567890"

    assert get_git_tag(str(temp_dir), is_remote=False) == "1234567"


@patch("skill_manager.core.skill_packages.updater.Repo")
def testrun_git_package_update_pull(mock_repo_class, temp_dir):
    clone_path = temp_dir / "existing-repo"
    clone_path.mkdir()
    (clone_path / ".git").mkdir()

    source = {
        "repository_url": "https://github.com/repo.git",
        "clone_path": str(clone_path),
        "package_path": str(clone_path),
    }

    mock_repo = mock_repo_class.return_value
    run_git_package_update(source, None)

    # Should call execute on repo.git
    mock_repo.git.execute.assert_called()
    args = mock_repo.git.execute.call_args[0][0]
    assert "pull" in args
    assert "--ff-only" in args


@patch("skill_manager.core.skill_packages.updater.Repo")
def testrun_git_package_update_conflict_and_network_failures(mock_repo_class, temp_dir):
    clone_path = temp_dir / "existing-repo"
    clone_path.mkdir()
    (clone_path / ".git").mkdir()

    source = {
        "repository_url": "https://github.com/repo.git",
        "clone_path": str(clone_path),
        "package_path": str(clone_path),
    }

    mock_repo = mock_repo_class.return_value
    mock_repo.git.execute.side_effect = RuntimeError("Conflict or network error")
    with pytest.raises(RuntimeError):
        run_git_package_update(source, None)

    new_clone_path = temp_dir / "new-repo"
    source_new = {
        "repository_url": "https://github.com/repo.git",
        "clone_path": str(new_clone_path),
        "package_path": str(new_clone_path),
    }
    with patch("skill_manager.core.skill_packages.updater.cmd.Git") as mock_git_class:
        mock_git = mock_git_class.return_value
        mock_git.execute.side_effect = RuntimeError("Could not resolve host")
        with pytest.raises(RuntimeError):
            run_git_package_update(source_new, None)


def test_run_process_timeout_handling():
    with (
        patch(
            "skill_manager.core.skill_packages.process.resolve_process_command",
            return_value=["some-cmd"],
        ),
        patch("subprocess.Popen") as mock_popen,
    ):
        mock_popen.side_effect = subprocess.SubprocessError("Process failed to start")
        with pytest.raises(subprocess.SubprocessError):
            _run_process(["some-cmd"], None)


def testdetect_command_type_edge_cases():
    assert detect_command_type("npx --yes my-pkg") == "npx"
    assert detect_command_type("git clone ...") == "custom"
    assert detect_command_type("copy file ...") == "custom"


@patch("shutil.which")
def test_run_process_missing_executable(mock_which):
    mock_which.return_value = None
    with pytest.raises(FileNotFoundError) as exc:
        _run_process(["non-existent-cmd"], None)
    assert "not found" in str(exc.value)


@patch("subprocess.Popen")
def test_run_process_timeout(mock_popen):
    mock_proc = MagicMock()
    mock_proc.poll.return_value = None
    mock_proc.communicate.return_value = (b"", b"")
    mock_popen.return_value = mock_proc

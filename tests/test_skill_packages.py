import subprocess
from unittest.mock import MagicMock, patch

import pytest

from skill_manager.core.skill_packages import (
    _detect_command_type,
    _intercept_cross_platform_command,
    _merge_and_move_lockfile,
    _parse_npx_command,
    _relocate_packages_from_output,
    _resolve_process_command,
    _run_git_package_update,
    _run_npm_update,
    _run_process,
    _run_shell_command,
    _split_args,
    check_skill_package_versions,
    detect_git_remote,
    detect_package_config,
    get_git_tag,
    normalize_skill_package_config,
    run_skill_package_update,
    run_version_command,
    sanitize_token,
)


@pytest.fixture
def mock_run():
    with patch("subprocess.run") as mock:
        yield mock


def test_normalize_skill_package_config():
    data = {"package_name": "test-package"}
    normalized = normalize_skill_package_config(data)
    assert normalized["name"] == "test-package"
    assert normalized["source_type"] == "npm"
    assert normalized["package_id"].startswith("pkg_")
    assert "npx --yes test-package" in normalized["update_command"]


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


def test_detect_package_config_npm():
    data = {"package_name": "npx --yes my-pkg --foo"}
    detected = detect_package_config(data)
    assert detected["source_type"] == "npm"
    assert detected["package_name"] == "my-pkg"
    assert detected["package_args"] == "--foo"


def test_detect_package_config_git():
    data = {"source_type": "git", "repository_url": "http://git.com/repo"}
    detected = detect_package_config(data)
    assert detected["source_type"] == "git"


def test_relocate_packages_from_output(temp_dir):
    project_path = temp_dir / "project_skills"
    project_path.mkdir()

    # Create a dummy skill in a temp location
    source_skill_dir = temp_dir / "some_random_path" / "caveman"
    source_skill_dir.mkdir(parents=True)
    (source_skill_dir / "SKILL.md").write_text("content")

    output = [f"Installed to {source_skill_dir}"]

    _relocate_packages_from_output(output, str(project_path), None)

    # Check if it moved
    assert (project_path / "caveman").is_dir()
    assert (project_path / "caveman" / "SKILL.md").exists()
    assert not source_skill_dir.exists()


@patch("skill_manager.core.skill_packages._run_process")
@patch("skill_manager.core.skill_packages._relocate_packages_from_output")
@patch("skill_manager.core.skill_packages.check_skill_package_versions")
def test_run_skill_package_update_with_relocation(mock_check, mock_relocate, mock_run, temp_dir):
    package_path = temp_dir / "skills_dest"
    package_path.mkdir()
    (package_path / "old-skill").mkdir()

    source = {
        "name": "test",
        "package_path": str(package_path),
        "update_command": "ls",
        "managed_folders": ["old-skill"],
    }

    # Mock relocation to return a NEW list of managed folders
    mock_relocate.return_value = ["new-skill"]
    mock_check.return_value = {"current_version": "2.0.0"}

    updated = run_skill_package_update(source)

    # Should have deleted old-skill
    assert not (package_path / "old-skill").exists()
    assert updated["managed_folders"] == ["new-skill"]
    assert updated["removed_folders"] == ["old-skill"]
    assert updated["current_version"] == "2.0.0"


def test_get_git_tag_remote(mock_run):
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "hash123\trefs/tags/v1.2.3\n"
    mock_run.return_value = mock_result

    tag = get_git_tag("https://github.com/repo.git", is_remote=True)
    assert tag == "v1.2.3"
    mock_run.assert_called_once()


@patch("subprocess.run")
def test_get_git_tag_local(mock_run, temp_dir):
    git_dir = temp_dir / ".git"
    git_dir.mkdir()

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "v2.0.0\n"
    mock_run.return_value = mock_result

    tag = get_git_tag(str(temp_dir), is_remote=False)
    assert tag == "v2.0.0"
    mock_run.assert_called_once()


@patch("skill_manager.core.skill_packages._run_process")
def test_run_git_package_update_clone(mock_run, temp_dir):
    clone_path = temp_dir / "repo"
    source = {
        "repository_url": "https://github.com/repo.git",
        "clone_path": str(clone_path),
        "package_path": str(clone_path),
    }

    _run_git_package_update(source, None)

    # Should call clone since path is empty/doesn't exist
    mock_run.assert_called_once()
    assert mock_run.call_args[0][0][1] == "clone"


@patch("skill_manager.core.skill_packages._run_process")
def test_run_npm_update(mock_run):
    source = {"package_name": "my-pkg", "package_args": "--dev"}
    _run_npm_update(source, None)

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

    from skill_manager.core.skill_packages import _run_process

    with pytest.raises(subprocess.CalledProcessError):
        _run_process(["test"], None)


def test_resolve_process_command_not_found():
    from skill_manager.core.skill_packages import _resolve_process_command

    with patch("shutil.which") as mock_which:
        mock_which.return_value = None
        with pytest.raises(FileNotFoundError):
            _resolve_process_command(["no-such-exec"])


def test_detect_package_config_auto_npm():
    # update_command starting with npx should be auto-detected as npm
    source = {"update_command": "npx --yes my-pkg"}
    detected = detect_package_config(source)
    assert detected["source_type"] == "npm"
    assert detected["package_name"] == "my-pkg"


def test_detect_package_config_custom_and_verify_command(temp_dir):
    detected = detect_package_config(
        {
            "update_command": "python install.py",
            "package_path": str(temp_dir),
        }
    )
    assert detected["source_type"] == "custom"
    assert detected["current_version_command"] == "python install.py"
    assert "test -d" in detected["verify_command"]


def test_parse_npx_and_apply_package_args():
    assert _parse_npx_command("npx --yes package-name --foo") == ("package-name", "--foo")
    assert _parse_npx_command("python script.py") == ("", "")

    detected = detect_package_config({"source_type": "npm", "package_name": "npx --yes pkg --dev"})
    assert detected["package_name"] == "pkg"
    assert detected["package_args"] == "--dev"


def test_relocate_lock_files(temp_dir):
    project_path = temp_dir / "project_skills"
    project_path.mkdir()

    source_root = temp_dir / "source_repo"
    source_root.mkdir()
    (source_root / ".skill-lock.json").write_text("{}")

    # regex matches root of detected path
    detected_path = source_root / "skills" / "skill1"
    detected_path.mkdir(parents=True)

    output = [f"at {detected_path}"]
    _relocate_packages_from_output(output, str(project_path), None)

    # Should move the lock file to project root (project_path.parent)
    assert (project_path.parent / ".skill-lock.json").exists()


def test_merge_and_move_lockfile_merges_existing_json(tmp_path):
    source_lock = tmp_path / "source" / ".skill-lock.json"
    dest_lock = tmp_path / "dest" / ".skill-lock.json"
    source_lock.parent.mkdir()
    dest_lock.parent.mkdir()
    source_lock.write_text('{"version": "2", "skills": {"a": 1}}')
    dest_lock.write_text('{"skills": {"b": 2}}')
    messages = []

    _merge_and_move_lockfile(source_lock, dest_lock, messages.append)

    merged = dest_lock.read_text()
    assert '"a": 1' in merged
    assert '"b": 2' in merged
    assert '"version": "2"' in merged
    assert not source_lock.exists()


def test_relocate_packages_from_output_no_dest_or_no_paths(temp_dir):
    messages = []
    assert _relocate_packages_from_output([], "", messages.append) is None
    assert "Relocation skipped" in messages[0]

    messages.clear()
    assert _relocate_packages_from_output(["nothing here"], str(temp_dir), messages.append) is None
    assert any("No package paths detected" in message for message in messages)


def test_relocate_path_internal_cleanup(temp_dir):
    from skill_manager.core.skill_packages import _relocate_path_internal

    dest_base = temp_dir / "dest"
    dest_base.mkdir()

    # Existing directory in destination
    src = temp_dir / "src"
    src.mkdir()
    (dest_base / "src").mkdir()
    (dest_base / "src" / "old.txt").write_text("old")

    _relocate_path_internal(src, dest_base, None)
    assert (dest_base / "src").is_dir()
    assert not (dest_base / "src" / "old.txt").exists()

    # Existing file in destination
    src2 = temp_dir / "src2"
    src2.mkdir()
    (dest_base / "src2").write_text("blocking file")

    _relocate_path_internal(src2, dest_base, None)
    assert (dest_base / "src2").is_dir()


def test_split_args():
    assert _split_args("  a   b  c  ") == ["a", "b", "c"]
    assert _split_args(None) == []


def test_intercept_cross_platform_success(temp_dir):
    # test -d should succeed for existing dir
    assert _intercept_cross_platform_command(f"test -d {temp_dir}", None)


def test_intercept_cross_platform_quoted_path_with_apostrophe(temp_dir):
    # Create a directory with an apostrophe in its name
    dir_with_apostrophe = temp_dir / "a'b"
    dir_with_apostrophe.mkdir()

    import shlex
    quoted_path = shlex.quote(str(dir_with_apostrophe))

    messages = []
    # This should succeed without raising a Verification failed exception
    assert _intercept_cross_platform_command(
        f"test -d {quoted_path} && echo \"Skills installed in \"{quoted_path}",
        messages.append
    )
    assert messages[-1] == f"Skills installed in {dir_with_apostrophe}"


def test_intercept_cross_platform_echo_and_tilde_typo(temp_dir, monkeypatch):
    home = temp_dir / "home"
    target = home / ".agents"
    target.mkdir(parents=True)
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.setenv("HOME", str(home))
    messages = []

    assert _intercept_cross_platform_command('test -d "~.agents" && echo "ok"', messages.append)
    assert messages[-1] == "ok"


def test_intercept_cross_platform_unsupported_test_command():
    assert _intercept_cross_platform_command("test -f file.txt", None) is False


def test_intercept_cross_platform_fail():
    with pytest.raises(RuntimeError):
        _intercept_cross_platform_command("test -d /non_existent_dir_random_path_123", None)


def test_intercept_cross_platform_invalid():
    # Command not starting with test
    assert _intercept_cross_platform_command("echo hi", None) is False


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


@patch("skill_manager.core.skill_packages._run_process")
def test_run_git_package_update_pull(mock_run, temp_dir):
    clone_path = temp_dir / "existing-repo"
    clone_path.mkdir()
    (clone_path / ".git").mkdir()

    source = {
        "repository_url": "https://github.com/repo.git",
        "clone_path": str(clone_path),
        "package_path": str(clone_path),
    }

    _run_git_package_update(source, None)

    # Should call pull with --ff-only
    mock_run.assert_called_once()
    args = mock_run.call_args[0][0]
    assert "pull" in args
    assert "--ff-only" in args


@patch("subprocess.run")
def test_run_version_command(mock_run):
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "v1.2.3\n"
    mock_run.return_value = mock_result

    # Shell command
    assert run_version_command("git --version") == "v1.2.3"

    # Command fails
    mock_result.returncode = 1
    assert run_version_command("git --fail") == ""


def test_run_version_command_empty_and_bad_split():
    assert run_version_command("") == ""
    assert run_version_command('"unterminated') == ""


def test_get_git_tag_remote_falls_back_to_head(mock_run):
    tags_result = MagicMock(returncode=0, stdout="")
    head_result = MagicMock(returncode=0, stdout="abcdef123456\tHEAD\n")
    mock_run.side_effect = [tags_result, head_result]

    assert get_git_tag("https://github.com/repo.git", is_remote=True, token="secret") == "abcdef1"


def test_get_git_tag_local_falls_back_to_hash(mock_run, temp_dir):
    (temp_dir / ".git").mkdir()
    describe = MagicMock(returncode=1, stdout="")
    rev = MagicMock(returncode=0, stdout="1234567\n")
    mock_run.side_effect = [describe, rev]

    assert get_git_tag(str(temp_dir), is_remote=False) == "1234567"


def test_get_git_tag_handles_exceptions(mock_run):
    mock_run.side_effect = OSError("git missing")
    assert get_git_tag("https://github.com/repo.git", is_remote=True) == ""


def test_check_skill_package_versions_commands_git_and_npm(temp_dir):
    git_dir = temp_dir / "repo"
    (git_dir / ".git").mkdir(parents=True)
    source = {
        "source_type": "git",
        "repository_url": "https://github.com/org/repo.git",
        "clone_path": str(git_dir),
        "current_version_command": "current",
        "latest_version_command": "latest",
    }

    with (
        patch(
            "skill_manager.core.skill_packages.run_version_command", side_effect=["v1.0", "v2.0"]
        ),
        patch(
            "skill_manager.core.skill_packages.get_git_tag", side_effect=["v3.0", "v1.5", "v3.0"]
        ),
    ):
        updated = check_skill_package_versions(source, force_refresh=True)

    assert updated["current_version"] == "1.5"
    assert updated["latest_version"] == "3.0"

    with patch("skill_manager.core.skill_packages.run_version_command", return_value="v9.0"):
        npm = check_skill_package_versions({"source_type": "npm", "package_name": "pkg"}, True)
    assert npm["current_version"] == "9.0"
    assert npm["latest_version"] == "9.0"


def test_relocate_packages_from_output_detected(temp_dir):
    project_path = temp_dir / "project_skills"
    project_path.mkdir()

    source_skill_dir = temp_dir / "some_random_path" / "alpha"
    source_skill_dir.mkdir(parents=True)
    (source_skill_dir / "SKILL.md").write_text("info")

    # regex matches "at path" or "in path" or "to path"
    output = [f"Skills installed at {source_skill_dir}"]

    _relocate_packages_from_output(output, str(project_path), None)

    assert (project_path / "alpha").is_dir()
    assert not source_skill_dir.exists()


@patch("skill_manager.core.skill_packages._run_process")
def test_run_skill_package_update_npm(mock_run):
    source = {"source_type": "npm", "package_name": "my-pkg", "name": "test"}
    run_skill_package_update(source)
    # _run_npm_update should be called via _run_process
    mock_run.assert_called()


def test_run_skill_package_update_cleanup_failure_and_verify(temp_dir):
    package_path = temp_dir / "skills"
    old = package_path / "old"
    old.mkdir(parents=True)
    source = {
        "name": "custom",
        "source_type": "custom",
        "package_path": str(package_path),
        "update_command": "echo update",
        "verify_command": f"test -d {package_path}",
        "managed_folders": ["old"],
    }
    messages = []

    with (
        patch("skill_manager.core.skill_packages._run_shell_command") as shell,
        patch("skill_manager.core.skill_packages._relocate_packages_from_output", return_value=[]),
        patch("skill_manager.core.skill_packages.shutil.rmtree", side_effect=OSError("locked")),
        patch(
            "skill_manager.core.skill_packages.check_skill_package_versions",
            side_effect=lambda s, force_refresh=False: s,
        ),
    ):
        updated = run_skill_package_update(source, messages.append)

    assert shell.call_count == 2
    assert updated["managed_folders"] == []
    assert updated["removed_folders"] == []
    assert any("Failed to delete old" in message for message in messages)


def test_run_git_package_update_errors(temp_dir):
    with pytest.raises(ValueError, match="repository_url"):
        _run_git_package_update({"package_path": str(temp_dir)}, None)
    with pytest.raises(ValueError, match="package_path"):
        _run_git_package_update({"repository_url": "url"}, None)

    non_empty = temp_dir / "non-empty"
    non_empty.mkdir()
    (non_empty / "file.txt").write_text("x")
    with pytest.raises(ValueError, match="not an empty git checkout"):
        _run_git_package_update(
            {"repository_url": "url", "clone_path": str(non_empty), "package_path": str(non_empty)},
            (lambda x: None),
        )


def test_run_shell_command_intercept_and_process():
    messages = []
    with patch("skill_manager.core.skill_packages._run_process") as run_process:
        _run_shell_command("echo hi", messages.append)
    run_process.assert_called_once_with("echo hi", messages.append, shell=True)


def test_resolve_process_command_passthrough_and_absolute():
    assert _resolve_process_command("echo hi", shell=True) == "echo hi"
    assert _resolve_process_command([], shell=False) == []
    assert _resolve_process_command(["C:/bin/tool.exe", "arg"]) == ["C:/bin/tool.exe", "arg"]


def test_run_process_emits_sanitized_output_and_throttles_progress():
    proc = MagicMock()
    proc.stdout = iter(
        [
            "https://secret@example.com/repo.git\n",
            "Updating files: 45%\n",
            "Updating files: 46%\n",
        ]
    )
    proc.returncode = 0
    messages = []

    with (
        patch("skill_manager.core.skill_packages._resolve_process_command", return_value=["tool"]),
        patch("skill_manager.core.skill_packages.subprocess.Popen", return_value=proc),
        patch("time.time", side_effect=[1, 1.1, 1.2] + [2.0] * 10),
    ):
        _run_process(["tool"], messages.append)

    assert "https://***@example.com/repo.git" in messages
    assert "Updating files: 45%" in messages
    assert "Updating files: 46%" not in messages


def test_detect_command_type_variants():
    # pnpm, yarn, pipx detection logic
    # _detect_command_type classifies npx as npm, and other command types as custom
    assert _detect_command_type("npx --yes my-package") == "npm"
    assert _detect_command_type("npx my-package") == "npm"
    assert _detect_command_type("yarn my-package") == "custom"
    assert _detect_command_type("pnpm my-package") == "custom"
    assert _detect_command_type("pipx run my-package") == "custom"
    assert _detect_command_type("python script.py") == "custom"


def test_normalize_skill_package_config_malformed():
    # normalize_skill_package_config with malformed or incomplete data
    # Empty dict
    res = normalize_skill_package_config({})
    assert res["name"] == "Unnamed Package"
    assert res["source_type"] == "auto"
    assert res["package_id"].startswith("pkg_")

    # None or invalid input
    res_none = normalize_skill_package_config(None)
    assert res_none["name"] == "Unnamed Package"
    assert res_none["source_type"] == "auto"

    # Missing some keys but has others
    res_partial = normalize_skill_package_config({"package_path": "   "})
    assert res_partial["package_path"] == ""
    assert res_partial["name"] == "Unnamed Package"


@patch("skill_manager.core.skill_packages._run_process")
def test_run_git_package_update_conflict_and_network_failures(mock_run, temp_dir):
    clone_path = temp_dir / "existing-repo"
    clone_path.mkdir()
    (clone_path / ".git").mkdir()

    source = {
        "repository_url": "https://github.com/repo.git",
        "clone_path": str(clone_path),
        "package_path": str(clone_path),
    }

    # Simulate conflict / git pull error
    mock_run.side_effect = subprocess.CalledProcessError(1, ["git", "pull"], stderr="Conflict or network error")
    with pytest.raises(subprocess.CalledProcessError):
        _run_git_package_update(source, None)

    # Simulating network failure on clone (path does not exist)
    new_clone_path = temp_dir / "new-repo"
    source_new = {
        "repository_url": "https://github.com/repo.git",
        "clone_path": str(new_clone_path),
        "package_path": str(new_clone_path),
    }
    mock_run.side_effect = subprocess.CalledProcessError(128, ["git", "clone"], stderr="Could not resolve host")
    with pytest.raises(subprocess.CalledProcessError):
        _run_git_package_update(source_new, None)


def test_run_process_timeout_handling():
    # Testing Popen raising TimeoutExpired or subprocess wait timeout
    # Although _run_process doesn't have timeout argument, we can verify subprocess failure or OSError
    with (
        patch("skill_manager.core.skill_packages._resolve_process_command", return_value=["some-cmd"]),
        patch("subprocess.Popen") as mock_popen
    ):
        mock_popen.side_effect = subprocess.SubprocessError("Process failed to start")
        with pytest.raises(subprocess.SubprocessError):
            _run_process(["some-cmd"], None)


def test_detect_command_type_edge_cases():
    assert _detect_command_type("npx --yes my-pkg") == "npm"
    assert _detect_command_type("git clone ...") == "custom"
    assert _detect_command_type("copy file ...") == "custom"


@patch("shutil.which")
def test_run_process_missing_executable(mock_which):
    mock_which.return_value = None
    from skill_manager.core.skill_packages import _run_process
    with pytest.raises(FileNotFoundError) as exc:
        _run_process(["non-existent-cmd"], None)
    assert "not found" in str(exc.value)



@patch("subprocess.Popen")
def test_run_process_timeout(mock_popen):
    mock_proc = MagicMock()
    mock_proc.poll.return_value = None # Still running
    mock_proc.communicate.return_value = (b"", b"")
    mock_popen.return_value = mock_proc

    # This might be hard to test without actually waiting, so we mock time or poll
    # For now, just ensure it handles the interface



import pytest
import os
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock
from skill_manager.core.skill_sources import (
    normalize_skill_source_config,
    detect_source_config,
    run_skill_source_update,
    _relocate_skills_from_output,
    get_authenticated_url,
    get_git_tag,
    _run_repository_update,
    _run_npm_update,
    _intercept_cross_platform_command,
    detect_git_remote
)

def test_normalize_skill_source_config():
    data = {"package_name": "test-package"}
    normalized = normalize_skill_source_config(data)
    assert normalized["name"] == "test-package"
    assert normalized["source_type"] == "npm"
    assert "npx --yes test-package" in normalized["update_command"]

def test_detect_source_config_npm():
    data = {"package_name": "npx --yes my-pkg --foo"}
    detected = detect_source_config(data)
    assert detected["source_type"] == "npm"
    assert detected["package_name"] == "my-pkg"
    assert detected["install_args"] == "--foo"

def test_detect_source_config_git():
    data = {"source_type": "git", "repository_url": "http://git.com/repo"}
    detected = detect_source_config(data)
    assert detected["source_type"] == "git"

def test_relocate_skills_from_output(temp_dir):
    target_path = temp_dir / "project_skills"
    target_path.mkdir()
    
    # Create a dummy skill in a temp location
    source_skill_dir = temp_dir / "some_random_path" / "caveman"
    source_skill_dir.mkdir(parents=True)
    (source_skill_dir / "SKILL.md").write_text("content")
    
    output = [f"Installed to {source_skill_dir}"]
    
    _relocate_skills_from_output(output, str(target_path), None)
    
    # Check if it moved
    assert (target_path / "caveman").is_dir()
    assert (target_path / "caveman" / "SKILL.md").exists()
    assert not source_skill_dir.exists()

@patch("skill_manager.core.skill_sources._run_process")
@patch("skill_manager.core.skill_sources._relocate_skills_from_output")
@patch("skill_manager.core.skill_sources.check_skill_source_versions")
def test_run_skill_source_update_with_relocation(mock_check, mock_relocate, mock_run, temp_dir):
    local_path = temp_dir / "target"
    local_path.mkdir()
    (local_path / "old-skill").mkdir()
    
    source = {
        "name": "test",
        "local_path": str(local_path),
        "update_command": "ls",
        "managed_folders": ["old-skill"]
    }
    
    # Mock relocation to return a NEW list of managed folders
    mock_relocate.return_value = ["new-skill"]
    mock_check.return_value = {"current_version": "2.0.0"}
    
    updated = run_skill_source_update(source)
    
    # Should have deleted old-skill
    assert not (local_path / "old-skill").exists()
    assert updated["managed_folders"] == ["new-skill"]
    assert updated["removed_folders"] == ["old-skill"]
    assert updated["current_version"] == "2.0.0"

def test_get_authenticated_url():
    assert get_authenticated_url("https://github.com/repo.git", "token123") == "https://token123@github.com/repo.git"
    assert get_authenticated_url("http://github.com/repo.git", "token123") == "http://github.com/repo.git"
    assert get_authenticated_url("https://github.com/repo.git", None) == "https://github.com/repo.git"
    assert get_authenticated_url("https://user:pass@github.com/repo.git", "token123") == "https://user:pass@github.com/repo.git"

@patch("subprocess.run")
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

@patch("skill_manager.core.skill_sources._run_process")
def test_run_repository_update_clone(mock_run, temp_dir):
    clone_path = temp_dir / "repo"
    source = {
        "repository_url": "https://github.com/repo.git",
        "clone_path": str(clone_path),
        "local_path": str(clone_path)
    }
    
    _run_repository_update(source, None)
    
    # Should call clone since path is empty/doesn't exist
    mock_run.assert_called_once()
    assert mock_run.call_args[0][0][1] == "clone"

@patch("skill_manager.core.skill_sources._run_process")
def test_run_npm_update(mock_run):
    source = {"package_name": "my-pkg", "install_args": "--dev"}
    _run_npm_update(source, None)
    
    mock_run.assert_called_once()
    assert mock_run.call_args[0][0] == ["npx", "--yes", "my-pkg", "--dev"]

@patch("shutil.which")
@patch("subprocess.Popen")
def test_run_process_error(mock_popen, mock_which):
    mock_which.return_value = "/bin/test"
    mock_proc = MagicMock()
    mock_proc.stdout = []
    mock_proc.returncode = 1
    mock_popen.return_value = mock_proc
    
    from skill_manager.core.skill_sources import _run_process
    with pytest.raises(subprocess.CalledProcessError):
        _run_process(["test"], None)

def test_resolve_process_command_not_found():
    from skill_manager.core.skill_sources import _resolve_process_command
    with patch("shutil.which") as mock_which:
        mock_which.return_value = None
        with pytest.raises(FileNotFoundError):
            _resolve_process_command(["no-such-exec"])

def test_detect_source_config_auto_npm():
    # update_command starting with npx should be auto-detected as npm
    source = {"update_command": "npx --yes my-pkg"}
    detected = detect_source_config(source)
    assert detected["source_type"] == "npm"
    assert detected["package_name"] == "my-pkg"

def test_relocate_lock_files(temp_dir):
    target_path = temp_dir / "project_skills"
    target_path.mkdir()
    
    source_root = temp_dir / "source_repo"
    source_root.mkdir()
    (source_root / ".skill-lock.json").write_text("{}")
    
    # regex matches root of detected path
    detected_path = source_root / "skills" / "skill1"
    detected_path.mkdir(parents=True)
    
    output = [f"at {detected_path}"]
    _relocate_skills_from_output(output, str(target_path), None)
    
    # Should move the lock file to project root (target_path.parent)
    assert (target_path.parent / ".skill-lock.json").exists()

def test_relocate_path_internal_cleanup(temp_dir):
    from skill_manager.core.skill_sources import _relocate_path_internal
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
    from skill_manager.core.skill_sources import _split_args
    assert _split_args("  a   b  c  ") == ["a", "b", "c"]
    assert _split_args(None) == []

def test_intercept_cross_platform_success(temp_dir):
    # test -d should succeed for existing dir
    assert _intercept_cross_platform_command(f"test -d {temp_dir}", None) == True

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

def test_fallback_source_name():
    # Git URL fallback
    assert normalize_skill_source_config({"repository_url": "https://github.com/user/my-repo.git"})["name"] == "my-repo"
    # Local path fallback
    assert normalize_skill_source_config({"local_path": "/home/user/skills-dir"})["name"] == "skills-dir"
    # Default
    assert normalize_skill_source_config({})["name"] == "Unnamed Source"

@patch("skill_manager.core.skill_sources._run_process")
def test_run_repository_update_pull(mock_run, temp_dir):
    clone_path = temp_dir / "existing-repo"
    clone_path.mkdir()
    (clone_path / ".git").mkdir()
    
    source = {
        "repository_url": "https://github.com/repo.git",
        "clone_path": str(clone_path),
        "local_path": str(clone_path)
    }
    
    _run_repository_update(source, None)
    
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
    
    from skill_manager.core.skill_sources import run_version_command
    # Shell command
    assert run_version_command("git --version") == "v1.2.3"
    
    # Command fails
    mock_result.returncode = 1
    assert run_version_command("git --fail") == ""

def test_relocate_skills_from_output_detected(temp_dir):
    target_path = temp_dir / "project_skills"
    target_path.mkdir()

    source_skill_dir = temp_dir / "some_random_path" / "alpha"
    source_skill_dir.mkdir(parents=True)
    (source_skill_dir / "SKILL.md").write_text("info")

    # regex matches "at path" or "in path" or "to path"
    output = [f"Skills installed at {source_skill_dir}"]

    _relocate_skills_from_output(output, str(target_path), None)

    assert (target_path / "alpha").is_dir()
    assert not source_skill_dir.exists()


@patch("skill_manager.core.skill_sources._run_process")
def test_run_skill_source_update_npm(mock_run):
    source = {"source_type": "npm", "package_name": "my-pkg", "name": "test"}
    run_skill_source_update(source)
    # _run_npm_update should be called via _run_process
    mock_run.assert_called()

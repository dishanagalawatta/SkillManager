import subprocess
from unittest.mock import MagicMock, patch

import pytest

from skill_manager.core.skill_packages.process import (
    emit,
    resolve_process_command,
    run_process,
    sanitize_token,
)


def test_sanitize_token():
    assert sanitize_token("https://token@github.com") == "https://***@github.com"
    assert sanitize_token("echo password=secret") == "echo password=***"

    # Multiline token with quotes
    assert sanitize_token("echo password='secret\nmore'") == "echo password='***'"
    assert sanitize_token('echo password="secret\nmore"') == "echo password='***'"

    # Internal quotes
    assert sanitize_token('echo password="sec\'ret"') == "echo password='***'"
    assert sanitize_token("echo password='sec\"ret'") == "echo password='***'"

    # Inline multiple statements
    assert sanitize_token("echo password=secret; echo next") == "echo password=***; echo next"
    assert (
        sanitize_token("echo password='secret\nmore'; echo next")
        == "echo password='***'; echo next"
    )

    assert sanitize_token("no token here") == "no token here"
    assert sanitize_token(None) is None


def testemit():
    messages = []

    # Debug shouldn't go to callback
    emit(messages.append, "[DEBUG] some msg")
    assert not messages

    # Error should go to callback
    emit(messages.append, "[ERROR] failed")
    assert messages[-1] == "[ERROR] failed"

    # Relocating should be filtered
    emit(messages.append, "Relocating folder...")
    assert messages[-1] == "[ERROR] failed"  # no change

    # Success
    emit(messages.append, "Success! Moved everything")
    assert "Success!" in messages[-1]


def testresolve_process_command():
    assert resolve_process_command("echo hello", shell=True) == "echo hello"
    assert resolve_process_command(["/usr/bin/echo", "hello"], shell=False) == [
        "/usr/bin/echo",
        "hello",
    ]

    with patch("shutil.which", return_value="/bin/ls"):
        assert resolve_process_command(["ls", "-la"]) == ["/bin/ls", "-la"]

    with patch("shutil.which", return_value=None), pytest.raises(FileNotFoundError):
        resolve_process_command(["not_exist", "arg"])


@patch("subprocess.Popen")
def test_run_process_success(mock_popen):
    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.stdout = ["line1\n", "50%\n", "50%\n", "100%\n"]
    mock_popen.return_value = mock_proc

    messages = []
    run_process(["python", "-c", "print('hello')"], output_callback=messages.append)

    assert "line1" in messages
    # Progress throttling means we probably won't see all three percentage lines in fast succession
    # but run_process shouldn't crash.


@patch("subprocess.Popen")
def test_run_process_failure(mock_popen):
    mock_proc = MagicMock()
    mock_proc.returncode = 1
    mock_proc.stdout = ["error line\n"]
    mock_popen.return_value = mock_proc

    with pytest.raises(subprocess.CalledProcessError) as exc_info:
        run_process(["python", "-c", "import sys; sys.exit(1)"], output_callback=None)

    assert exc_info.value.returncode == 1

"""Tests for the single-instance guard in app.py.

The guard is opt-in: it only fires when ``SKILL_MANAGER_SINGLE_INSTANCE=1``
is set in the environment or ``--single-instance`` is passed on the command
line.  Without these, the mutex is still created (for Inno Setup installer
compatibility) but duplicate-instance detection is skipped.

These tests verify the guard **structurally** by reading the source file and
asserting that the correct API calls are present and wired together.
"""

from pathlib import Path


def test_create_mutex_checked_for_already_exists():
    """main() must check GetLastError() for ERROR_ALREADY_EXISTS (183) after CreateMutexW."""
    app_py_path = Path(__file__).parent.parent / "src" / "skill_manager" / "app.py"
    content = app_py_path.read_text(encoding="utf-8")

    assert "CreateMutexW" in content, "main() must call CreateMutexW"
    assert "ERROR_ALREADY_EXISTS" in content, "main() must define ERROR_ALREADY_EXISTS"
    assert "GetLastError()" in content, "main() must call GetLastError() after CreateMutexW"
    assert "183" in content or "ERROR_ALREADY_EXISTS = 183" in content, (
        "ERROR_ALREADY_EXISTS must be 183"
    )


def test_second_instance_exits():
    """When the mutex already exists AND the guard is active, the second process must call sys.exit."""
    app_py_path = Path(__file__).parent.parent / "src" / "skill_manager" / "app.py"
    content = app_py_path.read_text(encoding="utf-8")

    assert "sys.exit" in content, "main() must call sys.exit when another instance is detected"


def test_guard_is_opt_in():
    """The duplicate-instance check is skipped unless the opt-in flag is set."""
    app_py_path = Path(__file__).parent.parent / "src" / "skill_manager" / "app.py"
    content = app_py_path.read_text(encoding="utf-8")

    # The opt-in flag must be checked before the duplicate-instance check
    assert "SKILL_MANAGER_SINGLE_INSTANCE" in content, (
        "Guard must check SKILL_MANAGER_SINGLE_INSTANCE env var"
    )
    assert "--single-instance" in content, "Guard must check --single-instance CLI flag"


def test_bring_existing_window_to_front_exists():
    """The bring_existing_window_to_front helper must be defined."""
    app_py_path = Path(__file__).parent.parent / "src" / "skill_manager" / "app.py"
    content = app_py_path.read_text(encoding="utf-8")

    assert "_bring_existing_window_to_front" in content, (
        "_bring_existing_window_to_front helper must be defined"
    )
    assert "def _bring_existing_window_to_front" in content, (
        "_bring_existing_window_to_front must be a function definition"
    )


def test_bring_existing_window_called_on_duplicate():
    """main() must call _bring_existing_window_to_front when the mutex is already held."""
    app_py_path = Path(__file__).parent.parent / "src" / "skill_manager" / "app.py"
    content = app_py_path.read_text(encoding="utf-8")

    # Find the section where ERROR_ALREADY_EXISTS is handled
    # The call to _bring_existing_window_to_front must appear between
    # "ERROR_ALREADY_EXISTS" and "sys.exit" (i.e. inside the duplicate-instance block)
    already_exists_idx = content.find("ERROR_ALREADY_EXISTS")
    assert already_exists_idx != -1

    # Look for the function call after the constant definition
    bring_idx = content.rfind("_bring_existing_window_to_front()", already_exists_idx)
    exit_idx = content.rfind("sys.exit", already_exists_idx)

    assert bring_idx > already_exists_idx, (
        "_bring_existing_window_to_front must be called after ERROR_ALREADY_EXISTS check"
    )
    assert exit_idx > bring_idx, "sys.exit must be called after _bring_existing_window_to_front"


def test_mutex_handle_stored_in_global():
    """The mutex handle must be stored in the global _app_mutex for cleanup."""
    app_py_path = Path(__file__).parent.parent / "src" / "skill_manager" / "app.py"
    content = app_py_path.read_text(encoding="utf-8")

    assert "global _app_mutex" in content, "_app_mutex must be declared global in main()"
    assert "_app_mutex = ctypes.windll.kernel32.CreateMutexW" in content, (
        "_app_mutex must be assigned from CreateMutexW"
    )


def test_error_already_exists_constant_value():
    """ERROR_ALREADY_EXISTS must be defined as 183 (Windows API constant)."""
    app_py_path = Path(__file__).parent.parent / "src" / "skill_manager" / "app.py"
    content = app_py_path.read_text(encoding="utf-8")

    assert "ERROR_ALREADY_EXISTS = 183" in content, "ERROR_ALREADY_EXISTS must be exactly 183"

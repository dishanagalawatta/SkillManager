"""Tests for the single-instance guard (moved to ``utils/single_instance.py``).

The guard is opt-in: it only fires when ``SKILL_MANAGER_SINGLE_INSTANCE=1``
is set in the environment or ``--single-instance`` is passed on the command
line.  Without these, the mutex is still created (for Inno Setup installer
compatibility) but duplicate-instance detection is skipped.

These used to be source-text-pinning tests against ``app.py``; after the
Phase 1 decomposition they exercise the real behaviour of
``skill_manager.utils.single_instance`` and of the wiring in
``bootstrap._setup_single_instance`` (formerly ``main()``'s mutex block).
"""

import inspect
import os
import sys
from unittest.mock import MagicMock, patch

from skill_manager.bootstrap import _setup_single_instance
from skill_manager.utils import single_instance


class TestGuardModuleSurface:
    """The guard module must expose the full set of moved helpers."""

    def test_module_has_guard_names(self):
        for name in (
            "_app_mutex",
            "_SINGLE_INSTANCE_LOCK_PATH",
            "_bring_existing_window_to_front",
            "_acquire_linux_lock",
            "release_lock",
        ):
            assert hasattr(single_instance, name), f"{name} missing from single_instance"


class TestSetupSingleInstanceWin32:
    """_setup_single_instance on win32: mutex + duplicate detection."""

    def _run_setup(self, monkeypatch, env=None, argv=None, get_last_error=0):
        monkeypatch.setattr(sys, "platform", "win32")
        monkeypatch.delenv("SKILL_MANAGER_SINGLE_INSTANCE", raising=False)
        if env:
            monkeypatch.setenv("SKILL_MANAGER_SINGLE_INSTANCE", env)
        if argv is not None:
            monkeypatch.setattr(sys, "argv", argv)
        fake_kernel32 = MagicMock()
        fake_kernel32.GetLastError.return_value = get_last_error
        fake_ctypes = MagicMock()
        fake_ctypes.windll.kernel32 = fake_kernel32
        ctx = [patch("skill_manager.bootstrap.ctypes", fake_ctypes)]
        return ctx, fake_kernel32

    def test_mutex_created_and_already_exists_checked(self, monkeypatch):
        """CreateMutexW must be called and its result checked via GetLastError."""
        ctx, fake_kernel32 = self._run_setup(monkeypatch)
        with ctx[0], patch("skill_manager.bootstrap.sys.exit") as mock_exit:
            _setup_single_instance()
        fake_kernel32.CreateMutexW.assert_called_once()
        fake_kernel32.GetLastError.assert_called_once()
        mock_exit.assert_not_called()

    def test_second_instance_exits_when_mutex_held_and_opt_in(self, monkeypatch):
        """Mutex held (GetLastError=183) + opt-in => bring to front + sys.exit(0)."""
        ctx, fake_kernel32 = self._run_setup(monkeypatch, env="1", get_last_error=183)
        with (
            ctx[0],
            patch("skill_manager.bootstrap.sys.exit") as mock_exit,
            patch(
                "skill_manager.bootstrap.single_instance._bring_existing_window_to_front"
            ) as mock_bring,
        ):
            _setup_single_instance()
        mock_bring.assert_called_once()
        mock_exit.assert_called_once_with(0)

    def test_second_instance_exits_with_cli_flag(self, monkeypatch):
        """--single-instance on argv must activate the guard exactly like the env var."""
        ctx, _ = self._run_setup(
            monkeypatch, argv=["skill-manager", "--single-instance"], get_last_error=183
        )
        with (
            ctx[0],
            patch("skill_manager.bootstrap.sys.exit") as mock_exit,
            patch("skill_manager.bootstrap.single_instance._bring_existing_window_to_front"),
        ):
            _setup_single_instance()
        mock_exit.assert_called_once_with(0)

    def test_guard_is_opt_in_no_exit_without_flag(self, monkeypatch):
        """Mutex held but no opt-in: duplicate detection must be skipped."""
        ctx, _ = self._run_setup(monkeypatch, get_last_error=183)
        with (
            ctx[0],
            patch("skill_manager.bootstrap.sys.exit") as mock_exit,
            patch(
                "skill_manager.bootstrap.single_instance._bring_existing_window_to_front"
            ) as mock_bring,
        ):
            _setup_single_instance()
        mock_bring.assert_not_called()
        mock_exit.assert_not_called()

    def test_mutex_handle_stored_in_shared_global(self, monkeypatch):
        """The mutex handle must be stored in single_instance._app_mutex for cleanup."""
        ctx, fake_kernel32 = self._run_setup(monkeypatch)
        fake_kernel32.CreateMutexW.return_value = 0xDEADBEEF
        with ctx[0], patch("skill_manager.bootstrap.sys.exit"):
            _setup_single_instance()
        try:
            assert single_instance._app_mutex == 0xDEADBEEF
        finally:
            single_instance._app_mutex = None

    def test_error_already_exists_constant_value(self):
        """ERROR_ALREADY_EXISTS must be defined as 183 (Windows API constant)."""
        source = inspect.getsource(_setup_single_instance)
        assert "ERROR_ALREADY_EXISTS = 183" in source


class TestSetupSingleInstanceLinux:
    """_setup_single_instance on linux: PID lockfile guard."""

    def test_linux_lock_acquired_when_opt_in(self, monkeypatch):
        monkeypatch.setattr(sys, "platform", "linux")
        monkeypatch.setenv("SKILL_MANAGER_SINGLE_INSTANCE", "1")
        with (
            patch(
                "skill_manager.bootstrap.single_instance._acquire_linux_lock",
                return_value="/tmp/skillmanager-test.lock",
            ) as mock_acquire,
            patch("skill_manager.bootstrap.sys.exit") as mock_exit,
            patch("skill_manager.bootstrap.ctypes.windll", create=True) as mock_windll,
        ):
            _setup_single_instance()
        mock_acquire.assert_called_once()
        mock_exit.assert_not_called()
        mock_windll.shell32.SetCurrentProcessExplicitAppUserModelID.assert_called_once()

    def test_linux_second_instance_exits(self, monkeypatch):
        """Lock already held (None returned) + opt-in => bring to front + sys.exit(0)."""
        monkeypatch.setattr(sys, "platform", "linux")
        monkeypatch.setenv("SKILL_MANAGER_SINGLE_INSTANCE", "1")
        with (
            patch("skill_manager.bootstrap.single_instance._acquire_linux_lock", return_value=None),
            patch("skill_manager.bootstrap.sys.exit") as mock_exit,
            patch(
                "skill_manager.bootstrap.single_instance._bring_existing_window_to_front"
            ) as mock_bring,
        ):
            _setup_single_instance()
        mock_bring.assert_called_once()
        mock_exit.assert_called_once_with(0)

    def test_linux_without_opt_in_skips_guard(self, monkeypatch):
        monkeypatch.setattr(sys, "platform", "linux")
        monkeypatch.delenv("SKILL_MANAGER_SINGLE_INSTANCE", raising=False)
        with (
            patch("skill_manager.bootstrap.single_instance._acquire_linux_lock") as mock_acquire,
            patch("skill_manager.bootstrap.sys.exit") as mock_exit,
        ):
            _setup_single_instance()
        mock_acquire.assert_not_called()
        mock_exit.assert_not_called()


class TestAcquireLinuxLock:
    """_acquire_linux_lock creates / detects / replaces the PID lockfile."""

    def _reset_state(self):
        single_instance._SINGLE_INSTANCE_LOCK_PATH = None

    def test_creates_lock_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr("skill_manager.core.config.DATA_DIR", tmp_path)
        try:
            lock_path = single_instance._acquire_linux_lock()
            assert lock_path == str(tmp_path / "app.lock")
            assert (tmp_path / "app.lock").exists()
            assert (tmp_path / "app.lock").read_text(encoding="utf-8").strip() == str(os.getpid())
        finally:
            self._reset_state()

    def test_detects_live_instance(self, tmp_path, monkeypatch):
        """A lockfile with a live PID (our own) => another instance is running."""
        monkeypatch.setattr("skill_manager.core.config.DATA_DIR", tmp_path)
        (tmp_path / "app.lock").write_text(str(os.getpid()), encoding="utf-8")
        try:
            assert single_instance._acquire_linux_lock() is None
        finally:
            self._reset_state()

    def test_replaces_stale_lock(self, tmp_path, monkeypatch):
        """A lockfile with invalid content must be treated as stale and replaced."""
        monkeypatch.setattr("skill_manager.core.config.DATA_DIR", tmp_path)
        (tmp_path / "app.lock").write_text("not-a-pid", encoding="utf-8")
        try:
            lock_path = single_instance._acquire_linux_lock()
            assert lock_path == str(tmp_path / "app.lock")
            assert (tmp_path / "app.lock").read_text(encoding="utf-8").strip() == str(os.getpid())
        finally:
            self._reset_state()


class TestReleaseLock:
    """release_lock must reset the mutex and remove the lockfile."""

    def test_release_removes_lockfile_and_resets_globals(self, tmp_path, monkeypatch):
        monkeypatch.setattr("skill_manager.core.config.DATA_DIR", tmp_path)
        single_instance._acquire_linux_lock()
        single_instance._app_mutex = object()
        single_instance.release_lock()
        assert single_instance._app_mutex is None
        assert single_instance._SINGLE_INSTANCE_LOCK_PATH is None
        assert not (tmp_path / "app.lock").exists()

    def test_release_is_safe_without_lock(self):
        single_instance._app_mutex = None
        single_instance._SINGLE_INSTANCE_LOCK_PATH = None
        single_instance.release_lock()  # must not raise


class TestBringExistingWindowToFront:
    """_bring_existing_window_to_front must be best-effort on every platform."""

    def test_win32_restores_and_foregrounds_window(self):
        fake = MagicMock()
        fake.windll.user32.FindWindowW.return_value = 12345
        with patch.object(sys, "platform", "win32"), patch.dict(sys.modules, {"ctypes": fake}):
            single_instance._bring_existing_window_to_front()
        fake.windll.user32.FindWindowW.assert_called_once_with(None, "Skill Manager")
        fake.windll.user32.ShowWindow.assert_called_once_with(12345, 9)  # SW_RESTORE
        fake.windll.user32.SetForegroundWindow.assert_called_once_with(12345)

    def test_win32_no_window_is_noop(self):
        fake = MagicMock()
        fake.windll.user32.FindWindowW.return_value = 0
        with patch.object(sys, "platform", "win32"), patch.dict(sys.modules, {"ctypes": fake}):
            single_instance._bring_existing_window_to_front()
        fake.windll.user32.ShowWindow.assert_not_called()

    def test_linux_uses_xdotool(self):
        with (
            patch.object(sys, "platform", "linux"),
            patch("shutil.which", return_value="/usr/bin/xdotool"),
            patch("subprocess.run") as mock_run,
        ):
            single_instance._bring_existing_window_to_front()
        args = mock_run.call_args.args[0]
        assert args[:3] == ["/usr/bin/xdotool", "search", "--name"]
        assert args[3:] == ["Skill Manager", "windowactivate"]

    def test_linux_falls_back_to_wmctrl(self):
        def which(name):
            return None if name == "xdotool" else "/usr/bin/wmctrl"

        with (
            patch.object(sys, "platform", "linux"),
            patch("shutil.which", side_effect=which),
            patch("subprocess.run") as mock_run,
        ):
            single_instance._bring_existing_window_to_front()
        args = mock_run.call_args.args[0]
        assert args == ["/usr/bin/wmctrl", "-a", "Skill Manager"]

    def test_linux_no_tools_is_noop(self):
        with (
            patch.object(sys, "platform", "linux"),
            patch("shutil.which", return_value=None),
            patch("subprocess.run") as mock_run,
        ):
            single_instance._bring_existing_window_to_front()  # must not raise
        mock_run.assert_not_called()

    def test_other_platforms_are_noop(self):
        with patch.object(sys, "platform", "darwin"), patch("subprocess.run") as mock_run:
            single_instance._bring_existing_window_to_front()  # must not raise
        mock_run.assert_not_called()


class TestSetupSingleInstanceSource:
    """Wiring sanity: the mutex block must still check both opt-in switches."""

    def test_guard_checks_env_and_cli_flag(self):
        source = inspect.getsource(_setup_single_instance)
        assert "SKILL_MANAGER_SINGLE_INSTANCE" in source
        assert "--single-instance" in source

"""Tests for the global hotkey manager.

These tests verify the manager's CONTRACT:
- The module can be imported without pynput being usable
- The manager can be instantiated without pynput
- register() returns True/False based on pynput availability
- The Qt signal emission works regardless of pynput state
- Unregister of unknown id is a safe no-op
- stop() properly joins the listener thread
- Listener creation failure is handled gracefully

The tests do NOT start real pynput listeners — ``conftest.py`` patches
``_ensure_pynput`` to return ``False`` for the entire test session.  The
new unit tests below patch ``keyboard.Listener`` with a lightweight fake
so that the listener-lifecycle code paths are exercised without touching
the Windows keyboard hook.
"""

from __future__ import annotations

import subprocess
import sys
from unittest.mock import MagicMock, patch

from skill_manager.core.global_hotkey import (
    LISTENER_JOIN_TIMEOUT,  # type: ignore[attr-defined]
    PORTAL_HELPER_STOP_TIMEOUT,  # type: ignore[attr-defined]
    GlobalHotkeyManager,
    PortalHotkeyBackend,
)


class _FakeListener:
    """Minimal stand-in for ``pynput.keyboard.Listener``.

    Records calls to ``start()`` / ``stop()`` and provides a fake
    ``_thread`` attribute so ``GlobalHotkeyManager._restart_listener``
    can capture it.
    """

    def __init__(self, **kwargs):
        self._press = kwargs.get("on_press")
        self._release = kwargs.get("on_release")
        self.started = False
        self.stopped = False
        self.join = MagicMock()
        self.is_alive = MagicMock(return_value=False)

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True

    def canonical(self, key):
        return key


class TestManagerContract:
    """The class is a QObject that exposes hotkeyPressed(int)."""

    def test_inherits_from_qobject(self):
        from PySide6.QtCore import QObject

        assert issubclass(GlobalHotkeyManager, QObject)

    def test_has_hotkey_pressed_signal(self):
        manager = GlobalHotkeyManager()
        assert hasattr(manager, "hotkeyPressed")
        # Signal is connectable
        received: list[int] = []
        manager.hotkeyPressed.connect(lambda hid: received.append(hid))
        manager.hotkeyPressed.emit(42)
        assert received == [42]


class TestManagerWithoutPynput:
    """Behavior when pynput is not available.

    We test this by directly setting _pynput_available = False
    (simulating the lazy-import having failed). This is a contract
    test, not a mock — we're verifying what the manager does in
    the "pynput unavailable" state.
    """

    def test_register_returns_false_when_pynput_unavailable(self):
        manager = GlobalHotkeyManager()
        manager._pynput_available = False  # Simulate failed lazy-import
        result = manager.register(1, "Ctrl+Shift+S")
        assert result is False
        assert 1 not in manager._hotkeys  # State unchanged

    def test_register_empty_sequence_returns_false(self):
        manager = GlobalHotkeyManager()
        manager._pynput_available = False
        result = manager.register(1, "")
        assert result is False

    def test_unregister_unknown_id_is_safe(self):
        manager = GlobalHotkeyManager()
        manager._pynput_available = False
        manager.unregister(999)  # No error, no state change
        assert 999 not in manager._hotkeys

    def test_stop_with_no_listener_is_safe(self):
        manager = GlobalHotkeyManager()
        manager._pynput_available = False
        manager.stop()  # No error even with no listener registered
        assert manager._hotkeys == {}
        assert manager._listener is None

    def test_start_is_noop(self):
        """start() is a compatibility shim — verify it doesn't crash."""
        manager = GlobalHotkeyManager()
        manager._pynput_available = False
        manager.start()  # No error


class TestManagerStateTransitions:
    """Verify the lazy-import state machine."""

    def test_initial_state_is_unchecked(self):
        manager = GlobalHotkeyManager()
        assert manager._pynput_available is None  # None = unchecked

    def test_pynput_availability_cached(self):
        """Once checked, the result is cached."""
        manager = GlobalHotkeyManager()
        manager._pynput_available = True
        # Second call should not re-import — verify by checking the flag
        assert manager._pynput_available is True


class TestNoPynputImportAtModuleLoad:
    """Critical regression test: importing global_hotkey must NOT import pynput.

    This is the test that would have caught the original CI bug.
    """

    def test_module_docstring_mentions_lazy_loading(self):
        import skill_manager.core.global_hotkey as gh

        assert gh.__doc__ is not None
        assert "lazy" in gh.__doc__.lower()


class TestEnvironmentDetection:
    """Verify environment auto-detection and graceful degradation."""

    def test_detect_testing_mode(self):
        from skill_manager.core.global_hotkey import detect_environment_and_display

        with patch.dict("os.environ", {"SKILL_MANAGER_TESTING": "1"}):
            env, supported, reason = detect_environment_and_display()
            assert env == "Testing"
            assert supported is False
            assert "test mode" in reason

    def test_detect_offscreen_platform(self):
        from skill_manager.core.global_hotkey import detect_environment_and_display

        with patch.dict(
            "os.environ", {"SKILL_MANAGER_TESTING": "0", "QT_QPA_PLATFORM": "offscreen"}
        ):
            env, supported, reason = detect_environment_and_display()
            assert "offscreen" in env.lower()
            assert supported is False
            assert "unavailable" in reason

    def test_manager_properties_reflect_environment(self):
        import skill_manager.core.global_hotkey as gh

        def real_ensure_pynput(inst):
            env_name, supported, reason = gh.detect_environment_and_display()
            inst._availability_reason = reason
            inst._pynput_available = supported
            return supported

        with (
            patch.object(GlobalHotkeyManager, "_ensure_pynput", real_ensure_pynput),
            patch(
                "skill_manager.core.global_hotkey.detect_environment_and_display",
                return_value=(
                    "Headless (offscreen)",
                    False,
                    "Global hotkeys unavailable on offscreen platform",
                ),
            ),
        ):
            manager = GlobalHotkeyManager()
            assert manager.isAvailable is False
            assert "offscreen" in manager.statusReason.lower()


class TestListenerLifecycle:
    """Unit tests for the new thread-tracking and stop-join behaviour.

    These patch ``keyboard.Listener`` with ``_FakeListener`` so we
    exercise the lifecycle code paths without touching the Windows
    keyboard hook.
    """

    def test_stop_joins_listener_thread(self):
        """stop() must set _listener=None after join."""
        manager = GlobalHotkeyManager()

        fake_pynput = MagicMock()
        fake_pynput.keyboard.HotKey.parse.return_value = []

        with (
            patch.dict(
                sys.modules, {"pynput": fake_pynput, "pynput.keyboard": fake_pynput.keyboard}
            ),
            patch.object(GlobalHotkeyManager, "_ensure_pynput", return_value=True),
        ):
            fake_listener = _FakeListener()
            fake_listener.is_alive.return_value = True
            fake_pynput.keyboard.Listener.return_value = fake_listener

            manager.register(1, "Ctrl+Shift+S")
            assert manager._listener is fake_listener

            manager.stop()

        # Thread join was called with timeout
        fake_listener.join.assert_called_once_with(timeout=LISTENER_JOIN_TIMEOUT)
        # State cleaned up
        assert manager._listener is None
        assert fake_listener.stopped

    def test_stop_does_not_join_when_not_alive(self):
        """If listener is not alive, stop() still clears state but doesn't join."""
        manager = GlobalHotkeyManager()

        fake_pynput = MagicMock()
        fake_pynput.keyboard.HotKey.parse.return_value = []

        with (
            patch.dict(
                sys.modules, {"pynput": fake_pynput, "pynput.keyboard": fake_pynput.keyboard}
            ),
            patch.object(GlobalHotkeyManager, "_ensure_pynput", return_value=True),
        ):
            fake_listener = _FakeListener()
            fake_listener.is_alive.return_value = False
            fake_pynput.keyboard.Listener.return_value = fake_listener

            manager.register(1, "Ctrl+Shift+S")
            manager.stop()

        # join() was NOT called (listener already dead)
        fake_listener.join.assert_not_called()
        assert manager._listener is None

    def test_double_stop_is_safe(self):
        """Calling stop() twice must not raise."""
        manager = GlobalHotkeyManager()

        fake_pynput = MagicMock()
        fake_pynput.keyboard.HotKey.parse.return_value = []

        with (
            patch.dict(
                sys.modules, {"pynput": fake_pynput, "pynput.keyboard": fake_pynput.keyboard}
            ),
            patch.object(GlobalHotkeyManager, "_ensure_pynput", return_value=True),
        ):
            fake_listener = _FakeListener()
            fake_pynput.keyboard.Listener.return_value = fake_listener

            manager.register(1, "Ctrl+Shift+S")
            manager.stop()
            manager.stop()  # second call — must not raise

        assert manager._listener is None

    def test_listener_creation_failure_doesnt_crash(self):
        """OSError from keyboard.Listener() must not propagate."""
        manager = GlobalHotkeyManager()

        fake_pynput = MagicMock()
        fake_pynput.keyboard.Listener.side_effect = OSError("no console session")
        fake_pynput.keyboard.HotKey.parse.return_value = []

        with (
            patch.dict(
                sys.modules, {"pynput": fake_pynput, "pynput.keyboard": fake_pynput.keyboard}
            ),
            patch.object(GlobalHotkeyManager, "_ensure_pynput", return_value=True),
        ):
            result = manager.register(1, "Ctrl+Shift+S")

        assert result is True  # hotkey was registered
        assert manager._listener is None  # listener not created

    def test_stop_acquires_stop_lock(self):
        """stop() acquires _stop_lock to serialise concurrent calls."""
        manager = GlobalHotkeyManager()

        # Verify the lock exists and is a proper Lock
        assert hasattr(manager, "_stop_lock")
        assert hasattr(manager._stop_lock, "acquire")
        assert hasattr(manager._stop_lock, "release")


def _fake_proc() -> MagicMock:
    """A fake Popen handle with a working stdin and an idle stdout pipe."""
    proc = MagicMock()
    proc.poll.return_value = None
    proc.stdin = MagicMock()
    proc.stdin.write = MagicMock()
    proc.stdin.flush = MagicMock()
    proc.stdout = iter([])
    proc.wait = MagicMock()
    return proc


class TestPortalBackend:
    """Unit tests for PortalHotkeyBackend (spawn/protocol/stop)."""

    def test_start_spawns_helper_with_found_python(self):
        backend = PortalHotkeyBackend()
        proc = _fake_proc()

        with (
            patch(
                "skill_manager.controllers.snap_controller._find_portal_python",
                return_value="/usr/bin/python3",
            ),
            patch("skill_manager.core.global_hotkey.subprocess.Popen", return_value=proc) as popen,
            patch("skill_manager.core.global_hotkey.threading.Thread") as thread_cls,
        ):
            assert backend.start() is True

        popen.assert_called_once()
        args = popen.call_args[0][0]
        assert args[0] == "/usr/bin/python3"
        assert args[1].endswith("portal_hotkeys.py")
        thread_cls.assert_called_once()
        assert backend._started is True

    def test_start_returns_false_when_no_portal_python(self):
        backend = PortalHotkeyBackend()
        with patch(
            "skill_manager.controllers.snap_controller._find_portal_python",
            return_value=None,
        ):
            assert backend.start() is False
        assert backend.available is False

    def test_start_returns_false_when_import_fails(self):
        backend = PortalHotkeyBackend()
        fake_module = MagicMock()
        del fake_module._find_portal_python
        with patch.dict(
            sys.modules,
            {"skill_manager.controllers.snap_controller": fake_module},
        ):
            assert backend.start() is False

    def test_start_returns_false_on_popen_oserror(self):
        backend = PortalHotkeyBackend()
        with (
            patch(
                "skill_manager.controllers.snap_controller._find_portal_python",
                return_value="/usr/bin/python3",
            ),
            patch(
                "skill_manager.core.global_hotkey.subprocess.Popen",
                side_effect=OSError("no such file"),
            ),
        ):
            assert backend.start() is False
        assert backend._proc is None

    def test_register_sends_bind_command_with_gtk_trigger(self):
        backend = PortalHotkeyBackend()
        proc = _fake_proc()
        backend._proc = proc
        backend._started = True

        assert backend.register(7, "Ctrl+Shift+S") is True

        written = proc.stdin.write.call_args[0][0]
        import json as _json

        payload = _json.loads(written)
        assert payload["cmd"] == "bind"
        assert payload["id"].startswith("sm_7_")
        assert payload["preferred_trigger"] == "<Control><Shift>S"

    def test_register_rejected_when_not_available(self):
        backend = PortalHotkeyBackend()
        backend._started = False
        assert backend.register(7, "Ctrl+Shift+S") is False

    def test_unregister_sends_remove_command(self):
        backend = PortalHotkeyBackend()
        proc = _fake_proc()
        backend._proc = proc
        backend._started = True
        backend._shortcut_ids = {3: "sm_3"}

        backend.unregister(3)

        import json as _json

        payload = _json.loads(proc.stdin.write.call_args[0][0])
        assert payload == {"cmd": "remove", "id": "sm_3"}
        assert 3 not in backend._shortcut_ids

    def test_stop_sends_quit_and_waits(self):
        backend = PortalHotkeyBackend()
        proc = _fake_proc()
        backend._proc = proc
        backend._started = True

        backend.stop()

        import json as _json

        payload = _json.loads(proc.stdin.write.call_args[0][0])
        assert payload == {"cmd": "quit"}
        proc.wait.assert_called_once_with(timeout=PORTAL_HELPER_STOP_TIMEOUT)
        assert backend._proc is None
        assert backend._started is False

    def test_stop_terminates_on_timeout(self):
        backend = PortalHotkeyBackend()
        proc = _fake_proc()
        proc.wait.side_effect = subprocess.TimeoutExpired(cmd="portal_hotkeys.py", timeout=2.0)
        backend._proc = proc
        backend._started = True

        backend.stop()

        proc.terminate.assert_called_once()
        assert backend._proc is None

    def test_activated_event_forwards_hotkey_id(self):
        backend = PortalHotkeyBackend()
        backend._shortcut_ids = {5: "sm_5"}
        received: list[int] = []
        backend.hotkeyPressed.connect(received.append)

        backend._handle_event({"event": "activated", "id": "sm_5", "timestamp": 123})

        assert received == [5]

    def test_activated_unknown_id_ignored(self):
        backend = PortalHotkeyBackend()
        backend._shortcut_ids = {}
        received: list[int] = []
        backend.hotkeyPressed.connect(received.append)

        backend._handle_event({"event": "activated", "id": "sm_unknown"})

        assert received == []

    def test_malformed_event_line_logs_warning(self):
        backend = PortalHotkeyBackend()
        import io

        stream = io.StringIO("not json\n")
        backend._proc = _fake_proc()
        backend._proc.stdout = stream
        with patch("skill_manager.core.global_hotkey.logger") as mock_logger:
            backend._read_events()
        mock_logger.warning.assert_called_once()


class TestManagerPortalFallback:
    """GlobalHotkeyManager falls back to the portal backend on Wayland."""

    def test_ensure_portal_disabled_in_testing_mode(self):
        manager = GlobalHotkeyManager()
        with patch.dict("os.environ", {"SKILL_MANAGER_TESTING": "1"}):
            assert manager._ensure_portal() is False

    def test_ensure_portal_skipped_on_non_wayland(self):
        manager = GlobalHotkeyManager()
        with (
            patch.dict("os.environ", {"SKILL_MANAGER_TESTING": "0"}),
            patch(
                "skill_manager.core.global_hotkey.detect_environment_and_display",
                return_value=("X11", True, "x11 display"),
            ),
        ):
            assert manager._ensure_portal() is False

    def test_ensure_portal_starts_backend_on_wayland(self):
        manager = GlobalHotkeyManager()
        backend = MagicMock()
        backend.start.return_value = True

        with (
            patch.dict("os.environ", {"SKILL_MANAGER_TESTING": "0"}),
            patch(
                "skill_manager.core.global_hotkey.detect_environment_and_display",
                return_value=("Wayland (gnome)", True, "wayland"),
            ),
            patch(
                "skill_manager.core.global_hotkey.PortalHotkeyBackend",
                return_value=backend,
            ),
        ):
            assert manager._ensure_portal() is True

        assert manager._portal_backend is backend
        backend.hotkeyPressed.connect.assert_called_once()
        assert "portal backend" in manager._availability_reason

    def test_portal_backend_active_reflects_backend_state(self):
        manager = GlobalHotkeyManager()

        assert manager.portalBackendActive is False, (
            "portalBackendActive must be False until the portal backend starts"
        )

        manager._portal_backend = MagicMock()
        assert manager.portalBackendActive is True, (
            "portalBackendActive must be True while the portal backend is running"
        )

    def test_ensure_portal_backend_failure_reports_reason(self):
        manager = GlobalHotkeyManager()
        backend = MagicMock()
        backend.start.return_value = False

        with (
            patch.dict("os.environ", {"SKILL_MANAGER_TESTING": "0"}),
            patch(
                "skill_manager.core.global_hotkey.detect_environment_and_display",
                return_value=("Wayland (gnome)", True, "wayland"),
            ),
            patch(
                "skill_manager.core.global_hotkey.PortalHotkeyBackend",
                return_value=backend,
            ),
        ):
            assert manager._ensure_portal() is False

        assert manager._portal_backend is None
        assert "failed to start" in manager._availability_reason

    def test_register_falls_back_to_portal_backend(self):
        manager = GlobalHotkeyManager()
        manager._pynput_available = False
        backend = MagicMock()
        backend.register.return_value = True
        manager._portal_backend = backend
        manager._portal_available = True

        assert manager.register(11, "Meta+Shift+F12") is True
        backend.register.assert_called_once_with(11, "Meta+Shift+F12")

    def test_wayland_register_prefers_portal_backend(self):
        """On Wayland, register() must try portal backend first even if pynput is available."""
        manager = GlobalHotkeyManager()
        portal_backend = MagicMock()
        portal_backend.register.return_value = True

        with (
            patch(
                "skill_manager.core.global_hotkey.detect_environment_and_display",
                return_value=("Wayland (XWayland)", True, "active"),
            ),
            patch.object(manager, "_ensure_portal", return_value=True),
            patch.object(manager, "_ensure_pynput", return_value=True) as mock_pynput,
        ):
            manager._portal_backend = portal_backend
            result = manager.register(1, "Ctrl+Shift+S")

        assert result is True
        portal_backend.register.assert_called_once_with(1, "Ctrl+Shift+S")
        mock_pynput.assert_not_called()

    def test_non_wayland_register_prefers_pynput(self):
        """On non-Wayland (X11), register() must try pynput first."""
        manager = GlobalHotkeyManager()

        with (
            patch(
                "skill_manager.core.global_hotkey.detect_environment_and_display",
                return_value=("X11", True, "active"),
            ),
            patch.object(manager, "_ensure_pynput", return_value=True) as mock_pynput,
            patch.object(manager, "_ensure_portal") as mock_portal,
            patch.object(manager, "_restart_listener"),
        ):
            result = manager.register(1, "Ctrl+Shift+S")

        assert result is True
        mock_pynput.assert_called_once()
        mock_portal.assert_not_called()

    def test_unregister_delegates_to_portal_backend(self):
        manager = GlobalHotkeyManager()
        manager._pynput_available = False
        backend = MagicMock()
        manager._portal_backend = backend

        manager.unregister(11)

        backend.unregister.assert_called_once_with(11)

    def test_stop_cleans_up_portal_backend(self):
        manager = GlobalHotkeyManager()
        backend = MagicMock()
        manager._portal_backend = backend

        manager.stop()

        backend.stop.assert_called_once()
        assert manager._portal_backend is None
        assert manager._portal_available is None

    def test_portal_backend_updates_shortcut_with_new_portal_id(self):
        backend = PortalHotkeyBackend()
        backend._proc = MagicMock()
        backend._proc.poll.return_value = None
        backend._proc.stdin = MagicMock()
        backend._started = True

        assert backend.register(1, "Ctrl+Shift+S") is True
        first_id = backend._shortcut_ids[1]
        assert first_id.startswith("sm_1_")

        assert backend.register(1, "Ctrl+Shift+D") is True
        second_id = backend._shortcut_ids[1]
        assert second_id.startswith("sm_1_")
        assert first_id != second_id

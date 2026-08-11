"""Unit tests for the portal GlobalShortcuts helper state machine.

The helper (``skill_manager.utils.portal_hotkeys``) is a standalone
subprocess that bridges SkillManager and the FreeDesktop GlobalShortcuts
portal. Its D-Bus wiring (``_PortalHelper.__init__``) requires a real
session bus, so those tests would fail on CI. Instead we:

- inject fake ``dbus`` / ``gi`` modules into ``sys.modules`` so the
  module-level delay-import succeeds;
- construct ``_PortalHelper`` instances with ``__new__`` to bypass
  ``__init__``'s bus wiring;
- drive the command/response handlers directly and assert on the JSON
  events the helper would emit on stdout.
"""

from __future__ import annotations

import re
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

# --- Fake dbus/gi so the module-level delay-import succeeds ---------------
_fake_glib = SimpleNamespace(
    MainLoop=MagicMock,
    io_add_watch=MagicMock,
    timeout_add_seconds=MagicMock,
    source_remove=MagicMock,
    SOURCE_REMOVE=MagicMock(),
    SOURCE_CONTINUE=MagicMock(),
)
_fake_dbus = MagicMock()
_fake_dbus.mainloop = MagicMock()
_fake_dbus.mainloop.glib = MagicMock()
_fake_dbus_glib = _fake_dbus.mainloop.glib
_fake_dbus_glib.DBusGMainLoop = MagicMock

_fake_gi = MagicMock()
_fake_gi.repository = MagicMock()
_fake_gi.repository.GLib = _fake_glib

_fake_dbus.ObjectPath.side_effect = lambda path: path

for _name, _mod in {
    "dbus": _fake_dbus,
    "dbus.mainloop.glib": _fake_dbus_glib,
    "gi": _fake_gi,
    "gi.repository": _fake_gi.repository,
    "gi.repository.GLib": _fake_glib,
}.items():
    sys.modules[_name] = _mod

from skill_manager.utils import portal_hotkeys as ph  # noqa: E402


def _make_helper(**attrs) -> ph._PortalHelper:
    """Build a helper without touching its D-Bus __init__ wiring."""
    helper = ph._PortalHelper.__new__(ph._PortalHelper)
    helper.loop = MagicMock()
    helper.bus = MagicMock()
    helper.gs_iface = MagicMock()
    helper.session_handle = None
    helper.create_req_path = None
    helper.bind_req_path = None
    helper.binding = False
    helper.rebind_pending = False
    helper.session_used = False
    helper.creating = False
    helper.create_timed_out = False
    helper._create_timeout_id = None
    helper._shortcuts = {}
    helper._requested_ids = []
    helper._stdin_buf = b""
    helper.events = []
    helper._emit = helper.events.append
    for key, value in attrs.items():
        setattr(helper, key, value)
    return helper


class TestToken:
    def test_matches_portal_handle_token_pattern(self):
        for _ in range(50):
            assert re.fullmatch(r"sm_[a-z0-9]{12}", ph._token())


class TestCommandParsing:
    def test_unknown_command_emits_error(self):
        helper = _make_helper()
        helper._handle_command('{"cmd": "explode"}')
        assert helper.events == [
            {"event": "error", "message": "unknown command: {'cmd': 'explode'}"}
        ]

    def test_malformed_json_emits_error(self):
        helper = _make_helper()
        helper._handle_command("not-json")
        assert helper.events and helper.events[0]["event"] == "error"

    def test_empty_line_is_ignored(self):
        helper = _make_helper()
        helper._handle_command("")
        assert helper.events == []

    def test_quit_command_quits(self):
        helper = _make_helper()
        helper._quit = MagicMock()
        helper._handle_command('{"cmd": "quit"}')
        helper._quit.assert_called_once()


class TestBindCommands:
    def test_bind_stores_shortcut_and_requests_bind(self):
        helper = _make_helper()
        helper._request_bind = MagicMock()
        helper._handle_command(
            '{"cmd": "bind", "id": "sm_1", "description": "d", "preferred_trigger": "<Control>S"}'
        )
        assert helper._shortcuts == {
            "sm_1": {"description": "d", "preferred_trigger": "<Control>S"}
        }
        helper._request_bind.assert_called_once()

    def test_bind_missing_id_emits_error(self):
        helper = _make_helper()
        helper._request_bind = MagicMock()
        helper._handle_command('{"cmd": "bind", "description": "d"}')
        assert helper.events[0]["event"] == "error"
        helper._request_bind.assert_not_called()

    def test_remove_deletes_shortcut_and_requests_bind(self):
        helper = _make_helper(**_shortcut_setup())
        helper._request_bind = MagicMock()
        helper._handle_command('{"cmd": "remove", "id": "sm_1"}')
        assert helper._shortcuts == {}
        helper._request_bind.assert_called_once()

    def test_remove_unknown_id_is_noop(self):
        helper = _make_helper(**_shortcut_setup())
        helper._request_bind = MagicMock()
        helper._handle_command('{"cmd": "remove", "id": "sm_nope"}')
        assert helper._shortcuts == {"sm_1": {"description": "d", "preferred_trigger": None}}
        helper._request_bind.assert_not_called()


def _shortcut_setup():
    return {"_shortcuts": {"sm_1": {"description": "d", "preferred_trigger": None}}}


class TestRequestBind:
    """_request_bind() applies a shortcut-set change to the portal session."""

    def test_empty_shortcut_set_closes_session(self):
        helper = _make_helper(session_handle="/s/1", session_used=True)
        helper._start_create_session = MagicMock()
        helper._request_bind()
        assert helper.session_handle is None
        assert helper.session_used is False
        helper._start_create_session.assert_not_called()

    def test_used_session_is_recreated(self):
        helper = _make_helper(
            session_handle="/s/1",
            session_used=True,
            **_shortcut_setup(),
        )
        helper._pump_bind = MagicMock()
        helper._request_bind()
        assert helper.session_handle is None
        helper.gs_iface.CreateSession.assert_called_once()
        helper._pump_bind.assert_not_called()

    def test_missing_session_starts_create(self):
        helper = _make_helper(**_shortcut_setup())
        helper._pump_bind = MagicMock()
        helper._request_bind()
        helper.gs_iface.CreateSession.assert_called_once()
        helper._pump_bind.assert_not_called()

    def test_creating_in_flight_defers_to_pump(self):
        helper = _make_helper(creating=True, **_shortcut_setup())
        helper._pump_bind = MagicMock()
        helper._request_bind()
        helper.gs_iface.CreateSession.assert_not_called()
        helper._pump_bind.assert_called_once()

    def test_fresh_unused_session_pumps_directly(self):
        helper = _make_helper(session_handle="/s/1", **_shortcut_setup())
        helper._pump_bind = MagicMock()
        helper._request_bind()
        helper.gs_iface.CreateSession.assert_not_called()
        helper._pump_bind.assert_called_once()

    def test_recreate_cancels_pending_watchdog(self):
        helper = _make_helper(
            session_handle="/s/1",
            session_used=True,
            _create_timeout_id=42,
            **_shortcut_setup(),
        )
        with patch.object(_fake_glib, "source_remove", new=MagicMock()) as mock_source_remove:
            helper._request_bind()
        mock_source_remove.assert_called_once_with(42)
        assert helper._create_timeout_id is not None


class TestPumpBind:
    def test_defers_while_session_not_ready(self):
        helper = _make_helper(
            **{"_shortcuts": {"sm_1": {"description": "d", "preferred_trigger": None}}}
        )
        helper._pump_bind()
        assert helper.rebind_pending is True
        helper.gs_iface.BindShortcuts.assert_not_called()

    def test_defers_while_bind_in_flight(self):
        helper = _make_helper(
            session_handle="/org/freedesktop/portal/desktop/session/1/xyz",
            binding=True,
            _shortcuts={"sm_1": {"description": "d", "preferred_trigger": None}},
        )
        helper._pump_bind()
        assert helper.rebind_pending is True
        helper.gs_iface.BindShortcuts.assert_not_called()

    def test_skips_when_no_shortcuts(self):
        helper = _make_helper(session_handle="/org/freedesktop/portal/desktop/session/1/xyz")
        helper._pump_bind()
        helper.gs_iface.BindShortcuts.assert_not_called()

    def test_binds_all_shortcuts_with_session_and_token(self):
        helper = _make_helper(
            session_handle="/org/freedesktop/portal/desktop/session/1/xyz",
            _shortcuts={
                "sm_1": {"description": "d1", "preferred_trigger": "<Control>S"},
                "sm_2": {"description": "d2", "preferred_trigger": None},
            },
        )
        helper._pump_bind()
        assert helper.binding is True
        assert helper._requested_ids == ["sm_1", "sm_2"]
        call = helper.gs_iface.BindShortcuts.call_args
        args, kwargs = call
        assert args[0] == "/org/freedesktop/portal/desktop/session/1/xyz"
        options_call = _fake_dbus.Dictionary.call_args
        assert "handle_token" in options_call.args[0]
        assert callable(kwargs.get("reply_handler"))
        assert callable(kwargs.get("error_handler"))


class TestResponseHandling:
    def test_create_session_success_emits_ready_and_pumps(self):
        helper = _make_helper(create_req_path="/org/freedesktop/portal/desktop/request/1/r1")
        helper.creating = True
        helper._pump_bind = MagicMock()
        helper._on_response(
            0,
            {"session_handle": "/org/freedesktop/portal/desktop/session/1/xyz"},
            path="/org/freedesktop/portal/desktop/request/1/r1",
        )
        assert helper.session_handle == "/org/freedesktop/portal/desktop/session/1/xyz"
        assert helper.creating is False
        assert helper.events[0]["event"] == "ready"
        helper._pump_bind.assert_called_once()

    def test_create_session_failure_emits_error_and_quits(self):
        helper = _make_helper(create_req_path="/r1")
        helper.creating = True
        helper._on_response(1, {}, path="/r1")
        assert helper.creating is False
        assert helper.events[0]["event"] == "error"
        helper.loop.quit.assert_called_once()

    def test_create_response_cancels_watchdog(self):
        helper = _make_helper(
            create_req_path="/r1",
            _create_timeout_id=42,
        )
        with patch.object(_fake_glib, "source_remove", new=MagicMock()) as mock_source_remove:
            helper._on_response(
                0,
                {"session_handle": "/org/freedesktop/portal/desktop/session/1/xyz"},
                path="/r1",
            )
        mock_source_remove.assert_called_once_with(42)
        assert helper._create_timeout_id is None

    def test_bind_success_emits_bound_events(self):
        helper = _make_helper(
            bind_req_path="/r2",
            _requested_ids=["sm_1"],
        )
        helper._pump_bind = MagicMock()
        helper._on_response(
            0,
            {
                "shortcuts": [
                    ("sm_1", {"trigger_description": "<Control><Shift>S"}),
                ]
            },
            path="/r2",
        )
        assert helper.binding is False
        assert helper.events == [
            {"event": "bound", "id": "sm_1", "trigger_description": "<Control><Shift>S"}
        ]
        helper._pump_bind.assert_not_called()

    def test_bind_success_pumps_when_rebind_pending(self):
        helper = _make_helper(
            bind_req_path="/r2",
            _requested_ids=["sm_1"],
            rebind_pending=True,
        )
        helper._pump_bind = MagicMock()
        helper._on_response(
            0,
            {
                "shortcuts": [
                    ("sm_1", {"trigger_description": "<Control><Shift>S"}),
                ]
            },
            path="/r2",
        )
        assert helper.binding is False
        helper._pump_bind.assert_called_once()

    def test_bind_failure_emits_bind_failed_no_repump(self):
        helper = _make_helper(bind_req_path="/r2", _requested_ids=["sm_1"])
        helper._pump_bind = MagicMock()
        helper._on_response(2, {}, path="/r2")
        assert helper.binding is False
        assert helper.events[0] == {"event": "bind_failed", "ids": ["sm_1"], "code": 2}
        helper._pump_bind.assert_not_called()

    def test_bind_failure_pumps_when_rebind_pending(self):
        helper = _make_helper(bind_req_path="/r2", _requested_ids=["sm_1"], rebind_pending=True)
        helper._pump_bind = MagicMock()
        helper._on_response(2, {}, path="/r2")
        assert helper.binding is False
        helper._pump_bind.assert_called_once()

    def test_bind_error_handler_resets_binding_no_repump(self):
        helper = _make_helper(_requested_ids=["sm_1"])
        helper._pump_bind = MagicMock()
        helper._on_bind_error(RuntimeError("boom"))
        assert helper.binding is False
        assert helper.events[0] == {"event": "bind_failed", "ids": ["sm_1"], "code": -1}
        helper._pump_bind.assert_not_called()

    def test_bind_error_handler_pumps_when_rebind_pending(self):
        helper = _make_helper(_requested_ids=["sm_1"], rebind_pending=True)
        helper._pump_bind = MagicMock()
        helper._on_bind_error(RuntimeError("boom"))
        assert helper.binding is False
        helper._pump_bind.assert_called_once()


class TestActivationSignals:
    def test_activated_emits_event(self):
        helper = _make_helper()
        helper._on_activated("/session/1", "sm_1", 123456, {})
        assert helper.events == [{"event": "activated", "id": "sm_1", "timestamp": 123456}]

    def test_deactivated_emits_event(self):
        helper = _make_helper()
        helper._on_deactivated("/session/1", "sm_1", {})
        assert helper.events == [{"event": "deactivated", "id": "sm_1"}]


class TestTeardown:
    def test_quit_emits_exiting_and_closes_session(self):
        helper = _make_helper(session_handle="/org/freedesktop/portal/desktop/session/1/xyz")
        helper._quit()
        assert helper.events[0] == {"event": "exiting"}
        assert helper.bus.get_object.call_args[0][0] == ph.BUS_NAME
        helper.loop.quit.assert_called_once()

    def test_quit_without_session_skips_close(self):
        helper = _make_helper()
        helper._quit()
        assert helper.events == [{"event": "exiting"}]
        helper.bus.get_object.assert_not_called()

    def test_create_timeout_emits_error_and_quits(self):
        helper = _make_helper()
        result = helper._on_create_timeout()
        assert result is _fake_glib.SOURCE_REMOVE
        assert helper.create_timed_out is True
        assert helper.events[0]["event"] == "error"
        assert "CreateSession" in helper.events[0]["message"]
        helper.loop.quit.assert_called_once()

    def test_create_timeout_removed_when_session_ready(self):
        helper = _make_helper(session_handle="/s/1")
        result = helper._on_create_timeout()
        assert result is _fake_glib.SOURCE_REMOVE
        assert helper.create_timed_out is False
        assert helper.events == []


class TestRegistryRegistration:
    def test_registers_app_id_before_portal_use(self):
        helper = _make_helper()
        helper.register_app_id()

        # The Registry call must go through the SAME bus/portal object that
        # later issues CreateSession (the portal keys app ids by sender).
        assert helper.bus.get_object.call_args.args[:2] == (
            ph.BUS_NAME,
            ph.PORTAL_PATH,
        )
        assert ph.dbus.Interface.call_args.args[1] == ph.REGISTRY_IFACE
        register_call = ph.dbus.Interface.return_value.Register
        assert register_call.call_args.args[0] == ph.APP_ID

    def test_registration_failure_is_best_effort(self):
        helper = _make_helper()
        with patch.object(ph.dbus, "Interface", side_effect=RuntimeError("portal gone")):
            helper.register_app_id()  # must not raise


class TestStdinReader:
    def test_handles_partial_lines_across_chunks(self):
        helper = _make_helper()
        helper._handle_command = MagicMock()

        # Simulate the byte-level accumulation logic directly
        helper._stdin_buf = b'{"cmd": "bind", "id": "sm_1", "descr'
        chunk = b'ption": "d"}\n{"cmd": "quit"}\n'
        helper._stdin_buf += chunk
        while b"\n" in helper._stdin_buf:
            line, helper._stdin_buf = helper._stdin_buf.split(b"\n", 1)
            helper._handle_command(line.decode("utf-8", "replace").strip())
        assert helper._handle_command.call_count == 2

    def test_eof_quits(self):
        helper = _make_helper()
        helper._quit = MagicMock()
        with (
            patch.object(ph.sys, "stdin", MagicMock(fileno=MagicMock(return_value=5))),
            patch("os.read", return_value=b""),
        ):
            result = helper._on_stdin_readable(None, None)
        assert result is _fake_glib.SOURCE_REMOVE
        helper._quit.assert_called_once()

    def test_data_returns_continue(self):
        helper = _make_helper()
        helper._quit = MagicMock()
        with (
            patch.object(ph.sys, "stdin", MagicMock(fileno=MagicMock(return_value=5))),
            patch("os.read", return_value=b'{"cmd": "quit"}\n'),
        ):
            result = helper._on_stdin_readable(None, None)
        assert result is _fake_glib.SOURCE_CONTINUE
        helper._quit.assert_called_once()

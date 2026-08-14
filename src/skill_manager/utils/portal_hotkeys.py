"""
Persistent FreeDesktop portal GlobalShortcuts helper subprocess.

Usage:
    <python-with-dbus> /path/to/portal_hotkeys.py

Long-lived bridge between SkillManager and the
``org.freedesktop.portal.GlobalShortcuts`` portal. A portal session dies the
moment its D-Bus connection closes, so the session must live in a dedicated
process rather than the PySide6 app (whose event loop also conflicts with the
GLib mainloop this script requires).

The helper owns the full lifecycle: create session → bind shortcuts → forward
``Activated``/``Deactivated`` signals → close on quit.

stdin — JSON commands (one per line):
    {"cmd": "bind", "id": "<portal-id>", "description": "...",
     "preferred_trigger": "<gtk-accelerator>"}
        Register or update one shortcut. Re-binds the *full* shortcut list
        (portal semantics) and may open a system dialog for the user to assign
        the trigger — there is deliberately NO timeout on this call. The portal
        allows only one BindShortcuts per session, so any change after the
        first bind runs against a freshly created session.
    {"cmd": "remove", "id": "<portal-id>"}
        Remove a shortcut; re-binds the remaining list on a fresh session, or
        closes the session when the last shortcut is removed.
    {"cmd": "quit"}
        Close the portal session and exit 0.

stdout — JSON events (one per line, flushed immediately):
    {"event": "ready", "session": "<object-path>"}   session created, accepting binds
    {"event": "bound", "id": "...", "trigger_description": "..."}  trigger assigned
    {"event": "bind_failed", "ids": [...], "code": <int>}  dialog cancelled / error
    {"event": "activated", "id": "...", "timestamp": <int>}  user pressed the shortcut
    {"event": "deactivated", "id": "..."}  shortcut became unavailable (stolen/disabled)
    {"event": "error", "message": "..."}   fatal; helper is exiting
    {"event": "exiting"}                   emitted just before exit 0

Environment:
    Runs standalone (no Qt), so it is unit-testable only via subprocess
    interaction — mirrors the portal_capture.py precedent.
"""

import json
import os
import sys
import uuid

# ---------------------------------------------------------------------
# Delay-import dbus + gi so a missing dependency produces an actionable
# error on stderr instead of a traceback (same pattern as portal_capture.py).
# ---------------------------------------------------------------------
try:
    import dbus
    import dbus.mainloop.glib
    from gi.repository import GLib
except ImportError as exc:
    print(
        f"portal_hotkeys: missing dependency — {exc}. Install python3-dbus and python3-gi.",
        file=sys.stderr,
    )
    sys.exit(1)

BUS_NAME = "org.freedesktop.portal.Desktop"
PORTAL_PATH = "/org/freedesktop/portal/desktop"
GS_IFACE = "org.freedesktop.portal.GlobalShortcuts"
REQUEST_IFACE = "org.freedesktop.portal.Request"
SESSION_IFACE = "org.freedesktop.portal.Session"
REGISTRY_IFACE = "org.freedesktop.host.portal.Registry"

# App id associated with this D-Bus peer via Registry.Register. Must match
# the basename of an installed .desktop file (skill-manager.desktop) — see
# data/org.freedesktop.host.portal.Registry.xml in xdg-desktop-portal.
APP_ID = "skill-manager"

# How long to wait for the CreateSession Response before giving up. A session
# is created in milliseconds on a healthy portal; a >10s stall means the portal
# crashed or hung. This MUST NOT apply to BindShortcuts — the user may take
# arbitrarily long to assign a trigger in the system dialog.
CREATE_TIMEOUT_SECONDS = 10


def _token() -> str:
    """Portal handle token — must match ``^[a-z_][a-z0-9_]*$``."""
    return "sm_" + uuid.uuid4().hex[:12]


class _PortalHelper:
    """State machine for the GlobalShortcuts portal session."""

    def __init__(self) -> None:
        self.loop = GLib.MainLoop()
        # MUST be set before the first SessionBus() — dbus-python raises
        # RuntimeError otherwise when making async calls or receiving signals.
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

        self.bus = dbus.SessionBus()
        portal_obj = self.bus.get_object(BUS_NAME, PORTAL_PATH)
        self.gs_iface = dbus.Interface(portal_obj, GS_IFACE)

        self.session_handle: str | None = None
        self.create_req_path: str | None = None
        self.bind_req_path: str | None = None
        self.binding = False  # a BindShortcuts request is in flight
        self.rebind_pending = False  # shortcuts changed while a bind was in flight
        self.session_used = False  # BindShortcuts already attempted on this session
        self.creating = False  # a CreateSession request is in flight
        self.create_timed_out = False
        self._create_timeout_id: int | None = None
        self._shortcuts: dict[str, dict[str, str | None]] = {}
        # id -> {"description": str|None, "preferred_trigger": str|None}
        self._requested_ids: list[str] = []
        self._stdin_buf = b""

        self.bus.add_signal_receiver(
            self._on_response,
            signal_name="Response",
            dbus_interface=REQUEST_IFACE,
            bus_name=BUS_NAME,
            path_keyword="path",
        )
        self.bus.add_signal_receiver(
            self._on_activated,
            signal_name="Activated",
            dbus_interface=GS_IFACE,
            bus_name=BUS_NAME,
        )
        self.bus.add_signal_receiver(
            self._on_deactivated,
            signal_name="Deactivated",
            dbus_interface=GS_IFACE,
            bus_name=BUS_NAME,
        )
        GLib.io_add_watch(sys.stdin.fileno(), GLib.IO_IN, self._on_stdin_readable)

    # ------------------------------------------------------ portal identity
    def register_app_id(self) -> None:
        """Claim this D-Bus peer's app id via the host Registry portal.

        xdg-desktop-portal derives a host app's id from its systemd user
        unit (``app-*`` scope + matching .desktop file); launched from a
        plain terminal the helper lands in ``ptyxis-spawn-*.scope``, so
        CreateSession is rejected with "An app id is required". Registering
        the peer explicitly is the documented mechanism for unsandboxed apps
        and must happen before any portal method call on this connection.
        Best-effort: on failure we keep going — in an ``app-*`` scope the
        portal already knows the id and CreateSession works without it.
        """
        try:
            registry = dbus.Interface(self.bus.get_object(BUS_NAME, PORTAL_PATH), REGISTRY_IFACE)
            registry.Register(APP_ID, dbus.Dictionary({}, signature="sv"))
        except Exception as exc:  # best-effort registration, never fatal
            print(f"   !! Registry.Register({APP_ID}) failed: {exc}", file=sys.stderr)
        else:
            print(f"   -> Registry.Register({APP_ID})", file=sys.stderr)

    # ------------------------------------------------------------ events
    def _emit(self, event: dict) -> None:
        print(json.dumps(event), flush=True)

    def _emit_error(self, message: str) -> None:
        self._emit({"event": "error", "message": message})

    # -------------------------------------------------------- stdin reader
    def _on_stdin_readable(self, _source: object, _condition: object) -> bool:
        """Read raw bytes so partial lines never block the GLib loop."""
        try:
            chunk = os.read(sys.stdin.fileno(), 4096)
        except OSError:
            chunk = b""
        if not chunk:  # parent closed the pipe
            self._quit()
            return GLib.SOURCE_REMOVE
        self._stdin_buf += chunk
        while b"\n" in self._stdin_buf:
            line, self._stdin_buf = self._stdin_buf.split(b"\n", 1)
            self._handle_command(line.decode("utf-8", "replace").strip())
        return GLib.SOURCE_CONTINUE

    def _handle_command(self, line: str) -> None:
        if not line:
            return
        try:
            command = json.loads(line)
        except json.JSONDecodeError:
            self._emit_error(f"invalid command: {line[:200]!r}")
            return
        cmd = command.get("cmd")
        if cmd == "bind":
            self._on_bind_command(command)
        elif cmd == "remove":
            self._on_remove_command(command)
        elif cmd == "quit":
            self._quit()
        else:
            self._emit_error(f"unknown command: {command!r}")

    # ------------------------------------------------------------ commands
    def _on_bind_command(self, command: dict) -> None:
        shortcut_id = command.get("id")
        if not isinstance(shortcut_id, str) or not shortcut_id:
            self._emit_error("bind: missing 'id'")
            return
        self._shortcuts[shortcut_id] = {
            "description": command.get("description"),
            "preferred_trigger": command.get("preferred_trigger"),
        }
        self._request_bind()

    def _on_remove_command(self, command: dict) -> None:
        shortcut_id = command.get("id")
        if shortcut_id in self._shortcuts:
            del self._shortcuts[shortcut_id]
            self._request_bind()

    def _request_bind(self) -> None:
        """Apply a shortcut-set change, recreating the session if needed.

        The GlobalShortcuts portal allows only ONE BindShortcuts call per
        session ("An application can only attempt bind shortcuts of a
        session once"), so any change after the initial bind — new shortcut,
        trigger edit, removal — must run against a fresh session. We close
        the old one and start over; the CreateSession response handler
        re-pumps the bind for the new session.

        An empty shortcut set (last shortcut removed) closes the session
        outright — the portal unbinds everything a session owns on close.
        """
        if not self._shortcuts:
            self._close_session()
            return
        if self.session_handle is not None and self.session_used:
            print("   -> session recreated for shortcut change", file=sys.stderr)
            self._close_session()
            self._start_create_session()
            return
        if self.session_handle is None and not self.creating:
            # No live session (startup race, or one was closed after the
            # last shortcut was removed) — start a fresh one now.
            self._start_create_session()
            return
        self._pump_bind()

    def _start_create_session(self) -> None:
        """Issue CreateSession with fresh tokens and (re)arm the timeout."""
        self.creating = True
        self._arm_create_timeout()
        print("   -> CreateSession (handle_token + session_handle_token)", file=sys.stderr)
        self.gs_iface.CreateSession(
            dbus.Dictionary(
                {
                    "handle_token": dbus.String(_token()),
                    "session_handle_token": dbus.String(_token()),
                },
                signature="sv",
            ),
            reply_handler=self._on_create_reply,
            error_handler=self._on_create_error,
        )

    def _arm_create_timeout(self) -> None:
        """(Re)arm the CreateSession watchdog; replaces any pending one."""
        self._cancel_create_timeout()
        self._create_timeout_id = GLib.timeout_add_seconds(
            CREATE_TIMEOUT_SECONDS, self._on_create_timeout
        )

    def _cancel_create_timeout(self) -> None:
        if self._create_timeout_id is not None:
            GLib.source_remove(self._create_timeout_id)
            self._create_timeout_id = None

    def _on_create_error(self, error: Exception) -> None:
        self.creating = False
        self._cancel_create_timeout()
        self._emit_error(f"CreateSession: {error}")
        self.loop.quit()

    def _close_session(self) -> None:
        """Best-effort close of the current portal session and state reset."""
        if self.session_handle is not None:
            try:
                session_obj = self.bus.get_object(BUS_NAME, dbus.ObjectPath(self.session_handle))
                dbus.Interface(session_obj, SESSION_IFACE).Close()
            except Exception as exc:  # best-effort close
                print(f"   !! session close failed: {exc}", file=sys.stderr)
        self.session_handle = None
        self.create_req_path = None
        self.bind_req_path = None
        self.binding = False
        self.rebind_pending = False
        self.session_used = False
        self.creating = False
        self._cancel_create_timeout()

    def _pump_bind(self) -> None:
        """Serialize BindShortcuts calls: the portal shows ONE dialog at a time.

        The shortcut list is replaced wholesale on every call (portal
        semantics), so a command that arrives mid-bind is folded into the next
        full-list bind.
        """
        if self.session_handle is None or self.binding:
            self.rebind_pending = True
            return
        if not self._shortcuts:
            return
        self.rebind_pending = False
        self.binding = True
        self.session_used = True
        shortcuts = dbus.Array(
            [
                dbus.Struct(
                    (
                        dbus.String(shortcut_id),
                        dbus.Dictionary(
                            {k: dbus.String(v) for k, v in opts.items() if v},
                            signature="sv",
                        ),
                    ),
                    signature=None,
                )
                for shortcut_id, opts in self._shortcuts.items()
            ],
            signature="(sa{sv})",
        )
        print(
            f"   -> BindShortcuts ({', '.join(self._shortcuts)})",
            file=sys.stderr,
        )
        self._requested_ids = list(self._shortcuts)
        self.gs_iface.BindShortcuts(
            dbus.ObjectPath(self.session_handle),
            shortcuts,
            dbus.String(""),
            dbus.Dictionary({"handle_token": dbus.String(_token())}, signature="sv"),
            reply_handler=self._on_bind_reply,
            error_handler=self._on_bind_error,
        )

    # ------------------------------------------------------------ callbacks
    def _on_create_reply(self, *args: object) -> None:
        if args:
            self.create_req_path = str(args[0])

    def _on_bind_reply(self, *args: object) -> None:
        if args:
            self.bind_req_path = str(args[0])

    def _on_bind_error(self, error: Exception) -> None:
        self.binding = False
        self._emit({"event": "bind_failed", "ids": self._requested_ids, "code": -1})
        print(f"   !! BindShortcuts error: {error}", file=sys.stderr)
        if self.rebind_pending:
            self._pump_bind()

    def _on_response(self, response: int, results: dict, path: str | None = None) -> None:
        """Response signal for CreateSession / BindShortcuts requests."""
        if path == self.create_req_path:
            self.creating = False
            self._cancel_create_timeout()
            if response == 0 and isinstance(results, dict):
                session = results.get("session_handle")
                if session:
                    self.session_handle = str(session)
                    print(f"   -> session: {self.session_handle}", file=sys.stderr)
                    self._emit({"event": "ready", "session": self.session_handle})
                    self._pump_bind()
            else:
                self._emit_error(f"CreateSession response code={response}")
                self.loop.quit()
            return
        if path == self.bind_req_path:
            self.binding = False
            if response == 0 and isinstance(results, dict):
                self._on_bind_success(results)
            else:
                self._emit(
                    {
                        "event": "bind_failed",
                        "ids": self._requested_ids,
                        "code": int(response),
                    }
                )
                print(f"   !! bind response code={response}", file=sys.stderr)
            if self.rebind_pending:
                self._pump_bind()

    def _on_bind_success(self, results: dict) -> None:
        shortcuts = results.get("shortcuts")
        if not shortcuts:
            return
        for item in shortcuts:
            try:
                shortcut_id = str(item[0])
                options = item[1] or {}
            except (IndexError, TypeError):
                continue
            trigger = str(options.get("trigger_description") or "")
            self._emit({"event": "bound", "id": shortcut_id, "trigger_description": trigger})

    def _on_activated(
        self,
        _session_handle: object,
        shortcut_id: str,
        timestamp: int,
        options: dict,
    ) -> None:
        print(f"   -> Activated {shortcut_id}", file=sys.stderr)
        event = {
            "event": "activated",
            "id": str(shortcut_id),
            "timestamp": int(timestamp),
        }
        if isinstance(options, dict) and "activation_token" in options:
            event["activation_token"] = str(options["activation_token"])
        self._emit(event)

    def _on_deactivated(self, _session_handle: object, shortcut_id: str, _options: dict) -> None:
        self._emit({"event": "deactivated", "id": str(shortcut_id)})

    def _on_create_timeout(self) -> bool:
        if self.session_handle is not None:
            return GLib.SOURCE_REMOVE
        self.create_timed_out = True
        self._create_timeout_id = None  # the source has already fired
        self._emit_error(
            "no CreateSession Response within "
            f"{CREATE_TIMEOUT_SECONDS}s — portal unavailable or crashed"
        )
        self.loop.quit()
        return GLib.SOURCE_REMOVE

    # ------------------------------------------------------------- teardown
    def _quit(self) -> None:
        self._emit({"event": "exiting"})
        self._close_session()
        self.loop.quit()


def _main() -> None:
    helper = _PortalHelper()
    # Unsandboxed apps must claim an app id BEFORE any portal method call,
    # otherwise the GlobalShortcuts portal rejects CreateSession with
    # "An app id is required" when launched from a plain terminal.
    helper.register_app_id()
    # BOTH handle_token and session_handle_token are mandatory: without
    # session_handle_token, xdg-desktop-portal 1.21.1 aborts the whole portal
    # process (flatpak/xdg-desktop-portal#2037) instead of replying.
    helper._start_create_session()
    helper.loop.run()
    sys.exit(1 if helper.create_timed_out else 0)


if __name__ == "__main__":
    _main()

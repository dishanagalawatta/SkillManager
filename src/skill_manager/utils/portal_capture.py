"""
Standalone Wayland portal screenshot capture script.

Usage:
    /usr/bin/python3 /path/to/portal_capture.py <output_path>

Captures the full screen silently via the FreeDesktop Portal Screenshot API
(``interactive: False`` — no system UI) and copies the result PNG to
``<output_path>``. Prints the output path on success, exits with code 1
on failure or timeout.

Intended to be spawned as a subprocess by the screenshot controller because
the GLib mainloop it requires conflicts with PySide6's event loop when
running in-process.
"""

import os
import shutil
import sys
import uuid
from urllib.parse import unquote


def _main() -> None:
    if len(sys.argv) < 2:
        print("Usage: portal_capture.py <output_path>", file=sys.stderr)
        sys.exit(1)

    output_path = sys.argv[1]

    # ------------------------------------------------------------------
    # Delay-import dbus-python so ImportError is caught here rather
    # than at top-level — keeps the message actionable.
    # ------------------------------------------------------------------
    try:
        import dbus
        import dbus.mainloop.glib
        from gi.repository import GLib
    except ImportError as exc:
        print(
            f"portal_capture: missing dependency — {exc}. Install python3-dbus and python3-gi.",
            file=sys.stderr,
        )
        sys.exit(1)

    # MUST set the default mainloop BEFORE creating any SessionBus,
    # otherwise dbus-python raises RuntimeError when trying to receive
    # signals or make async calls.  dbus.SessionBus() is a singleton,
    # so the first call creates the shared connection for the process.
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

    # ------------------------------------------------------------------
    # Try to pre-authorise via PermissionStore before the portal call.
    # This is best-effort: if it fails, the portal may show a dialog
    # or fail — we still try the Screenshot call regardless.
    # ------------------------------------------------------------------
    _pre_authorize_portal()

    handle_token = "sm_" + uuid.uuid4().hex[:12]
    result: dict[str, str | None] = {"path": None}

    loop = GLib.MainLoop()
    bus = dbus.SessionBus()

    def response_handler(
        response: int,
        results: dict,
        path: str | None = None,  # injected via path_keyword
    ) -> None:
        """Callback invoked when the portal emits the Response signal."""
        print(f"   <- Response code={response} path={path}", file=sys.stderr)
        if response == 0 and isinstance(results, dict):
            uri = results.get("uri", "")
            if uri:
                local_path = unquote(str(uri).replace("file://", "", 1))
                if os.path.isfile(local_path):
                    shutil.copy2(local_path, output_path)
                    result["path"] = output_path
                else:
                    print(f"   -> file not found: {local_path}", file=sys.stderr)
        elif response == 1:
            print("   -> denied by user", file=sys.stderr)
        elif response == 2:
            print("   -> cancelled", file=sys.stderr)
        else:
            print(f"   -> unexpected response {response}", file=sys.stderr)
        loop.quit()

    bus.add_signal_receiver(
        response_handler,
        signal_name="Response",
        dbus_interface="org.freedesktop.portal.Request",
        bus_name="org.freedesktop.portal.Desktop",
        path_keyword="path",
    )

    portal_obj = bus.get_object(
        "org.freedesktop.portal.Desktop",
        "/org/freedesktop/portal/desktop",
    )
    screenshot_iface = dbus.Interface(portal_obj, "org.freedesktop.portal.Screenshot")

    def on_error(e: Exception) -> None:
        print(f"   !! async error: {e}", file=sys.stderr)
        loop.quit()

    def on_reply(*args: object) -> None:
        """Callback invoked when the portal acknowledges the Screenshot request."""
        print(f"   -> request accepted: {args}", file=sys.stderr)

    # Non-interactive: silent full-screen capture, no system UI
    print(
        f"   -> calling Screenshot (handle_token={handle_token})",
        file=sys.stderr,
    )
    screenshot_iface.Screenshot(
        "",
        {"handle_token": handle_token, "interactive": False},
        reply_handler=on_reply,
        error_handler=on_error,
    )

    # Safety timeout — if portal never responds, don't hang forever
    GLib.timeout_add_seconds(20, loop.quit)
    loop.run()

    if result["path"] and os.path.isfile(str(result["path"])):
        print(str(result["path"]))
        sys.exit(0)

    print("   !! no Response signal received within 20s", file=sys.stderr)
    sys.exit(1)


def _pre_authorize_portal() -> None:
    """Pre-authorise screenshot portal access via PermissionStore.

    Best-effort; silently ignored if PermissionStore is not available.
    xdg-desktop-portal resolves the caller's *permissions ID* (from the
    systemd user unit or snap metadata) and looks it up in the
    ``screenshot`` table under the permission ID ``screenshot``; a
    missing key forces the interactive dialog, which GNOME refuses for
    unfocused apps.  Write ``['yes']`` for every ID the app can resolve
    to (terminal launch → ``""``, desktop launch → ``skill-manager``).
    """
    try:
        import dbus
    except ImportError:
        return

    try:
        bus = dbus.SessionBus()
        store_obj = bus.get_object(
            "org.freedesktop.impl.portal.PermissionStore",
            "/org/freedesktop/impl/portal/PermissionStore",
        )
        store_iface = dbus.Interface(
            store_obj,
            "org.freedesktop.impl.portal.PermissionStore",
        )
        for permission_id in ("", "skill-manager", "skill-manager.desktop"):
            store_iface.SetPermission(
                "screenshot",
                True,
                "screenshot",
                permission_id,
                ["yes"],
            )
    except Exception:
        pass  # best-effort


if __name__ == "__main__":
    _main()

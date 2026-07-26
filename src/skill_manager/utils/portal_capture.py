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

import dbus
import dbus.mainloop.glib
from gi.repository import GLib


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: portal_capture.py <output_path>", file=sys.stderr)
        sys.exit(1)

    output_path = sys.argv[1]
    handle_token = "sm_" + uuid.uuid4().hex[:12]
    result: dict[str, str | None] = {"path": None}

    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    loop = GLib.MainLoop()
    bus = dbus.SessionBus()

    def response_handler(response: int, results: dict) -> None:
        if response == 0 and isinstance(results, dict):
            uri = results.get("uri", "")
            if uri:
                local_path = unquote(str(uri).replace("file://", "", 1))
                if os.path.isfile(local_path):
                    shutil.copy2(local_path, output_path)
                    result["path"] = output_path
        loop.quit()

    bus.add_signal_receiver(
        response_handler,
        signal_name="Response",
        dbus_interface="org.freedesktop.portal.Request",
        bus_name="org.freedesktop.portal.Desktop",
    )

    portal_obj = bus.get_object(
        "org.freedesktop.portal.Desktop",
        "/org/freedesktop/portal/desktop",
    )
    screenshot_iface = dbus.Interface(portal_obj, "org.freedesktop.portal.Screenshot")

    def on_error(e: Exception) -> None:
        print(str(e), file=sys.stderr)
        loop.quit()

    # Non-interactive: silent full-screen capture, no system UI
    screenshot_iface.Screenshot(
        "",
        {"handle_token": handle_token, "interactive": False},
        reply_handler=lambda *_: None,
        error_handler=on_error,
    )

    # Safety timeout — if portal never responds, don't hang forever
    GLib.timeout_add_seconds(20, loop.quit)
    loop.run()

    if result["path"] and os.path.isfile(str(result["path"])):
        print(str(result["path"]))
        sys.exit(0)

    sys.exit(1)


if __name__ == "__main__":
    main()

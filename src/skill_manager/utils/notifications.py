"""Desktop notification delivery via the freedesktop D-Bus Notifications API.

Used to tell the user the capture overlay is waiting for the app to become
active again (see Main.qml ``captureActivationTimer``): on GNOME Wayland a
global hotkey does not carry an xdg-activation token, so the overlay can only
map on top of the ACTIVE app.  The notification gives the user a clickable
target that restores focus, and the click itself is the guaranteed active
interaction that lets the overlay raise above the previously-active window.

Notifications must NEVER be sent from tests or headless processes (no bus to
talk to, and nothing to show); those environments set ``PYTEST_CURRENT_TEST``
and/or ``QT_QPA_PLATFORM=offscreen``.
"""

from __future__ import annotations

import os

from PySide6.QtDBus import QDBus, QDBusConnection, QDBusMessage

_SERVICE = "org.freedesktop.Notifications"
_PATH = "/org/freedesktop/Notifications"
_INTERFACE = "org.freedesktop.Notifications"
_METHOD_NOTIFY = "Notify"
_METHOD_CLOSE = "CloseNotification"

# Describes the app to the notification daemon (name, vendor, version, icon).
_APP_ID = "skill-manager"

_last_notification_id = 0


def notifications_enabled() -> bool:
    """Return True only in a real interactive desktop session.

    Mirrors ``input_guard.injection_allowed``: never send notifications from
    tests, CI, or headless processes.
    """
    if "PYTEST_CURRENT_TEST" in os.environ:
        return False
    return os.environ.get("QT_QPA_PLATFORM") != "offscreen"


def send_notification(title: str, body: str) -> int:
    """Show a desktop notification, best-effort (never raises).

    Uses ``org.freedesktop.Notifications.Notify`` with a 0-millisecond
    expiry so the notification stays until dismissed or clicked.  Clicking it
    restores focus to the app, which lets the capture overlay map on top.
    Failures (no daemon, no session bus, offscreen/test environment) are
    silently ignored — the notification is a convenience, not a requirement.

    Returns the notification ID, or 0 when nothing could be sent.
    """
    global _last_notification_id
    if not notifications_enabled():
        return 0
    session_bus = QDBusConnection.sessionBus()
    if not session_bus.isConnected():
        return 0
    message = QDBusMessage.createMethodCall(_SERVICE, _PATH, _INTERFACE, _METHOD_NOTIFY)
    message.setArguments([_APP_ID, 0, "", title, body, [], {}, 0])
    # QDBus.CallMode enum required — a raw int raises TypeError on PySide6 6.11.
    reply = session_bus.call(message, QDBus.CallMode.Block, 500)
    try:
        notification_id = int(reply.arguments()[0])
    except (IndexError, TypeError, ValueError):
        notification_id = 0
    if notification_id:
        _last_notification_id = notification_id
    return notification_id


def close_notification() -> None:
    """Close the last notification sent by this module, best-effort."""
    global _last_notification_id
    if not notifications_enabled() or not _last_notification_id:
        return
    session_bus = QDBusConnection.sessionBus()
    if not session_bus.isConnected():
        return
    message = QDBusMessage.createMethodCall(_SERVICE, _PATH, _INTERFACE, _METHOD_CLOSE)
    message.setArguments([_last_notification_id])
    session_bus.call(message, QDBus.CallMode.Block, 500)
    _last_notification_id = 0

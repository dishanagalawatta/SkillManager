"""Unit tests for the desktop notification utility."""

import pytest

from skill_manager.utils import notifications


class _FakeReply:
    def __init__(self, arguments):
        self._arguments = arguments

    def arguments(self):
        return self._arguments


class _FakeBus:
    def __init__(self, reply_arguments=(7,)):
        self._reply_arguments = reply_arguments
        self.calls = []
        self.connected = True

    # Mirrors PySide6 QDBusConnection.isConnected() camelCase API.
    def isConnected(self):  # noqa: N802
        return self.connected

    def call(self, message, mode, timeout):
        self.calls.append((message, mode, timeout))
        return _FakeReply(list(self._reply_arguments))


@pytest.fixture
def fake_bus(monkeypatch):
    bus = _FakeBus()
    monkeypatch.setattr(
        notifications.QDBusConnection,
        "sessionBus",
        staticmethod(lambda: bus),
    )
    monkeypatch.setattr(notifications, "notifications_enabled", lambda: True)
    return bus


def test_notifications_disabled_under_pytest():
    assert notifications.notifications_enabled() is False


def test_send_notification_noop_when_disabled(monkeypatch):
    def fail_bus(*_args, **_kwargs):
        raise AssertionError("session bus must not be touched when disabled")

    monkeypatch.setattr(notifications.QDBusConnection, "sessionBus", fail_bus)
    assert notifications.send_notification("Title", "Body") == 0


def test_close_notification_noop_when_disabled(monkeypatch):
    def fail_bus(*_args, **_kwargs):
        raise AssertionError("session bus must not be touched when disabled")

    monkeypatch.setattr(notifications.QDBusConnection, "sessionBus", fail_bus)
    notifications.close_notification()


def test_send_notification_sends_notify_call(fake_bus):
    notification_id = notifications.send_notification("Title", "Body")

    assert notification_id == 7
    assert len(fake_bus.calls) == 1
    message, mode, timeout = fake_bus.calls[0]
    assert message.service() == "org.freedesktop.Notifications"
    assert message.path() == "/org/freedesktop/Notifications"
    assert message.interface() == "org.freedesktop.Notifications"
    assert message.member() == "Notify"
    # [app_id, replaces_id, icon, title, body, actions, hints, timeout]
    assert message.arguments()[0] == "skill-manager"
    assert message.arguments()[1] == 0
    assert message.arguments()[3] == "Title"
    assert message.arguments()[4] == "Body"
    assert message.arguments()[7] == 0  # no expiry
    assert mode == 1  # QDBusConnection.NoEventLoop


def test_close_notification_closes_last_sent(fake_bus):
    notifications.send_notification("Title", "Body")

    notifications.close_notification()

    assert len(fake_bus.calls) == 2
    close_message = fake_bus.calls[1][0]
    assert close_message.member() == "CloseNotification"
    assert close_message.arguments() == [7]


def test_close_notification_noop_when_nothing_sent(fake_bus):
    notifications.close_notification()
    assert fake_bus.calls == []


def test_send_notification_no_reply_returns_zero(fake_bus, monkeypatch):
    monkeypatch.setattr(
        notifications.QDBusConnection,
        "sessionBus",
        staticmethod(lambda: _FakeBus(reply_arguments=())),
    )
    assert notifications.send_notification("Title", "Body") == 0

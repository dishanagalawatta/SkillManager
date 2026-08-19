from unittest.mock import MagicMock, patch

from skill_manager.utils.qt_threading import schedule_on_ui_thread


def test_schedule_on_ui_thread_runs_immediate_callback_on_receiver():
    receiver = MagicMock()
    callback = MagicMock()

    with patch("skill_manager.utils.qt_threading.QTimer.singleShot") as single_shot:
        schedule_on_ui_thread(receiver, callback)

    single_shot.assert_called_once_with(0, receiver, callback)


def test_schedule_on_ui_thread_starts_delayed_timer_after_ui_handoff():
    receiver = MagicMock()
    callback = MagicMock()
    calls = []

    def fake_single_shot(delay_ms, receiver_arg, callback_arg):
        calls.append((delay_ms, receiver_arg, callback_arg))
        if delay_ms == 0:
            callback_arg()

    with patch(
        "skill_manager.utils.qt_threading.QTimer.singleShot",
        side_effect=fake_single_shot,
    ):
        schedule_on_ui_thread(receiver, callback, delay_ms=200)

    assert [call[0] for call in calls] == [0, 200]
    assert calls[0][1] is receiver
    assert calls[1][1] is receiver
    callback.assert_not_called()

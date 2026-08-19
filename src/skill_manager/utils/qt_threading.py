"""
Purpose: Provides small Qt thread-handoff helpers for controller callbacks.
Usage: Schedule UI callbacks from worker threads without starting delayed timers there.
"""

from collections.abc import Callable

from PySide6.QtCore import QObject, QTimer


def schedule_on_ui_thread(
    receiver: QObject,
    callback: Callable[[], None],
    *,
    delay_ms: int = 0,
) -> None:
    """Run callback on receiver's thread, creating delayed timers there."""
    if delay_ms <= 0:
        QTimer.singleShot(0, receiver, callback)
        return

    def start_delayed_timer() -> None:
        QTimer.singleShot(delay_ms, receiver, callback)

    QTimer.singleShot(0, receiver, start_delayed_timer)

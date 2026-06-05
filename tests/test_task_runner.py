import asyncio
import threading

from skill_manager.utils.task_runner import (
    BackgroundTaskRunner,
    QtAsyncioTaskRunner,
    SynchronousTaskRunner,
)


def test_synchronous_task_runner():
    runner = SynchronousTaskRunner()
    result = []

    def task(val):
        result.append(val)
        return val * 2

    ret = runner.run(task, args=(10,))

    assert result == [10]
    assert ret == 20


def test_background_task_runner():
    runner = BackgroundTaskRunner()
    result = []
    event = threading.Event()

    def task(val):
        # Ensure we are in a different thread
        if threading.current_thread() is not threading.main_thread():
            result.append(val)
        event.set()

    runner.run(task, args=(5,))

    # Wait for the background thread to finish
    assert event.wait(timeout=1.0)
    assert result == [5]


def test_synchronous_task_runner_kwargs():
    runner = SynchronousTaskRunner()

    def task(a=1, b=2):
        return a + b

    assert runner.run(task, kwargs={"a": 10, "b": 20}) == 30


def test_background_task_runner_no_args():
    runner = BackgroundTaskRunner()
    event = threading.Event()

    def task():
        event.set()

    runner.run(task)
    assert event.wait(timeout=1.0)


def test_task_runner_submit_invokes_callback():
    seen = []
    runner = SynchronousTaskRunner()

    runner.submit(lambda: "done", seen.append)

    assert seen == ["done"]


def test_qt_asyncio_task_runner_runs_coroutine_without_qtasyncio(monkeypatch):
    runner = QtAsyncioTaskRunner()
    monkeypatch.setattr("skill_manager.utils.task_runner.QtAsyncio", None)

    async def work():
        await asyncio.sleep(0)
        return "async-done"

    assert runner.run(work) == "async-done"

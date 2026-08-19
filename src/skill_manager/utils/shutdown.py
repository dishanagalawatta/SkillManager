"""Shutdown diagnostics and watchdog failsafe.

Historically these lived inline in ``app.py``: temporary crash-instrumentation
that dumped a 15 MB ``shutdown_diag.log`` into the repository root on every
quit. They are now isolated here so the application module stays focused, the
log lands in the user data dir, and the dump is opt-in via ``SKILL_MANAGER_DIAG=1``.
"""

import contextlib
import os
import threading
import time

from skill_manager.core.config import DATA_DIR

DIAG_FILE = DATA_DIR / "shutdown_diag.log"

_diag_lock = threading.Lock()


def dump_diagnostics(reason: str) -> None:
    """Write comprehensive stack traces, threads, and child processes to the diag log.

    Runs during shutdown steps or from the watchdog thread to identify hangs.
    No-op unless ``SKILL_MANAGER_DIAG=1`` is set — otherwise every quit would
    append to the log indefinitely.
    """
    if os.environ.get("SKILL_MANAGER_DIAG") != "1":
        return
    try:
        import sys
        import traceback

        import psutil

        # Query child processes info
        child_info = []
        try:
            parent = psutil.Process(os.getpid())
            for child in parent.children(recursive=True):
                with contextlib.suppress(Exception):
                    child_info.append(f"{child.name()}({child.pid})[{child.status()}]")
        except Exception as e:
            child_info.append(f"error:{e}")

        children_str = ",".join(child_info) if child_info else "none"

        # Print a clear diagnostic message directly to the terminal
        console_msg = f"[SHUTDOWN_DIAG] {reason} (PID: {os.getpid()}, Threads: {threading.active_count()}, Children: {children_str})\n"
        with contextlib.suppress(Exception):
            os.write(2, console_msg.encode())

        with _diag_lock, DIAG_FILE.open("a", encoding="utf-8") as f:
            f.write(f"\n================ DIAGNOSTICS: {reason} ================\n")
            f.write(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"PID: {os.getpid()}\n")
            f.write(f"Active Threads count: {threading.active_count()}\n")

            # Log children in detail
            f.write(f"\n--- CHILD PROCESSES ({len(child_info)}) ---\n")
            try:
                parent = psutil.Process(os.getpid())
                for child in parent.children(recursive=True):
                    try:
                        f.write(
                            f"PID: {child.pid}, Name: {child.name()}, Status: {child.status()}, Created: {child.create_time()}\n"
                        )
                    except Exception as e:
                        f.write(f"PID: {child.pid} error: {e}\n")
            except Exception as e:
                f.write(f"Failed to get children: {e}\n")

            f.write("\n--- THREAD LIST ---\n")
            for t in threading.enumerate():
                daemon_str = "daemon" if t.daemon else "non-daemon"
                f.write(f"Thread: {t.name} (ID: {t.ident}, {daemon_str}, alive: {t.is_alive()})\n")

            f.write("\n--- STACK TRACES ---\n")
            for thread_id, frame in sys._current_frames().items():
                t = next((x for x in threading.enumerate() if x.ident == thread_id), None)
                t_name = t.name if t else "Unknown"
                f.write(f"\nStack for thread {t_name} (ID {thread_id}):\n")
                traceback.print_stack(frame, file=f)

            f.write("\n=======================================================\n")
    except Exception as e:
        with contextlib.suppress(Exception):
            os.write(2, f"Failed to dump diagnostics: {e}\n".encode())


def watchdog_exit(ret: int, timeout: float = 5.0) -> threading.Thread:
    """Force-kill the process after *timeout* seconds if shutdown hangs.

    Spawns a daemon thread that periodically dumps diagnostics to the diag log
    and calls ``os._exit()`` after the timeout.
    """

    def _force_exit():
        # Log diagnostics every 1 second until the timeout is reached
        start_time = time.time()
        tick = 1
        while True:
            remaining = timeout - (time.time() - start_time)
            if remaining <= 0:
                break
            time.sleep(min(1.0, remaining))
            if timeout - (time.time() - start_time) > 0:
                dump_diagnostics(f"Watchdog tick {tick}s")
                tick += 1

        # Final diagnostics dump right before force-exit
        dump_diagnostics("Watchdog final timeout reached")

        with contextlib.suppress(Exception):
            os.write(
                2,
                f"\n[SHUTDOWN] Watchdog timeout: calling os._exit({ret})\n".encode(),
            )
        os._exit(ret)

    t = threading.Thread(target=_force_exit, daemon=True)
    t.start()
    return t

"""Backend selector for joblib.Parallel.

In PyInstaller-frozen builds, ``prefer="processes"`` is broken on Windows
because loky's frozen-mode command line omits ``parent_pid``, causing
``OSError: [WinError 6] The handle is invalid`` in the worker process.

We auto-select ``"threads"`` in frozen mode; dev mode keeps ``"processes"``
for true parallelism.

See ADR-0019 (original) and ADR-0021 (frozen-build override).
"""

import os
import sys

_MAX_WORKERS = min(2, os.cpu_count() or 1)


def joblib_prefer() -> str:
    """Return ``"threads"`` for frozen builds, ``"processes"`` for dev."""
    return "threads" if getattr(sys, "frozen", False) else "processes"


def joblib_workers() -> int:
    """Number of workers to pass to ``joblib.Parallel(n_jobs=...)``."""
    return _MAX_WORKERS

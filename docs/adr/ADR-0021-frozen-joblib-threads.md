# ADR-0021: Frozen-build joblib backend override

> Status: **Accepted**
> Date: 2026-07-01
> Owner: @DIKKA

## Context

ADR-0019 replaced `ThreadPoolExecutor` with `joblib.Parallel(prefer="processes")` for CPU-bound work. In dev mode this works correctly: loky passes `parent_pid` to child processes, allowing Windows `DuplicateHandle` to resolve the inherited pipe handle.

In PyInstaller-frozen builds, loky's `get_command_line()` omits `parent_pid`:

```python
# popen_loky_win32.get_command_line — joblib 1.5.3
if getattr(sys, "frozen", False):
    return [sys.executable, "--multiprocessing-fork", pipe_handle]  # no parent_pid
```

This causes `multiprocessing.reduction.duplicate(pipe_handle, source_process=None)` to raise `OSError: [WinError 6] The handle is invalid` in every worker spawn attempt.

The app's existing intercept in `__main__.py` tried to call `loky_main(pipe_handle=...)` directly, but without `parent_pid` the Windows handle lookup still fails. Two `joblib.Parallel` call sites at startup (`discovery.py`, `quick_copy.py`) each attempt worker spawns, producing the user-visible popup error window **twice**.

## Decision

Use `prefer="threads"` in PyInstaller-frozen builds; keep `prefer="processes"` in dev mode. A `joblib_prefer()` helper in `utils/joblib_backend.py` selects the backend based on `sys.frozen`.

```python
# utils/joblib_backend.py
def joblib_prefer() -> str:
    return "threads" if getattr(sys, "frozen", False) else "processes"
```

Remove the broken loky intercept code from both `__main__.py` and `app.py`. The `_JOBLIB_WORKERS` constant is centralized in the new helper module.

## Consequences

### Positive

- Eliminates the `WinError 6` popup in frozen builds completely
- Removes 44 lines of dead, broken code from `__main__.py` and `app.py`
- Centralizes `_JOBLIB_WORKERS` (was duplicated in two files)
- Dev mode keeps true process parallelism

### Negative

- Frozen builds use threads instead of processes — GIL contention applies. The parallel work (markdown parsing, file I/O) is I/O-bound, so this is negligible.

### Neutral

- ADR-0019 remains Accepted; ADR-0021 carves out the frozen-build exception
- `multiprocessing.freeze_support()` is still called in both entrypoints (for PyInstaller's standard multiprocessing hooks)

## Alternatives Considered

### Pass parent_pid via environment variable

Rejected: race condition between fork and exec; the env var may not be visible to the child before loky overwrites the process environment.

### Custom PyInstaller runtime hook for loky

Rejected: requires patching loky internals across joblib versions; fragile when loky updates its spawn protocol.

### Error-then-fallback to threads

Rejected: still shows the popup on the failure path before the fallback runs.

### Use loky's standard `spawn` backend

Rejected: loky doesn't support a `spawn` backend; it always uses `loky` backend which relies on `multiprocessing.reduction` handle inheritance.

## References

- ADR-0019 (original multiprocessing/joblib decision)
- [joblib loky popen_loky_win32.py — get_command_line()](https://github.com/joblib/joblib/blob/master/joblib/externals/loky/backend/popen_loky_win32.py)
- [PyInstaller multiprocessing runtime hook](https://pyinstaller.org/en/stable/hooks.html)

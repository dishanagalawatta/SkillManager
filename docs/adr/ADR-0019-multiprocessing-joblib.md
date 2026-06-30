# ADR-0019: Multiprocessing with Joblib

> Status: **Accepted**
> Date: 2026-05-28
> Owner: @DIKKA

## Context

SkillManager performs CPU-intensive operations: parsing skill files, building filter indexes, computing search indices, and constructing Qt model rows. Initially, these ran on Python threads via `ThreadPoolExecutor`.

The GIL (Global Interpreter Lock) prevented true parallelism for CPU-bound work. The PySide6 event loop would stall during heavy parsing, causing UI freezes and `isLoading` flicker.

## Decision

Replace `ThreadPoolExecutor` with `joblib.Parallel` for CPU-bound work:

```python
from joblib import Parallel, delayed

# Before (blocked by GIL)
with ThreadPoolExecutor() as pool:
    futures = [pool.submit(parse_skill, s) for s in skills]

# After (true parallelism)
results = Parallel(n_jobs=-1)(
    delayed(parse_skill)(s) for s in skills
)
```

### Threading Model

| Thread | Purpose | Library |
|--------|---------|---------|
| Main | PySide6 event loop, QML rendering | PySide6 |
| Background | Skill parsing, filter passes | `joblib.Parallel` |
| Background | Async operations (copy, update) | `BackgroundTaskRunner` |
| Background | File system watching | `watchdog` |
| Background | Periodic polling | `APScheduler` (`QtScheduler`) |

### Incubation Coordination

QML delegates are "incubated" (created lazily) when the model has data. Resetting the model while incubation is in progress causes "Object destroyed during incubation" errors.

**Solution:** `PreparedModelState` dataclass + `cacheBuffer = 0` before reset:

1. Set `cacheBuffer = 0` → QML stops incubating
2. `beginResetModel()` → signal model is changing
3. Background thread computes new state (parsing, filtering, row prep)
4. `endResetModel()` → commit new data atomically
5. Restore `cacheBuffer = 200` → QML resumes incubation

## Consequences

### Positive

- True parallelism for CPU-bound work (no GIL contention)
- UI remains responsive during heavy parsing
- `PreparedModelState` eliminates incubation race conditions
- Background refresh with cooperative cancellation (generation counter)

### Negative

- `joblib` adds a dependency (acceptable for the parallelism benefit)
- Serialization overhead between processes (mitigated by process pools)

### Neutral

- `pytest-xdist` for test parallelism (same pattern)
- `BackgroundTaskRunner` handles async operations that need Future tracking

## Alternatives Considered

### `multiprocessing.Pool`

Rejected — more boilerplate; `joblib` provides a cleaner API with automatic process management.

### `concurrent.futures.ProcessPoolExecutor`

Considered but `joblib` has better Windows support and automatic serialization.

### Keep `ThreadPoolExecutor`

Rejected — GIL prevents true parallelism; UI freezes persisted.

## References

- [Joblib Documentation](https://joblib.readthedocs.io/)
- [Python GIL](https://docs.python.org/3/glossary.html#global-interpreter-lock)
- [`DESIGN.md`](../../DESIGN.md) — Threading Model section

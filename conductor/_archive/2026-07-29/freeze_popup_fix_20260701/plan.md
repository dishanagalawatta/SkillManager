# Plan: Fix PyInstaller frozen-build popup error

## Context

PyInstaller-frozen builds of SkillManager show a Windows popup error:
`OSError: [WinError 6] The handle is invalid` from loky's process fork.
The popup appears twice because two `joblib.Parallel` call sites attempt worker
spawns that fail.

Root cause: loky's `get_command_line()` omits `parent_pid` in frozen mode,
so `multiprocessing.reduction.duplicate()` cannot resolve the pipe handle.

## Decision

Switch joblib from `processes` to `threads` in frozen builds (ADR-0021).
Dev mode keeps `processes` for true parallelism.

## Tasks

- [x] Create `src/skill_manager/utils/joblib_backend.py` with `joblib_prefer()` / `joblib_workers()`
- [x] Refactor `discovery.py` to use `joblib_prefer()` / `joblib_workers()`
- [x] Refactor `quick_copy.py` to use `joblib_prefer()` / `joblib_workers()`
- [x] Remove dead loky intercept from `__main__.py`
- [x] Remove dead loky intercept from `app.py`
- [x] Update `tests/test_app_initialization.py` (new contract)
- [x] Create `tests/test_joblib_backend.py`
- [x] Create `docs/adr/ADR-0021-frozen-joblib-threads.md`
- [x] Update `ADR_INDEX.md`
- [x] Lint, format, and test

## Validation

- [ ] `uv run ruff check src tests` — 0 errors
- [ ] `uv run pytest tests/test_joblib_backend.py tests/test_app_initialization.py -v` — pass
- [ ] `uv run pytest -n auto` — all green
- [ ] `uv run python scripts/build_app.py` — build succeeds
- [ ] Launch `SkillManager.exe` — no popup within 5 s
- [ ] Trigger Quick Copy refresh — no popup

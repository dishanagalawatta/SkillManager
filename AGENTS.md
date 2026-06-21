# Agent Instructions

> Read [`ADR_INDEX.md`](ADR_INDEX.md) once at session start. Read
> [`README.md`](README.md) for layout.

## Package Manager

`uv`. All commands use `uv run …` or `uv run pytest …`.

## File-Scoped Commands

| Task       | Command                                       |
|------------|-----------------------------------------------|
| Lint       | `uv run ruff check path/to/file.py --fix`     |
| Format     | `uv run ruff format path/to/file.py`          |
| Test       | `uv run pytest path/to/file.py`               |
| Full Suite | `python run_tests.py`                         |

## Conventions

- **GUI.** PySide6 / QML. UI files in
  `src/skill_manager/SkillManagerComponents/`. Token map in
  `Theme.qml`. See [`DESIGN.md`](DESIGN.md).
- **Logic.** `src/skill_manager/core/`. Categorization synced with
  [`docs/CATEGORIES.md`](docs/CATEGORIES.md).
- **Tests.** `pytest`; parallel via `pytest-xdist`. Configuration in
  `pyproject.toml`. Diagnostic coverage enforced by
  `tests/test_qml_comprehensive_diagnostic.py` (ADR-0003, ADR-0004).
- **Releases.** python-semantic-release with opt-in tokens. See
  ADR-0009 and [`docs/VERSIONING.md`](docs/VERSIONING.md).
- **Diagnostic logging.** Use
  `skill_manager.core.diagnostics.get_diagnostic_logger().log_event()`
  with a `CATEGORY_*` constant. Do not use `logging`.
- **Out of scope.** `TODO.md`, `.agents/commands/**`. Do not read,
  modify, or reference.

## Required Reading

1. [`README.md`](README.md)
2. [`DESIGN.md`](DESIGN.md)
3. [`ADR_INDEX.md`](ADR_INDEX.md)
4. [`docs/API.md`](docs/API.md)
5. [`docs/ENVIRONMENT.md`](docs/ENVIRONMENT.md)

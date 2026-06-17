# Agent Instructions

## Package Manager

Use **uv**: `uv sync`, `uv run skill-manager`, `python run_tests.py`

## File-Scoped Commands

| Task       | Command                                     |
| ---------- | ------------------------------------------- |
| Lint       | `uv run ruff check path/to/file.py --fix` |
| Format     | `uv run ruff format path/to/file.py`      |
| Test       | `uv run pytest path/to/file.py`           |
| Full Suite | `python run_tests.py`                     |

## Key Conventions

- **GUI**: Built with PySide6/QML. UI files are in `src/skill_manager/SkillManagerComponents/`.
- **Tests**: Use `pytest`. Parallel execution is supported via `pytest-xdist`.
- **Logic**: Follow patterns in `src/skill_manager/core/`.
- **Categorization**: Keep logic in `src/skill_manager/core/parsing/` synced with `docs/CATEGORIES.md`.
- **Releases**: Strictly Opt-in. Use `[patch]`, `[minor]`, `[major]`, or `[dev]` in commits.
- **Diagnostic Logging**: Use `skill_manager.core.diagnostics.get_diagnostic_logger().log_event()` with a `CATEGORY_*` constant for UI/Agent-facing events. Do not use standard `logging`.

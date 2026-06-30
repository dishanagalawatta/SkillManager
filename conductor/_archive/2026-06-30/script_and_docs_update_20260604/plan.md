# Plan

Update the `run_tests.py` script to include linting via `ruff`, and update project documentation including the creation of a strict `AGENTS.md` file.

## Scope

- **In:** Updating `run_tests.py`, creating `AGENTS.md` and `CLAUDE.md`, updating `docs/DEVELOPMENT.md` and `README.md`.
- **Out:** Modifying skill folders or core application logic.

## Action Items

- [x] Task 1.1: Update `run_tests.py` to execute `uv run ruff check src tests --fix` before running `pytest`. Ensure the script handles linting errors gracefully.
- [x] Task 1.2: Create `AGENTS.md` strictly following the minimalist `<60` lines structure defined in the `agents-md` skill.
- [x] Task 1.3: Create `CLAUDE.md` as a copy/symlink of `AGENTS.md`.
- [x] Task 1.4: Update `docs/DEVELOPMENT.md` to feature the unified `python run_tests.py` script in the Testing and Available Scripts sections.
- [x] Task 1.5: Review `README.md` to ensure any script references remain accurate.

## Open Questions

- None

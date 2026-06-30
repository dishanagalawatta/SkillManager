# Plan

Create a single `run_tests.py` script to execute the test suite in parallel with clean progress output and detailed error reporting using the `pytest-xdist` and `pytest-sugar` plugins.

## Scope

- **In:** Adding `pytest-xdist` and `pytest-sugar` to dev dependencies, creating `run_tests.py`.
- **Out:** Modifying existing test logic, creating new tests.

## Action Items

- [x] Task 1.1: Add `pytest-xdist` and `pytest-sugar` to the `dev` dependency group in `pyproject.toml`.
- [x] Task 1.2: Sync `uv.lock` with the updated dependencies using `uv sync` or similar.
- [x] Task 1.3: Create `run_tests.py` in the root directory that executes `uv run pytest -n auto`.
- [x] Task 1.4: Execute `python run_tests.py` to validate that the script runs successfully and displays the progress bar and clean output.

## Open Questions

- None

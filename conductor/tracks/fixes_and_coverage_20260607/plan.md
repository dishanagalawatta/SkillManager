# Implementation Plan: Fixes and Test Coverage

## Phase 1: Linting
- [x] Task 1.1: Run `uv run ruff check .` to identify linting issues.
- [x] Task 1.2: Apply automated fixes with `uv run ruff check --fix .`.
- [x] Task 1.3: Manually resolve any remaining linting issues (e.g., unused imports, type hint warnings).
- [x] Task 1.4: Run `uv run ruff format .` to ensure consistent formatting.

## Phase 2: Debugging Existing Tests
- [x] Task 2.1: Run the full test suite `uv run pytest`.
- [x] Task 2.2: Identify failing tests and perform root cause analysis.
- [x] Task 2.3: Formulate hypotheses and implement minimal fixes for the root causes.
- [x] Task 2.4: Verify all existing tests pass consistently.

## Phase 3: Coverage Analysis and Generation
- [x] Task 3.1: Run coverage analysis: `uv run pytest --cov=src --cov-report=term-missing`.
- [x] Task 3.2: Identify coverage gaps, focusing on `screenshot_controller.py`, `app.py`, and `quick_copy.py`.
- [x] Task 3.3: Generate new tests for `screenshot_controller.py` to cover edge cases and error handling.
- [x] Task 3.4: Generate new tests for `app.py` or other identified low-coverage modules.
- [x] Task 3.5: Run tests to confirm coverage has increased and tests are stable.

## Phase 4: Final Verification
- [x] Task 4.1: Run a final clean pass of `uv run ruff check .`.
- [x] Task 4.2: Run a final pass of `uv run pytest` to ensure everything is green.
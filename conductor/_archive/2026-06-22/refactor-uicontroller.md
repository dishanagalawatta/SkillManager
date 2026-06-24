# Refactoring Plan: UIController (SDET)

> Historical refactor plan — preserved for traceability. See
> [`conductor/tracks.md`](tracks.md) for the active track record.

**Status:** Historical (completed) · **Date:** unknown

## Background & Motivation

The `UIController` manages window geometry, themes, filters, and user preferences. Currently, it suffers from:
- **Loose Typing (Dictionary State)**: It reads and writes raw dictionaries (`ui_state`) to the config file without strict validation boundaries.
- **Test Coverage Gaps**: Significant portions of the controller—including nearly all boolean toggles, filtering methods, and selection helpers—are completely untested.
- **Model Coupling**: It directly manipulates internal attributes of the `skillModel` during filtering operations, bypassing encapsulation.

## Scope & Impact

**In Scope:**
- Define a `UIStateRecord` Pydantic model in `src/skill_manager/core/schemas.py` to enforce strict validation and default constraints for all UI state variables.
- Refactor `UIController` to initialize and persist state using this strict schema.
- Implement 100% unit test coverage for `UIController`, filling the gaps for property setters, filters, and slots.
- Implement a UI/E2E test using `pytest-qt` to verify the end-to-end flow of view filtering and state persistence.

**Out of Scope:**
- Changes to the underlying QML frontend code.
- Modification of other config domains.

## Implementation Steps

### Phase 1: Schemas
- Add `UIStateRecord` to `schemas.py` with strict types, constraints (e.g., `ge=1050` for width), and default values.

### Phase 2: Refactor UIController
- Update `UIController.__init__` to load and validate state via `UIStateRecord.model_validate`.
- Update property setters to modify the validated record and trigger saves.
- Refactor `saveUiState` to serialize the record (`model_dump()`).
- Clean up filter logic to use public APIs if available, or at least encapsulate the batch operations safely.

### Phase 3: Unit Testing
- Add tests for all missing properties: `windowHeight`, `windowX`, `windowY`, `darkMode`, `compactListRows`, etc.
- Add tests for `resetUiState`, `selectAllVisibleSkills`, `clearViewFilters`, and the core filter logic.

### Phase 4: UI/E2E Testing
- Implement a `pytest-qt` test to verify that changing filters via the UI Controller correctly triggers the debounced save and updates the underlying model state.

## Verification & Rollback

- **Verification:** Run the relevant test files.
- **Rollback:** Standard git revert.

## Cross-references

- Workflow: [`conductor/workflow.md`](workflow.md)
- Active tracks: [`conductor/tracks.md`](tracks.md)
- ADRs: [`../ADR_INDEX.md`](../ADR_INDEX.md)

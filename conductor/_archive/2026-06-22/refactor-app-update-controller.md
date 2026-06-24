# Plan: Refactor AppUpdateController (SDET Round 8)

> Historical refactor plan — preserved for traceability. See
> [`conductor/tracks.md`](tracks.md) for the active track record.

**Status:** Historical (completed) · **Date:** unknown

## Background & Motivation

Refactor `AppUpdateController` to use Pydantic models for update state management and extract core update logic into a testable service.

## Scope & Impact

- **In:** `src/skill_manager/controllers/app_update_controller.py`, `src/skill_manager/core/schemas.py`, new `src/skill_manager/core/update_service.py`.
- **Out:** QML changes, other controllers.

## Implementation Steps

- [ ] Schema: Define `AppUpdateState` and `AppUpdateMetadata` models in `schemas.py`.
- [ ] Implementation: Create `AppUpdateService` in `core/update_service.py` to encapsulate `tufup` Client interactions.
- [ ] Implementation: Refactor `AppUpdateController` to use `AppUpdateState` for signaling and delegate to `AppUpdateService`.
- [ ] Implementation: Modernize `pathlib` usage and remove brittle monkey-patching in the controller.
- [ ] Validation: Implement unit tests in `tests/test_app_update_sdet.py` achieving 100% coverage.
- [ ] Validation: Implement E2E UI test in `tests/test_ui_app_update_flow.py` using `pytest-qt`.

## Verification & Rollback

- **Verification:** Run `pytest tests/test_app_update_sdet.py tests/test_ui_app_update_flow.py`.
- **Rollback:** Standard git revert.

## Cross-references

- Workflow: [`conductor/workflow.md`](workflow.md)
- Active tracks: [`conductor/tracks.md`](tracks.md)
- ADRs: [`../ADR_INDEX.md`](../ADR_INDEX.md)

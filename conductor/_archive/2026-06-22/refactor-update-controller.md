# Refactoring Plan: UpdateController (SDET)

> Historical refactor plan — preserved for traceability. See
> [`conductor/tracks.md`](tracks.md) for the active track record.

**Status:** Historical (completed) · **Date:** unknown

## Background & Motivation

The `UpdateController` manages skill updates, synchronizations, and package scans. While it has good unit test coverage, it currently relies on loose dictionary manipulation for state management. This lacks strict runtime type safety and validation at the boundary. Furthermore, the controller lacks an end-to-end `pytest-qt` UI flow test to verify the complete user lifecycle of adding, updating, and syncing packages.

## Scope & Impact

**In Scope:**
- Update `PackageConfig` (or define a new `UpdatePackageRecord`) in `src/skill_manager/core/schemas.py` to strongly type the skill package state.
- Refactor `UpdateController` methods to validate inputs using the Pydantic schema.
- Refactor internal list manipulation to utilize the validated schema objects.
- Expand test coverage to ensure 100%, specifically targeting boundary validations and edge cases.
- Create a `pytest-qt` E2E test to simulate the full update lifecycle.

**Out of Scope:**
- Changes to the core underlying `UpdateService` algorithm.
- QML frontend refactoring.

## Implementation Steps

### Phase 1: Schema Hardening
- Introduce or enhance the Pydantic model for update packages in `schemas.py` (e.g., ensuring `is_updating`, `just_finished`, `last_updated` have strict defaults).

### Phase 2: Controller Refactor
- Update `UpdateController.addSkillPackage` and `updateUpdatePackage` to parse incoming data through the Pydantic schema.
- Update internal state management to handle safe serialization to the config.

### Phase 3: Unit Testing
- Add tests to verify that invalid payloads are caught by Pydantic and do not corrupt the application state.
- Verify that `addUpdatePackage` sets correct default values via the schema.

### Phase 4: UI/E2E Testing
- Create a `pytest-qt` test.
- Simulate adding a package, triggering an update, and verifying the UI state signals and configuration persistence.

## Verification & Rollback

- **Verification:** Run the relevant test files.
- **Rollback:** Standard git revert.

## Cross-references

- Workflow: [`conductor/workflow.md`](workflow.md)
- Active tracks: [`conductor/tracks.md`](tracks.md)
- ADRs: [`../ADR_INDEX.md`](../ADR_INDEX.md)

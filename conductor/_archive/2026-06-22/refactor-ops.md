# Refactoring Plan: OpsController and State Consistency (SDET)

> Historical refactor plan — preserved for traceability. See
> [`conductor/tracks.md`](tracks.md) for the active track record.

**Status:** Historical (completed) · **Date:** unknown

## Background & Motivation

`OpsController` manages critical file system and state operations (deletion, archiving, starring, copying). Current flaws:
- Input data in `deleteSkills` and other methods lacks strict validation.
- State synchronization between models (`_library_model`, `_quick_copy_model`) relies on direct private attribute manipulation, which is brittle and hard to test.
- Redundant logic between `toggleArchive` and `toggleStarred`.
- Mixed responsibilities: UI messaging, background task orchestration, and low-level data transformation.

## Scope & Impact

**In Scope:**
- Refactor `src/skill_manager/controllers/ops_controller.py` to use `SkillRecord` (Pydantic) for validation.
- Implement a robust `_updateModelsProperty` helper using public model APIs where possible.
- Unify boolean toggle logic.
- Rewrite `tests/test_ops_controller.py` to achieve 100% coverage on operational edge cases.
- Create a UI/E2E test for the "Delete Skill" and "Toggle Star" flows using `pytest-qt`.

**Out of Scope:**
- Rewriting the background `task_runner`.
- Changes to the underlying `persistence.py` logic.

## Implementation Steps

### Phase 1: Model & Schema Alignment
- Update `SkillModel` to expose a public `updateSkillProperty(path, key, value)` method to encapsulate state changes.
- Update `OpsController` to use `SkillRecord.model_validate` for items in `deleteSkills`.

### Phase 2: Refactor OpsController
- Extract shared toggle logic into `_toggle_skill_boolean(self, property_name, signal_name)`.
- Refactor `deleteSkills` to use atomic Pydantic-validated lists.
- Decouple background logic from UI status updates.

### Phase 3: Unit Testing (`tests/test_ops_sdet.py`)
- Test deletions with invalid paths, multiple items, and mixed command/screenshot types.
- Verify model synchronization across both models.
- Mock file system errors during deletion to ensure graceful failure.

### Phase 4: UI/E2E Testing
- Implement `tests/test_ui_ops_flow.py` to verify that clicking "Delete" in the UI correctly updates the models and filesystem.

## Verification & Rollback

- **Verification:** `pytest --cov=src/skill_manager/controllers/ops_controller.py`.
- **Rollback:** Standard git revert.

## Cross-references

- Workflow: [`conductor/workflow.md`](workflow.md)
- Active tracks: [`conductor/tracks.md`](tracks.md)
- ADRs: [`../ADR_INDEX.md`](../ADR_INDEX.md)

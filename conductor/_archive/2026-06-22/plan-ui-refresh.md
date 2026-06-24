# Plan: Fix UI Update on Starring/Archiving Skills

> Historical plan — preserved for traceability. See
> [`conductor/tracks.md`](tracks.md) for the active track record.

**Status:** Historical (completed) · **Date:** unknown

## Objective

Ensure the QML UI updates immediately when a skill's starred or archived status is toggled, without requiring a window refresh. Provide fluid motion using native Qt signal emissions for optimal performance, avoiding the need for additional open-source libraries.

## Scope

- **In:** `src/skill_manager/controllers/ops_controller.py`, `src/skill_manager/core/models/qt_model.py`.
- **Out:** Other components.

## Action Items

1. **Update `_updateModelsSource` in `ops_controller.py`**:
   - Import the necessary Roles from `SkillModel` (or map them based on the property key).
   - Iterate over both `_library_model` and `_quick_copy_model`.
   - Update the property in `_all_skills`.
   - Crucially, check if the skill is currently visible in `_filtered_skills`. If it is, find its row index.
   - Emit the `dataChanged` signal for that specific row and role, ensuring the QML view updates instantly.

## Verification

- Select a skill in the Library view and toggle the Star button. Verify the star icon and row styling update immediately.
- Toggle the Archive status and verify the view reflects the change immediately.
- Ensure no regressions occur in the Quick Copy view.

## Cross-references

- Workflow: [`conductor/workflow.md`](workflow.md)
- Active tracks: [`conductor/tracks.md`](tracks.md)
- ADRs: [`../ADR_INDEX.md`](../ADR_INDEX.md)

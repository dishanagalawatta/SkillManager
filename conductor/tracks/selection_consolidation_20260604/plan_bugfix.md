# Implementation Plan - Selection Fix & Polish

## Phase 7: Model Core Fix

- [x] Task 7.1: Add `visibleSelectableCount` and `visibleSelectedCount` properties to `src/skill_manager/core/models/qt_model.py`.
- [x] Task 7.2: Ensure `selectedCountChanged` is emitted when the layout changes.

## Phase 8: UI Logic & Design

- [x] Task 8.1: Update `src/skill_manager/SkillManagerComponents/GlassCheckBox.qml` with the refined modern design.
- [x] Task 8.2: Update `LibraryView.qml` to use the new model properties for selection logic.
- [x] Task 8.3: Update `QuickCopyView.qml` to use the new model properties for selection logic.

## Phase 9: Verification

- [x] Task 9.1: Run `pytest tests/test_selection_logic.py`.
- [x] Task 9.2: Perform manual UI verification.

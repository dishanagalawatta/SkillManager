# Spec: Fix Selection Consolidation and Refine Design

The recently implemented selection checkbox has two issues:
1. **Functional**: Deselect all doesn't work after selecting all because the UI compares the selected skills count against the total visible rows (including headers).
2. **Visual**: The user finds the current checkbox design "ugly" and wants a "more modern style icon".

## Requirements

1. **Model Updates (`qt_model.py`)**
   - Add `visibleSelectableCount`: Number of skills (non-headers) currently visible in the list.
   - Add `visibleSelectedCount`: Number of selected skills that are currently visible.
   - These properties must notify on `selectedCountChanged`.

2. **UI Logic Updates (`LibraryView.qml`, `QuickCopyView.qml`)**
   - Bind `GlassCheckBox.checkState` using `visibleSelectedCount` and `visibleSelectableCount`.
   - Update `onToggled` to use `visibleSelectedCount` to determine if we should clear or select all.

3. **Design Refinement (`GlassCheckBox.qml`)**
   - Transition from a sharp-cornered box to a clean circle/pill design.
   - Use `Theme.radiusSmall` or `Theme.radiusPill`.
   - Improve the "minus" icon for the partially checked state.
   - Add subtle shadow and border for a more "glass" feel.

## Verification Plan

- **Manual Verification**:
  - Filter the list so some items are collapsed.
  - Click the selection checkbox: only visible items should be selected.
  - Click again: all items (even those just selected) should be cleared.
  - Ensure the partially checked state (minus) appears correctly when some, but not all, visible items are selected.
  - Verify the new design matches the modern style of other UI components.
- **Automated Verification**:
  - Run `pytest tests/test_selection_logic.py`.

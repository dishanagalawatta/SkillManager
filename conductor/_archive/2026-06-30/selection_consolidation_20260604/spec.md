# Spec: Consolidate Select All and Clear Selection into a Checkbox

This track replaces the explicit "Select All" and "Clear Selection" buttons in `LibraryView` and `QuickCopyView` with a single, space-saving standard `CheckBox`.

## Requirements

- Standard `CheckBox` from `QtQuick.Controls` positioned after the "Toggle All" button's separator.
- Use `checkState` binding to dynamically display `Qt.Unchecked`, `Qt.PartiallyChecked`, or `Qt.Checked`.
- Logic based on the ratio of `selectedCount` to `rowCount()`.
- Custom `nextCheckState` function to only toggle between `Checked` and `Unchecked`.
- Tooltips for "Select All" and "Clear Selection".
- Remove old buttons and their separators.

## Affected Files

- `src/skill_manager/SkillManagerComponents/views/LibraryView.qml`
- `src/skill_manager/SkillManagerComponents/views/QuickCopyView.qml`

## Verification Plan

- Navigate to Library View.
- Verify Checkbox appears and functions (select all / clear all).
- Verify partially checked state when some items are selected.
- Repeat for Quick Copy View.

# Spec: Custom GlassCheckBox Component

The standard `CheckBox` component from QtQuick.Controls is clashing with the application's modern, glass-morphism aesthetic. Furthermore, its native tri-state logic is conflicting with our property bindings. 

This plan involves creating a new custom component, `GlassCheckBox`, and integrating it into the selection action bars.

## Requirements

1. **New Component: `GlassCheckBox.qml`**
   - Must mirror the visual styling of `IconButton` and `GlassToggleButton` (radius, glass hover/active states, transparent borders).
   - Handles three visual states: Checked (Check icon), Partially Checked (Minus icon), and Unchecked (Empty).
   - Exposes a `checkState` property and a `toggled` signal.
   - Click interactions must ONLY emit the `toggled` signal; state management remains the responsibility of the parent view.
   - Must be registered in `qmldir`.

2. **Integration**
   - Replace the standard `CheckBox` in `LibraryView.qml` and `QuickCopyView.qml` with the new `GlassCheckBox`.
   - Ensure the tooltip logic and state bindings remain intact.

## Verification Plan

- Navigate to Library View.
- Verify the new checkbox perfectly matches the size, rounding, and hover effects of the adjacent action buttons.
- Verify clicking it toggles selection correctly.
- Verify partial selection displays a white minus symbol.
- Repeat for Quick Copy View.

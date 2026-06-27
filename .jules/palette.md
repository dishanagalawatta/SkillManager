## 2024-05-21 - Custom QML Buttons A11y
**Learning:** Custom interactive QML elements require Accessible.role, Accessible.name properties for screen reader support.
**Action:** Always check interactive elements to ensure they define Accessible properties.
## 2024-05-23 - Accessibility of QML Interactive Elements
**Learning:** Adding interactive accessibility properties like `Accessible.role`, `Accessible.name`, and `Accessible.description` to all custom `MouseArea` items and `AbstractButton` implementations is a crucial step in ensuring custom QML components are well-supported by screen readers, but some areas like subcomponents (buttons in custom TitleBars, custom KeySequenceCapture) were missed in the initial passes.
**Action:** Always scan for `MouseArea`, `TapHandler`, and custom Button components and explicitly evaluate if they need `Accessible` mappings. Tools relying solely on string matches might miss these if they format multiline uniquely, so manual inspection or advanced parsing is necessary.
## 2024-05-24 - ComboBox Focus Rings
**Learning:** Custom QML `ComboBox` controls do not automatically receive keyboard accessibility focus rings like standard system inputs, and their default `Rectangle` backgrounds need explicit bindings for `control.visualFocus` mapping to the border width and color.
**Action:** Always check custom `ComboBox` implementations and their `background` properties to ensure focus rings are visible when navigating by keyboard, matching the pattern used in custom buttons.
## 2024-05-25 - Custom QML Item Focus Accessibility
**Learning:** Custom interactive QML components built on plain `Item` or `Rectangle` (like `KeySequenceCapture`) are not reachable via keyboard navigation by default, even if their inner `MouseArea` has accessibility mappings.
**Action:** Always add `activeFocusOnTab: true` to the root `Item` of custom controls, map `activeFocus` to visual indicators like border width and color, and handle `Keys.onPressed` for standard activation keys (Space, Enter) so users can trigger them via keyboard.
## 2025-02-23 - Custom Multi-Select ComboBox A11y
**Learning:** Custom multi-select or dropdown components built on plain `Item` (like `GlassMultiSelect.qml`) do not inherit native `ComboBox` accessibility. They require explicit `Accessible.role: Accessible.ComboBox`, `activeFocusOnTab: true`, and manual `Keys.onPressed` handling for Space/Enter to emulate standard interactions.
**Action:** Always check custom dropdown implementations to ensure they define `Accessible.ComboBox`, map `activeFocus` to a visual ring, and handle keyboard events for toggling the popup.
## 2025-02-23 - Tooltip Keyboard Accessibility Focus
**Learning:** Tooltips in QML typically rely on hover interactions (`control.hovered`) by default. Relying purely on hover causes tooltips to be invisible for keyboard-only or screen reader users navigating via Tab.
**Action:** Always include keyboard focus bindings (`visualFocus` for Quick Controls, `activeFocus` for standard Items) alongside hover in tooltip visibility checks. For example: `visible: (control.hovered || control.visualFocus) && control.tooltipText !== ""`

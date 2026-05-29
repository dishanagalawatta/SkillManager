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
## 2024-05-26 - Category Header Focus Accessibility
**Learning:** Custom interactive list header items built on plain `Item` (like `CategoryHeader.qml`) lack keyboard navigability. They need `activeFocusOnTab: true`, specific key event handling for Space/Enter, and dynamic visual indicators for `activeFocus` mapped to border attributes.
**Action:** Always add keyboard accessibility features (tab focus, key handlers, focus rings) to list group headers or custom clickable items to ensure they are fully navigable via standard keyboard controls.

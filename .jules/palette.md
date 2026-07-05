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

## 2026-06-29 - Keyboard Accessibility for QML Tooltips
**Learning:** In QML standard controls (like `Button`), binding a tooltip's `visible` property solely to `hovered` breaks keyboard accessibility for screen reader and keyboard-only users navigating via Tab.
**Action:** Always include `visualFocus` in the visibility condition (e.g., `visible: (control.hovered || control.visualFocus) && condition`) to ensure the tooltip is accessible when navigated to via keyboard.

## 2025-02-23 - Avoid Redundant Accessible Descriptions
**Learning:** Setting `Accessible.description` to the exact same value as `Accessible.name` (e.g., both referencing a tooltip's text) creates a harmful redundancy where screen readers will announce the exact same text twice to the user.
**Action:** When evaluating custom QML controls, if the desired description is identical to the accessible name, simply omit the `Accessible.description` property altogether to streamline screen reader verbosity.
## 2026-06-29 - Consolidate Tooltips using Built-in Properties
**Learning:** When custom QML controls (like `IconButton` in `skill_manager`) provide a built-in `tooltipText` property, manually nesting `SleekToolTip` elements and redefining `Accessible.name`/`Accessible.description` leads to verbose, redundant code that is prone to accessibility bugs (like missing `visualFocus` bindings or double-announcing).
**Action:** Always favor using the built-in `tooltipText` property over manually nesting tooltip items.

## 2024-05-18 - QML Signal Handler Parameters Warning
**Learning:** In QML, attaching a parameterized signal handler like `(mouse) =>` to a signal that emits no parameters (e.g., standard `Button.clicked`) produces `qmllint` warnings complaining about "more formal parameters than the signal it handles".
**Action:** Use parameterless functions or plain blocks for simple signals to avoid noisy linter warnings and potential runtime ambiguity.

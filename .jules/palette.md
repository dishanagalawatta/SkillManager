## 2024-05-21 - Custom QML Buttons A11y
**Learning:** Custom interactive QML elements require Accessible.role, Accessible.name properties for screen reader support.
**Action:** Always check interactive elements to ensure they define Accessible properties.
## 2024-05-23 - Accessibility of QML Interactive Elements
**Learning:** Adding interactive accessibility properties like `Accessible.role`, `Accessible.name`, and `Accessible.description` to all custom `MouseArea` items and `AbstractButton` implementations is a crucial step in ensuring custom QML components are well-supported by screen readers, but some areas like subcomponents (buttons in custom TitleBars, custom KeySequenceCapture) were missed in the initial passes.
**Action:** Always scan for `MouseArea`, `TapHandler`, and custom Button components and explicitly evaluate if they need `Accessible` mappings. Tools relying solely on string matches might miss these if they format multiline uniquely, so manual inspection or advanced parsing is necessary.
## 2024-05-24 - ComboBox Focus Rings
**Learning:** Custom QML `ComboBox` controls do not automatically receive keyboard accessibility focus rings like standard system inputs, and their default `Rectangle` backgrounds need explicit bindings for `control.visualFocus` mapping to the border width and color.
**Action:** Always check custom `ComboBox` implementations and their `background` properties to ensure focus rings are visible when navigating by keyboard, matching the pattern used in custom buttons.
## 2024-05-25 - Redundant Accessible Descriptions
**Learning:** Avoid setting `Accessible.description` to the exact same value as `Accessible.name` (like a label text). This causes screen readers to read the identical text twice, harming UX.
**Action:** Only add `Accessible.description` if it provides *additional* useful context beyond what is already in `Accessible.name`.

## 2024-05-25 - Explicit Cursor Change for Buttons
**Learning:** In standard QML components, particularly un-styled or custom controls built with `Button`, a hover cursor change is not automatic. Interactive elements require explicit configuration to show visual clickability cues.
**Action:** Always verify if a custom QML component needs a `HoverHandler { cursorShape: Qt.PointingHandCursor }` added to communicate affordance effectively.

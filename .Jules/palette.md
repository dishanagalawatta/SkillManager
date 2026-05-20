## 2026-05-18 - Custom Button Focus States
**Learning:** Custom QML controls lack built-in keyboard focus styling, which is a major accessibility issue for keyboard users who rely on the 'Tab' key to navigate.
**Action:** Always include `control.visualFocus` in the `border.color` and `border.width` properties of custom buttons to provide clear visual feedback during keyboard navigation.
## 2026-05-19 - Focus Styling for Custom Form Elements
**Learning:** In QML, components like Custom Switches (`GlassSwitch.qml`) and interactive labels (`FilterPill.qml`) also require explicit `control.visualFocus` binding to support keyboard navigation properly, not just buttons. Furthermore, custom interactive items may lack `Accessible.role` and `Accessible.name`, hiding them from screen readers.
**Action:** Audit and update focus indicators (`border.color`, `border.width`) on all custom interactive elements, and ensure their `Accessible` properties are explicitly set.
## 2026-05-20 - Accessible Properties for Custom QML Controls
**Learning:** Custom QML components (like Switches and ComboBoxes built on top of Qt Quick Controls) do not automatically inherit all accessibility attributes, especially when customized. Screen readers need explicit roles (e.g., `Accessible.CheckBox`, `Accessible.ComboBox`) and names to properly identify these controls.
**Action:** Always verify and set `Accessible.role` and `Accessible.name` (using descriptive labels, avoiding dynamic values like `control.displayText` for dropdowns) on custom interactive QML components to ensure full screen reader support.

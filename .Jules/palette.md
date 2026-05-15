## 2024-05-15 - Missing Interactive States in QML MouseAreas
**Learning:** Found a pattern where interactive elements built with raw `MouseArea` components in QML (like sidebar collapse toggles or checkbox elements) lack standard UX affordances like `cursorShape: Qt.PointingHandCursor`, `hoverEnabled: true`, and `ToolTip.text`. This makes discoverability poor for icon-only interactions.
**Action:** When working with custom QML `MouseArea` buttons instead of the standard QtQuick.Controls `Button`, always ensure we manually add hover states, cursor shapes, and tooltips for better accessibility and user confidence.

## 2024-05-16 - Standard Components Lose Hover Cursors When Customized
**Learning:** Standard QtQuick.Controls components like `Switch`, inner `Button` inside `TextField` backgrounds, and custom `Button` styles often do not inherit or display the expected `Qt.PointingHandCursor` by default when hovered, leading to lower discoverability.
**Action:** When customizing these input components, embed a `HoverHandler { cursorShape: Qt.PointingHandCursor }` at the root of the control to ensure proper interaction feedback.

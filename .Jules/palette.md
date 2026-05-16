## 2024-05-15 - Missing Interactive States in QML MouseAreas
**Learning:** Found a pattern where interactive elements built with raw `MouseArea` components in QML (like sidebar collapse toggles or checkbox elements) lack standard UX affordances like `cursorShape: Qt.PointingHandCursor`, `hoverEnabled: true`, and `ToolTip.text`. This makes discoverability poor for icon-only interactions.
**Action:** When working with custom QML `MouseArea` buttons instead of the standard QtQuick.Controls `Button`, always ensure we manually add hover states, cursor shapes, and tooltips for better accessibility and user confidence.

## 2024-05-15 - Missing Interactive States in CategoryHeader
**Learning:** Found a pattern where interactive elements built with raw `MouseArea` components in QML lack standard UX affordances like `cursorShape: Qt.PointingHandCursor`, `hoverEnabled: true`, and `ToolTip.text`. This makes discoverability poor for icon-only interactions. Added a tooltip and pointing hand cursor shape to `CategoryHeader.qml` to improve discoverability and accessibility.
**Action:** When working with custom QML `MouseArea` buttons instead of the standard QtQuick.Controls `Button`, always ensure we manually add hover states, cursor shapes, and tooltips for better accessibility and user confidence.
## 2024-05-15 - Confirmed Missing Interactive States Pattern
**Learning:** Found another instance of the missing interactive states pattern in `CategoryHeader.qml`. While it had `hoverEnabled: true` for changing the background color, it lacked the crucial `cursorShape` and `ToolTip` to explain the collapse/expand action.
**Action:** Continues to validate the previous learning. We should systematically check all `MouseArea` components that act as buttons to ensure they have the full suite of UX affordances.
## 2024-05-16 - Standard Components Lose Hover Cursors When Customized
**Learning:** Standard QtQuick.Controls components like `Switch`, inner `Button` inside `TextField` backgrounds, and custom `Button` styles often do not inherit or display the expected `Qt.PointingHandCursor` by default when hovered, leading to lower discoverability.
**Action:** When customizing these input components, embed a `HoverHandler { cursorShape: Qt.PointingHandCursor }` at the root of the control to ensure proper interaction feedback.

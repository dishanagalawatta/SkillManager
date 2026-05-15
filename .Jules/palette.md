## 2024-05-15 - Missing Interactive States in QML MouseAreas
**Learning:** Found a pattern where interactive elements built with raw `MouseArea` components in QML (like sidebar collapse toggles or checkbox elements) lack standard UX affordances like `cursorShape: Qt.PointingHandCursor`, `hoverEnabled: true`, and `ToolTip.text`. This makes discoverability poor for icon-only interactions.
**Action:** When working with custom QML `MouseArea` buttons instead of the standard QtQuick.Controls `Button`, always ensure we manually add hover states, cursor shapes, and tooltips for better accessibility and user confidence.

## 2024-05-15 - Confirmed Missing Interactive States Pattern
**Learning:** Found another instance of the missing interactive states pattern in `CategoryHeader.qml`. While it had `hoverEnabled: true` for changing the background color, it lacked the crucial `cursorShape` and `ToolTip` to explain the collapse/expand action.
**Action:** Continues to validate the previous learning. We should systematically check all `MouseArea` components that act as buttons to ensure they have the full suite of UX affordances.

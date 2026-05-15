## 2024-05-15 - Missing Interactive States in QML MouseAreas
**Learning:** Found a pattern where interactive elements built with raw `MouseArea` components in QML (like sidebar collapse toggles or checkbox elements) lack standard UX affordances like `cursorShape: Qt.PointingHandCursor`, `hoverEnabled: true`, and `ToolTip.text`. This makes discoverability poor for icon-only interactions.
**Action:** When working with custom QML `MouseArea` buttons instead of the standard QtQuick.Controls `Button`, always ensure we manually add hover states, cursor shapes, and tooltips for better accessibility and user confidence.

## 2024-05-15 - Missing Interactive States in CategoryHeader
**Learning:** Found a pattern where interactive elements built with raw `MouseArea` components in QML lack standard UX affordances like `cursorShape: Qt.PointingHandCursor`, `hoverEnabled: true`, and `ToolTip.text`. This makes discoverability poor for icon-only interactions. Added a tooltip and pointing hand cursor shape to `CategoryHeader.qml` to improve discoverability and accessibility.
**Action:** When working with custom QML `MouseArea` buttons instead of the standard QtQuick.Controls `Button`, always ensure we manually add hover states, cursor shapes, and tooltips for better accessibility and user confidence.

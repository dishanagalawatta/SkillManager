pragma Singleton
import QtQuick

QtObject {
    id: theme

    // --- State ---
    property bool darkMode: false

    // --- Colors ---
    // Warm Stone (Solid Matte) - Eye Comfort & Clarity
    readonly property color appBackground: darkMode ? "#121214" : "#FAFAF9"
    readonly property real glassNoiseOpacity: 0.0 // True matte finish
    
    // Material System
    readonly property color glassPill: darkMode ? "#1E1E22" : "#FFFFFF"
    readonly property color glassHover: darkMode ? "#2D2D34" : "#F1F5F9"
    readonly property color glassActive: darkMode ? "#3C3C46" : "#E2E8F0"
    readonly property color sidebarBackground: darkMode ? "#0F0F11" : "#F8FAFC"
    
    // Border System (Solid for matte surfaces)
    readonly property color glassBorder: darkMode ? "#2A2A30" : "#E2E8F0"
    readonly property color glassInnerBorder: "transparent"
    readonly property color glassOuterBorder: glassBorder
    
    readonly property color glassShadow: darkMode ? Qt.rgba(0.0, 0.0, 0.0, 0.5) : Qt.rgba(0.0, 0.0, 0.0, 0.04)
    readonly property color separator: darkMode ? "#26262B" : "#E2E8F0"
    
    // Overlay System — scrims stay black in both modes: they cover arbitrary
    // desktop/UI content that is not theme-aware, so a dark scrim guarantees
    // the selection/highlight always recedes regardless of theme or content.
    readonly property color scrim: Qt.rgba(0.0, 0.0, 0.0, 0.5)
    
    readonly property color disabledControl: darkMode ? "#1D1D21" : "#F1F5F9"
    readonly property color selectedRow: darkMode ? "#1E293B" : "#ECFDF5"
    readonly property color selectedRowHover: darkMode ? "#2A3B56" : "#D1FAE5"
    readonly property color selectedRowBorder: darkMode ? "#3B82F6" : accent
    readonly property color dangerHover: darkMode ? "#3F1A1A" : "#FEF2F2"
    
    readonly property color label: darkMode ? "#F3F4F6" : "#000000"
    readonly property color secondaryLabel: darkMode ? "#9CA3AF" : "#3F3F46"
    // Third-level text: hint/guidance copy that must recede further than
    // secondaryLabel without disappearing.
    readonly property color tertiaryLabel: darkMode ? "#6B7280" : "#71717A"
    
    // Icon Contrast System (Pure Black #000000 for Light Mode - Whole Icon Dark & Contrasty)
    readonly property color iconLabel: darkMode ? "#F3F4F6" : "#000000"
    readonly property color iconSecondaryLabel: darkMode ? "#9CA3AF" : "#3F3F46"
    
    readonly property color accent: darkMode ? "#3B82F6" : "#059669" // Modern Blue for Dark, Sage for Light
    readonly property color success: darkMode ? "#10B981" : "#10B981"
    readonly property color danger: darkMode ? "#EF4444" : "#DC2626"
    // Informational status colour: DEBUG rows in the diagnostics pane. Not a
    // failure state, so it must stay distinct from danger and warning.
    readonly property color info: darkMode ? "#60A5FA" : "#1D4ED8"
    // "Needs attention but nothing failed": e.g. a version check that could not
    // reach its remote.  Distinct from danger (an action failed) and accent
    // (an update is available).
    readonly property color warning: darkMode ? "#F59E0B" : "#B45309"
    readonly property color warningHover: darkMode ? "#3A2E14" : "#FFFBEB"
    
    // Aliases for compatibility
    readonly property color hoverBackground: glassHover

    // --- Layout (Softened for Forest look) ---
    readonly property real radiusPill: 20
    readonly property real radiusCard: 12 // Synchronized with native Win11 rounding (12px)
    readonly property real radiusButton: 20
    readonly property real radiusField: 20 // Pill style fields
    readonly property real radiusSmall: 10 // Reverted from 12
    
    // --- List Row Geometry ---
    // Compact rows are the single, permanent list design. The former "normal"
    // (46 px) variant and its user-facing toggle were removed; these metrics
    // are the canonical values every skill/command row uses.
    readonly property real rowHeight: 32
    readonly property real rowTopMargin: 2
    readonly property real rowIconSize: 22
    readonly property real rowIconGlyphSize: 14
    readonly property real rowTitleSize: 11
    readonly property real rowCheckboxSize: 16
    readonly property real rowCheckMarkSize: 10
    readonly property real rowSelectionBarHeight: 16

    // --- Typography ---
    readonly property string fontFamily: "Segoe UI Variable Display, Segoe UI, system-ui"
    readonly property real sizeHeading: 28
    readonly property real sizeLargeTitle: 24
    readonly property real sizeSectionTitle: 16
    readonly property real sizeBody: 14
    readonly property real sizeMetadata: 12
    readonly property real sizeCaption: sizeMetadata
    // Alias kept for guidance/hint copy that reads better at body-adjacent size.
    readonly property real sizeSubtext: sizeCaption

    function alpha(colorVal, opacity) {
        var c = Qt.color(colorVal)
        return Qt.rgba(c.r, c.g, c.b, opacity)
    }
}

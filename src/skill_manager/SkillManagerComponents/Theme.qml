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
    readonly property color disabledControl: darkMode ? "#1D1D21" : "#F1F5F9"
    readonly property color selectedRow: darkMode ? "#1E293B" : "#ECFDF5"
    readonly property color selectedRowHover: darkMode ? "#2A3B56" : "#D1FAE5"
    readonly property color selectedRowBorder: darkMode ? "#3B82F6" : accent
    readonly property color dangerHover: darkMode ? "#3F1A1A" : "#FEF2F2"
    
    readonly property color label: darkMode ? "#F3F4F6" : "#000000"
    readonly property color secondaryLabel: darkMode ? "#9CA3AF" : "#3F3F46"
    
    // Icon Contrast System (Pure Black #000000 for Light Mode - Whole Icon Dark & Contrasty)
    readonly property color iconLabel: darkMode ? "#F3F4F6" : "#000000"
    readonly property color iconSecondaryLabel: darkMode ? "#9CA3AF" : "#3F3F46"
    
    readonly property color accent: darkMode ? "#3B82F6" : "#059669" // Modern Blue for Dark, Sage for Light
    readonly property color success: darkMode ? "#10B981" : "#10B981"
    readonly property color danger: darkMode ? "#EF4444" : "#DC2626"
    
    // Aliases for compatibility
    readonly property color hoverBackground: glassHover

    // --- Layout (Softened for Forest look) ---
    readonly property real radiusPill: 20
    readonly property real radiusCard: 12 // Synchronized with native Win11 rounding (12px)
    readonly property real radiusButton: 20
    readonly property real radiusField: 20 // Pill style fields
    readonly property real radiusSmall: 10 // Reverted from 12
    
    // --- Typography ---
    readonly property string fontFamily: "Segoe UI Variable Display, Segoe UI, system-ui"
    readonly property real sizeHeading: 28
    readonly property real sizeLargeTitle: 24
    readonly property real sizeSectionTitle: 16
    readonly property real sizeBody: 14
    readonly property real sizeMetadata: 12
    readonly property real sizeCaption: sizeMetadata

    function alpha(colorVal, opacity) {
        var c = Qt.color(colorVal)
        return Qt.rgba(c.r, c.g, c.b, opacity)
    }
}

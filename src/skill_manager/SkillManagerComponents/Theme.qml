pragma Singleton
import QtQuick

QtObject {
    id: theme

    // --- State ---
    property bool darkMode: false

    // --- Colors ---
    // Modern Graphite (Solid Matte) - High Clarity
    readonly property color appBackground: darkMode ? "#121214" : "#F5F7F9"
    readonly property real glassNoiseOpacity: 0.0 // True matte finish
    
    // Material System
    readonly property color glassPill: darkMode ? "#1E1E22" : "#FFFFFF"
    readonly property color glassHover: darkMode ? "#2D2D34" : "#E8EAEF"
    readonly property color glassActive: darkMode ? "#3C3C46" : "#FFFFFF"
    readonly property color sidebarBackground: darkMode ? "#0F0F11" : "#F5F7F9"
    
    // Border System (Solid for matte surfaces)
    readonly property color glassBorder: darkMode ? "#2A2A30" : Qt.rgba(0.0, 0.0, 0.0, 0.08)
    readonly property color glassInnerBorder: "transparent"
    readonly property color glassOuterBorder: glassBorder
    
    readonly property color glassShadow: darkMode ? Qt.rgba(0.0, 0.0, 0.0, 0.5) : Qt.rgba(0.0, 0.0, 0.0, 0.12)
    readonly property color separator: darkMode ? "#26262B" : Qt.rgba(0.0, 0.0, 0.0, 0.08)
    readonly property color disabledControl: darkMode ? "#1D1D21" : "#EEF1F4"
    readonly property color selectedRow: darkMode ? "#1E293B" : "#DDF5EA"
    readonly property color selectedRowHover: darkMode ? "#2A3B56" : "#CFF0E2"
    readonly property color selectedRowBorder: darkMode ? "#3B82F6" : accent
    readonly property color dangerHover: darkMode ? "#3F1A1A" : "#FEE2E2"
    
    readonly property color label: darkMode ? "#F3F4F6" : "#111827"
    readonly property color secondaryLabel: darkMode ? "#9CA3AF" : "#6B7280"
    
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

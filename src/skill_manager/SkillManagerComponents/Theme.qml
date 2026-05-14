pragma Singleton
import QtQuick

QtObject {
    id: theme

    // --- State ---
    property bool darkMode: false

    // --- Colors ---
    // Hybrid Forest (Soft Matte) - High Clarity
    // Hybrid Forest (Solid Matte) - High Clarity
    readonly property color appBackground: darkMode ? "#0E1210" : "#F5F7F9"
    readonly property real glassNoiseOpacity: 0.0 // True matte finish
    
    // Material System
    readonly property color glassPill: darkMode ? "#1A201E" : "#FFFFFF"
    readonly property color glassHover: darkMode ? "#242D29" : "#E8EAEF"
    readonly property color glassActive: darkMode ? "#2D3833" : "#FFFFFF"
    readonly property color sidebarBackground: darkMode ? "#070A09" : "#F5F7F9"
    
    // Border System (Solid for matte surfaces)
    readonly property color glassBorder: darkMode ? "#2D3531" : Qt.rgba(0.0, 0.0, 0.0, 0.08)
    readonly property color glassInnerBorder: "transparent"
    readonly property color glassOuterBorder: glassBorder
    
    readonly property color glassShadow: darkMode ? Qt.rgba(0.0, 0.0, 0.0, 0.5) : Qt.rgba(0.0, 0.0, 0.0, 0.12)
    readonly property color separator: darkMode ? "#2D3531" : Qt.rgba(0.0, 0.0, 0.0, 0.08)
    
    readonly property color label: darkMode ? "#F3F4F6" : "#111827"
    readonly property color secondaryLabel: darkMode ? "#9CA3AF" : "#6B7280"
    
    readonly property color accent: darkMode ? "#10B981" : "#059669" // Vibrant Emerald for Dark, Sage for Light
    readonly property color success: darkMode ? "#34D399" : "#10B981"
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
}

pragma Singleton
import QtQuick

QtObject {
    id: theme

    // --- State ---
    property bool darkMode: false

    // --- Colors ---
    // Hybrid Forest (Soft Matte) - High Clarity
    // Hybrid Forest (Solid Matte) - High Clarity
    readonly property color appBackground: darkMode ? "#0B0F0D" : "#F5F7F9"
    readonly property real glassNoiseOpacity: 0.0 // True matte finish
    
    // Material System
    readonly property color glassPill: darkMode ? "#17201C" : "#FFFFFF"
    readonly property color glassHover: darkMode ? "#22312B" : "#E8EAEF"
    readonly property color glassActive: darkMode ? "#294139" : "#FFFFFF"
    readonly property color sidebarBackground: darkMode ? "#070A09" : "#F5F7F9"
    
    // Border System (Solid for matte surfaces)
    readonly property color glassBorder: darkMode ? "#34423B" : Qt.rgba(0.0, 0.0, 0.0, 0.08)
    readonly property color glassInnerBorder: "transparent"
    readonly property color glassOuterBorder: glassBorder
    
    readonly property color glassShadow: darkMode ? Qt.rgba(0.0, 0.0, 0.0, 0.5) : Qt.rgba(0.0, 0.0, 0.0, 0.12)
    readonly property color separator: darkMode ? "#2A3732" : Qt.rgba(0.0, 0.0, 0.0, 0.08)
    readonly property color disabledControl: darkMode ? "#1B2420" : "#EEF1F4"
    readonly property color selectedRow: darkMode ? "#123B2E" : "#DDF5EA"
    readonly property color selectedRowHover: darkMode ? "#164A39" : "#CFF0E2"
    readonly property color selectedRowBorder: darkMode ? "#31D19B" : accent
    readonly property color dangerHover: darkMode ? "#3B1718" : "#FEE2E2"
    
    readonly property color label: darkMode ? "#F2F7F4" : "#111827"
    readonly property color secondaryLabel: darkMode ? "#A8B4AE" : "#6B7280"
    
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

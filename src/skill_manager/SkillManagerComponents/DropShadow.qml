// Compatibility DropShadow component using Qt6 MultiEffect
// Replaces broken Qt5Compat.GraphicalEffects.DropShadow
// Used as: layer.effect: DropShadow { horizontalOffset: 0; verticalOffset: 4; ... }
import QtQuick
import QtQuick.Effects

MultiEffect {
    id: root

    // Qt5Compat DropShadow compatible properties
    // These map to the old API that callers expect
    property color color: Theme ? Theme.glassShadow : "#40000000"
    property int samples: 25
    property real radius: 0.5
    property real horizontalOffset: 0
    property real verticalOffset: 4
    property bool transparentBorder: true

    // Apply shadow effect using Qt6 MultiEffect API
    shadowEnabled: true
    shadowColor: root.color
    shadowBlur: root.radius / 24.0  // Normalize radius to 0-1 range for blur
    shadowHorizontalOffset: root.horizontalOffset
    shadowVerticalOffset: root.verticalOffset
    
    autoPaddingEnabled: true
}

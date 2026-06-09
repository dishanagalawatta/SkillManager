import QtQuick
import QtQuick.Controls

ScrollBar {
    id: control
    
    implicitWidth: 8
    policy: ScrollBar.AsNeeded
    interactive: true
    
    property bool _isScrolling: false
    
    Timer {
        id: hideTimer
        interval: 800
        onTriggered: control._isScrolling = false
    }
    
    onPositionChanged: {
        control._isScrolling = true
        hideTimer.restart()
    }

    contentItem: Rectangle {
        implicitWidth: 6
        radius: 3
        color: Theme.secondaryLabel
        
        readonly property bool shouldShow: control.active || control.hovered || control.pressed || control._isScrolling
        
        // Fully visible at 0.8 when hovered or pressed.
        // Active scroll visible at 0.6.
        // Invisible when inactive.
        opacity: shouldShow ? (control.hovered || control.pressed ? 0.8 : 0.6) : 0.0
        
        Behavior on opacity { NumberAnimation { duration: 250 } }
    }
    
    background: Item {
        implicitWidth: 8
    }
}

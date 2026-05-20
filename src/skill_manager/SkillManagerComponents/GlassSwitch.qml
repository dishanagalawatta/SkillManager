import QtQuick
import QtQuick.Controls
import Qt5Compat.GraphicalEffects
import App 1.0

Switch {
    id: control
    
    implicitWidth: 44
    implicitHeight: 24

    indicator: Rectangle {
        implicitWidth: 44
        implicitHeight: 24
        x: control.leftPadding
        y: parent.height / 2 - height / 2
        radius: height / 2
        color: control.checked ? Theme.accent : Theme.glassHover
        border.color: control.visualFocus ? Theme.accent : Theme.glassBorder
        border.width: control.visualFocus ? 2 : 1

        Behavior on color {
            ColorAnimation { duration: 200 }
        }

        Behavior on border.color {
            ColorAnimation { duration: 200 }
        }

        // Inner Glow / Shadow for depth
        InnerShadow {
            anchors.fill: parent
            radius: 8
            samples: 16
            horizontalOffset: 0
            verticalOffset: 1
            color: control.checked ? Qt.rgba(0,0,0,0.2) : Qt.rgba(1,1,1,0.05)
            source: parent
        }

        Rectangle {
            id: handle
            x: control.checked ? parent.width - width - 4 : 4
            y: 4
            width: 16
            height: 16
            radius: 8
            color: Theme.darkMode ? "#E2E8F0" : "#FFFFFF"
            
            layer.enabled: true
            layer.effect: RectangularGlow {
                anchors.fill: handle
                glowRadius: 4
                spread: 0.2
                color: control.checked ? (Theme.darkMode ? Qt.rgba(0.2, 0.73, 0.5, 0.4) : Qt.rgba(0, 0.53, 0.35, 0.4)) : "transparent"
                cornerRadius: handle.radius
                
                Behavior on color {
                    ColorAnimation { duration: 200 }
                }
            }
            
            // The white circle on top of the glow
            Rectangle {
                anchors.fill: parent
                radius: parent.radius
                color: Theme.darkMode ? "#E2E8F0" : "#FFFFFF"
                
                layer.enabled: true
                layer.effect: DropShadow {
                    transparentBorder: true
                    radius: 4
                    samples: 8
                    color: Qt.rgba(0,0,0,0.3)
                }
            }

            Behavior on x {
                NumberAnimation {
                    duration: 250
                    easing.type: Easing.OutQuint
                }
            }
        }
    }

    contentItem: Text {
        text: control.text
        font: control.font
        color: Theme.label
        verticalAlignment: Text.AlignVCenter
        leftPadding: control.indicator.width + control.spacing
    }

    HoverHandler {
        cursorShape: Qt.PointingHandCursor
    }

    Accessible.role: Accessible.CheckBox
    Accessible.name: control.text
}

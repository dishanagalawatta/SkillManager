import QtQuick
import QtQuick.Controls
import App 1.0

Item {
    id: control
    
    property int checkState: Qt.Unchecked
    property string tooltipText: checkState === Qt.Unchecked ? "Select All" : "Clear Selection"
    property int buttonSize: 28
    property int iconSize: 12

    signal toggled()

    width: buttonSize
    height: buttonSize

    activeFocusOnTab: true

    Keys.onSpacePressed: { control.toggled(); event.accepted = true; }
    Keys.onReturnPressed: { control.toggled(); event.accepted = true; }
    Keys.onEnterPressed: { control.toggled(); event.accepted = true; }

    Rectangle {
        id: bgRect
        anchors.fill: parent
        radius: width / 2
        
        // Background color logic: Accent for active states, glass for inactive
        color: {
            if (control.checkState === Qt.Checked || control.checkState === Qt.PartiallyChecked) {
                return mouseArea.pressed ? Theme.alpha(Theme.accent, 0.8) : Theme.accent
            }
            return mouseArea.pressed ? Theme.glassActive : (mouseArea.containsMouse ? Theme.glassHover : "transparent")
        }
        
        border.color: {
            if (control.activeFocus) return Theme.accent
            if (control.checkState === Qt.Checked || control.checkState === Qt.PartiallyChecked) {
                return "transparent"
            }
            return mouseArea.containsMouse ? Theme.accent : Theme.alpha(Theme.label, 0.15)
        }
        border.width: control.activeFocus ? 2 : 1

        Behavior on color { ColorAnimation { duration: 200 } }
        Behavior on border.color { ColorAnimation { duration: 200 } }

        // The Checkmark or Minus icon
        Item {
            anchors.centerIn: parent
            width: control.iconSize
            height: control.iconSize
            opacity: control.checkState !== Qt.Unchecked ? 1.0 : 0.0
            scale: control.checkState !== Qt.Unchecked ? 1.0 : 0.5
            
            Behavior on opacity { NumberAnimation { duration: 200 } }
            Behavior on scale { NumberAnimation { duration: 200; easing.type: Easing.OutBack } }

            Image {
                id: iconImg
                anchors.centerIn: parent
                width: control.iconSize
                height: control.iconSize
                source: AppController.ui_controller.getAssetUri("ui/check-icon.svg")
                sourceSize.width: 32
                sourceSize.height: 32
                fillMode: Image.PreserveAspectFit
                smooth: true
                visible: control.checkState === Qt.Checked
            }
            
            ColorOverlay {
                anchors.fill: iconImg
                source: iconImg
                color: "white"
                visible: control.checkState === Qt.Checked
            }
            
            // Refined minus sign for partially checked
            Rectangle {
                anchors.centerIn: parent
                width: 8
                height: 2
                radius: 1
                color: "white"
                visible: control.checkState === Qt.PartiallyChecked
            }
        }
    }

    MouseArea {
        id: mouseArea
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: {
            control.forceActiveFocus();
            control.toggled();
        }
    }

    SleekToolTip {
        id: cbToolTip
        visible: mouseArea.containsMouse && tooltipText !== ""
        text: tooltipText
    }
    
    Accessible.role: Accessible.CheckBox
    Accessible.name: tooltipText
    Accessible.checked: checkState === Qt.Checked || checkState === Qt.PartiallyChecked
}

import QtQuick
import QtQuick.Controls
import App 1.0

Item {
    id: control
    
    property int checkState: Qt.Unchecked
    property string tooltipText: checkState === Qt.Unchecked ? "Select All" : "Clear Selection"
    property int buttonSize: 28
    property int iconSize: 12
    property color checkedColor: Theme.accent
    property color checkedHoverColor: Theme.alpha(Theme.accent, 0.8)
    property color iconColor: "white"

    signal toggled()

    width: buttonSize
    height: buttonSize

    activeFocusOnTab: true

    Keys.onSpacePressed: (event) => { control.toggled(); event.accepted = true; }
    Keys.onReturnPressed: (event) => { control.toggled(); event.accepted = true; }
    Keys.onEnterPressed: (event) => { control.toggled(); event.accepted = true; }

    // If true, the checkbox acts purely as a 'clear' button when checked/partially checked
    property bool isClearAction: false

    Rectangle {
        id: bgRect
        anchors.fill: parent
        radius: width / 2
        
        color: {
            if (control.checkState === Qt.Checked && !control.isClearAction) {
                return mouseArea.pressed ? control.checkedHoverColor : control.checkedColor
            }
            return mouseArea.pressed ? Theme.glassActive : (mouseArea.containsMouse ? Theme.glassHover : "transparent")
        }
        
        border.color: {
            if (control.checkState === Qt.PartiallyChecked || (control.isClearAction && control.checkState === Qt.Checked)) return "transparent"
            if (control.activeFocus) return Theme.accent
            if (control.checkState === Qt.Checked) {
                return control.checkedColor === "transparent" ? Theme.glassBorder : "transparent"
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
                visible: control.checkState === Qt.Checked && !control.isClearAction
            }
            
            ColorOverlay {
                anchors.fill: iconImg
                source: iconImg
                color: control.iconColor
                visible: iconImg.visible
            }
            
            Image {
                id: minusImg
                anchors.centerIn: parent
                width: control.buttonSize
                height: control.buttonSize
                source: AppController.ui_controller.getAssetUri("ui/close-circle-broken.svg")
                sourceSize.width: 32
                sourceSize.height: 32
                fillMode: Image.PreserveAspectFit
                smooth: true
                visible: control.checkState === Qt.PartiallyChecked || (control.isClearAction && control.checkState === Qt.Checked)
            }
            
            ColorOverlay {
                anchors.fill: minusImg
                source: minusImg
                color: control.iconColor
                visible: minusImg.visible
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
        visible: (mouseArea.containsMouse || control.activeFocus) && control.tooltipText !== ""
        text: control.tooltipText
    }
    
    Accessible.role: Accessible.CheckBox
    Accessible.name: tooltipText
    Accessible.checked: checkState === Qt.Checked || checkState === Qt.PartiallyChecked
}

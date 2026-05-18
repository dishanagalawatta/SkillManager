import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App 1.0
import SkillManagerComponents 1.0

Button {
    id: control

    property bool active: false
    property string iconText: ""
    property string labelText: ""

    padding: 0
    implicitHeight: 36

    contentItem: Item {
        implicitHeight: 36
        implicitWidth: contentLayout.implicitWidth + 24

        RowLayout {
            id: contentLayout
            anchors.centerIn: parent
            spacing: 8

            Text {
                text: control.iconText
                font.family: Theme.fontFamily
                font.pixelSize: Theme.sizeBody
                font.weight: control.active ? Font.Bold : Font.Normal
                color: control.active ? Theme.label : Theme.secondaryLabel
                visible: control.iconText !== ""
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                Layout.alignment: Qt.AlignVCenter
            }

            Text {
                text: control.labelText
                font.family: Theme.fontFamily
                font.pixelSize: Theme.sizeBody
                font.weight: control.active ? Font.Bold : Font.Normal
                color: control.active ? Theme.label : Theme.secondaryLabel
                visible: control.labelText !== ""
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                Layout.alignment: Qt.AlignVCenter
            }
        }
    }

    background: Rectangle {
        color: control.active ? Theme.glassActive : (control.hovered ? Theme.glassHover : "transparent")
        radius: Theme.radiusPill
        border.color: control.visualFocus ? Theme.accent : "transparent"
        border.width: control.visualFocus ? 2 : 0

        Rectangle {
            visible: control.active
            anchors.bottom: parent.bottom
            anchors.horizontalCenter: parent.horizontalCenter
            width: parent.width * 0.6
            height: 3
            radius: Theme.radiusSmall
            color: Theme.accent
        }
    }
    Accessible.role: Accessible.Button
    Accessible.name: control.labelText

    HoverHandler {
        cursorShape: Qt.PointingHandCursor
    }
}

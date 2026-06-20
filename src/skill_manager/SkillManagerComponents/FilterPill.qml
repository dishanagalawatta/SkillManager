import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App 1.0

Button {
    id: control

    property bool isActive: false
    property string iconText: ""

    signal activeChanged(bool active)

    padding: 0

    contentItem: Item {
        implicitHeight: 32
        implicitWidth: contentRow.implicitWidth + 16

        RowLayout {
            id: contentRow
            anchors.centerIn: parent
            spacing: 6

            Text {
                text: control.iconText
                font.pixelSize: 14
                color: Theme.secondaryLabel
                visible: control.iconText !== ""
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                Layout.alignment: Qt.AlignVCenter
            }

            Text {
                text: control.text
                font.family: Theme.fontFamily
                font.pixelSize: 12
                font.weight: control.isActive ? Font.Bold : Font.Normal
                color: Theme.label
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                Layout.alignment: Qt.AlignVCenter
            }
        }
    }

    background: Rectangle {
        implicitHeight: 32
        radius: Theme.radiusPill
        color: control.isActive ? Theme.glassActive : (control.hovered ? Theme.glassHover : Theme.glassPill)
        border.color: control.visualFocus ? Theme.accent : (control.isActive ? Theme.accent : Theme.glassBorder)
        border.width: control.visualFocus ? 2 : 1

        Behavior on color { ColorAnimation { duration: 200 } }
        Behavior on border.color { ColorAnimation { duration: 200 } }
    }

    onClicked: control.activeChanged(control.isActive)

    Accessible.role: Accessible.Button
    Accessible.name: control.text
}

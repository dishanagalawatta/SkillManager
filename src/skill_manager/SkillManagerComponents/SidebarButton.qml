import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App 1.0

Button {
    id: control

    property bool active: false
    property bool collapsed: false
    property string iconText: ""
    property string iconSource: ""
    property string labelText: ""

    Layout.fillWidth: true
    Layout.preferredHeight: 40
    padding: 0

    SleekToolTip {
        id: btnToolTip
        visible: control.hovered && control.collapsed
        text: control.labelText
    }

    contentItem: Item {
        implicitHeight: 40

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 12
            anchors.rightMargin: 12
            spacing: 12

            Item {
                visible: control.iconText !== "" || control.iconSource !== ""
                width: 16
                height: 16
                Layout.alignment: Qt.AlignVCenter

                Text {
                    anchors.centerIn: parent
                    text: control.iconText
                    visible: control.iconSource === "" && control.iconText !== ""
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.sizeBody
                    font.weight: control.active ? Font.Bold : Font.Normal
                    color: control.active ? Theme.label : Theme.secondaryLabel
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }

                Image {
                    id: iconImg
                    anchors.fill: parent
                    visible: control.iconSource !== ""
                    source: control.iconSource
                    sourceSize.width: 16
                    sourceSize.height: 16
                    fillMode: Image.PreserveAspectFit
                    smooth: true
                }

                ColorOverlay {
                    anchors.fill: iconImg
                    source: iconImg
                    color: control.active ? Theme.label : Theme.secondaryLabel
                    visible: control.iconSource !== ""
                }
            }

            Text {
                text: control.labelText
                font.family: Theme.fontFamily
                font.pixelSize: Theme.sizeBody
                font.weight: control.active ? Font.Bold : Font.Normal
                color: control.active ? Theme.label : Theme.secondaryLabel
                Layout.fillWidth: true
                Layout.alignment: Qt.AlignVCenter
                visible: !control.collapsed
                elide: Text.ElideRight
                verticalAlignment: Text.AlignVCenter
            }
        }
    }

    background: Rectangle {
        color: control.active ? Theme.glassActive : (control.hovered ? Theme.glassHover : "transparent")
        radius: Theme.radiusPill
        border.color: control.visualFocus ? Theme.accent : "transparent"
        border.width: control.visualFocus ? 2 : 0
    }
    Accessible.role: Accessible.Button
    Accessible.name: control.labelText

    HoverHandler {
        cursorShape: Qt.PointingHandCursor
    }
}

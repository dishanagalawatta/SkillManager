import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Qt5Compat.GraphicalEffects
import App 1.0

Button {
    id: control

    property bool active: false
    property string iconText: ""
    property string iconSource: ""
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
                visible: control.labelText !== ""
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                Layout.alignment: Qt.AlignVCenter
            }
        }
    }

    background: Item {
        Rectangle {
            anchors.fill: parent
            color: control.active ? Theme.glassActive : (control.hovered ? Theme.glassHover : "transparent")
            radius: Theme.radiusPill
            border.color: control.visualFocus ? Theme.accent : "transparent"
            border.width: control.visualFocus ? 2 : 0
        }

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

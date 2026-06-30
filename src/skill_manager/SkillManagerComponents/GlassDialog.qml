import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import App 1.0
import "."

Dialog {
    id: root

    property string dialogTitle: ""
    property string dialogIcon: ""
    property bool showCloseButton: true

    modal: true
    padding: 0
    // We intentionally omit `title` to prevent the native OS header from rendering.

    background: Rectangle {
        color: Theme.glassPill
        radius: Theme.radiusCard
        border.color: Theme.glassBorder
        border.width: 1

        layer.enabled: true
        layer.effect: DropShadow {
            radius: 20
            color: Theme.glassShadow
            verticalOffset: 8
            horizontalOffset: 0
        }
    }

    header: Item {
        width: root.width
        height: root.dialogTitle !== "" ? 60 : 0
        implicitHeight: height
        visible: root.dialogTitle !== ""

        Rectangle {
            anchors.fill: parent
            color: "transparent"

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 24
                anchors.rightMargin: 16
                spacing: 12

                Text {
                    text: root.dialogIcon
                    font.pixelSize: 20
                    visible: root.dialogIcon !== ""
                }

                Text {
                    text: root.dialogTitle
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.sizeSectionTitle
                    font.weight: Font.Bold
                    color: Theme.label
                    Layout.fillWidth: true
                    elide: Text.ElideRight
                }

                IconButton {
                    text: "\u2715"
                    flat: true
                    Layout.preferredWidth: 32
                    Layout.preferredHeight: 32
                    visible: root.showCloseButton
                    onClicked: root.reject()

                    background: Rectangle {
                        radius: 16
                        color: parent.hovered ? Theme.glassHover : "transparent"
                    }

                    contentItem: Text {
                        text: parent.text
                        font.pixelSize: 16
                        color: Theme.secondaryLabel
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                }
            }

            Rectangle {
                anchors.bottom: parent.bottom
                width: parent.width
                height: 1
                color: Theme.separator
            }
        }
    }
}

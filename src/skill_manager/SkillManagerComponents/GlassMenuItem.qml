import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import App 1.0

MenuItem {
    id: control

    property string iconText: ""
    property string shortcut: ""
    property bool showIcon: AppController.config_controller.showMenuIcons
    property bool isCompact: AppController.config_controller.compactMenu

    implicitWidth: 200
    implicitHeight: isCompact ? 32 : 40

    contentItem: RowLayout {
        spacing: 12
        anchors.fill: parent
        anchors.leftMargin: 12
        anchors.rightMargin: 12

        Text {
            visible: control.showIcon && control.iconText !== ""
            text: control.iconText
            font.pixelSize: 16
            Layout.alignment: Qt.AlignVCenter
        }

        Text {
            text: control.text
            font.family: Theme.fontFamily
            font.pixelSize: 13
            font.weight: control.highlighted ? Font.DemiBold : Font.Normal
            color: control.highlighted ? Theme.label : Theme.secondaryLabel
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignVCenter
            elide: Text.ElideRight
        }

        Text {
            visible: control.shortcut !== ""
            text: control.shortcut
            font.family: Theme.fontFamily
            font.pixelSize: 11
            color: Theme.secondaryLabel
            opacity: 0.6
            Layout.alignment: Qt.AlignVCenter
        }
    }

    background: Rectangle {
        implicitWidth: 200
        implicitHeight: control.isCompact ? 32 : 40
        opacity: enabled ? 1 : 0.3
        color: control.highlighted ? Theme.glassHover : "transparent"
        radius: Theme.radiusSmall

        Behavior on color {
            ColorAnimation { duration: 150 }
        }

        // Left accent indicator on hover
        Rectangle {
            anchors.left: parent.left
            anchors.leftMargin: 4
            anchors.verticalCenter: parent.verticalCenter
            width: 3
            height: parent.height * 0.4
            radius: 2
            color: Theme.accent
            visible: control.highlighted
        }
    }
}

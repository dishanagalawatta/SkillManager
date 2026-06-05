import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import Qt5Compat.GraphicalEffects
import App 1.0

MenuItem {
    id: control

    property string iconText: ""
    property string iconSource: ""
    property string shortcut: ""
    property bool showIcon: AppController.config_controller ? AppController.config_controller.showMenuIcons : true
    property bool isCompact: AppController.config_controller ? AppController.config_controller.compactMenu : false

    implicitWidth: 200
    implicitHeight: isCompact ? 32 : 40

    contentItem: RowLayout {
        spacing: 12
        anchors.fill: parent
        anchors.leftMargin: 12
        anchors.rightMargin: 12

        Item {
            visible: control.showIcon && (control.iconText !== "" || control.iconSource !== "")
            width: 16
            height: 16
            Layout.alignment: Qt.AlignVCenter

            Text {
                anchors.centerIn: parent
                visible: control.iconSource === "" && control.iconText !== ""
                text: control.iconText
                font.pixelSize: 16
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
                color: control.highlighted ? Theme.label : Theme.secondaryLabel
                visible: control.iconSource !== ""
            }
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

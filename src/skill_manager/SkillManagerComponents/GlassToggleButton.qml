import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Effects
import App 1.0

/**
 * Purpose: A modernized, glass-styled toggle button for the Skill Manager.
 * Usage:
 *   GlassToggleButton {
 *       text: "Show Archived"
 *       checked: model.showArchived
 *       onClicked: model.showArchived = !checked
 *   }
 */
Button {
    id: control

    property string iconInactive: ""
    property string iconActive: ""
    property string iconSourceInactive: ""
    property string iconSourceActive: ""
    property string textInactive: text
    property string textActive: text
    property string tooltipText: checked ? textActive : textInactive

    checkable: true
    padding: 0

    implicitWidth: contentLayout.implicitWidth + 32
    implicitHeight: 36

    contentItem: Item {
        implicitWidth: contentLayout.implicitWidth
        implicitHeight: 36

        RowLayout {
            id: contentLayout
            anchors.centerIn: parent
            spacing: 8

            Item {
                visible: (control.checked ? (control.iconActive !== "" || control.iconSourceActive !== "") : (control.iconInactive !== "" || control.iconSourceInactive !== ""))
                width: 16
                height: 16
                Layout.alignment: Qt.AlignVCenter

                Text {
                    anchors.centerIn: parent
                    text: control.checked ? control.iconActive : control.iconInactive
                    visible: control.checked ? (control.iconSourceActive === "" && control.iconActive !== "") : (control.iconSourceInactive === "" && control.iconInactive !== "")
                    font.family: Theme.fontFamily
                    font.pixelSize: 16
                    color: control.checked ? Theme.accent : Theme.secondaryLabel
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter

                    Behavior on color { ColorAnimation { duration: 200 } }
                }

                Image {
                    id: iconImg
                    anchors.fill: parent
                    visible: control.checked ? control.iconSourceActive !== "" : control.iconSourceInactive !== ""
                    source: control.checked ? control.iconSourceActive : control.iconSourceInactive
                    sourceSize.width: 16
                    sourceSize.height: 16
                    fillMode: Image.PreserveAspectFit
                    smooth: true
                }

                ColorOverlay {
                    anchors.fill: iconImg
                    source: iconImg
                    color: control.checked ? Theme.accent : Theme.secondaryLabel
                    visible: iconImg.visible
                }
            }

            Text {
                text: control.checked ? control.textActive : control.textInactive
                font.family: Theme.fontFamily
                font.pixelSize: Theme.sizeBody
                font.weight: control.checked ? Font.DemiBold : Font.Normal
                color: control.checked ? Theme.label : Theme.secondaryLabel
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                Layout.alignment: Qt.AlignVCenter

                Behavior on color { ColorAnimation { duration: 200 } }
            }
        }
    }

    background: Item {
        Rectangle {
            id: bgRect
            anchors.fill: parent
            radius: Theme.radiusPill
            color: control.checked ? Theme.selectedRow : (control.down ? Theme.glassActive : (control.hovered ? Theme.glassHover : Theme.glassPill))
            border.color: control.visualFocus ? Theme.accent : (control.checked ? Theme.selectedRowBorder : Theme.glassBorder)
            border.width: control.visualFocus ? 2 : 1

            Behavior on color { ColorAnimation { duration: 200 } }
            Behavior on border.color { ColorAnimation { duration: 200 } }

            layer.enabled: true
            layer.effect: MultiEffect {
                shadowEnabled: control.hovered || control.checked
                shadowBlur: 0.5
                shadowColor: Theme.glassShadow
                shadowVerticalOffset: 2
            }
        }
    }

    HoverHandler {
        cursorShape: Qt.PointingHandCursor
    }

    SleekToolTip {
        id: btnToolTip
        visible: (control.hovered || control.visualFocus) && control.tooltipText !== ""
        text: control.tooltipText
    }
    Accessible.role: Accessible.Button
    Accessible.name: text
    Accessible.description: tooltipText
}

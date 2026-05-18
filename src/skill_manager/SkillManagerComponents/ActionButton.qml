import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import SkillManagerComponents 1.0

Button {
    id: control

    property string iconText: ""
    property string labelText: text
    property string role: "secondary" // primary, secondary, destructive
    property string tooltipText: ""
    property string accessibleName: labelText
    property int buttonHeight: 36
    property int sidePadding: labelText !== "" ? 16 : 0

    Layout.preferredHeight: buttonHeight
    implicitHeight: buttonHeight
    implicitWidth: Math.max(buttonHeight, contentRow.implicitWidth + sidePadding * 2)
    padding: 0
    flat: true

    contentItem: Item {
        implicitWidth: contentRow.implicitWidth
        implicitHeight: control.buttonHeight

        RowLayout {
            id: contentRow
            anchors.centerIn: parent
            spacing: control.iconText !== "" && control.labelText !== "" ? 7 : 0

            Text {
                text: control.iconText
                visible: control.iconText !== ""
                font.family: Theme.fontFamily
                font.pixelSize: 14
                color: {
                    if (!control.enabled) return Theme.secondaryLabel
                    if (control.role === "primary") return "white"
                    if (control.role === "destructive") return Theme.danger
                    return control.hovered || control.down ? Theme.label : Theme.accent
                }
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                Layout.alignment: Qt.AlignVCenter
            }

            Text {
                text: control.labelText
                visible: control.labelText !== ""
                font.family: Theme.fontFamily
                font.pixelSize: 12
                font.weight: control.role === "primary" ? Font.Bold : Font.DemiBold
                color: {
                    if (!control.enabled) return Theme.secondaryLabel
                    if (control.role === "primary") return "white"
                    if (control.role === "destructive") return Theme.danger
                    return control.hovered || control.down ? Theme.label : Theme.accent
                }
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                Layout.alignment: Qt.AlignVCenter
            }
        }
    }

    background: Rectangle {
        radius: Theme.radiusField
        color: {
            if (!control.enabled) return Theme.disabledControl
            if (control.role === "primary") return control.down ? Theme.glassActive : (control.hovered ? Theme.selectedRowBorder : Theme.accent)
            if (control.role === "destructive") return control.down ? Theme.dangerHover : (control.hovered ? Theme.dangerHover : "transparent")
            return control.down ? Theme.glassActive : (control.hovered ? Theme.glassHover : "transparent")
        }
        border.color: {
            if (control.visualFocus) return Theme.accent
            if (!control.enabled) return Theme.glassBorder
            if (control.role === "destructive") return control.hovered || control.down ? Theme.danger : "transparent"
            return control.hovered || control.down ? Theme.glassBorder : "transparent"
        }
        border.width: control.visualFocus ? 2 : (control.role === "primary" ? 0 : (control.hovered || !control.enabled ? 1 : 0))
        opacity: control.enabled ? 1.0 : 0.65
    }

    ToolTip.visible: hovered && tooltipText !== ""
    ToolTip.delay: 400
    ToolTip.text: tooltipText
    Accessible.role: Accessible.Button
    Accessible.name: accessibleName
    Accessible.description: tooltipText

    HoverHandler {
        cursorShape: control.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
    }
}

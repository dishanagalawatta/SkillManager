import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Button {
    id: control

    property string iconText: ""
    property string iconSource: ""
    property string labelText: text
    property string role: "secondary" // primary, secondary, destructive, danger
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
            spacing: (control.iconText !== "" || control.iconSource !== "") && control.labelText !== "" ? 7 : 0

            Item {
                visible: control.iconText !== "" || control.iconSource !== ""
                width: 14
                height: 14
                Layout.alignment: Qt.AlignVCenter

                Text {
                    anchors.centerIn: parent
                    text: control.iconText
                    visible: control.iconSource === "" && control.iconText !== ""
                    font.family: Theme.fontFamily
                    font.pixelSize: 14
                    color: {
                        if (!control.enabled) return Theme.secondaryLabel
                        if (control.role === "primary") return "white"
                        if (control.role === "danger") return "white"
                        if (control.role === "destructive") return Theme.danger
                        return control.hovered || control.down ? Theme.label : Theme.accent
                    }
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }

                Image {
                    id: iconImg
                    anchors.fill: parent
                    visible: control.iconSource !== ""
                    source: control.iconSource
                    sourceSize.width: 14
                    sourceSize.height: 14
                    fillMode: Image.PreserveAspectFit
                    smooth: true
                }

                ColorOverlay {
                    anchors.fill: iconImg
                    source: iconImg
                    color: {
                        if (!control.enabled) return Theme.secondaryLabel
                        if (control.role === "primary") return "white"
                        if (control.role === "danger") return "white"
                        if (control.role === "destructive") return Theme.danger
                        return control.hovered || control.down ? Theme.label : Theme.accent
                    }
                    visible: control.iconSource !== ""
                }
            }

            Text {
                text: control.labelText
                visible: control.labelText !== ""
                font.family: Theme.fontFamily
                font.pixelSize: 12
                font.weight: control.role === "primary" || control.role === "danger" ? Font.Bold : Font.DemiBold
                color: {
                    if (!control.enabled) return Theme.secondaryLabel
                    if (control.role === "primary") return "white"
                    if (control.role === "danger") return "white"
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
            if (control.role === "danger") return !control.enabled ? Theme.disabledControl : (control.down ? Theme.dangerHover : (control.hovered ? Theme.alpha(Theme.danger, 0.88) : Theme.danger))
            if (control.role === "destructive") return control.down ? Theme.dangerHover : (control.hovered ? Theme.dangerHover : "transparent")
            return control.down ? Theme.glassActive : (control.hovered ? Theme.glassHover : "transparent")
        }
        border.color: {
            if (control.visualFocus) return Theme.accent
            if (!control.enabled) return Theme.glassBorder
            if (control.role === "danger") return control.visualFocus ? Theme.label : "transparent"
            if (control.role === "destructive") return control.hovered || control.down ? Theme.danger : "transparent"
            return control.hovered || control.down ? Theme.glassBorder : "transparent"
        }
        border.width: control.visualFocus ? 2 : (control.role === "primary" || control.role === "danger" ? 0 : (control.hovered || !control.enabled ? 1 : 0))
        opacity: control.enabled ? 1.0 : 0.65
    }

    SleekToolTip {
        visible: control.hovered && control.tooltipText !== ""
        text: control.tooltipText
    }
    Accessible.role: Accessible.Button
    Accessible.name: accessibleName
    Accessible.description: tooltipText

    HoverHandler {
        cursorShape: control.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
    }
}

import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import App 1.0

/*!
    \qmltype InspectorMetadataRow
    \inqmlmodule SkillManagerComponents
    \brief Reusable metadata pill flow component for inspector panels with collapsible header.

    Renders key-value badges (Location, Type, Risk, Source, Date) using design system
    tokens from Theme.qml. Supports interactive expand/collapse to free up vertical space for skill body content.
*/
ColumnLayout {
    id: root

    property var selectedSkill: null
    property var contextMenu: null
    property bool isExpanded: true

    Layout.fillWidth: true
    spacing: 4
    visible: root.selectedSkill && root.selectedSkill.local_path !== undefined && !root.selectedSkill.is_snap

    // Section Header Row
    Item {
        id: headerItem
        Layout.fillWidth: true
        implicitHeight: metaHeaderRow.implicitHeight
        activeFocusOnTab: true

        Keys.onPressed: (event) => {
            if (event.key === Qt.Key_Space || event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
                root.isExpanded = !root.isExpanded
                event.accepted = true
            } else {
                event.accepted = false
            }
        }

        Rectangle {
            anchors.fill: parent
            color: headerItem.activeFocus ? Theme.glassActive : (headerHover.hovered ? Theme.glassHover : "transparent")
            radius: Theme.radiusSmall
            border.color: headerItem.activeFocus ? Theme.accent : "transparent"
            border.width: headerItem.activeFocus ? 2 : 0
            anchors.margins: -4
        }

        RowLayout {
            id: metaHeaderRow
            anchors.fill: parent
            spacing: 4

            Text {
                text: "Metadata"
                font.family: Theme.fontFamily
                font.pixelSize: 10
                font.weight: Font.Bold
                color: Theme.secondaryLabel
                opacity: 0.8
            }

            Item { Layout.fillWidth: true }

            IconButton {
                id: metaToggleBtn
                buttonSize: 18
                iconSize: 12
                role: "ghost"
                focusPolicy: Qt.NoFocus
                tooltipText: "" // Handled by headerItem
                iconSource: root.isExpanded ?
                    AppController.ui_controller.getAssetUri("ui/collapse-arrow-up-broken.svg") :
                    AppController.ui_controller.getAssetUri("ui/collapse-arrow-down-broken.svg")
            }
        }

        TapHandler {
            onTapped: root.isExpanded = !root.isExpanded
        }

        HoverHandler {
            id: headerHover
            cursorShape: Qt.PointingHandCursor
        }

        SleekToolTip {
            visible: headerHover.hovered || headerItem.activeFocus
            text: root.isExpanded ? "Collapse Metadata" : "Expand Metadata"
        }

        Accessible.role: Accessible.Button
        Accessible.name: root.isExpanded ? "Collapse Metadata" : "Expand Metadata"
    }

    Flow {
        id: metaFlow
        Layout.fillWidth: true
        spacing: 8
        visible: root.isExpanded

        Repeater {
            model: (root.selectedSkill && root.selectedSkill.local_path) ? [
                { label: "Location", value: root.selectedSkill.project_label || "Unknown" },
                { label: "Type", value: root.selectedSkill.category || "Unknown" },
                { label: "Risk", value: root.selectedSkill.risk || "Unknown" },
                { label: "Source", value: root.selectedSkill.source || "Unknown" },
                { label: "Date", value: root.selectedSkill.date || "Unknown" }
            ] : []

            Rectangle {
                height: 26
                width: rowLayout.implicitWidth + 16
                radius: Theme.radiusSmall
                color: Theme.glassPill
                border.color: Theme.glassBorder
                border.width: 1
                visible: modelData.value && modelData.value.toLowerCase() !== "unknown"

                Row {
                    id: rowLayout
                    anchors.centerIn: parent
                    spacing: 4

                    Text {
                        text: modelData.label + ":"
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.sizeMetadata
                        font.weight: Font.DemiBold
                        color: Theme.secondaryLabel
                        anchors.verticalCenter: parent.verticalCenter
                    }

                    TextEdit {
                        id: metaValEdit
                        text: modelData.value
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.sizeMetadata
                        color: Theme.label
                        readOnly: true
                        selectByMouse: true
                        cursorVisible: false
                        anchors.verticalCenter: parent.verticalCenter

                        MouseArea {
                            anchors.fill: parent
                            acceptedButtons: Qt.RightButton
                            onClicked: (mouse) => {
                                if (root.contextMenu) {
                                    root.contextMenu.targetControl = metaValEdit
                                    root.contextMenu.popup()
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}


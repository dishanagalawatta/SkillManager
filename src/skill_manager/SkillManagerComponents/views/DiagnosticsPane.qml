/**
 * Purpose: Diagnostics pane for the Settings About tab.
 * Surfaces raw collection data, project resolution, missing-skills output,
 * diagnostic log path, recent events, and bundle export for agent/agent use.
 */
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import ".."
import App 1.0

Item {
    id: root

    property bool expanded: false
    property string collectionsJson: "{}"
    property string projectResolutionJson: "{}"
    property string selectedCollection: ""
    property string missingCheckJson: "{}"
    property string diagnosticLogPath: ""
    property string recentEventsJson: "[]"
    property string bundleExportResult: ""

    implicitHeight: contentLayout.implicitHeight + 32

    function refresh() {
        collectionsJson = AppController.config_controller.getCollectionsDiagnostic()
        projectResolutionJson = AppController.config_controller.getProjectResolutionTable()
        diagnosticLogPath = AppController.config_controller.getDiagnosticLogPath()
        recentEventsJson = AppController.config_controller.getRecentDiagnosticEvents(20)
        if (selectedCollection !== "") {
            missingCheckJson = AppController.config_controller.checkMissingSkills(selectedCollection)
        }
    }

    ColumnLayout {
        id: contentLayout
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: 16
        spacing: 12

        // Section header
        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            Text {
                text: "Diagnostics"
                font.family: Theme.fontFamily
                font.pixelSize: Theme.sizeSectionTitle
                font.weight: Font.Bold
                color: Theme.label
            }

            Item { Layout.fillWidth: true }

            GlassToggleButton {
                id: expandToggle
                Layout.preferredWidth: 90
                Layout.preferredHeight: 28
                text: root.expanded ? "Collapse" : "Expand"
                onClicked: {
                    root.expanded = !root.expanded
                    if (root.expanded) root.refresh()
                }
            }

            IconButton {
                buttonSize: 28
                iconSize: 10
                iconSource: AppController.ui_controller.getAssetUri("ui/refresh-icon.svg")
                role: "secondary"
                tooltipText: "Refresh diagnostics"
                visible: root.expanded
                onClicked: root.refresh()
            }
        }

        // Diagnostic body — collapsed by default
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: root.expanded ? bodyContentLayout.implicitHeight + 32 : 0
            visible: root.expanded
            clip: true
            radius: Theme.radiusCard
            color: Theme.glassPill
            border.color: Theme.glassBorder
            border.width: 1

            ColumnLayout {
                id: bodyContentLayout
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: 16
                spacing: 16

                // --- Diagnostic Log Path ---
                ColumnLayout {
                    spacing: 4
                    Text {
                        text: "Diagnostic Log"
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.sizeBody
                        font.weight: Font.DemiBold
                        color: Theme.label
                    }
                    Rectangle {
                        Layout.fillWidth: true
                        height: 1
                        color: Theme.separator
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 36
                    radius: Theme.radiusField
                    color: Theme.glassHover
                    border.color: Theme.glassBorder

                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 4
                        spacing: 4

                        Text {
                            Layout.fillWidth: true
                            text: root.diagnosticLogPath || "(not initialized)"
                            font.family: "Courier"
                            font.pixelSize: Theme.sizeCaption
                            color: Theme.secondaryLabel
                            elide: Text.ElideMiddle
                            verticalAlignment: Text.AlignVCenter
                        }

                        IconButton {
                            buttonSize: 24
                            iconSize: 8
                            iconSource: AppController.ui_controller.getAssetUri("ui/copy-icon.svg")
                            role: "secondary"
                            tooltipText: "Copy log path"
                            visible: root.diagnosticLogPath !== ""
                            onClicked: AppController.ops_controller.copyTextToClipboard(root.diagnosticLogPath)
                        }
                    }
                }

                // --- Recent Events ---
                ColumnLayout {
                    spacing: 4
                    Text {
                        text: "Recent Events (last 20)"
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.sizeBody
                        font.weight: Font.DemiBold
                        color: Theme.label
                    }
                    Rectangle {
                        Layout.fillWidth: true
                        height: 1
                        color: Theme.separator
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: 120
                    radius: Theme.radiusField
                    color: Theme.glassHover
                    border.color: Theme.glassBorder

                    Flickable {
                        anchors.fill: parent
                        anchors.margins: 4
                        contentHeight: eventsText.implicitHeight
                        clip: true

                        Text {
                            id: eventsText
                            width: parent.width
                            text: root.recentEventsJson
                            font.family: "Courier"
                            font.pixelSize: Theme.sizeCaption
                            color: Theme.secondaryLabel
                            wrapMode: Text.Wrap
                        }
                    }
                }

                ActionButton {
                    Layout.preferredWidth: 130
                    Layout.preferredHeight: 28
                    labelText: "Copy Events"
                    role: "secondary"
                    onClicked: AppController.ops_controller.copyTextToClipboard(root.recentEventsJson)
                }

                // --- Export & Clear ---
                RowLayout {
                    spacing: 8
                    Layout.fillWidth: true

                    ActionButton {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 32
                        labelText: "Export Bundle"
                        role: "secondary"
                        onClicked: {
                            var result = AppController.config_controller.exportDiagnosticBundle("")
                            if (result !== "") {
                                bundleExportResult = "Bundle saved to: " + result
                                AppController.ops_controller.copyTextToClipboard(result)
                            } else {
                                bundleExportResult = "Export failed — check log directory"
                            }
                        }
                    }

                    ActionButton {
                        Layout.preferredWidth: 90
                        Layout.preferredHeight: 32
                        labelText: "Clear Logs"
                        role: "danger"
                        onClicked: {
                            AppController.config_controller.clearDiagnosticLogs()
                            root.refresh()
                        }
                    }
                }

                Text {
                    visible: root.bundleExportResult !== ""
                    text: root.bundleExportResult
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.sizeCaption
                    color: Theme.secondaryLabel
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                }

                // --- Collections Diagnostic ---
                ColumnLayout {
                    spacing: 4
                    Text {
                        text: "Collections"
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.sizeBody
                        font.weight: Font.DemiBold
                        color: Theme.label
                    }
                    Rectangle {
                        Layout.fillWidth: true
                        height: 1
                        color: Theme.separator
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: 120
                    radius: Theme.radiusField
                    color: Theme.glassHover
                    border.color: Theme.glassBorder

                    Flickable {
                        anchors.fill: parent
                        anchors.margins: 4
                        contentHeight: collectionsText.implicitHeight
                        clip: true

                        Text {
                            id: collectionsText
                            width: parent.width
                            text: root.collectionsJson
                            font.family: "Courier"
                            font.pixelSize: Theme.sizeCaption
                            color: Theme.secondaryLabel
                            wrapMode: Text.Wrap
                        }
                    }
                }

                ActionButton {
                    Layout.preferredWidth: 120
                    Layout.preferredHeight: 28
                    labelText: "Copy Collections"
                    role: "secondary"
                    onClicked: AppController.ops_controller.copyTextToClipboard(root.collectionsJson)
                }

                // --- Project Resolution ---
                ColumnLayout {
                    spacing: 4
                    Text {
                        text: "Project Resolution"
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.sizeBody
                        font.weight: Font.DemiBold
                        color: Theme.label
                    }
                    Rectangle {
                        Layout.fillWidth: true
                        height: 1
                        color: Theme.separator
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: 120
                    radius: Theme.radiusField
                    color: Theme.glassHover
                    border.color: Theme.glassBorder

                    Flickable {
                        anchors.fill: parent
                        anchors.margins: 4
                        contentHeight: projectResText.implicitHeight
                        clip: true

                        Text {
                            id: projectResText
                            width: parent.width
                            text: root.projectResolutionJson
                            font.family: "Courier"
                            font.pixelSize: Theme.sizeCaption
                            color: Theme.secondaryLabel
                            wrapMode: Text.Wrap
                        }
                    }
                }

                ActionButton {
                    Layout.preferredWidth: 140
                    Layout.preferredHeight: 28
                    labelText: "Copy Resolution"
                    role: "secondary"
                    onClicked: AppController.ops_controller.copyTextToClipboard(root.projectResolutionJson)
                }

                // --- Missing Skills Check ---
                ColumnLayout {
                    spacing: 4
                    Text {
                        text: "Missing Skills Check"
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.sizeBody
                        font.weight: Font.DemiBold
                        color: Theme.label
                    }
                    Rectangle {
                        Layout.fillWidth: true
                        height: 1
                        color: Theme.separator
                    }
                }

                RowLayout {
                    spacing: 8
                    Layout.fillWidth: true

                    Text {
                        text: "Collection:"
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.sizeCaption
                        color: Theme.secondaryLabel
                    }

                    ComboBox {
                        id: collectionCombo
                        Layout.preferredWidth: 160
                        model: AppController.customCollections
                        onCurrentTextChanged: {
                            root.selectedCollection = currentText
                            if (root.expanded) {
                                root.missingCheckJson = AppController.config_controller.checkMissingSkills(currentText)
                            }
                        }
                    }

                    IconButton {
                        buttonSize: 28
                        iconSize: 10
                        iconSource: AppController.ui_controller.getAssetUri("ui/refresh-icon.svg")
                        role: "secondary"
                        tooltipText: "Re-check missing skills"
                        onClicked: {
                            if (root.selectedCollection !== "") {
                                root.missingCheckJson = AppController.config_controller.checkMissingSkills(root.selectedCollection)
                            }
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: 120
                    radius: Theme.radiusField
                    color: Theme.glassHover
                    border.color: Theme.glassBorder

                    Flickable {
                        anchors.fill: parent
                        anchors.margins: 4
                        contentHeight: missingText.implicitHeight
                        clip: true

                        Text {
                            id: missingText
                            width: parent.width
                            text: root.missingCheckJson
                            font.family: "Courier"
                            font.pixelSize: Theme.sizeCaption
                            color: Theme.secondaryLabel
                            wrapMode: Text.Wrap
                        }
                    }
                }

                ActionButton {
                    Layout.preferredWidth: 130
                    Layout.preferredHeight: 28
                    labelText: "Copy Missing"
                    role: "secondary"
                    onClicked: AppController.ops_controller.copyTextToClipboard(root.missingCheckJson)
                }
            }
        }
    }
}

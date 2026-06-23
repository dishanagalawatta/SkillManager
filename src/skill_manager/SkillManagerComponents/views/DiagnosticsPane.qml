/**
 * Purpose: Diagnostic log summary card for the Settings About tab.
 * Shows event counts, health status, log path, filterable event list,
 * and export/clear actions. Focused on diagnostic log only — no skill inventory.
 */
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import ".."
import App 1.0

Item {
    id: root

    property bool expanded: false
    property string diagnosticLogPath: ""
    property string recentEventsJson: "[]"
    property string bundleExportResult: ""
    property string healthStatus: "green"
    property int errorCount: 0
    property int warningCount: 0
    property int infoCount: 0
    property int debugCount: 0
    property int activeFilter: 0  // 0=All, 1=Errors, 2=Warnings, 3=Info

    implicitHeight: mainLayout.implicitHeight + 32

    function refresh() {
        var cc = AppController.config_controller
        if (cc) {
            diagnosticLogPath = cc.getDiagnosticLogPath()
            recentEventsJson = cc.getRecentDiagnosticEvents(100)
            healthStatus = cc.getDiagnosticHealthStatus()
            var counts = JSON.parse(cc.getDiagnosticCounts())
            errorCount = counts.errors || 0
            warningCount = counts.warnings || 0
            infoCount = counts.info || 0
            debugCount = counts.debug || 0
        }
    }

    function filteredEvents() {
        var events = JSON.parse(recentEventsJson)
        if (activeFilter === 0) return events
        var levelMap = {1: "ERROR", 2: "WARNING", 3: "INFO"}
        var target = levelMap[activeFilter]
        var filtered = []
        for (var i = 0; i < events.length; i++) {
            if (events[i].level === target) filtered.push(events[i])
        }
        return filtered
    }

    function formatEventRow(event) {
        var ts = event.ts || ""
        var time = ts.length >= 19 ? ts.substring(11, 19) : ts
        var level = event.level || ""
        var cat = event.category || ""
        var msg = event.msg || ""
        if (msg.length > 80) msg = msg.substring(0, 77) + "..."
        return time + "  " + padRight(level, 7) + "  " + padRight(cat, 24) + "  " + msg
    }

    function padRight(str, len) {
        while (str.length < len) str += " "
        return str
    }

    ColumnLayout {
        id: mainLayout
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: 16
        spacing: 16

        // Header row — always visible
        RowLayout {
            id: headerRow
            Layout.fillWidth: true
            spacing: 8

            // Title
            Text {
                text: "Diagnostics"
                font.family: Theme.fontFamily
                font.pixelSize: Theme.sizeSectionTitle
                font.weight: Font.Bold
                color: Theme.label
            }

            // Health indicator pill
            Rectangle {
                height: 22
                width: healthRow.implicitWidth + 12
                radius: 11
                color: root.healthStatus === "red" ? Qt.rgba(Theme.danger.r, Theme.danger.g, Theme.danger.b, 0.12)
                     : root.healthStatus === "yellow" ? Qt.rgba(0.96, 0.62, 0.04, 0.12)
                     : Qt.rgba(0.13, 0.77, 0.37, 0.12)

                Row {
                    id: healthRow
                    anchors.centerIn: parent
                    spacing: 4

                    Rectangle {
                        width: 6
                        height: 6
                        radius: 3
                        color: root.healthStatus === "red" ? Theme.danger
                             : root.healthStatus === "yellow" ? "#F59E0B"
                             : "#22C55E"
                        anchors.verticalCenter: parent.verticalCenter
                    }

                    Text {
                        text: root.healthStatus === "red" ? "Errors"
                            : root.healthStatus === "yellow" ? "Warnings"
                            : "Healthy"
                        font.family: Theme.fontFamily
                        font.pixelSize: 11
                        font.weight: Font.DemiBold
                        color: root.healthStatus === "red" ? Theme.danger
                             : root.healthStatus === "yellow" ? "#F59E0B"
                             : "#22C55E"
                        anchors.verticalCenter: parent.verticalCenter
                    }
                }
            }

            Item { Layout.fillWidth: true }

            // Count chips — only when expanded
            Row {
                spacing: 4
                visible: root.expanded

                Repeater {
                    model: [
                        {count: root.errorCount, color: Theme.danger},
                        {count: root.warningCount, color: "#F59E0B"},
                        {count: root.infoCount, color: "#3B82F6"},
                        {count: root.debugCount, color: Theme.secondaryLabel}
                    ]

                    Rectangle {
                        width: chipRow.implicitWidth + 12
                        height: 20
                        radius: 10
                        color: Qt.rgba(modelData.color.r, modelData.color.g, modelData.color.b, 0.15)

                        Row {
                            id: chipRow
                            anchors.centerIn: parent
                            spacing: 3

                            Rectangle {
                                width: 6
                                height: 6
                                radius: 3
                                color: modelData.color
                                anchors.verticalCenter: parent.verticalCenter
                            }

                            Text {
                                text: modelData.count
                                font.family: Theme.fontFamily
                                font.pixelSize: 10
                                font.weight: Font.Bold
                                color: modelData.color
                                anchors.verticalCenter: parent.verticalCenter
                            }
                        }
                    }
                }
            }

            // Expand/Collapse
            GlassToggleButton {
                Layout.preferredWidth: 90
                Layout.preferredHeight: 28
                text: root.expanded ? "Collapse" : "Expand"
                onClicked: {
                    root.expanded = !root.expanded
                    if (root.expanded) root.refresh()
                }
            }

            // Refresh — only when expanded
            IconButton {
                buttonSize: 28
                iconSize: 10
                iconSource: AppController.ui_controller ? AppController.ui_controller.getAssetUri("ui/refresh-icon.svg") : ""
                role: "secondary"
                tooltipText: "Refresh diagnostics"
                visible: root.expanded
                onClicked: root.refresh()
            }
        }

        // Body — collapsed by default
        ColumnLayout {
            id: bodyLayout
            visible: root.expanded
            Layout.fillWidth: true
            spacing: 12

            // Log path row
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 36
                radius: Theme.radiusField
                color: Theme.glassHover
                border.color: Theme.glassBorder

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 12
                    anchors.rightMargin: 4
                    spacing: 8

                    Text {
                        Layout.fillWidth: true
                        text: root.diagnosticLogPath || "(not initialized)"
                        font.family: "Courier"
                        font.pixelSize: Theme.sizeCaption
                        color: Theme.label
                        elide: Text.ElideMiddle
                        verticalAlignment: Text.AlignVCenter
                    }

                    IconButton {
                        buttonSize: 28
                        iconSize: 12
                        iconSource: AppController.ui_controller ? AppController.ui_controller.getAssetUri("ui/copy-icon.svg") : ""
                        role: "secondary"
                        tooltipText: "Copy log path"
                        visible: root.diagnosticLogPath !== ""
                        onClicked: if (AppController.ops_controller) AppController.ops_controller.copyTextToClipboard(root.diagnosticLogPath)
                    }
                }
            }

            // Filter chips row
            RowLayout {
                spacing: 6
                Layout.fillWidth: true

                FilterPill {
                    text: "All"
                    isActive: root.activeFilter === 0
                    onClicked: root.activeFilter = 0
                }
                FilterPill {
                    text: "Errors"
                    isActive: root.activeFilter === 1
                    onClicked: root.activeFilter = 1
                }
                FilterPill {
                    text: "Warnings"
                    isActive: root.activeFilter === 2
                    onClicked: root.activeFilter = 2
                }
                FilterPill {
                    text: "Info"
                    isActive: root.activeFilter === 3
                    onClicked: root.activeFilter = 3
                }

                Item { Layout.fillWidth: true }
            }

            // Event table
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 200
                radius: Theme.radiusField
                color: Theme.glassHover
                border.color: Theme.glassBorder

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 6
                    spacing: 0

                    // Table header
                    Rectangle {
                        Layout.fillWidth: true
                        height: 24
                        color: "transparent"

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 4
                            anchors.rightMargin: 4
                            spacing: 8

                            Text {
                                text: "TIME"
                                font.family: Theme.fontFamily
                                font.pixelSize: 10
                                font.weight: Font.DemiBold
                                color: Theme.secondaryLabel
                                Layout.preferredWidth: 70
                            }
                            Text {
                                text: "LEVEL"
                                font.family: Theme.fontFamily
                                font.pixelSize: 10
                                font.weight: Font.DemiBold
                                color: Theme.secondaryLabel
                                Layout.preferredWidth: 70
                            }
                            Text {
                                text: "CATEGORY"
                                font.family: Theme.fontFamily
                                font.pixelSize: 10
                                font.weight: Font.DemiBold
                                color: Theme.secondaryLabel
                                Layout.preferredWidth: 150
                            }
                            Text {
                                text: "MESSAGE"
                                font.family: Theme.fontFamily
                                font.pixelSize: 10
                                font.weight: Font.DemiBold
                                color: Theme.secondaryLabel
                                Layout.fillWidth: true
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        height: 1
                        color: Theme.separator
                        Layout.bottomMargin: 4
                    }

                    // Event rows
                    Flickable {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        contentHeight: eventColumn.implicitHeight
                        flickableDirection: Flickable.VerticalFlick

                        Column {
                            id: eventColumn
                            width: parent.width

                            Repeater {
                                id: eventRepeater
                                model: root.filteredEvents()

                                Rectangle {
                                    width: eventColumn.width
                                    height: 22
                                    color: index % 2 === 0 ? "transparent" : Qt.rgba(1, 1, 1, 0.02)
                                    radius: 4

                                    RowLayout {
                                        anchors.fill: parent
                                        anchors.leftMargin: 4
                                        anchors.rightMargin: 4
                                        spacing: 8

                                        Text {
                                            text: {
                                                var ts = modelData.ts || ""
                                                return ts.length >= 19 ? ts.substring(11, 19) : ts
                                            }
                                            font.family: "Courier"
                                            font.pixelSize: 11
                                            color: Theme.secondaryLabel
                                            Layout.preferredWidth: 70
                                        }
                                        Text {
                                            text: modelData.level || ""
                                            font.family: "Courier"
                                            font.pixelSize: 11
                                            font.weight: Font.DemiBold
                                            color: modelData.level === "ERROR" ? Theme.danger
                                                 : modelData.level === "WARNING" ? "#F59E0B"
                                                 : modelData.level === "DEBUG" ? Theme.secondaryLabel
                                                 : "#3B82F6"
                                            Layout.preferredWidth: 70
                                        }
                                        Text {
                                            text: modelData.category || ""
                                            font.family: "Courier"
                                            font.pixelSize: 11
                                            color: Theme.secondaryLabel
                                            Layout.preferredWidth: 150
                                            elide: Text.ElideRight
                                        }
                                        Text {
                                            text: modelData.msg || ""
                                            font.family: "Courier"
                                            font.pixelSize: 11
                                            color: Theme.label
                                            Layout.fillWidth: true
                                            elide: Text.ElideRight
                                        }
                                    }
                                }
                            }

                            // Empty state
                            Item {
                                width: parent.width
                                height: 120
                                visible: eventRepeater.count === 0

                                Text {
                                    text: root.recentEventsJson === "[]" ? "No events recorded yet" : "No events match filter"
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.sizeBody
                                    color: Theme.secondaryLabel
                                    anchors.centerIn: parent
                                }
                            }
                        }
                    }
                }
            }

            // Action row
            RowLayout {
                spacing: 12
                Layout.fillWidth: true
                Layout.topMargin: 4

                ActionButton {
                    Layout.preferredHeight: 32
                    labelText: "Export Bundle"
                    role: "secondary"
                    onClicked: {
                        if (AppController.config_controller) {
                            var result = AppController.config_controller.exportDiagnosticBundle("")
                            if (result !== "") {
                                bundleExportResult = "Bundle saved: " + result
                            } else {
                                bundleExportResult = "Export failed — check log directory"
                            }
                        }
                    }
                }

                ActionButton {
                    Layout.preferredHeight: 32
                    labelText: "Copy Events"
                    role: "secondary"
                    onClicked: if (AppController.ops_controller) AppController.ops_controller.copyTextToClipboard(root.recentEventsJson)
                }

                Item { Layout.fillWidth: true }

                ActionButton {
                    Layout.preferredHeight: 32
                    labelText: "Clear Logs"
                    role: "danger"
                    onClicked: {
                        if (AppController.config_controller) {
                            AppController.config_controller.clearDiagnosticLogs()
                            bundleExportResult = "Logs cleared"
                            root.refresh()
                        }
                    }
                }
            }

            // Result/status text
            Text {
                visible: root.bundleExportResult !== ""
                text: root.bundleExportResult
                font.family: Theme.fontFamily
                font.pixelSize: Theme.sizeCaption
                color: Theme.secondaryLabel
                Layout.fillWidth: true
                wrapMode: Text.Wrap
            }
        }
    }
}

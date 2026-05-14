import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import QtQuick.Dialogs
import App 1.0
import SkillManagerComponents 1.0
import "../dialogs"

Item {
    id: updatesRoot

    // --- Dialogs ---
    FolderPickerNative {
        id: uv_folderPicker
        onFolderSelected: (path) => {
            if (mode === "source") {
                AppController.addSource(path)
            } else if (mode === "target") {
                AppController.addTarget(path)
            }
        }
    }

    SourceEditDialog {
        id: uv_sourceEditDialog
    }

    ProjectRenameDialog {
        id: uv_projectRenameDialog
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 0
        spacing: 16

        // Header
        ColumnLayout {
            spacing: 4
            Text {
                text: "Sync & Updates"
                font.family: Theme.fontFamily
                font.pixelSize: Theme.sizeHeading
                font.weight: Font.Bold
                color: Theme.label
            }
            Text {
                text: "Synchronize skills between local source and project targets."
                font.family: Theme.fontFamily
                font.pixelSize: Theme.sizeBody
                color: Theme.secondaryLabel
            }
        }

        // Main Layout with SplitView
        SplitView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            orientation: Qt.Horizontal
            handle: Rectangle {
                implicitWidth: 4
                color: "transparent"
            }

            // Left Pane: Folder Managers
            ColumnLayout {
                SplitView.preferredWidth: 400
                SplitView.minimumWidth: 280
                Layout.fillHeight: true
                spacing: 16

                // Sources Manager
                GlassPill {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 16
                        
                        RowLayout {
                            id: uv_sourcesHeader
                            Text {
                                text: "Sources (Skill Providers)"
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.sizeSectionTitle
                                font.weight: Font.Bold
                                color: Theme.label
                                Layout.fillWidth: true
                            }
                            RowLayout {
                                spacing: 8
                                Button {
                                    text: "+ Add Provider"
                                    onClicked: {
                                        uv_sourceEditDialog.editIndex = -1
                                        uv_sourceEditDialog.open()
                                    }
                                    background: Rectangle {
                                        radius: Theme.radiusButton
                                        color: parent.down ? Theme.accent : (parent.hovered ? Theme.accent + "22" : "transparent")
                                        border.color: Theme.accent
                                        border.width: 1
                                    }
                                    contentItem: Text {
                                        text: parent.text
                                        color: Theme.accent
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.sizeCaption
                                        font.weight: Font.Bold
                                        horizontalAlignment: Text.AlignHCenter
                                        verticalAlignment: Text.AlignVCenter
                                    }
                                }
                                Button {
                                    text: "+ Folder"
                                    onClicked: {
                                        uv_folderPicker.mode = "source"
                                        uv_folderPicker.open()
                                    }
                                    background: Rectangle {
                                        radius: Theme.radiusButton
                                        color: parent.down ? Theme.accent : (parent.hovered ? Theme.accent + "22" : "transparent")
                                        border.color: Theme.accent
                                        border.width: 1
                                    }
                                    contentItem: Text {
                                        text: parent.text
                                        color: Theme.accent
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.sizeCaption
                                        font.weight: Font.Bold
                                        horizontalAlignment: Text.AlignHCenter
                                        verticalAlignment: Text.AlignVCenter
                                    }
                                }
                            }
                        }

                        ListView {
                            id: uv_sourcesList
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            clip: true
                            model: AppController.updateSources
                            spacing: 8
                            delegate: Rectangle {
                                width: uv_sourcesList.width
                                height: 65
                                color: Theme.glassPill
                                radius: Theme.radiusCard
                                border.color: Theme.glassBorder
                                border.width: 1

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.margins: 12
                                    spacing: 12

                                    Rectangle {
                                        width: 36
                                        height: 36
                                        radius: 18
                                        color: Theme.accent + "11"
                                        Text {
                                            anchors.centerIn: parent
                                            text: modelData.source_type === "git" ? "🌐" : (modelData.source_type === "npm" ? "📦" : "📁")
                                            font.pixelSize: 18
                                        }
                                    }

                                    ColumnLayout {
                                        spacing: 2
                                        Layout.fillWidth: true
                                        Text {
                                            text: modelData.name
                                            font.family: Theme.fontFamily
                                            font.pixelSize: Theme.sizeBody
                                            font.weight: Font.Medium
                                            color: Theme.label
                                            elide: Text.ElideRight
                                        }
                                        Text {
                                            text: modelData.source_type === "git" ? modelData.repository_url : (modelData.local_path || "Central library")
                                            font.family: Theme.fontFamily
                                            font.pixelSize: Theme.sizeCaption
                                            color: Theme.secondaryLabel
                                            elide: Text.ElideMiddle
                                            Layout.fillWidth: true
                                        }
                                    }

                                    RowLayout {
                                        spacing: 4
                                        Button {
                                            text: "✎"
                                            visible: modelData.source_type !== undefined
                                            onClicked: {
                                                uv_sourceEditDialog.editIndex = index
                                                uv_sourceEditDialog.loadSource(modelData)
                                                uv_sourceEditDialog.open()
                                            }
                                            flat: true
                                            Layout.preferredWidth: 32
                                            Layout.preferredHeight: 32
                                        }
                                        Button {
                                            text: "✕"
                                            onClicked: {
                                                if (modelData.source_type !== undefined) {
                                                    Qt.callLater(AppController.removeUpdateSource, index)
                                                } else {
                                                    Qt.callLater(AppController.removeSourceByIndex, index)
                                                }
                                            }
                                            flat: true
                                            Layout.preferredWidth: 32
                                            Layout.preferredHeight: 32
                                            ToolTip.visible: hovered
                                            ToolTip.text: "Remove source"
                                        }
                                    }
                                }

                                ProgressBar {
                                    anchors.bottom: parent.bottom
                                    anchors.left: parent.left
                                    anchors.right: parent.right
                                    height: 3
                                    indeterminate: true
                                    visible: (modelData && modelData.is_updating) ? true : false
                                    background: Item {}
                                    contentItem: Item {
                                        Rectangle {
                                            width: parent.width
                                            height: parent.height
                                            color: Theme.accent
                                            radius: 1.5
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                // Targets Manager
                GlassPill {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 16
                        
                        RowLayout {
                            Text {
                                text: "Targets (Skill Folders)"
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.sizeSectionTitle
                                font.weight: Font.Bold
                                color: Theme.label
                                Layout.fillWidth: true
                            }
                            Button {
                                text: "+ Add Project"
                                onClicked: {
                                    uv_folderPicker.mode = "target"
                                    uv_folderPicker.open()
                                }
                                background: Rectangle {
                                    radius: Theme.radiusButton
                                    color: parent.down ? Theme.accent : (parent.hovered ? Theme.accent + "22" : "transparent")
                                    border.color: Theme.accent
                                    border.width: 1
                                }
                                contentItem: Text {
                                    text: parent.text
                                    color: Theme.accent
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.sizeCaption
                                    font.weight: Font.Bold
                                    horizontalAlignment: Text.AlignHCenter
                                    verticalAlignment: Text.AlignVCenter
                                }
                            }
                        }

                        ListView {
                            id: uv_targetsList
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            clip: true
                            model: AppController.updateTargets
                            spacing: 8
                            delegate: Rectangle {
                                width: uv_targetsList.width
                                height: 70
                                color: Theme.glassPill
                                radius: Theme.radiusCard
                                border.color: Theme.glassBorder
                                border.width: 1

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.margins: 12
                                    spacing: 12

                                    Rectangle {
                                        width: 40
                                        height: 40
                                        radius: 20
                                        color: Theme.accent + "11"
                                        Text {
                                            anchors.centerIn: parent
                                            text: "🚀"
                                            font.pixelSize: 20
                                        }
                                    }

                                    ColumnLayout {
                                        spacing: 2
                                        Layout.fillWidth: true
                                        RowLayout {
                                            Text {
                                                text: modelData.name
                                                font.family: Theme.fontFamily
                                                font.pixelSize: Theme.sizeBody
                                                font.weight: Font.Bold
                                                color: Theme.label
                                                elide: Text.ElideRight
                                            }
                                            Text {
                                                text: "(" + modelData.skill_count + " skills)"
                                                font.family: Theme.fontFamily
                                                font.pixelSize: Theme.sizeCaption
                                                color: Theme.secondaryLabel
                                            }
                                        }
                                        Text {
                                            text: modelData.path
                                            font.family: Theme.fontFamily
                                            font.pixelSize: Theme.sizeCaption
                                            color: Theme.secondaryLabel
                                            elide: Text.ElideMiddle
                                            Layout.fillWidth: true
                                        }
                                    }

                                    RowLayout {
                                        spacing: 4
                                        Button {
                                            text: "✎"
                                            onClicked: {
                                                uv_projectRenameDialog.targetPath = modelData.path
                                                uv_projectRenameDialog.currentName = modelData.name
                                                uv_projectRenameDialog.open()
                                            }
                                            flat: true
                                            Layout.preferredWidth: 32
                                            Layout.preferredHeight: 32
                                        }
                                        Button {
                                            text: "✕"
                                            onClicked: Qt.callLater(AppController.removeUpdateTarget, index)
                                            flat: true
                                            Layout.preferredWidth: 32
                                            Layout.preferredHeight: 32
                                        }
                                    }
                                }

                                ProgressBar {
                                    anchors.bottom: parent.bottom
                                    anchors.left: parent.left
                                    anchors.right: parent.right
                                    height: 3
                                    indeterminate: true
                                    visible: (modelData && modelData.is_updating) ? true : false
                                    background: Item {}
                                    contentItem: Item {
                                        Rectangle {
                                            width: parent.width
                                            height: parent.height
                                            color: Theme.accent
                                            radius: 1.5
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }

            // Right Pane: Summary & Analysis
            ColumnLayout {
                SplitView.fillWidth: true
                Layout.fillHeight: true
                spacing: 16

                GlassPill {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 16
                        spacing: 12

                        RowLayout {
                            ColumnLayout {
                                spacing: 2
                                Layout.fillWidth: true
                                Text {
                                    text: "Analysis Summary"
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.sizeSectionTitle
                                    font.weight: Font.Bold
                                    color: Theme.label
                                }
                                Text {
                                    text: AppController.updateTargets.length > 0 ? 
                                          "Checking skills across " + AppController.updateTargets.length + " targets" :
                                          "Add targets to begin analysis"
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.sizeCaption
                                    color: Theme.secondaryLabel
                                }
                            }

                            Button {
                                text: "Scan Now"
                                Layout.preferredHeight: 36
                                enabled: AppController.updateSources.length > 0 && AppController.updateTargets.length > 0
                                onClicked: AppController.scanForUpdates()
                                background: Rectangle {
                                    radius: Theme.radiusButton
                                    color: parent.enabled ? (parent.down ? Theme.accent : (parent.hovered ? Theme.accent + "EE" : Theme.accent)) : Theme.glassBorder
                                }
                                contentItem: Text {
                                    text: parent.text
                                    color: parent.enabled ? "white" : Theme.secondaryLabel
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.sizeCaption
                                    font.weight: Font.Bold
                                    horizontalAlignment: Text.AlignHCenter
                                    verticalAlignment: Text.AlignVCenter
                                    leftPadding: 16
                                    rightPadding: 16
                                }
                            }
                        }

                        // Status Overview Cards
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 12
                            
                            Repeater {
                                model: ListModel {
                                    id: uv_summaryModel
                                    ListElement { title: "Up to Date"; count: "0"; icon: "✅"; color: "#4CAF50" }
                                    ListElement { title: "Outdated"; count: "0"; icon: "🔄"; color: "#FF9800" }
                                    ListElement { title: "Missing"; count: "0"; icon: "❓"; color: "#F44336" }
                                }
                                Rectangle {
                                    Layout.fillWidth: true
                                    height: 80
                                    color: Theme.glassPill
                                    radius: Theme.radiusCard
                                    border.color: Theme.glassBorder
                                    
                                    ColumnLayout {
                                        anchors.centerIn: parent
                                        spacing: 4
                                        RowLayout {
                                            spacing: 6
                                            Text { text: model.icon; font.pixelSize: 16 }
                                            Text {
                                                text: model.title
                                                font.family: Theme.fontFamily
                                                font.pixelSize: Theme.sizeCaption
                                                color: Theme.secondaryLabel
                                            }
                                        }
                                        Text {
                                            text: {
                                                if (index === 0) return AppController.statsUpToDate
                                                if (index === 1) return AppController.statsOutdated
                                                return AppController.statsMissing
                                            }
                                            font.family: Theme.fontFamily
                                            font.pixelSize: 24
                                            font.weight: Font.Bold
                                            color: Theme.label
                                            Layout.alignment: Qt.AlignHCenter
                                        }
                                    }
                                }
                            }
                        }

                        // Detailed List
                        ListView {
                            id: uv_summaryList
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            clip: true
                            model: AppController.updateResults
                            spacing: 4
                            
                            header: RowLayout {
                                width: uv_summaryList.width
                                height: 30
                                spacing: 10
                                Text { text: "Skill Name"; Layout.fillWidth: true; font.weight: Font.Bold; color: Theme.secondaryLabel; font.pixelSize: 11 }
                                Text { text: "Version"; Layout.preferredWidth: 80; font.weight: Font.Bold; color: Theme.secondaryLabel; font.pixelSize: 11 }
                                Text { text: "Status"; Layout.preferredWidth: 100; font.weight: Font.Bold; color: Theme.secondaryLabel; font.pixelSize: 11 }
                                Item { Layout.preferredWidth: 40 }
                            }

                            delegate: Rectangle {
                                width: uv_summaryList.width
                                height: 45
                                color: hovered ? Theme.glassPill : "transparent"
                                radius: 4
                                property bool hovered: uv_summaryMouseArea.containsMouse

                                MouseArea {
                                    id: uv_summaryMouseArea
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    onClicked: {
                                        uv_inspector.skillData = modelData
                                        uv_inspector.open()
                                    }
                                }

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.margins: 8
                                    spacing: 10

                                    Text {
                                        text: modelData.name
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.sizeBody
                                        color: Theme.label
                                        Layout.fillWidth: true
                                        elide: Text.ElideRight
                                    }

                                    Text {
                                        text: modelData.version
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.sizeCaption
                                        color: Theme.secondaryLabel
                                        Layout.preferredWidth: 80
                                    }

                                    Rectangle {
                                        Layout.preferredWidth: 100
                                        height: 24
                                        radius: 12
                                        color: modelData.status === "up_to_date" ? "#114CAF50" : 
                                               (modelData.status === "outdated" ? "#11FF9800" : "#11F44336")
                                        
                                        Text {
                                            anchors.centerIn: parent
                                            text: modelData.status_text
                                            font.pixelSize: 10
                                            font.weight: Font.Bold
                                            color: modelData.status === "up_to_date" ? "#4CAF50" : 
                                                   (modelData.status === "outdated" ? "#FF9800" : "#F44336")
                                        }
                                    }

                                    Text {
                                        text: "›"
                                        font.pixelSize: 18
                                        color: Theme.secondaryLabel
                                        Layout.preferredWidth: 20
                                        horizontalAlignment: Text.AlignRight
                                    }
                                }
                            }
                        }
                    }
                }

                // Global Actions
                GlassPill {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 120
                    
                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 20
                        spacing: 16
                        
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 4
                            Text {
                                text: "Bulk Actions"
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.sizeBody
                                font.weight: Font.Bold
                                color: Theme.label
                            }
                            Text {
                                text: AppController.statsOutdated + " skills can be updated across all targets."
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.sizeCaption
                                color: Theme.secondaryLabel
                            }
                        }

                        Button {
                            text: "Update All Outdated"
                            Layout.preferredHeight: 50
                            Layout.preferredWidth: 200
                            enabled: AppController.statsOutdated > 0
                            onClicked: AppController.updateAllOutdated()
                            background: Rectangle {
                                radius: Theme.radiusButton
                                color: parent.enabled ? (parent.down ? Theme.accent : (parent.hovered ? Theme.accent + "EE" : Theme.accent)) : Theme.glassBorder
                            }
                            contentItem: Text {
                                text: parent.text
                                color: parent.enabled ? "white" : Theme.secondaryLabel
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.sizeBody
                                font.weight: Font.Bold
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                            }
                        }

                        Button {
                            text: "Sync Now"
                            Layout.preferredHeight: 50
                            Layout.preferredWidth: 160
                            onClicked: AppController.syncNow()
                            background: Rectangle {
                                radius: Theme.radiusButton
                                color: "transparent"
                                border.color: Theme.accent
                                border.width: 1
                            }
                            contentItem: Text {
                                text: parent.text
                                color: Theme.accent
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.sizeBody
                                font.weight: Font.Bold
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                            }
                        }
                    }
                }
            }
        }

        // Bottom Status Bar
        GlassPill {
            Layout.fillWidth: true
            Layout.preferredHeight: 40
            visible: AppController.statusMessage !== ""
            
            RowLayout {
                anchors.fill: parent
                anchors.margins: 12
                spacing: 12
                
                Text {
                    text: "Status:"
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.sizeCaption
                    font.weight: Font.Bold
                    color: Theme.accent
                }
                
                Text {
                    text: AppController.statusMessage
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.sizeCaption
                    color: Theme.label
                    Layout.fillWidth: true
                    elide: Text.ElideRight
                }
            }
        }
    }

    // Detail Inspector (Drawer-like)
    Popup {
        id: uv_inspector
        property var skillData: null
        
        width: 400
        height: parent.height
        x: parent.width - width
        y: 0
        modal: true
        focus: true
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        
        background: Rectangle {
            color: Theme.appBackground
            border.color: Theme.glassBorder
            border.width: 1
        }

        contentItem: ColumnLayout {
            spacing: 20
            
            RowLayout {
                Layout.fillWidth: true
                Text {
                    text: "Skill Details"
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.sizeHeading
                    font.weight: Font.Bold
                    color: Theme.label
                    Layout.fillWidth: true
                }
                Button {
                    text: "✕"
                    onClicked: uv_inspector.close()
                    flat: true
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 16
                visible: uv_inspector.skillData !== null

                // Info Card
                Rectangle {
                    Layout.fillWidth: true
                    height: 120
                    color: Theme.glassPill
                    radius: Theme.radiusCard
                    border.color: Theme.glassBorder
                    
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 16
                        Text {
                            text: uv_inspector.skillData ? uv_inspector.skillData.name : ""
                            font.family: Theme.fontFamily
                            font.pixelSize: 20
                            font.weight: Font.Bold
                            color: Theme.label
                        }
                        Text {
                            text: uv_inspector.skillData ? "Current Version: " + uv_inspector.skillData.version : ""
                            color: Theme.secondaryLabel
                        }
                        Text {
                            text: uv_inspector.skillData ? "Latest Available: " + uv_inspector.skillData.latest_version : ""
                            color: Theme.accent
                            font.weight: Font.Bold
                        }
                    }
                }

                Text {
                    text: "Affected Targets"
                    font.weight: Font.Bold
                    color: Theme.label
                }

                ListView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    model: uv_inspector.skillData ? uv_inspector.skillData.targets : []
                    spacing: 8
                    delegate: Rectangle {
                        width: parent.width
                        height: 50
                        color: Theme.glassPill
                        radius: Theme.radiusCard
                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 12
                            Text {
                                text: modelData.name
                                Layout.fillWidth: true
                                color: Theme.label
                            }
                            Button {
                                text: "Update"
                                onClicked: AppController.updateSkillInTarget(uv_inspector.skillData.name, modelData.name)
                            }
                        }
                    }
                }
            }
        }
    }
}

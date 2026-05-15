import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import QtQuick.Effects
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



        // Bulk Action Bar (Redesigned as Pebble Bar)
        GlassPill {
            Layout.fillWidth: true
            Layout.preferredHeight: 44
            Layout.leftMargin: 16
            Layout.rightMargin: 16
            radius: 22 // Pebble style
            
            RowLayout {
                anchors.fill: parent
                anchors.margins: 4
                anchors.leftMargin: 16
                anchors.rightMargin: 8
                spacing: 12
                
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10
                    Text {
                        text: "Sync & Updates"
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.sizeBody
                        font.weight: Font.Bold
                        color: Theme.label
                    }
                    Rectangle {
                        width: 1
                        height: 12
                        color: Theme.separator
                    }
                    Text {
                        text: AppController.isLoading ? "Checking..." : (AppController.statsOutdated + " updates")
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.sizeCaption
                        color: AppController.isLoading ? Theme.accent : Theme.secondaryLabel
                    }
                }

                RowLayout {
                    spacing: 8
                    
                    Button {
                        text: "Scan"
                        enabled: !AppController.isLoading
                        onClicked: AppController.scanForUpdates()
                        background: Rectangle {
                            radius: height / 2
                            color: "transparent"
                            border.color: parent.enabled ? Theme.accent : Theme.glassBorder
                            border.width: 1
                        }
                        contentItem: Text {
                            text: parent.text
                            color: parent.enabled ? Theme.accent : Theme.secondaryLabel
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.sizeCaption
                            font.weight: Font.Bold
                            leftPadding: 12
                            rightPadding: 12
                        }
                    }

                    Button {
                        text: "Update All"
                        enabled: !AppController.isLoading && AppController.statsOutdated > 0
                        onClicked: AppController.updateAllOutdated()
                        background: Rectangle {
                            radius: height / 2
                            color: parent.enabled ? Theme.accent : Theme.glassBorder
                        }
                        contentItem: Text {
                            text: parent.text
                            color: parent.enabled ? "white" : Theme.secondaryLabel
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.sizeCaption
                            font.weight: Font.Bold
                            leftPadding: 16
                            rightPadding: 16
                        }
                    }
                }
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

            // Left Pane: Sources Manager
            ColumnLayout {
                SplitView.preferredWidth: parent.width * 0.45
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
                                height: 52
                                color: Theme.glassPill
                                radius: 12
                                border.color: Theme.glassBorder
                                border.width: 1

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.margins: 10
                                    spacing: 10

                                    Rectangle {
                                        width: 28
                                        height: 28
                                        radius: 14
                                        color: Theme.accent + "11"
                                        Text {
                                            anchors.centerIn: parent
                                            text: modelData.source_type === "git" ? "🌐" : (modelData.source_type === "npm" ? "📦" : "📁")
                                            font.pixelSize: 14
                                        }
                                    }

                                    ColumnLayout {
                                        spacing: 0
                                        Layout.fillWidth: true
                                        Text {
                                            text: modelData.name
                                            font.family: Theme.fontFamily
                                            font.pixelSize: 13
                                            font.weight: Font.Medium
                                            color: Theme.label
                                            elide: Text.ElideRight
                                        }
                                        RowLayout {
                                            spacing: 4
                                            Text {
                                                text: "v" + (modelData.current_version || "1.0.0")
                                                font.family: Theme.fontFamily
                                                font.pixelSize: Theme.sizeCaption
                                                color: Theme.secondaryLabel
                                            }
                                            Text {
                                                text: "→"
                                                font.pixelSize: 10
                                                color: Theme.secondaryLabel
                                                visible: Boolean(modelData.latest_version && modelData.latest_version !== modelData.current_version)
                                            }
                                            Text {
                                                text: "v" + modelData.latest_version
                                                font.family: Theme.fontFamily
                                                font.pixelSize: Theme.sizeCaption
                                                font.weight: Font.Bold
                                                color: Theme.accent
                                                visible: Boolean(modelData.latest_version && modelData.latest_version !== modelData.current_version)
                                            }
                                        }
                                    }

                                    RowLayout {
                                        spacing: 4
                                        
                                        // Update Button / Status
                                        Button {
                                            id: uv_itemUpdateBtn
                                            property bool isLatest: Boolean(!modelData.latest_version || modelData.latest_version === modelData.current_version)
                                            text: modelData.is_updating ? "Updating..." : (isLatest ? "✓ Up to Date" : "Update")
                                            enabled: !isLatest && !modelData.is_updating
                                            onClicked: AppController.runUpdate(index)
                                            
                                            background: Rectangle {
                                                implicitWidth: 80
                                                implicitHeight: 24
                                                radius: 12
                                                color: uv_itemUpdateBtn.isLatest ? "transparent" : (uv_itemUpdateBtn.enabled ? Theme.accent : Theme.glassBorder)
                                                border.color: uv_itemUpdateBtn.isLatest ? Theme.success : "transparent"
                                                border.width: uv_itemUpdateBtn.isLatest ? 1 : 0
                                            }
                                            contentItem: Text {
                                                text: parent.text
                                                color: uv_itemUpdateBtn.isLatest ? Theme.success : (uv_itemUpdateBtn.enabled ? "white" : Theme.secondaryLabel)
                                                font.family: Theme.fontFamily
                                                font.pixelSize: 10
                                                font.weight: Font.Bold
                                                horizontalAlignment: Text.AlignHCenter
                                                verticalAlignment: Text.AlignVCenter
                                            }
                                        }


                                        Button {
                                            text: "✎"
                                            visible: Boolean(modelData && modelData.source_type !== undefined)
                                            onClicked: {
                                                uv_sourceEditDialog.editIndex = index
                                                uv_sourceEditDialog.loadSource(modelData)
                                                uv_sourceEditDialog.open()
                                            }
                                            flat: true
                                            Layout.preferredWidth: 28
                                            Layout.preferredHeight: 28
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
                                            Layout.preferredWidth: 28
                                            Layout.preferredHeight: 28
                                        }
                                    }
                                }

                                ProgressBar {
                                    anchors.bottom: parent.bottom
                                    anchors.left: parent.left
                                    anchors.right: parent.right
                                    height: 3
                                    indeterminate: true
                                    visible: Boolean(modelData && modelData.is_updating)
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

            // Right Pane: Targets Manager
            ColumnLayout {
                SplitView.preferredWidth: parent.width * 0.55
                SplitView.minimumWidth: 320
                Layout.fillHeight: true
                spacing: 16

                // Targets Manager
                GlassPill {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 16
                        
                        RowLayout {
                            Text {
                                text: "Targets (Project Skill Folders)"
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
                                height: 52
                                color: Theme.glassPill
                                radius: 12
                                border.color: Theme.glassBorder
                                border.width: 1

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.margins: 10
                                    spacing: 10

                                    Rectangle {
                                        width: 28
                                        height: 28
                                        radius: 14
                                        color: Theme.accent + "11"
                                        Text {
                                            anchors.centerIn: parent
                                            text: "🚀"
                                            font.pixelSize: 16
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
                                    visible: Boolean(modelData && modelData.is_updating)
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

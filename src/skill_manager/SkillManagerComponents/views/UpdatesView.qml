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
            if (mode === "package") {
                AppController.addSource(path)
            } else if (mode === "project") {
                AppController.addProject(path)
            }
        }
    }

    PackageEditDialog {
        id: uv_packageEditDialog
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
                    
                    ActionButton {
                        labelText: "Scan"
                        role: "secondary"
                        tooltipText: enabled ? "Check configured projects for available skill updates." : "Update scan is already running."
                        enabled: !AppController.isLoading
                        onClicked: (mouse) => AppController.scanForUpdates()
                    }

                    ActionButton {
                        labelText: "Update All"
                        role: "primary"
                        tooltipText: enabled ? "Update every skill currently marked outdated." : "No outdated skills are ready to update."
                        enabled: !AppController.isLoading && AppController.statsOutdated > 0
                        onClicked: (mouse) => AppController.updateAllOutdated()
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

            // Left Pane: Packages Manager
            ColumnLayout {
                SplitView.preferredWidth: parent.width * 0.45
                SplitView.minimumWidth: 280
                Layout.fillHeight: true
                spacing: 16

                // Packages Manager
                GlassPill {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 16
                        
                        RowLayout {
                            id: uv_packagesHeader
                            Text {
                                text: "Skill Packages"
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.sizeSectionTitle
                                font.weight: Font.Bold
                                color: Theme.label
                                Layout.fillWidth: true
                            }
                            RowLayout {
                                spacing: 8
                                ActionButton {
                                    labelText: "Add Package"
                                    iconText: "+"
                                    role: "secondary"
                                    onClicked: (mouse) => {
                                        uv_packageEditDialog.editIndex = -1
                                        uv_packageEditDialog.open()
                                    }
                                }
                                ActionButton {
                                    labelText: "Folder"
                                    iconText: "+"
                                    role: "secondary"
                                    onClicked: (mouse) => {
                                        uv_folderPicker.mode = "package"
                                        uv_folderPicker.open()
                                    }
                                }
                            }
                        }

                        ListView {
                            id: uv_packagesList
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            clip: true
                            model: AppController.updatePackages
                            spacing: 8
                            delegate: Rectangle {
                                width: uv_packagesList.width
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
                                        ActionButton {
                                            id: uv_itemUpdateBtn
                                            property bool isLatest: Boolean(!modelData.latest_version || modelData.latest_version === modelData.current_version)
                                            labelText: modelData.is_updating ? "Updating..." : (isLatest ? "Up to Date" : "Update")
                                            role: isLatest ? "secondary" : "primary"
                                            buttonHeight: 26
                                            enabled: !isLatest && !modelData.is_updating
                                            onClicked: (mouse) => AppController.runPackageUpdate(index)
                                        }


                                        IconButton {
                                            iconText: "Edit"
                                            iconSize: 10
                                            buttonSize: 28
                                            role: "ghost"
                                            tooltipText: "Edit package"
                                            visible: Boolean(modelData && modelData.source_type !== undefined)
                                            onClicked: (mouse) => {
                                                uv_packageEditDialog.editIndex = index
                                                uv_packageEditDialog.loadPackage(modelData)
                                                uv_packageEditDialog.open()
                                            }
                                        }
                                        IconButton {
                                            iconText: "Del"
                                            iconSize: 10
                                            buttonSize: 28
                                            role: "destructive"
                                            tooltipText: "Remove package"
                                            onClicked: (mouse) => {
                                                if (modelData.source_type !== undefined) {
                                                    Qt.callLater(AppController.removeUpdatePackage, index)
                                                } else {
                                                    Qt.callLater(AppController.removeSourceByIndex, index)
                                                }
                                            }
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

            // Right Pane: Projects Manager
            ColumnLayout {
                SplitView.preferredWidth: parent.width * 0.55
                SplitView.minimumWidth: 320
                Layout.fillHeight: true
                spacing: 16

                // Projects Manager
                GlassPill {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 16
                        
                        RowLayout {
                            Text {
                                text: "Projects (Skill Folders)"
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.sizeSectionTitle
                                font.weight: Font.Bold
                                color: Theme.label
                                Layout.fillWidth: true
                            }
                            ActionButton {
                                labelText: "Add Project"
                                iconText: "+"
                                role: "secondary"
                                onClicked: (mouse) => {
                                    uv_folderPicker.mode = "project"
                                    uv_folderPicker.open()
                                }
                            }
                        }

                        ListView {
                            id: uv_projectsList
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            clip: true
                            model: AppController.updateProjects
                            spacing: 8
                            delegate: Rectangle {
                                width: uv_projectsList.width
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
                                        IconButton {
                                            iconText: "Edit"
                                            iconSize: 10
                                            buttonSize: 32
                                            role: "ghost"
                                            tooltipText: "Rename project"
                                            onClicked: (mouse) => {
                                                uv_projectRenameDialog.projectPath = modelData.path
                                                uv_projectRenameDialog.currentName = modelData.name
                                                uv_projectRenameDialog.open()
                                            }
                                        }
                                        IconButton {
                                            iconText: "Del"
                                            iconSize: 10
                                            buttonSize: 32
                                            role: "destructive"
                                            tooltipText: "Remove project"
                                            onClicked: (mouse) => Qt.callLater(AppController.removeUpdateProject, index)
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
                IconButton {
                    text: "✕"
                    onClicked: (mouse) => uv_inspector.close()
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
                    text: "Affected Projects"
                    font.weight: Font.Bold
                    color: Theme.label
                }

                ListView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    model: uv_inspector.skillData ? uv_inspector.skillData.projects : []
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
                            ActionButton {
                                text: "Update"
                                onClicked: (mouse) => AppController.updateSkillInProject(uv_inspector.skillData.name, modelData.name)
                            }
                        }
                    }
                }
            }
        }
    }
}

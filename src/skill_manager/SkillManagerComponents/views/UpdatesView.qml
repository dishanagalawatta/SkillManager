import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import QtQuick.Effects
import QtQuick.Dialogs
import Qt5Compat.GraphicalEffects
import ".."
import App 1.0
import "../dialogs"

Item {
    id: updatesRoot

    // --- Dialogs ---
    FolderPickerNative {
        id: uv_folderPicker
        onFolderSelected: (path) => {
            if (mode === "package") {
                AppController.config_controller.addSource(path)
            } else if (mode === "project") {
                AppController.config_controller.addProject(path)
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
                        id: checkAppUpdatesBtn
                        labelText: AppController.app_update_controller.isCheckingForUpdates ? "Checking..." : "Check Updates"
                        iconSource: AppController.ui_controller.getAssetUri("ui/refresh-icon.svg")
                        role: "secondary"
                        tooltipText: "Check for new SkillManager application updates."
                        enabled: !AppController.app_update_controller.isCheckingForUpdates
                                 && !AppController.app_update_controller.isUpdating
                        onClicked: (mouse) => {
                            AppController.app_update_controller.checkForUpdates(true)
                        }
                    }

                    ActionButton {
                        objectName: "scanUpdatesBtn"
                        labelText: "Scan"
                        role: "secondary"
                        tooltipText: enabled ? "Check configured projects for available skill updates." : "Update scan is already running."
                        enabled: !AppController.isLoading
                        onClicked: (mouse) => AppController.update_controller.scanForUpdates()
                    }

                    ActionButton {
                        labelText: "Update All"
                        role: "primary"
                        tooltipText: enabled ? "Update every skill currently marked outdated." : "No outdated skills are ready to update."
                        enabled: !AppController.isLoading && AppController.statsOutdated > 0
                        onClicked: (mouse) => AppController.update_controller.updateAllOutdated()
                    }
                }
            }
        }

        // App Update Banner (always visible, state-driven)
        Rectangle {
            id: appUpdateBanner
            Layout.fillWidth: true
            Layout.preferredHeight: isUpdating ? 64 : 44
            Layout.leftMargin: 16
            Layout.rightMargin: 16
            radius: 8
            
            readonly property bool isChecking: AppController.app_update_controller.isCheckingForUpdates
            readonly property bool isUpdating: AppController.app_update_controller.isUpdating
            readonly property bool updateAvailable: AppController.app_update_controller.updateAvailable
            readonly property bool hasChecked: AppController.app_update_controller.hasCheckedForUpdates
            readonly property string latestVersion: AppController.app_update_controller.latestVersion
            readonly property string currentVersion: AppController.app_update_controller.currentVersion

            color: {
                if (updateAvailable || isUpdating) return Theme.accent
                return Theme.glassPill
            }
            border {
                color: Theme.glassBorder
                width: (!updateAvailable && !isUpdating) ? 1 : 0
            }

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 8
                anchors.leftMargin: 16
                anchors.rightMargin: 8
                spacing: 4

                RowLayout {
                    Layout.fillWidth: true

                    Text {
                        text: {
                            if (isChecking) return "Checking for app updates..."
                            if (isUpdating) return "Updating SkillManager to v" + latestVersion + "..."
                            if (updateAvailable) return "A new version of SkillManager (v" + latestVersion + ") is available!"
                            if (hasChecked) return "SkillManager is up to date (v" + currentVersion + ")"
                            return "App updates: check for new versions"
                        }
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.sizeBody
                        font.weight: Font.Bold
                        color: (updateAvailable || isUpdating) ? "white" : Theme.label
                        Layout.fillWidth: true
                        elide: Text.ElideRight
                    }

                    ActionButton {
                        id: updateNowBtn
                        visible: !isChecking
                        labelText: {
                            if (isUpdating) return "Updating..."
                            if (updateAvailable) return "Update Now"
                            if (hasChecked) return "Up to Date"
                            return "Check for Updates"
                        }
                        role: (updateAvailable && !isUpdating) ? "primary" : "secondary"
                        enabled: {
                            if (isUpdating) return false
                            if (updateAvailable) return true
                            if (hasChecked) return false
                            return true
                        }
                        onClicked: (mouse) => {
                            if (updateAvailable) {
                                AppController.app_update_controller.downloadAndApplyUpdate()
                            } else {
                                AppController.app_update_controller.checkForUpdates(true)
                            }
                        }
                        // Override style for "Update Now" button on accent background
                        background: Rectangle {
                            color: updateAvailable ? "white" : "transparent"
                            radius: Theme.radiusButton
                        }
                        contentItem: Text {
                            text: parent.labelText
                            color: updateAvailable ? Theme.accent : (enabled ? Theme.accent : Theme.secondaryLabel)
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.sizeCaption
                            font.weight: Font.Bold
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }
                    }
                }

                ProgressBar {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 4
                    visible: isUpdating
                    value: AppController.app_update_controller.updateProgress
                    background: Rectangle {
                        color: Qt.rgba(1, 1, 1, 0.2)
                        radius: 2
                    }
                    contentItem: Item {
                        Rectangle {
                            width: parent.visualPosition * parent.width
                            height: parent.height
                            color: "white"
                            radius: 2
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
                                    iconSource: AppController.ui_controller.getAssetUri("ui/plus-icon.svg")
                                    role: "secondary"
                                    onClicked: (mouse) => {
                                        uv_packageEditDialog.editIndex = -1
                                        uv_packageEditDialog.open()
                                    }
                                }
                                ActionButton {
                                    labelText: "Folder"
                                    iconSource: AppController.ui_controller.getAssetUri("ui/plus-icon.svg")
                                    role: "secondary"
                                    onClicked: (mouse) => {
                                        uv_folderPicker.mode = "package"
                                        uv_folderPicker.open()
                                    }
                                }
                            }
                        }

                        SmoothListView {
                            id: uv_packagesList
                            objectName: "uv_packagesList"
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
                                        color: Theme.alpha(Theme.accent, 0.07)

                                        Image {
                                            id: typeIcon
                                            anchors.centerIn: parent
                                            width: 14
                                            height: 14
                                            sourceSize.width: 14
                                            sourceSize.height: 14
                                            fillMode: Image.PreserveAspectFit
                                            smooth: true
                                            source: {
                                                if (modelData.source_type === "git") return AppController.ui_controller.getAssetUri("ui/globe-icon.svg")
                                                if (modelData.source_type === "npx") return AppController.ui_controller.getAssetUri("ui/box-icon.svg")
                                                return AppController.ui_controller.getAssetUri("ui/folder-icon.svg")
                                            }
                                        }

                                        ColorOverlay {
                                            anchors.fill: typeIcon
                                            source: typeIcon
                                            color: Theme.accent
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
                                            Layout.fillWidth: true
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
                                        Layout.alignment: Qt.AlignRight | Qt.AlignVCenter
                                        spacing: 4
                                        
                                        // Update Button / Status
                                        ActionButton {
                                            id: uv_itemUpdateBtn
                                            property bool isLatest: Boolean(!modelData.latest_version || modelData.latest_version === modelData.current_version)
                                            labelText: modelData.is_updating ? "Updating..." : (isLatest ? "Up to Date" : "Update")
                                            role: isLatest ? "secondary" : "primary"
                                            buttonHeight: 26
                                            Layout.preferredWidth: 100
                                            Layout.minimumWidth: 100
                                            Layout.maximumWidth: 100
                                            enabled: !isLatest && !modelData.is_updating
                                            onClicked: (mouse) => AppController.update_controller.runPackageUpdate(index)
                                        }


                                        IconButton {
                                            iconSource: AppController.ui_controller.getAssetUri("ui/edit-icon.svg")
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
                                            iconSource: AppController.ui_controller.getAssetUri("ui/delete-icon.svg")
                                            iconSize: 10
                                            buttonSize: 28
                                            role: "destructive"
                                            tooltipText: "Remove package"
                                            onClicked: (mouse) => {
                                                if (modelData.source_type !== undefined) {
                                                    Qt.callLater(AppController.update_controller.removeUpdatePackage, index)
                                                } else {
                                                    Qt.callLater(AppController.config_controller.removeSourceByIndex, index)
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
                                iconSource: AppController.ui_controller.getAssetUri("ui/plus-icon.svg")
                                role: "secondary"
                                onClicked: (mouse) => {
                                    uv_folderPicker.mode = "project"
                                    uv_folderPicker.open()
                                }
                            }
                        }

                        SmoothListView {
                            id: uv_projectsList
                            objectName: "uv_projectsList"
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            clip: true
                            model: AppController.config_controller.updateProjects
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
                                        color: Theme.alpha(Theme.accent, 0.07)

                                        Image {
                                            id: projectIcon
                                            anchors.centerIn: parent
                                            width: 16
                                            height: 16
                                            sourceSize.width: 16
                                            sourceSize.height: 16
                                            fillMode: Image.PreserveAspectFit
                                            smooth: true
                                            source: AppController.ui_controller.getAssetUri("ui/rocket-icon.svg")
                                        }

                                        ColorOverlay {
                                            anchors.fill: projectIcon
                                            source: projectIcon
                                            color: Theme.accent
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
                                            iconSource: AppController.ui_controller.getAssetUri("ui/edit-icon.svg")
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
                                            iconSource: AppController.ui_controller.getAssetUri("ui/delete-icon.svg")
                                            iconSize: 10
                                            buttonSize: 32
                                            role: "destructive"
                                            tooltipText: "Remove project"
                                            onClicked: (mouse) => Qt.callLater(AppController.config_controller.removeUpdateProject, index)
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
                                onClicked: (mouse) => AppController.update_controller.updateSkillInProject(uv_inspector.skillData.name, modelData.name)
                            }
                        }
                    }
                }
            }
        }
    }
}

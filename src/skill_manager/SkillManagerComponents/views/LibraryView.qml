import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import ".."
import App 1.0
import ".."

Item {
    id: lv_root
    objectName: "LibraryView"

    property bool showImageInspector: false
    property bool showCommandInspector: false

    function focusSearch() {
        lv_searchInput.forceActiveFocus()
        lv_searchInput.selectAll()
    }
    
    function scrollToTop() {
        lv_listView.positionViewAtBeginning()
    }

    function cleanup() {
        lv_listView.cacheBuffer = 0
        lv_listView.model = null
    }
    
    Component.onDestruction: {
        cleanup()
    }
    
    Component.onCompleted: {
        // Mode is handled by AppController currentView setter
    }

    // No forced reset on completion - use persistent state

    ColumnLayout {
        anchors.fill: parent
        spacing: 20

        // Header
        RowLayout {
            Layout.fillWidth: true
            spacing: 20

            ColumnLayout {
                spacing: 4
                Text {
                    text: "Skill Library"
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.sizeHeading
                    font.weight: Font.Bold
                    color: Theme.label
                }
                Text {
                    text: "Manage and organize your skills across all projects."
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.sizeBody
                    color: Theme.secondaryLabel
                }
            }

            Item { Layout.fillWidth: true }
            


            GlassDropdown {
                id: lv_categoryDrop
                model: ["All Categories"].concat(AppController.categories)
                currentIndex: {
                    let idx = model.indexOf(AppController.libraryModel.categoryFilter);
                    return idx === -1 ? 0 : idx;
                }
                onActivated: (index) => {
                    let cat = index === 0 ? "" : currentText
                    AppController.ui_controller.setViewFilterForView("Library", "category", cat)
                }
            }

            GlassSearchInput {
                id: lv_searchInput
                objectName: "librarySearchInput"
                Layout.preferredWidth: 250
                onDebouncedTextChanged: (text) => AppController.libraryModel.filterText = text
            }
            GlassToggleButton {
                text: "Show Archived"
                checked: AppController.libraryModel.showArchived
                onClicked: (mouse) => AppController.libraryModel.showArchived = checked
                
                iconSourceInactive: AppController.ui_controller.getAssetUri("ui/folder-icon.svg")
                iconSourceActive: AppController.ui_controller.getAssetUri("ui/archive-icon.svg")
                textActive: "Showing Archived"
            }

        }


        
        // Multi-select Action Bar
        Rectangle {
            id: selectionBar
            Layout.fillWidth: true
            Layout.preferredHeight: 48
            Layout.leftMargin: 4
            Layout.rightMargin: 4
            visible: true
            color: Theme.alpha(Theme.accent, 0.06)
            radius: Theme.radiusCard
            border.color: Theme.alpha(Theme.accent, 0.19)
            border.width: 1
            clip: true
            
            RowLayout {
                id: lv_selectionLayout
                anchors.fill: parent
                anchors.leftMargin: 12
                anchors.rightMargin: 12
                anchors.topMargin: 8
                anchors.bottomMargin: 8
                spacing: 12
                // LEFT: Toggle All
                IconButton {
                    id: lv_toggleAllBtn
                    buttonSize: 24
                    role: "ghost"
                    tooltipText: AppController.libraryModel.isAllExpanded ? "Collapse All" : "Expand All"
                    onClicked: (mouse) => AppController.libraryModel.toggleAll()
                    contentItem: Image {
                        source: AppController.libraryModel.isAllExpanded ?
                                AppController.ui_controller.getAssetUri(Theme.darkMode ? "ui/collapse-arrow-icon-dark.svg" : "ui/collapse-arrow-icon-light.svg") :
                                AppController.ui_controller.getAssetUri(Theme.darkMode ? "ui/expand-arrow-icon-dark.svg" : "ui/expand-arrow-icon-light.svg")
                        width: 16
                        height: 16
                        sourceSize.width: 72
                        sourceSize.height: 72
                        fillMode: Image.PreserveAspectFit
                        opacity: lv_toggleAllBtn.hovered ? 1.0 : 0.7
                        horizontalAlignment: Image.AlignHCenter
                        verticalAlignment: Image.AlignVCenter
                    }
                }

                Rectangle {
                    width: 1
                    height: 16
                    color: Theme.separator
                    Layout.leftMargin: 4
                    Layout.rightMargin: 4
                }

                GlassCheckBox {
                    id: lv_selectCheck
                    Layout.preferredWidth: 24
                    Layout.preferredHeight: 24

                    checkState: {
                        let count = AppController.libraryModel.visibleSelectedCount;
                        let total = AppController.libraryModel.visibleSelectableCount;
                        if (count === 0) return Qt.Unchecked;
                        if (count >= total && total > 0) return Qt.Checked;
                        return Qt.PartiallyChecked;
                    }

                    onToggled: {
                        if (checkState === Qt.Unchecked) {
                            AppController.libraryModel.selectAll();
                        } else {
                            AppController.libraryModel.clearSelection();
                        }
                    }
                }


                // LEFT: Selection Count
                RowLayout {
                    spacing: 12
                    visible: AppController.libraryModel.selectedCount > 0
                    
                    Rectangle {
                        Layout.preferredWidth: Math.max(24, libCountText.implicitWidth + 16)
                        Layout.preferredHeight: 24
                        radius: height / 2
                        color: Theme.accent
                        Text {
                            id: libCountText
                            anchors.centerIn: parent
                            text: AppController.libraryModel.selectedCount.toString()
                            color: "white"
                            font.family: Theme.fontFamily
                            font.weight: Font.Bold
                            font.pixelSize: 11
                        }
                    }

                    Text {
                        text: "Skills selected"
                        font.family: Theme.fontFamily
                        font.pixelSize: 12
                        color: Theme.label
                        font.weight: Font.Medium
                    }
                }
                
                Item { Layout.fillWidth: true }
                
                // Action Buttons
                RowLayout {
                    spacing: 8
                    
                    // Always Visible Actions
                    ActionButton {
                        id: lv_addCommandBtn
                        buttonHeight: 32
                        labelText: "Add"
                        iconSource: AppController.ui_controller.getAssetUri("ui/plus-icon.svg")
                        role: "secondary"
                        onClicked: (mouse) => lv_commandDialog.openWithContext()
                    }

                    // Selection-specific actions
                    RowLayout {
                        spacing: 8
                        visible: AppController.libraryModel.selectedCount > 0
                        
                        GlassDropdown {
                            id: lv_projectDrop
                            Layout.preferredHeight: 32
                            Layout.preferredWidth: 160
                            model: AppController.projectLabels
                            enabled: AppController.projects.length > 0
                            currentIndex: {
                                let idx = model.indexOf(AppController.currentProject);
                                return Math.max(0, idx);
                            }
                            onActivated: (index) => {
                                if (index >= 0 && index < AppController.projectLabels.length) {
                                    AppController.setCurrentProject(AppController.projectLabels[index])
                                }
                            }
                        }

                        ActionButton {
                            id: lv_tempCopyBtn
                            buttonHeight: 32
                            labelText: "Copy Temp"
                            role: "secondary"
                            enabled: AppController.projects.length > 0
                            tooltipText: enabled ? "Copies selected skills to the project temporarily. They will be deleted when you close this app." : "Add a project in Updates before copying skills."
                            onClicked: (mouse) => {
                                let path = AppController.config_controller.getProjectPath(AppController.currentProject)
                                if (path) {
                                    AppController.ops_controller.copySelectedSkillsToProjectTemporarily(path)
                                }
                            }
                        }

                        ActionButton {
                            id: lv_archiveBtn
                            buttonHeight: 32
                            labelText: "Archive"
                            iconSource: AppController.ui_controller.getAssetUri("ui/archive-icon.svg")
                            role: "secondary"
                            onClicked: (mouse) => lv_archiveConfirmDialog.confirmBulk(AppController.libraryModel.selectedCount, () => AppController.ops_controller.archiveSelectedSkills())
                        }

                        ActionButton {
                            id: lv_deleteBtn
                            buttonHeight: 32
                            labelText: "Delete"
                            iconSource: AppController.ui_controller.getAssetUri("ui/delete-icon.svg")
                            role: "destructive"
                            onClicked: (mouse) => lv_deleteConfirmDialog.confirmBulk(AppController.libraryModel.selectedCount, () => AppController.ops_controller.deleteSelectedSkills())
                        }

                        Rectangle {
                            objectName: "libraryDestructiveDivider"
                            width: 1
                            height: 16
                            color: Theme.separator
                            Layout.leftMargin: 4
                            Layout.rightMargin: 4
                        }

                        ActionButton {
                            id: lv_copyBtn
                            buttonHeight: 32
                            labelText: "Copy to Project"
                            role: "primary"
                            enabled: AppController.projects.length > 0
                            tooltipText: enabled ? "" : "Add a project in Updates before copying skills."
                            onClicked: (mouse) => {
                                let path = AppController.config_controller.getProjectPath(AppController.currentProject)
                                if (path) {
                                    AppController.ops_controller.copySelectedSkillsToProject(path)
                                }
                            }
                        }
                    }
                }
            }
        }

        // Library Content
        SplitView {
            id: lv_splitView
            Layout.fillWidth: true
            Layout.fillHeight: true
            orientation: Qt.Horizontal
            
            handle: Rectangle {
                implicitWidth: 12
                color: "transparent"
                
                Rectangle {
                    anchors.centerIn: parent
                    width: 2
                    height: 40
                    radius: 1
                    color: splitHandleArea.containsMouse ? Theme.accent : Theme.separator
                    opacity: splitHandleArea.containsMouse ? 1.0 : 0.3
                    Behavior on color { ColorAnimation { duration: 150 } }
                    Behavior on opacity { NumberAnimation { duration: 150 } }
                }
                
                MouseArea {
                    id: splitHandleArea
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.SizeHorCursor
                    Accessible.role: Accessible.Splitter
                    Accessible.name: "Resize Splitter"
                }
            }

            // Skill List
            SmoothListView {
                id: lv_listView
                SplitView.fillWidth: true
                SplitView.fillHeight: true
                SplitView.minimumWidth: 300
                model: AppController.libraryModel
                clip: true
                spacing: 0
                
                // Visual Blink: Dips opacity slightly during background refresh to mask micro-jumps
                opacity: (AppController.isLoading && _restoringScroll) ? 0.0 : 1.0
                Behavior on opacity { NumberAnimation { duration: 150 } }

                property real savedScrollPos: 0
                property bool _restoringScroll: false

                function _restoreScroll() {
                    if (AppController.isLoading && savedScrollPos > 0) {
                        _restoringScroll = true
                        
                        // Force immediate layout to ensure contentHeight is valid for restore
                        lv_listView.forceLayout()
                        lv_listView.contentY = savedScrollPos
                        
                        // Second pass: Ensure it stuck (sometimes required for large additions)
                        Qt.callLater(() => {
                            if (lv_listView.contentY !== savedScrollPos) {
                                lv_listView.forceLayout()
                                lv_listView.contentY = savedScrollPos
                            }
                            _restoringScroll = false
                        })
                    }
                }

                Connections {
                    target: AppController.libraryModel
                    function onLayoutAboutToBeChanged() {
                        if (AppController.isLoading) {
                            lv_listView.savedScrollPos = lv_listView.contentY
                            lv_listView.cacheBuffer = 0 // Safely abort active incubators
                        }
                    }
                    function onLayoutChanged() {
                        lv_listView.cacheBuffer = Math.max(lv_listView.height * 2, 1000)
                        lv_listView._restoreScroll()
                    }
                    function onModelAboutToBeReset() {
                        if (AppController.isLoading) {
                            lv_listView.savedScrollPos = lv_listView.contentY
                            lv_listView.cacheBuffer = 0
                        }
                    }
                    function onModelReset() {
                        lv_listView.cacheBuffer = Math.max(lv_listView.height * 2, 1000)
                        lv_listView._restoreScroll()
                    }
                    function onAboutToMutateStructure() {
                        if (AppController.isLoading) {
                            lv_listView.savedScrollPos = lv_listView.contentY
                            lv_listView.cacheBuffer = 0
                        }
                    }
                    function onStructureMutated() {
                        lv_listView.cacheBuffer = Math.max(lv_listView.height * 2, 1000)
                        lv_listView._restoreScroll()
                    }
                }

                section.property: "mainCategoryName"
                section.criteria: ViewSection.FullString
                section.delegate: CategoryHeader {
                    width: lv_listView.width
                    mainCatName: section
                }
                delegate: SkillItem {
                    width: lv_listView.width
                    isSelected: AppController.selectedSkill.local_path === model.path
                    showStarredIcon: false
                    showInlineDelete: false
                    onClicked: (mouse) => {
                        AppController.libraryModel.toggleSelection(index)
                    }
                    onDoubleClicked: (mouse) => {
                        AppController.ui_controller.selectSkill(index)
                    }
                    onRightClicked: {
                        if (AppController.selectedSkill && AppController.selectedSkill.local_path === model.path) {
                            AppController.ui_controller.selectSkill(-1)
                        } else {
                            AppController.ui_controller.selectSkill(index)
                        }
                    }
                    onDeleteRequested: (name, path) => {
                        lv_deleteConfirmDialog.confirmSingle(name, () => AppController.ops_controller.deleteSkill(path))
                    }
                    onInspectImageRequested: {
                        lv_root.showImageInspector = true
                    }
                }
            }

            // Inspector Pane (commands)
            CommandInspector {
                id: lv_commandInspector
                SplitView.fillHeight: true
                SplitView.preferredWidth: {
                    var p = AppController.ui_controller.inspectorWidth
                    return p > 0 ? Math.max(p, targetWidth) : targetWidth
                }
                skill: AppController.selectedSkill
                editDialog: lv_commandDialog
                visible: targetWidth > 0 && lv_root.showCommandInspector

                onWidthChanged: {
                    if (visible && width > 0) {
                        AppController.ui_controller.setInspectorWidth(width)
                    }
                }
                onClosed: {
                    lv_root.showCommandInspector = false
                    AppController.ui_controller.selectSkill(-1)
                }
            }

            // Inspector Pane (skills)
            SkillInspector {
                id: lv_inspector
                SplitView.fillHeight: true
                SplitView.preferredWidth: {
                    var p = AppController.ui_controller.inspectorWidth
                    return p > 0 ? Math.max(p, targetWidth) : targetWidth
                }
                skill: AppController.selectedSkill
                visible: targetWidth > 0 && !lv_root.showImageInspector && !lv_root.showCommandInspector

                onWidthChanged: {
                    if (visible && width > 0) {
                        AppController.ui_controller.setInspectorWidth(width)
                    }
                }
                onClosed: AppController.ui_controller.selectSkill(-1)
            }

            // Image Inspector (for screenshots)
            ImageInspector {
                id: lv_imageInspector
                SplitView.fillHeight: true
                SplitView.preferredWidth: {
                    var p = AppController.ui_controller.inspectorWidth
                    return p > 0 ? Math.max(p, targetWidth) : targetWidth
                }
                skill: AppController.selectedSkill
                visible: targetWidth > 0 && lv_root.showImageInspector

                onWidthChanged: {
                    if (visible && width > 0) {
                        AppController.ui_controller.setInspectorWidth(width)
                    }
                }
                onClosed: {
                    lv_root.showImageInspector = false
                    AppController.ui_controller.selectSkill(-1)
                }
            }
        }
    }

    // Toggle between SkillInspector, CommandInspector, and ImageInspector based on skill type
    Connections {
        target: AppController
        function onSelectedSkillChanged() {
            var skill = AppController.selectedSkill
            if (skill && skill.is_command) {
                lv_root.showCommandInspector = true
                lv_root.showImageInspector = false
            } else if (skill && skill.is_screenshot) {
                lv_root.showCommandInspector = false
                lv_root.showImageInspector = true
            } else {
                lv_root.showCommandInspector = false
                lv_root.showImageInspector = false
            }
        }
    }

    CommandCreateDialog {
        id: lv_commandDialog
    }

    DeleteConfirmDialog {
        id: lv_deleteConfirmDialog
    }

    ArchiveConfirmDialog {
        id: lv_archiveConfirmDialog
    }

}

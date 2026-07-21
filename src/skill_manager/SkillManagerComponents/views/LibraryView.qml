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
        // Handled globally in TopBar now
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
        var m = AppController.libraryModel
        if (m) {
            lv_listView.model = m
            lv_listView.cacheBuffer = Math.max(lv_listView.height * 2, 1000)
        }
    }

    Connections {
        target: AppController
        function onSkillModelChanged() {
            var newModel = AppController.libraryModel
            if (newModel === null || typeof newModel === "undefined") {
                lv_listView.cacheBuffer = 0
                lv_listView.model = null
            } else {
                lv_listView.cacheBuffer = 0
                lv_listView.model = newModel
                lv_listView.cacheBuffer = Math.max(lv_listView.height * 2, 1000)
            }
        }
    }

    // No forced reset on completion - use persistent state

    ColumnLayout {
        anchors.fill: parent
        spacing: 20

        // Header Section
        RowLayout {
            Layout.fillWidth: true
            spacing: 20

            GlassPill {
                Layout.fillWidth: true
                Layout.preferredHeight: 48
                radius: 24

                RowLayout {
                    id: headerControls
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.bottom: parent.bottom
                    anchors.margins: 4
                    anchors.leftMargin: 16
                    anchors.rightMargin: 8
                    spacing: 12



                    // LEFT: Toggle All
                IconButton {
                    id: lv_toggleAllBtn
                    buttonSize: 24
                    role: "ghost"
                    tooltipText: AppController.libraryModel.isAllExpanded ? "Collapse All" : "Expand All"
                    onClicked: (mouse) => AppController.libraryModel.toggleAll()
                    iconSize: 18
                    iconSource: AppController.libraryModel.isAllExpanded ?
                            AppController.ui_controller.getAssetUri("ui/collapse-arrow-up-broken.svg") :
                            AppController.ui_controller.getAssetUri("ui/collapse-arrow-down-broken.svg")
                    background: Rectangle {
                        radius: 12
                        color: lv_toggleAllBtn.hovered ? Theme.glassHover : "transparent"
                        border.color: Theme.alpha(Theme.label, 0.15)
                        border.width: 1
                    }
                }



                GlassCheckBox {
                    id: lv_selectCheck
                    Layout.preferredWidth: 24
                    Layout.preferredHeight: 24
                    isClearAction: true

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
                        text: "selected"
                        font.family: Theme.fontFamily
                        font.pixelSize: 12
                        color: Theme.label
                        font.weight: Font.Medium
                    }
                }

                IconButton {
                    id: lv_deleteBtn
                    buttonSize: 28
                    iconSource: AppController.ui_controller.getAssetUri("ui/delete-icon.svg")
                    tooltipText: "Delete Selected Skills"
                    role: "destructive"
                    flat: true
                    enabled: AppController.libraryModel.selectedCount > 0
                    onClicked: (mouse) => {
                        var selectedPaths = AppController.libraryModel.getSelectedPaths() || []
                        var allProjects = []
                        for (var i = 0; i < selectedPaths.length; i++) {
                            var path = selectedPaths[i]
                            var isCmd = path.endsWith(".md") || path.indexOf("/commands/") >= 0 || path.indexOf("\\commands\\") >= 0
                            var holders = isCmd ? (AppController.commandProjectsForPath(path) || []) : (AppController.skillProjectsForPath(path) || [])
                            for (var j = 0; j < holders.length; j++) {
                                if (allProjects.indexOf(holders[j]) === -1) allProjects.push(holders[j])
                            }
                        }
                        if (allProjects.length === 0 && AppController.currentProject) {
                            allProjects.push(AppController.currentProject)
                        }
                        lv_cmdDeleteDialog.openBulkSkill(AppController.libraryModel.selectedCount, allProjects, selectedPaths, AppController.libraryModel.getSelectedNames())
                    }
                }

                IconButton {
                    id: lv_addCommandBtn
                    buttonSize: 28
                    iconSource: AppController.ui_controller.getAssetUri("ui/layout-grid-add-icon.svg")
                    tooltipText: "Add Command"
                    onClicked: (mouse) => lv_commandDialog.openWithContext()
                }
                
                Item { Layout.fillWidth: true }
                
                // Right Controls Group
                RowLayout {
                    spacing: 12
                    
                    GlassDropdown {
                        id: lv_categoryDrop
                        Layout.preferredWidth: 160
                        iconSource: "ui/cosmetic-bold-duotone.svg"
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


                    
                    // Action Buttons
                    // Always Visible Actions



                        GlassDropdown {
                            id: lv_projectDrop
                            Layout.preferredWidth: 180
                            iconSource: "ui/folder-security-bold.svg"
                            visible: AppController.libraryModel.selectedCount > 0
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



                        IconButton {
                            id: lv_archiveBtn
                            buttonSize: 28
                            visible: AppController.libraryModel.selectedCount > 0
                            iconSource: AppController.ui_controller.getAssetUri("ui/inbox-in-bold-duotone.svg")
                            tooltipText: "Archive"
                            onClicked: (mouse) => lv_archiveConfirmDialog.confirmBulk(AppController.libraryModel.selectedCount, () => AppController.ops_controller.archiveSelectedSkills())
                        }

                        IconButton {
                            id: lv_showArchived
                            buttonSize: 28
                            iconSource: AppController.libraryModel.showArchived ? 
                                AppController.ui_controller.getAssetUri("ui/box-broken.svg") : 
                                AppController.ui_controller.getAssetUri("ui/box-bold-duotone.svg")
                            tooltipText: AppController.libraryModel.showArchived ? "Hide Archived" : "Show Archived"
                            onClicked: (mouse) => AppController.libraryModel.showArchived = !AppController.libraryModel.showArchived
                        }



                        Rectangle {
                            objectName: "libraryDestructiveDivider"
                            visible: AppController.libraryModel.selectedCount > 0
                            width: 1
                            height: 16
                            color: Theme.separator
                            Layout.leftMargin: 4
                            Layout.rightMargin: 4
                        }

                        IconButton {
                            id: lv_tempCopyBtn
                            visible: AppController.libraryModel.selectedCount > 0
                            buttonSize: 28
                            role: "secondary"
                            iconSource: AppController.ui_controller.getAssetUri("ui/file-right-broken.svg")
                            enabled: AppController.projects.length > 0
                            tooltipText: enabled ? "Copy Temp" : "Add a project in Updates before copying skills."
                            onClicked: (mouse) => {
                                let path = AppController.config_controller.getProjectPath(AppController.currentProject)
                                if (path) {
                                    AppController.ops_controller.copySelectedSkillsToProjectTemporarily(path)
                                }
                            }
                        }

                        IconButton {
                            id: lv_copyBtn
                            visible: AppController.libraryModel.selectedCount > 0
                            buttonSize: 28
                            role: "primary-outline"
                            iconSource: AppController.ui_controller.getAssetUri("ui/file-right-bold-duotone.svg")
                            enabled: AppController.projects.length > 0
                            tooltipText: enabled ? "Copy to Project" : "Add a project in Updates before copying skills."
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
                objectName: "libraryList"
                SplitView.fillWidth: true
                SplitView.fillHeight: true
                SplitView.minimumWidth: 300
                model: null
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
                        lv_listView.savedScrollPos = lv_listView.contentY
                        lv_listView.cacheBuffer = 0 // Safely abort active incubators
                    }
                    function onLayoutChanged() {
                        // Defer the restore while the model is still incubating:
                        // the reset fires mid-incubation, so restoring cacheBuffer
                        // here re-triggers a delegate burst that races the in-flight
                        // one ("Object or context destroyed during incubation").
                        // The restore is performed in onIncubatingChanged instead.
                        if (!AppController.libraryModel.incubating) {
                            lv_listView.cacheBuffer = Math.max(lv_listView.height * 2, 1000)
                            lv_listView._restoreScroll()
                        }
                    }
                    function onModelAboutToBeReset() {
                        lv_listView.savedScrollPos = lv_listView.contentY
                        lv_listView.cacheBuffer = 0
                    }
                    function onModelReset() {
                        if (!AppController.libraryModel.incubating) {
                            lv_listView.cacheBuffer = Math.max(lv_listView.height * 2, 1000)
                            lv_listView._restoreScroll()
                        }
                    }
                    function onAboutToMutateStructure() {
                        lv_listView.savedScrollPos = lv_listView.contentY
                        lv_listView.cacheBuffer = 0
                    }
                    function onStructureMutated() {
                        if (!AppController.libraryModel.incubating) {
                            lv_listView.cacheBuffer = Math.max(lv_listView.height * 2, 1000)
                            lv_listView._restoreScroll()
                        }
                    }
                }

                // Incubation coordination: when incubating transitions to False,
                // tell the model to replay deferred layout signals.
                Connections {
                    target: AppController.libraryModel
                    function onIncubatingChanged() {
                        if (!AppController.libraryModel.incubating) {
                            AppController.libraryModel.onIncubationReady()
                            // Incubation finished: now safe to re-enable the
                            // off-screen cache buffer without racing live delegates.
                            if (lv_listView.model) {
                                lv_listView.cacheBuffer = Math.max(lv_listView.height * 2, 1000)
                                lv_listView._restoreScroll()
                            }
                        }
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
                    onDeleteRequested: (name, path, isCommand) => {
                        if (isCommand) {
                            var holders = AppController.commandProjectsForPath(path) || []
                            if (holders.length === 0) holders = [AppController.currentProject || ""]
                            lv_cmdDeleteDialog.openForCommand(name, holders)
                        } else {
                            var holders = AppController.skillProjectsForPath(path) || []
                            if (holders.length === 0) holders = [AppController.currentProject || ""]
                            lv_cmdDeleteDialog.openForSkill(name, holders, path)
                        }
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
                onDeleteRequested: (name, path, isCommand) => {
                    var holders = AppController.commandProjectsForPath(path) || []
                    if (holders.length === 0) holders = [AppController.currentProject || ""]
                    lv_cmdDeleteDialog.openForCommand(name, holders)
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

    CommandDeleteDialog {
        id: lv_cmdDeleteDialog
    }

    ArchiveConfirmDialog {
        id: lv_archiveConfirmDialog
    }

    CommandCarrySkillsDialog {
        id: lv_carrySkillsDialog
        onCarryConfirmed: (confirmedSkills) => {
            AppController.confirmCommandSkillsCarry(
                lv_carrySkillsDialog.projectPath,
                JSON.stringify(lv_carrySkillsDialog.commandPaths),
                JSON.stringify(confirmedSkills)
            )
        }
    }

    Connections {
        target: AppController
        function onCommandSkillsCarryPrompt(commandPathsJson, projectPath, missingSkillsJson) {
            var cmdPaths = JSON.parse(commandPathsJson || "[]")
            var skills = JSON.parse(missingSkillsJson || "[]")
            lv_carrySkillsDialog.openWithContext(cmdPaths, projectPath, skills)
        }
    }

}


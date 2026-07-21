import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import ".."
import App 1.0
import ".."
import "../dialogs"

Item {
    id: qcv_root
    objectName: "QuickCopyView"

    property bool isEditingCollection: false
    property string editingCollectionName: ""
    property bool _isInternalSelectionChange: false
    property bool showImageInspector: false
    property bool showCommandInspector: false
    property var editingCollectionProjects: []

    function focusSearch() {
        // Handled globally in TopBar
    }

    function scrollToTop() {
        qcv_skillList.positionViewAtBeginning()
    }

    function cleanup() {
        qcv_skillList.cacheBuffer = 0
        qcv_skillList.model = null
    }

    Component.onDestruction: {
        cleanup()
    }

    Component.onCompleted: {
        // Mode is handled by AppController currentView
        // Update top bar search input if needed, handled globally
        var m = AppController.quickCopyModel
        if (m) {
            qcv_skillList.model = m
            qcv_skillList.cacheBuffer = Math.max(qcv_skillList.height * 2, 1000)
        }
    }

    Connections {
        target: AppController
        function onSkillModelChanged() {
            var newModel = AppController.quickCopyModel
            if (newModel === null || typeof newModel === "undefined") {
                qcv_skillList.cacheBuffer = 0
                qcv_skillList.model = null
            } else {
                qcv_skillList.cacheBuffer = 0
                qcv_skillList.model = newModel
                qcv_skillList.cacheBuffer = Math.max(qcv_skillList.height * 2, 1000)
            }
        }
    }

    Connections {
        target: AppController.quickCopyModel
        function onSelectionStateChanged() {
            if (qcv_root._isInternalSelectionChange) return

            // Auto-deselect: if collection applied and user changes selection, reset
            if (qcv_collectionDrop.currentIndex !== 0) {
                qcv_collectionDrop.currentIndex = 0
                AppController.ui_controller.setViewFilterForView("QuickCopy", "collection", "")
            }

            // Auto-detect: if selection exactly matches a collection, associate it
            var selectedPaths = AppController.quickCopyModel.getSelectedPaths()
            if (selectedPaths.length === 0) return

            var collections = AppController.customCollections || []
            for (var i = 0; i < collections.length; i++) {
                var collPaths = AppController.config_controller.getCollectionPaths(collections[i])
                if (collPaths.length !== selectedPaths.length) continue
                var selSet = new Set(selectedPaths)
                var collSet = new Set(collPaths)
                if (selSet.size === collSet.size && [...collSet].every(function(x) { return selSet.has(x) })) {
                    qcv_collectionDrop.currentIndex = i + 1
                    AppController.ui_controller.setViewFilterForView("QuickCopy", "collection", collections[i])
                    break
                }
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
                implicitHeight: headerControls.implicitHeight + 16
                radius: 22

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

                    // Filter Group
                    RowLayout {
                        spacing: 12
                        
                        IconButton {
                            id: qcv_toggleAllBtn
                            buttonSize: 24
                            tooltipText: AppController.quickCopyModel.isAllExpanded ? "Collapse All" : "Expand All"
                            onClicked: (mouse) => AppController.quickCopyModel.toggleAll()
                            iconSize: 18
                            iconSource: AppController.quickCopyModel.isAllExpanded ?
                                    AppController.ui_controller.getAssetUri("ui/collapse-arrow-up-broken.svg") :
                                    AppController.ui_controller.getAssetUri("ui/collapse-arrow-down-broken.svg")
                            background: Rectangle {
                                radius: 12
                                color: qcv_toggleAllBtn.hovered ? Theme.glassHover : "transparent"
                                border.color: Theme.alpha(Theme.label, 0.15)
                                border.width: 1
                            }
                        }

                        GlassCheckBox {
                            id: qcv_selectCheck
                            buttonSize: 24
                            Layout.alignment: Qt.AlignVCenter
                            checkedColor: Theme.glassPill
                            checkedHoverColor: Theme.glassHover
                            iconColor: Theme.label
                            isClearAction: true
                            
                            checkState: {
                                let count = AppController.quickCopyModel.visibleSelectedCount;
                                let total = AppController.quickCopyModel.visibleSelectableCount;
                                if (count === 0) return Qt.Unchecked;
                                if (count >= total && total > 0) return Qt.Checked;
                                return Qt.PartiallyChecked;
                            }

                            onToggled: {
                                if (checkState === Qt.Unchecked) {
                                    AppController.quickCopyModel.selectAll();
                                } else {
                                    AppController.quickCopyModel.clearSelection();
                                }
                            }
                        }

                        RowLayout {
                            id: qcv_infoGroup
                            spacing: 8
                            visible: AppController.quickCopyModel.selectedCount > 0
                            
                            Rectangle {
                                Layout.preferredWidth: Math.max(24, qcvCountText.implicitWidth + 16)
                                Layout.preferredHeight: 24
                                radius: 12
                                color: Theme.glassPill
                                border.color: Theme.glassBorder
                                border.width: 1
                                Text {
                                    id: qcvCountText
                                    anchors.centerIn: parent
                                    text: AppController.quickCopyModel.selectedCount.toString()
                                    color: Theme.label
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
                            id: barDeleteBtn
                            visible: !qcv_root.isEditingCollection
                            buttonSize: 28
                            iconSource: AppController.ui_controller.getAssetUri("ui/delete-icon.svg")
                            tooltipText: "Delete Selected Skills"
                            role: "destructive"
                            flat: true
                            enabled: AppController.quickCopyModel.selectedCount > 0
                            onClicked: (mouse) => AppController.ops_controller.deleteSelectedSkills()
                        }

                        IconButton {
                            id: barAddCombinedBtn
                            visible: !qcv_root.isEditingCollection
                            buttonSize: 28
                            iconSource: AppController.ui_controller.getAssetUri("ui/layout-grid-add-icon.svg")
                            tooltipText: AppController.quickCopyModel.selectedCount > 0 ? "Add Selected Skills..." : "Create New..."
                            onClicked: qcv_addMenu.popup(barAddCombinedBtn, 0, barAddCombinedBtn.height + 4)
                        }

                        GlassMenu {
                            id: qcv_addMenu
                            GlassMenuItem {
                                text: "+ Collection"
                                opacity: AppController.quickCopyModel.selectedCount > 1 ? 1.0 : 0.4
                                iconSource: AppController.ui_controller.getAssetUri("ui/notes-minimalistic-bold-duotone.svg")
                                
                                MouseArea {
                                    anchors.fill: parent
                                    enabled: AppController.quickCopyModel.selectedCount <= 1
                                    hoverEnabled: true
                                    onClicked: {
                                        AppController._set_status("Select at least 2 items to create a collection")
                                    }
                                }

                                onTriggered: {
                                    qcv_root.isEditingCollection = true
                                    qcv_root.editingCollectionName = ""
                                    qcv_root.editingCollectionProjects = []
                                }
                            }
                            GlassMenuItem {
                                text: "+ Command"
                                iconSource: AppController.ui_controller.getAssetUri("ui/magic-stick-3-bold-duotone.svg")
                                onTriggered: {
                                    qcv_commandDialog.openWithContext()
                                    var names = AppController.quickCopyModel.getSelectedNames()
                                    var refs = ""
                                    for (var i = 0; i < names.length; i++) {
                                        refs += "@" + names[i] + "\n"
                                    }
                                    qcv_commandDialog.prefillBody(refs)
                                }
                            }
                        }

                        Item { Layout.fillWidth: true }
                        
                        RowLayout {
                            visible: !qcv_root.isEditingCollection
                            spacing: 12

                            GlassCollectionDropdown {
                                id: qcv_collectionDrop
                                Layout.preferredWidth: 180
                                onCollectionSelected: (collectionName) => {
                                if (collectionName === "All Collections") {
                                    qcv_root._isInternalSelectionChange = true
                                    AppController.ui_controller.setViewFilterForView("QuickCopy", "collection", "")
                                    AppController.quickCopyModel.clearSelection()
                                    qcv_root._isInternalSelectionChange = false
                                } else {
                                    qcv_root._isInternalSelectionChange = true
                                    AppController.config_controller.applyCollectionSelection(collectionName)
                                    AppController.ui_controller.setViewFilterForView("QuickCopy", "collection", collectionName)
                                    qcv_root._isInternalSelectionChange = false
                                }
                            }
                            onEditCollectionClicked: (collectionName) => {
                                qcv_root.isEditingCollection = true
                                qcv_root.editingCollectionName = collectionName
                                qcv_root.editingCollectionProjects = AppController.config_controller.getCollectionProjects(collectionName)
                                qcv_root._isInternalSelectionChange = true
                                AppController.config_controller.applyCollectionSelection(collectionName)
                                AppController.ui_controller.setViewFilterForView("QuickCopy", "collection", "")
                                if (qcv_root.editingCollectionProjects.length > 0) {
                                    AppController.setCurrentProject(qcv_root.editingCollectionProjects[0])
                                } else {
                                    AppController.setCurrentProject("All Projects")
                                }
                                qcv_root._isInternalSelectionChange = false
                            }
                        }

                        GlassDropdown {
                            id: qcv_categoryDrop
                            Layout.preferredWidth: 160
                            iconSource: "ui/cosmetic-bold-duotone.svg"
                            model: ["All Categories"].concat(AppController.categories)
                            currentIndex: {
                                let idx = model.indexOf(AppController.quickCopyModel.categoryFilter);
                                return idx === -1 ? 0 : idx;
                            }
                            onActivated: (index) => {
                                let cat = index === 0 ? "" : currentText
                                AppController.ui_controller.setViewFilterForView("QuickCopy", "category", cat)
                            }
                        }

                        GlassDropdown {
                            id: qcv_projectDrop
                            Layout.preferredWidth: 180
                            iconSource: "ui/folder-security-bold.svg"
                            model: AppController.projectLabels
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
                            objectName: "cycleProjectButton"
                            buttonSize: 32 // matching dropdown height conceptually
                            iconSource: AppController.ui_controller.getAssetUri("ui/transfer-icon.svg")
                            tooltipText: AppController.lastProject !== ""
                                ? ("Switch to " + AppController.lastProject)
                                : "No previous project"
                            enabled: AppController.lastProject !== ""
                            onClicked: AppController.cycleProject()
                        }
                    }

                    Rectangle {
                        visible: !qcv_root.isEditingCollection
                        width: 1
                        height: 16
                        color: Theme.separator
                        Layout.leftMargin: 4
                        Layout.rightMargin: 4
                    }

                    // Client Format Group
                    RowLayout {
                        visible: !qcv_root.isEditingCollection
                        spacing: 8
                        Repeater {
                            model: AppController.clientFormats
                            delegate: IconButton {
                                id: clientBtn
                                buttonSize: 32
                                property bool isSelected: modelData === AppController.clientFormat
                                onClicked: (mouse) => AppController.ui_controller.setClientFormat(modelData)
                                contentItem: Item {
                                    implicitWidth: clientBtn.buttonSize
                                    implicitHeight: clientBtn.buttonSize
                                    Image {
                                        id: clientImg
                                        anchors.centerIn: parent
                                        source: AppController.ui_controller.getLogoSource(modelData)
                                        width: 16
                                        height: 16
                                        sourceSize.width: 16
                                        sourceSize.height: 16
                                        fillMode: Image.PreserveAspectFit
                                        opacity: clientBtn.isSelected ? 1.0 : 0.5
                                        visible: modelData !== "OpenCode"
                                    }
                                    ColorOverlay {
                                        anchors.fill: clientImg
                                        source: clientImg
                                        color: Theme.label
                                        visible: modelData === "OpenCode"
                                        opacity: clientBtn.isSelected ? 1.0 : 0.5
                                    }
                                }
                                background: Rectangle {
                                    radius: width / 2
                                    color: clientBtn.hovered ? Theme.glassHover : "transparent"
                                    border.color: isSelected ? Theme.accent : (clientBtn.hovered ? Theme.glassBorder : "transparent")
                                    border.width: 1
                                }
                                ToolTip.visible: clientBtn.hovered || clientBtn.visualFocus
                                ToolTip.text: modelData
                            }
                        }
                    }

                    Rectangle {
                        visible: !qcv_root.isEditingCollection
                        width: 1
                        height: 16
                        color: Theme.separator
                        Layout.leftMargin: 4
                        Layout.rightMargin: 4
                    }

                    IconButton {
                        id: barCopyBtn
                        visible: !qcv_root.isEditingCollection
                        buttonSize: 32
                        role: "primary-outline"
                        iconSource: AppController.ui_controller.getAssetUri("ui/copy-icon.svg")
                        tooltipText: AppController.quickCopyModel.selectedCount > 0 ? ("Copy Selected (" + AppController.quickCopyModel.selectedCount + ")") : "Copy (No selection)"
                        enabled: AppController.quickCopyModel.selectedCount > 0
                        opacity: enabled ? 1.0 : 0.5
                        objectName: "copySelectedBtn"
                        onClicked: (mouse) => AppController.ops_controller.copySelectedSkillsToClipboard()
                    }
                        }

                    // Fixed Controls Group (Right-most)
                    RowLayout {
                        id: fixedControls
                        spacing: 12
                        layoutDirection: Qt.LeftToRight // Keep internal items left-to-right

                        // Edit Collection Mode
                        RowLayout {
                            spacing: 8
                            visible: qcv_root.isEditingCollection

                            TextField {
                                id: qcv_colNameField
                                Layout.preferredHeight: 32
                                Layout.preferredWidth: 150
                                placeholderText: "Collection Name"
                                Accessible.role: Accessible.EditableText
                                Accessible.name: placeholderText
                                text: qcv_root.editingCollectionName
                                color: Theme.label
                                placeholderTextColor: Theme.secondaryLabel
                                background: Rectangle {
                                    radius: Theme.radiusField
                                    color: Theme.glassPill
                                    border.color: Theme.glassBorder
                                }
                                onTextChanged: qcv_root.editingCollectionName = text
                            }

                            GlassMultiSelect {
                                id: qcv_colProjectSelect
                                Layout.preferredWidth: 180
                                Layout.preferredHeight: 32
                                iconSource: "ui/folder-security-bold.svg"
                                model: AppController.projectLabels
                                selectedValues: qcv_root.editingCollectionProjects
                                placeholderText: "Select projects..."
                                allLabel: "All Projects"
                                onSelectionChanged: qcv_root.editingCollectionProjects = selectedValues
                            }

                            IconButton {
                                id: qcv_saveColBtn
                                buttonSize: 28
                                iconSize: 24
                                iconSource: AppController.ui_controller.getAssetUri("ui/check-circle-bold.svg")
                                role: "ghost"
                                customIconColor: Theme.accent
                                tooltipText: "Save collection"
                                flat: true
                                enabled: qcv_root.editingCollectionName !== "" && qcv_root.editingCollectionProjects.length > 0
                                onClicked: (mouse) => {
                                    let paths = AppController.quickCopyModel.getSelectedPaths()
                                    let projects = qcv_colProjectSelect.selectedValues

                                    AppController.config_controller.saveCustomCollection(qcv_root.editingCollectionName, paths, projects)

                                    let missingJson = AppController.config_controller.checkMissingSkills(qcv_root.editingCollectionName)
                                    let missing = JSON.parse(missingJson)

                                    let realMissing = {}
                                    for (let k in missing) {
                                        if (Array.isArray(missing[k]) && missing[k].length > 0) {
                                            realMissing[k] = missing[k]
                                        }
                                    }

                                    if (Object.keys(realMissing).length > 0) {
                                        qcv_missingSkillsDialog.currentCallback = function(action, checkedProjects) {
                                            if (action === "copy") {
                                                AppController.config_controller.copyMissingSkills(qcv_root.editingCollectionName, checkedProjects)
                                            } else if (action === "remove_projects") {
                                                AppController.config_controller.saveCustomCollection(qcv_root.editingCollectionName, paths, [])
                                            }
                                        }
                                        qcv_missingSkillsDialog.openWithMissing(qcv_root.editingCollectionName, realMissing)
                                    } else {
                                        AppController.config_controller.setStatus("All skills already present in selected projects")
                                    }

                                    qcv_root.isEditingCollection = false
                                    qcv_root.editingCollectionName = ""
                                    qcv_root.editingCollectionProjects = []
                                }
                            }

                            IconButton {
                                id: qcv_cancelColBtn
                                buttonSize: 28
                                iconSize: 24
                                iconSource: AppController.ui_controller.getAssetUri("ui/close-circle-broken.svg")
                                role: "destructive"
                                tooltipText: "Cancel collection editing"
                                flat: true
                                onClicked: (mouse) => {
                                    qcv_root.isEditingCollection = false
                                    qcv_root.editingCollectionName = ""
                                    qcv_root.editingCollectionProjects = []
                                }
                            }
                        }
                    }
                }



            } // End of GlassPill
        }



        // Main Content Area
        SplitView {
            id: qcv_splitView
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
                    color: qcv_splitHandleArea.containsMouse ? Theme.accent : Theme.separator
                    opacity: qcv_splitHandleArea.containsMouse ? 1.0 : 0.3
                    Behavior on color { ColorAnimation { duration: 150 } }
                    Behavior on opacity { NumberAnimation { duration: 150 } }
                }
                
                MouseArea {
                    id: qcv_splitHandleArea
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.SizeHorCursor
                    Accessible.role: Accessible.Splitter
                    Accessible.name: "Resize Splitter"
                }
            }

            // Skill List
            SmoothListView {
                id: qcv_skillList
                objectName: "quickCopyList"
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
                        qcv_skillList.forceLayout()
                        qcv_skillList.contentY = savedScrollPos
                        
                        // Second pass: Ensure it stuck (sometimes required for large additions)
                        Qt.callLater(() => {
                            if (qcv_skillList.contentY !== savedScrollPos) {
                                qcv_skillList.forceLayout()
                                qcv_skillList.contentY = savedScrollPos
                            }
                            _restoringScroll = false
                        })
                    }
                }

                Connections {
                    target: AppController.quickCopyModel
                    function onLayoutAboutToBeChanged() {
                        qcv_skillList.savedScrollPos = qcv_skillList.contentY
                        qcv_skillList.cacheBuffer = 0
                    }
                    function onLayoutChanged() {
                        // Only re-enable incubation while the list is still live.
                        // After cleanup() sets model = null (view teardown), a stray
                        // layout signal must NOT restore cacheBuffer, or incubated
                        // delegates race against the dying context.
                        // Also defer the restore while the model is still incubating:
                        // the reset fires mid-incubation, so restoring cacheBuffer
                        // here re-triggers a delegate burst that races the in-flight
                        // one ("Object or context destroyed during incubation").
                        // The restore is performed in onIncubatingChanged instead.
                        if (qcv_skillList.model && !AppController.quickCopyModel.incubating) {
                            qcv_skillList.cacheBuffer = Math.max(qcv_skillList.height * 2, 1000)
                            qcv_skillList._restoreScroll()
                        }
                    }
                    function onModelAboutToBeReset() {
                        qcv_skillList.savedScrollPos = qcv_skillList.contentY
                        qcv_skillList.cacheBuffer = 0
                    }
                    function onModelReset() {
                        if (qcv_skillList.model && !AppController.quickCopyModel.incubating) {
                            qcv_skillList.cacheBuffer = Math.max(qcv_skillList.height * 2, 1000)
                            qcv_skillList._restoreScroll()
                        }
                    }
                    function onAboutToMutateStructure() {
                        qcv_skillList.savedScrollPos = qcv_skillList.contentY
                        qcv_skillList.cacheBuffer = 0
                    }
                    function onStructureMutated() {
                        if (qcv_skillList.model && !AppController.quickCopyModel.incubating) {
                            qcv_skillList.cacheBuffer = Math.max(qcv_skillList.height * 2, 1000)
                            qcv_skillList._restoreScroll()
                        }
                    }
                }

                // Incubation coordination: when incubating transitions to False,
                // tell the model to replay deferred layout signals.
                Connections {
                    target: AppController.quickCopyModel
                    function onIncubatingChanged() {
                        if (!AppController.quickCopyModel.incubating) {
                            AppController.quickCopyModel.onIncubationReady()
                            // Incubation finished: now safe to re-enable the
                            // off-screen cache buffer without racing live delegates.
                            if (qcv_skillList.model) {
                                qcv_skillList.cacheBuffer = Math.max(qcv_skillList.height * 2, 1000)
                                qcv_skillList._restoreScroll()
                            }
                        }
                    }
                }

                section.property: "mainCategoryName"
                section.criteria: ViewSection.FullString
                section.delegate: CategoryHeader { 
                    mainCatName: section
                    width: qcv_skillList.width
                }
                
                delegate: SkillItem {
                    width: qcv_skillList.width
                    showStarredIcon: true
                    showInlineDelete: false
                    onClicked: (mouse) => {
                        AppController.quickCopyModel.toggleSelection(index)
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
                            qcv_cmdDeleteDialog.openForCommand(name, holders)
                        } else {
                            var holders = AppController.skillProjectsForPath(path) || []
                            if (holders.length === 0) holders = [AppController.currentProject || ""]
                            qcv_cmdDeleteDialog.openForSkill(name, holders, path)
                        }
                    }
                    onInspectImageRequested: {
                        qcv_root.showImageInspector = true
                    }
                }
            }

            // Command Inspector
            CommandInspector {
                id: qcv_commandInspector
                SplitView.fillHeight: true
                SplitView.preferredWidth: {
                    var p = AppController.ui_controller.inspectorWidth
                    return p > 0 ? Math.max(p, targetWidth) : targetWidth
                }
                skill: AppController.selectedSkill
                editDialog: qcv_commandDialog
                visible: targetWidth > 0 && qcv_root.showCommandInspector

                onWidthChanged: {
                    if (visible && width > 0) {
                        AppController.ui_controller.setInspectorWidth(width)
                    }
                }
                onClosed: {
                    qcv_root.showCommandInspector = false
                    AppController.ui_controller.selectSkill(-1)
                }
                onDeleteRequested: (name, path, isCommand) => {
                    var holders = AppController.commandProjectsForPath(path) || []
                    if (holders.length === 0) holders = [AppController.currentProject || ""]
                    qcv_cmdDeleteDialog.openForCommand(name, holders)
                }
            }

            // Overlay Inspector (skills)
            SkillInspector {
                id: qcv_inspector
                SplitView.fillHeight: true
                SplitView.preferredWidth: {
                    var p = AppController.ui_controller.inspectorWidth
                    return p > 0 ? Math.max(p, targetWidth) : targetWidth
                }
                skill: AppController.selectedSkill
                isQuickCopy: true
                visible: targetWidth > 0 && !qcv_root.showImageInspector && !qcv_root.showCommandInspector

                onWidthChanged: {
                    if (visible && width > 0) {
                        AppController.ui_controller.setInspectorWidth(width)
                    }
                }
                onClosed: AppController.ui_controller.selectSkill(-1)
            }

            // Image Inspector (for screenshots)
            ImageInspector {
                id: qcv_imageInspector
                SplitView.fillHeight: true
                SplitView.preferredWidth: {
                    var p = AppController.ui_controller.inspectorWidth
                    return p > 0 ? Math.max(p, targetWidth) : targetWidth
                }
                skill: AppController.selectedSkill
                visible: targetWidth > 0 && qcv_root.showImageInspector

                onWidthChanged: {
                    if (visible && width > 0) {
                        AppController.ui_controller.setInspectorWidth(width)
                    }
                }
                onClosed: {
                    qcv_root.showImageInspector = false
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
                qcv_root.showCommandInspector = true
                qcv_root.showImageInspector = false
            } else if (skill && skill.is_screenshot) {
                qcv_root.showCommandInspector = false
                qcv_root.showImageInspector = true
            } else {
                qcv_root.showCommandInspector = false
                qcv_root.showImageInspector = false
            }
        }
    }

    // Command Creation Dialog
    CommandCreateDialog {
        id: qcv_commandDialog
    }

    CommandDeleteDialog {
        id: qcv_cmdDeleteDialog
    }

    MissingSkillsDialog {
        id: qcv_missingSkillsDialog
    }

    CommandCarrySkillsDialog {
        id: qcv_carrySkillsDialog
        onCarryConfirmed: (confirmedSkills) => {
            AppController.confirmCommandSkillsCarry(
                qcv_carrySkillsDialog.projectPath,
                JSON.stringify(qcv_carrySkillsDialog.commandPaths),
                JSON.stringify(confirmedSkills)
            )
        }
    }

    Connections {
        target: AppController
        function onCommandSkillsCarryPrompt(commandPathsJson, projectPath, missingSkillsJson) {
            var cmdPaths = JSON.parse(commandPathsJson || "[]")
            var skills = JSON.parse(missingSkillsJson || "[]")
            qcv_carrySkillsDialog.openWithContext(cmdPaths, projectPath, skills)
        }
    }
}

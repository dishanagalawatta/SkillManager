import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import ".."
import App 1.0
import ".."
import "../dialogs"

Item {
    id: qcv_root
    
    property bool isEditingCollection: false
    property string editingCollectionName: ""
    property bool _isInternalSelectionChange: false
    property bool showImageInspector: false
    property bool showCommandInspector: false
    property var editingCollectionProjects: []

    function focusSearch() {
        searchInput.forceActiveFocus()
        searchInput.selectAll()
    }

    function scrollToTop() {
        qcv_skillList.positionViewAtBeginning()
    }

    Component.onCompleted: {
        // Mode is handled by AppController currentView setter
        searchInput.text = AppController.quickCopyModel.filterText
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

            ColumnLayout {
                spacing: 4
                RowLayout {
                    spacing: 12
                    Text {
                        text: "Quick Copy"
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.sizeHeading
                        font.weight: Font.Bold
                        color: Theme.label
                    }
                }
                Text {
                    text: "Select and copy skills to your clipboard instantly."
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.sizeBody
                    color: Theme.secondaryLabel
                }
            }

            Flow {
                id: headerControls
                Layout.fillWidth: true
                Layout.alignment: Qt.AlignVCenter
                spacing: 12
                layoutDirection: Qt.RightToLeft

                // Fixed Controls Group (Right-most)
                RowLayout {
                    id: fixedControls
                    spacing: 12
                    layoutDirection: Qt.LeftToRight // Keep internal items left-to-right

                    // Filter Group
                    RowLayout {
                        spacing: 12
                        
                        GlassCollectionDropdown {
                            id: qcv_collectionDrop
                            Layout.preferredWidth: 160
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
                                AppController.ui_controller.setViewFilterForView("QuickCopy", "collection", collectionName)
                                qcv_root._isInternalSelectionChange = false
                            }
                        }

                        GlassDropdown {
                            id: qcv_categoryDrop
                            Layout.preferredWidth: 130
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
                            Layout.preferredWidth: 150
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
                    }

                    // Client Format Group
                    RowLayout {
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
                                    color: isSelected ? Theme.alpha(Theme.accent, 0.20) : (clientBtn.hovered ? Theme.glassHover : "transparent")
                                    border.color: isSelected ? Theme.accent : (clientBtn.hovered ? Theme.glassBorder : "transparent")
                                    border.width: 1
                                }
                                ToolTip.visible: hovered
                                ToolTip.text: modelData
                            }
                        }
                    }
                }

                // Search Group (Flexible, Left-most on first line)
                GlassSearchInput {
                    id: searchInput
                    objectName: "quickCopySearchInput"
                    // Dynamic width: Fill remaining space on the line, or take full width if too small
                    readonly property real minSearchWidth: 200
                    readonly property real fixedWidth: fixedControls.width + headerControls.spacing

                    width: {
                        let available = headerControls.width - fixedWidth;
                        return available >= minSearchWidth ? available : headerControls.width;
                    }

                    onDebouncedTextChanged: (text) => {
                        AppController.quickCopyModel.filterText = text
                    }
                }

            }
        }



        // Selection Action Bar
        Rectangle {
            id: selectionBar
            Layout.fillWidth: true
            Layout.preferredHeight: 48
            visible: true
            color: Theme.alpha(Theme.accent, 0.06) // Subtle accent background
            radius: Theme.radiusCard
            border.color: Theme.alpha(Theme.accent, 0.19)
            border.width: 1
            clip: true
            
            RowLayout {
                id: qcv_selectionLayout
                anchors.fill: parent
                anchors.leftMargin: 12
                anchors.rightMargin: 12
                anchors.topMargin: 8
                anchors.bottomMargin: 8
                spacing: 12
                // LEFT: Toggle All
                IconButton {
                    id: qcv_toggleAllBtn
                    buttonSize: 28
                    role: "ghost"
                    tooltipText: AppController.quickCopyModel.isAllExpanded ? "Collapse All" : "Expand All"
                    onClicked: (mouse) => AppController.quickCopyModel.toggleAll()
                    contentItem: Image {
                        source: AppController.quickCopyModel.isAllExpanded ?
                                AppController.ui_controller.getAssetUri(Theme.darkMode ? "ui/collapse-arrow-icon-dark.svg" : "ui/collapse-arrow-icon-light.svg") :
                                AppController.ui_controller.getAssetUri(Theme.darkMode ? "ui/expand-arrow-icon-dark.svg" : "ui/expand-arrow-icon-light.svg")
                        width: 16
                        height: 16
                        sourceSize.width: 72
                        sourceSize.height: 72
                        fillMode: Image.PreserveAspectFit
                        opacity: qcv_toggleAllBtn.hovered ? 1.0 : 0.7
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
                    id: qcv_selectCheck
                    Layout.preferredWidth: 32
                    Layout.preferredHeight: 32
                    
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

                // LEFT: Selection Count & Info
                RowLayout {
                    id: qcv_infoGroup
                    spacing: 12
                    visible: AppController.quickCopyModel.selectedCount > 0
                    
                    Rectangle {
                        width: 24
                        height: 24
                        radius: Theme.radiusPill
                        color: Theme.accent
                        Text {
                            anchors.centerIn: parent
                            text: AppController.quickCopyModel.selectedCount
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
                    id: qcv_buttonGroup
                    spacing: 8
                    
                    // Regular Mode Actions
                    RowLayout {
                        spacing: 8
                        visible: !qcv_root.isEditingCollection

                        ActionButton {
                            id: barScreenshotBtn
                            objectName: "quickCopyScreenshotBtn"
                            buttonHeight: 32
                            labelText: "Screenshot"
                            iconSource: AppController.ui_controller.getAssetUri("ui/screenshot-icon.svg")
                            role: "secondary"
                            onClicked: (mouse) => AppController.screenshot_controller.takeScreenshot()
                        }

                        ActionButton {
                            id: barAddCommandBtn
                            buttonHeight: 32
                            labelText: "Add Command"
                            iconSource: AppController.ui_controller.getAssetUri("ui/plus-icon.svg")
                            role: "secondary"
                            onClicked: (mouse) => qcv_commandDialog.openWithContext()
                        }

                        // Selection-specific actions
                        RowLayout {
                            spacing: 8
                            visible: AppController.quickCopyModel.selectedCount > 0
                            
                            ActionButton {
                                id: barAddToColBtn
                                buttonHeight: 32
                                labelText: "Add to Collection"
                                role: "secondary"
                                onClicked: (mouse) => {
                                    qcv_root.isEditingCollection = true
                                    qcv_root.editingCollectionName = ""
                                }
                            }

                            ActionButton {
                                id: barDeleteBtn
                                buttonHeight: 32
                                objectName: "quickCopyDeleteSelectedBtn"
                                labelText: "Delete"
                                iconSource: AppController.ui_controller.getAssetUri("ui/delete-icon.svg")
                                role: "destructive"
                                onClicked: (mouse) => qcv_deleteConfirmDialog.confirmBulk(AppController.quickCopyModel.selectedCount, () => AppController.ops_controller.deleteSelectedSkills())
                            }

                            Rectangle {
                                objectName: "quickCopyDestructiveDivider"
                                width: 1
                                height: 16
                                color: Theme.separator
                                Layout.leftMargin: 4
                                Layout.rightMargin: 4
                            }

                            ActionButton {
                                id: barCopyBtn
                                buttonHeight: 32
                                objectName: "copySelectedBtn"
                                labelText: "Copy"
                                role: "primary"
                                onClicked: (mouse) => AppController.ops_controller.copySelectedSkillsToClipboard()
                            }
                        }
                    }

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
                            Layout.preferredWidth: 160
                            Layout.preferredHeight: 32
                            model: AppController.projectLabels
                            selectedValues: qcv_root.editingCollectionProjects
                            placeholderText: "Select projects..."
                            allLabel: "All Projects"
                            onSelectionChanged: qcv_root.editingCollectionProjects = selectedValues
                        }

                        IconButton {
                            id: qcv_saveColBtn
                            buttonSize: 32
                            iconSize: 12
                            iconSource: AppController.ui_controller.getAssetUri("ui/check-icon.svg")
                            role: "primary"
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
                            buttonSize: 32
                            iconSize: 10
                            iconSource: AppController.ui_controller.getAssetUri("ui/close-icon.svg")
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
                model: AppController.isLoading ? null : AppController.quickCopyModel
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
                    target: qcv_skillList.model
                    function onLayoutAboutToBeChanged() {
                        if (AppController.isLoading) {
                            qcv_skillList.savedScrollPos = qcv_skillList.contentY
                        }
                    }
                    function onLayoutChanged() {
                        qcv_skillList._restoreScroll()
                    }
                    function onModelAboutToBeReset() {
                        if (AppController.isLoading) {
                            qcv_skillList.savedScrollPos = qcv_skillList.contentY
                        }
                    }
                    function onModelReset() {
                        qcv_skillList._restoreScroll()
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
                    onDeleteRequested: (name, path) => {
                        qcv_deleteConfirmDialog.confirmSingle(name, () => AppController.ops_controller.deleteSkill(path))
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

    DeleteConfirmDialog {
        id: qcv_deleteConfirmDialog
    }

    MissingSkillsDialog {
        id: qcv_missingSkillsDialog
    }
}

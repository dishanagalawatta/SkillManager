import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import Qt5Compat.GraphicalEffects
import App 1.0
import SkillManagerComponents 1.0
import ".."
import "../dialogs"

Item {
    id: qcv_root
    
    property bool isEditingCollection: false
    property string editingCollectionName: ""
    property bool _isInternalSelectionChange: false

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
                            model: ["All Projects"].concat(AppController.projectLabels)
                            currentIndex: {
                                let idx = model.indexOf(AppController.quickCopyModel.projectFilter);
                                return idx === -1 ? 0 : idx;
                            }
                            onActivated: (index) => {
                                let proj = index === 0 ? "" : currentText
                                AppController.ui_controller.setViewFilterForView("QuickCopy", "project", proj)
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
                                        anchors.centerIn: parent
                                        source: AppController.ui_controller.getLogoSource(modelData)
                                        width: 16
                                        height: 16
                                        sourceSize.width: 16
                                        sourceSize.height: 16
                                        fillMode: Image.PreserveAspectFit
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
                    // Dynamic width: Fill remaining space on the line, or take full width if too small
                    readonly property real minSearchWidth: 200
                    readonly property real fixedWidth: fixedControls.width + headerControls.spacing
                    
                    width: {
                        let available = headerControls.width - fixedWidth;
                        return available >= minSearchWidth ? available : headerControls.width;
                    }

                    onTextChanged: {
                        AppController.quickCopyModel.filterText = text
                    }
                }
            }
        }

        Flow {
            Layout.fillWidth: true
            spacing: 8
            visible: searchInput.text !== "" || AppController.quickCopyModel.categoryFilter !== "" || AppController.quickCopyModel.projectFilter !== ""

            Repeater {
                model: [
                    { label: searchInput.text ? "Search: " + searchInput.text : "", clear: function() { searchInput.text = ""; AppController.quickCopyModel.filterText = "" } },
                    { label: AppController.quickCopyModel.projectFilter ? "Project: " + AppController.quickCopyModel.projectFilter : "", clear: function() { AppController.ui_controller.setViewFilterForView("QuickCopy", "project", "") } },
                    { label: AppController.quickCopyModel.categoryFilter ? "Category: " + AppController.quickCopyModel.categoryFilter : "", clear: function() { AppController.ui_controller.setViewFilterForView("QuickCopy", "category", "") } }
                ].filter((item) => item.label !== "")

                delegate: Rectangle {
                    height: 28
                    width: chipLabel.implicitWidth + 34
                    radius: Theme.radiusPill
                    color: Theme.glassPill
                    border.color: Theme.glassBorder
                    border.width: 1

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 10
                        anchors.rightMargin: 8
                        spacing: 6
                        Text {
                            id: chipLabel
                            text: modelData.label
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.sizeCaption
                            color: Theme.secondaryLabel
                            elide: Text.ElideRight
                        }
                        Text {
                            text: "x"
                            font.pixelSize: 13
                            color: Theme.accent
                        }
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: modelData.clear()
                    }
                }
            }
        }

        // Selection Action Bar
        Rectangle {
            id: selectionBar
            Layout.fillWidth: true
            Layout.preferredHeight: 64
            visible: true
            color: Theme.alpha(Theme.accent, 0.06) // Subtle accent background
            radius: Theme.radiusCard
            border.color: Theme.alpha(Theme.accent, 0.19)
            border.width: 1
            clip: true
            
            RowLayout {
                id: qcv_selectionLayout
                anchors.fill: parent
                anchors.margins: 12
                spacing: 12
                // LEFT: Toggle All
                IconButton {
                    id: qcv_toggleAllBtn
                    buttonSize: 32
                    role: "ghost"
                    tooltipText: AppController.quickCopyModel.isAllExpanded ? "Collapse All" : "Expand All"
                    onClicked: (mouse) => AppController.quickCopyModel.toggleAll()
                    contentItem: Image {
                        source: AppController.quickCopyModel.isAllExpanded ?
                                AppController.ui_controller.getAssetUri(Theme.darkMode ? "ui/collapse-arrow-icon-dark.svg" : "ui/collapse-arrow-icon-light.svg") :
                                AppController.ui_controller.getAssetUri(Theme.darkMode ? "ui/expand-arrow-icon-dark.svg" : "ui/expand-arrow-icon-light.svg")
                        width: 18
                        height: 18
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
                    height: 20
                    color: Theme.separator
                    Layout.leftMargin: 4
                    Layout.rightMargin: 4
                }

                // LEFT: Selection Count & Info
                RowLayout {
                    id: qcv_infoGroup
                    spacing: 12
                    visible: AppController.quickCopyModel.selectedCount > 0
                    
                    Rectangle {
                        width: 28
                        height: 28
                        radius: Theme.radiusPill
                        color: Theme.accent
                        Text {
                            anchors.centerIn: parent
                            text: AppController.quickCopyModel.selectedCount
                            color: "white"
                            font.family: Theme.fontFamily
                            font.weight: Font.Bold
                            font.pixelSize: 12
                        }
                    }

                    Text {
                        text: "Skills selected"
                        font.family: Theme.fontFamily
                        font.pixelSize: 13
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
                            id: barAddCommandBtn
                            labelText: "Add Command"
                            iconText: "+"
                            role: "secondary"
                            onClicked: (mouse) => qcv_commandDialog.openWithContext(AppController.quickCopyModel.projectFilter, AppController.ui_controller.clientFormat)
                        }

                        ActionButton {
                            id: barSelectAllBtn
                            labelText: "Select All"
                            role: "secondary"
                            visible: AppController.quickCopyModel.selectedCount < AppController.quickCopyModel.rowCount()
                            onClicked: (mouse) => AppController.quickCopyModel.selectAll()
                        }

                        // Selection-specific actions
                        RowLayout {
                            spacing: 8
                            visible: AppController.quickCopyModel.selectedCount > 0
                            
                            ActionButton {
                                id: barClearBtn
                                labelText: "Clear Selection"
                                role: "secondary"
                                onClicked: (mouse) => AppController.quickCopyModel.clearSelection()
                            }

                            Rectangle {
                                width: 1
                                height: 20
                                color: Theme.separator
                                Layout.leftMargin: 4
                                Layout.rightMargin: 4
                            }

                            ActionButton {
                                id: barAddToColBtn
                                labelText: "Add to Collection"
                                role: "secondary"
                                onClicked: (mouse) => {
                                    qcv_root.isEditingCollection = true
                                    qcv_root.editingCollectionName = ""
                                }
                            }

                            ActionButton {
                                id: barDeleteBtn
                                objectName: "quickCopyDeleteSelectedBtn"
                                labelText: "Delete Selected"
                                iconText: "🗑️"
                                role: "destructive"
                                onClicked: (mouse) => qcv_deleteConfirmDialog.confirmBulk(AppController.quickCopyModel.selectedCount, () => AppController.ops_controller.deleteSelectedSkills())
                            }

                            Rectangle {
                                objectName: "quickCopyDestructiveDivider"
                                width: 1
                                height: 20
                                color: Theme.separator
                                Layout.leftMargin: 4
                                Layout.rightMargin: 4
                            }

                            ActionButton {
                                id: barCopyBtn
                                objectName: "copySelectedBtn"
                                labelText: "Copy Selected"
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
                            Layout.preferredHeight: 36
                            Layout.preferredWidth: 200
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

                        IconButton {
                            id: qcv_saveColBtn
                            buttonSize: 36
                            iconSize: 12
                            iconText: "Save"
                            role: "primary"
                            tooltipText: "Save collection"
                            flat: true
                            onClicked: (mouse) => {
                                AppController.config_controller.saveCustomCollection(qcv_root.editingCollectionName, AppController.quickCopyModel.getSelectedPaths())
                                qcv_root.isEditingCollection = false
                                qcv_root.editingCollectionName = ""
                            }
                            contentItem: Text {
                                text: "✔"
                                font.pixelSize: 20
                                color: Theme.success
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                            }
                            background: Rectangle {
                                radius: Theme.radiusField
                                color: qcv_saveColBtn.hovered ? Theme.alpha(Theme.success, 0.125) : "transparent"
                            }
                        }

                        IconButton {
                            id: qcv_cancelColBtn
                            buttonSize: 36
                            iconSize: 10
                            iconText: "Cancel"
                            role: "destructive"
                            tooltipText: "Cancel collection editing"
                            flat: true
                            onClicked: (mouse) => {
                                qcv_root.isEditingCollection = false
                                qcv_root.editingCollectionName = ""
                            }
                            contentItem: Text {
                                text: "✖"
                                font.pixelSize: 20
                                color: Theme.danger
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                            }
                            background: Rectangle {
                                radius: Theme.radiusField
                                color: qcv_cancelColBtn.hovered ? Theme.alpha(Theme.danger, 0.125) : "transparent"
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
                }
            }

            // Skill List
            ListView {
                id: qcv_skillList
                objectName: "quickCopyList"
                SplitView.fillWidth: true
                SplitView.fillHeight: true
                SplitView.minimumWidth: 300
                model: AppController.quickCopyModel
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
                }

                ScrollBar.vertical: ScrollBar {
                    active: true
                }
            }

            // Overlay Inspector
            SkillInspector {
                id: qcv_inspector
                SplitView.fillHeight: true
                SplitView.preferredWidth: targetWidth
                skill: AppController.selectedSkill
                isQuickCopy: true
                visible: targetWidth > 0
                
                onClosed: AppController.ui_controller.selectSkill(-1)
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
}

import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import ".."
import App 1.0
import ".."

Item {
    id: lv_root

    function focusSearch() {
        lv_searchInput.forceActiveFocus()
        lv_searchInput.selectAll()
    }
    
    function scrollToTop() {
        lv_listView.positionViewAtBeginning()
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
                onTextChanged: AppController.libraryModel.filterText = text
            }

            GlassToggleButton {
                text: "Show Archived"
                checked: AppController.libraryModel.showArchived
                onClicked: (mouse) => AppController.libraryModel.showArchived = checked
                
                iconInactive: "📁"
                iconActive: "📦"
                textActive: "Showing Archived"
            }

        }

        Flow {
            Layout.fillWidth: true
            spacing: 8
            visible: lv_searchInput.text !== "" || AppController.libraryModel.categoryFilter !== ""

            Repeater {
                model: [
                    { label: lv_searchInput.text ? "Search: " + lv_searchInput.text : "", clear: function() { lv_searchInput.text = ""; AppController.libraryModel.filterText = "" } },
                    { label: AppController.libraryModel.categoryFilter ? "Category: " + AppController.libraryModel.categoryFilter : "", clear: function() { AppController.ui_controller.setViewFilterForView("Library", "category", "") } }
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
                        Accessible.role: Accessible.Button
                        Accessible.name: "Clear recent search: " + (modelData ? modelData : "")
                    }
                }
            }
        }
        
        // Multi-select Action Bar
        Rectangle {
            id: selectionBar
            Layout.fillWidth: true
            Layout.preferredHeight: 64
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
                anchors.margins: 12
                spacing: 12
                // LEFT: Toggle All
                IconButton {
                    id: lv_toggleAllBtn
                    buttonSize: 32
                    role: "ghost"
                    tooltipText: AppController.libraryModel.isAllExpanded ? "Collapse All" : "Expand All"
                    onClicked: (mouse) => AppController.libraryModel.toggleAll()
                    contentItem: Image {
                        source: AppController.libraryModel.isAllExpanded ?
                                AppController.ui_controller.getAssetUri(Theme.darkMode ? "ui/collapse-arrow-icon-dark.svg" : "ui/collapse-arrow-icon-light.svg") :
                                AppController.ui_controller.getAssetUri(Theme.darkMode ? "ui/expand-arrow-icon-dark.svg" : "ui/expand-arrow-icon-light.svg")
                        width: 18
                        height: 18
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
                    height: 20
                    color: Theme.separator
                    Layout.leftMargin: 4
                    Layout.rightMargin: 4
                }

                // LEFT: Selection Count
                RowLayout {
                    spacing: 12
                    visible: AppController.libraryModel.selectedCount > 0
                    
                    Rectangle {
                        width: 28
                        height: 28
                        radius: Theme.radiusPill
                        color: Theme.accent
                        Text {
                            anchors.centerIn: parent
                            text: AppController.libraryModel.selectedCount
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
                    spacing: 8
                    
                    // Always Visible Actions
                    ActionButton {
                        id: lv_addCommandBtn
                        labelText: "Add"
                        iconText: "+"
                        role: "secondary"
                        onClicked: (mouse) => lv_commandDialog.openWithContext("", AppController.clientFormat)
                    }

                    ActionButton {
                        id: lv_selectAllBtn
                        labelText: "Select All"
                        role: "secondary"
                        visible: AppController.libraryModel.selectedCount < AppController.libraryModel.rowCount()
                        onClicked: (mouse) => AppController.libraryModel.selectAll()
                    }

                    // Selection-specific actions
                    RowLayout {
                        spacing: 8
                        visible: AppController.libraryModel.selectedCount > 0
                        
                        ActionButton {
                            id: lv_clearBtn
                            labelText: "Clear"
                            role: "secondary"
                            onClicked: (mouse) => AppController.libraryModel.clearSelection()
                        }

                        Rectangle {
                            width: 1
                            height: 20
                            color: Theme.separator
                            Layout.leftMargin: 4
                            Layout.rightMargin: 4
                        }

                        GlassDropdown {
                            id: lv_projectDrop
                            Layout.preferredHeight: 36
                            Layout.preferredWidth: 160
                            model: AppController.projectLabels
                            enabled: AppController.projects.length > 0
                        }
                        
                        ActionButton {
                            id: lv_tempCopyBtn
                            labelText: "Copy Temp"
                            role: "secondary"
                            enabled: AppController.projects.length > 0
                            tooltipText: enabled ? "Copies selected skills to the project temporarily. They will be deleted when you close this app." : "Add a project in Updates before copying skills."
                            onClicked: (mouse) => {
                                if (lv_projectDrop.currentIndex >= 0 && lv_projectDrop.currentIndex < AppController.projects.length) {
                                    let path = AppController.projects[lv_projectDrop.currentIndex]
                                    AppController.ops_controller.copySelectedSkillsToProjectTemporarily(path)
                                }
                            }
                        }

                        ActionButton {
                            id: lv_archiveBtn
                            labelText: "Archive"
                            iconText: "📦"
                            role: "secondary"
                            onClicked: (mouse) => lv_archiveConfirmDialog.confirmBulk(AppController.libraryModel.selectedCount, () => AppController.ops_controller.archiveSelectedSkills())
                        }

                        ActionButton {
                            id: lv_deleteBtn
                            labelText: "Delete"
                            iconText: "🗑️"
                            role: "destructive"
                            onClicked: (mouse) => lv_deleteConfirmDialog.confirmBulk(AppController.libraryModel.selectedCount, () => AppController.ops_controller.deleteSelectedSkills())
                        }

                        Rectangle {
                            objectName: "libraryDestructiveDivider"
                            width: 1
                            height: 20
                            color: Theme.separator
                            Layout.leftMargin: 4
                            Layout.rightMargin: 4
                        }

                        ActionButton {
                            id: lv_copyBtn
                            labelText: "Copy to Project"
                            role: "primary"
                            enabled: AppController.projects.length > 0
                            tooltipText: enabled ? "" : "Add a project in Updates before copying skills."
                            onClicked: (mouse) => {
                                if (lv_projectDrop.currentIndex >= 0 && lv_projectDrop.currentIndex < AppController.projects.length) {
                                    let path = AppController.projects[lv_projectDrop.currentIndex]
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
            ListView {
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
                    target: lv_listView.model
                    function onLayoutAboutToBeChanged() {
                        if (AppController.isLoading) {
                            lv_listView.savedScrollPos = lv_listView.contentY
                        }
                    }
                    function onLayoutChanged() {
                        lv_listView._restoreScroll()
                    }
                    function onModelAboutToBeReset() {
                        if (AppController.isLoading) {
                            lv_listView.savedScrollPos = lv_listView.contentY
                        }
                    }
                    function onModelReset() {
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
                }

                ScrollBar.vertical: ScrollBar {
                    active: true
                }
            }

            // Inspector Pane
            SkillInspector {
                id: lv_inspector
                SplitView.fillHeight: true
                SplitView.preferredWidth: targetWidth
                skill: AppController.selectedSkill
                visible: targetWidth > 0

                onClosed: AppController.ui_controller.selectSkill(-1)
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

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

    Component.onCompleted: {
        // Mode is handled by AppController currentView setter
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
                                    AppController.setViewFilter("collection", "")
                                    AppController.skillModel.clearSelection()
                                    qcv_root._isInternalSelectionChange = false
                                } else {
                                    qcv_root._isInternalSelectionChange = true
                                    AppController.applyCollectionSelection(collectionName)
                                    AppController.setViewFilter("collection", collectionName)
                                    qcv_root._isInternalSelectionChange = false
                                }
                            }
                            onEditCollectionClicked: (collectionName) => {
                                qcv_root.isEditingCollection = true
                                qcv_root.editingCollectionName = collectionName
                                qcv_root._isInternalSelectionChange = true
                                AppController.applyCollectionSelection(collectionName)
                                AppController.setViewFilter("collection", collectionName)
                                qcv_root._isInternalSelectionChange = false
                            }

                            Connections {
                                target: AppController.skillModel
                                function onUserSelectionChanged() {
                                    if (!qcv_root.isEditingCollection && !qcv_root._isInternalSelectionChange) {
                                        if (qcv_collectionDrop.currentIndex !== 0) {
                                            qcv_collectionDrop.currentIndex = 0
                                        }
                                    }
                                }
                            }
                        }

                        GlassDropdown {
                            id: qcv_categoryDrop
                            Layout.preferredWidth: 130
                            model: ["All Categories"].concat(AppController.categories)
                            currentIndex: {
                                let idx = model.indexOf(AppController.skillModel.categoryFilter);
                                return idx === -1 ? 0 : idx;
                            }
                            onActivated: (index) => {
                                let cat = index === 0 ? "" : currentText
                                AppController.setViewFilter("category", cat)
                            }
                        }

                        GlassDropdown {
                            id: qcv_projectDrop
                            Layout.preferredWidth: 150
                            model: ["All Projects"].concat(AppController.projects)
                            currentIndex: {
                                let idx = model.indexOf(AppController.skillModel.projectFilter);
                                return idx === -1 ? 0 : idx;
                            }
                            onActivated: (index) => {
                                let proj = index === 0 ? "" : currentText
                                AppController.setViewFilter("project", proj)
                            }
                        }
                    }

                    // Client Format Group
                    RowLayout {
                        spacing: 8
                        Repeater {
                            model: AppController.clientFormats
                            delegate: Button {
                                id: clientBtn
                                Layout.preferredWidth: 32
                                Layout.preferredHeight: 32
                                flat: true
                                property bool isSelected: modelData === AppController.clientFormat
                                onClicked: (mouse) => AppController.setClientFormat(modelData)
                                contentItem: Image {
                                    source: AppController.getLogoSource(modelData)
                                    sourceSize.width: 20
                                    sourceSize.height: 20
                                    fillMode: Image.PreserveAspectFit
                                    opacity: clientBtn.isSelected ? 1.0 : 0.5
                                    horizontalAlignment: Image.AlignHCenter
                                    verticalAlignment: Image.AlignVCenter
                                }
                                background: Rectangle {
                                    radius: Theme.radiusField
                                    color: isSelected ? Theme.accent + "33" : "transparent"
                                    border.color: isSelected ? Theme.accent : "transparent"
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
                        AppController.skillModel.filterText = text
                    }
                }
            }
        }

        Flow {
            Layout.fillWidth: true
            spacing: 8
            visible: searchInput.text !== "" || AppController.skillModel.categoryFilter !== "" || AppController.skillModel.projectFilter !== ""

            Repeater {
                model: [
                    { label: searchInput.text ? "Search: " + searchInput.text : "", clear: function() { searchInput.text = ""; AppController.skillModel.filterText = "" } },
                    { label: AppController.skillModel.projectFilter ? "Project: " + AppController.skillModel.projectFilter : "", clear: function() { AppController.setViewFilter("project", "") } },
                    { label: AppController.skillModel.categoryFilter ? "Category: " + AppController.skillModel.categoryFilter : "", clear: function() { AppController.setViewFilter("category", "") } }
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
            color: Theme.accent + "10" // Subtle accent background
            radius: Theme.radiusCard
            border.color: Theme.accent + "30"
            border.width: 1
            clip: true
            
            RowLayout {
                id: qcv_selectionLayout
                anchors.fill: parent
                anchors.margins: 12
                spacing: 12
                // LEFT: Toggle All
                Button {
                    id: qcv_toggleAllBtn
                    Layout.preferredWidth: 32
                    Layout.preferredHeight: 32
                    flat: true
                    onClicked: (mouse) => AppController.skillModel.toggleAll()
                    contentItem: Image {
                        source: AppController.skillModel.isAllExpanded ? AppController.getAssetUri("ui/collapse.svg") : AppController.getAssetUri("ui/expand.svg")
                        sourceSize.width: 18
                        sourceSize.height: 18
                        fillMode: Image.PreserveAspectFit
                        opacity: qcv_toggleAllBtn.hovered ? 1.0 : 0.7
                        horizontalAlignment: Image.AlignHCenter
                        verticalAlignment: Image.AlignVCenter
                    }
                    background: Rectangle {
                        radius: Theme.radiusSmall
                        color: qcv_toggleAllBtn.hovered ? Theme.glassPill : "transparent"
                    }
                    ToolTip.visible: hovered
                    ToolTip.text: AppController.skillModel.isAllExpanded ? "Collapse All" : "Expand All"
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
                    visible: AppController.skillModel.selectedCount > 0
                    
                    Rectangle {
                        width: 28
                        height: 28
                        radius: Theme.radiusPill
                        color: Theme.accent
                        Text {
                            anchors.centerIn: parent
                            text: AppController.skillModel.selectedCount
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
                            onClicked: (mouse) => qcv_commandDialog.openWithContext(AppController.skillModel.projectFilter, AppController.clientFormat)
                        }

                        ActionButton {
                            id: barSelectAllBtn
                            labelText: "Select All"
                            role: "secondary"
                            visible: AppController.skillModel.selectedCount < AppController.skillModel.rowCount()
                            onClicked: (mouse) => AppController.skillModel.selectAll()
                        }

                        // Selection-specific actions
                        RowLayout {
                            spacing: 8
                            visible: AppController.skillModel.selectedCount > 0
                            
                            ActionButton {
                                id: barClearBtn
                                labelText: "Clear Selection"
                                role: "secondary"
                                onClicked: (mouse) => AppController.skillModel.clearSelection()
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
                                onClicked: (mouse) => qcv_deleteConfirmDialog.confirmBulk(AppController.skillModel.selectedCount, () => AppController.deleteSelectedSkills())
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
                                onClicked: (mouse) => AppController.copySelectedSkillsToClipboard()
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

                        Button {
                            id: qcv_saveColBtn
                            Layout.preferredWidth: 36
                            Layout.preferredHeight: 36
                            flat: true
                            onClicked: (mouse) => {
                                AppController.saveCustomCollection(qcv_root.editingCollectionName, AppController.skillModel.getSelectedPaths())
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
                                color: qcv_saveColBtn.hovered ? Theme.success + "20" : "transparent"
                            }
                        }

                        Button {
                            id: qcv_cancelColBtn
                            Layout.preferredWidth: 36
                            Layout.preferredHeight: 36
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
                                color: qcv_cancelColBtn.hovered ? Theme.danger + "20" : "transparent"
                            }
                        }
                    }
                }
            }
        }

        // Main Content Area
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0

            // Skill List
            ListView {
                id: qcv_skillList
                objectName: "quickCopyList"
                Layout.fillWidth: true
                Layout.fillHeight: true
                model: AppController.skillModel
                clip: true
                spacing: 0
                
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
                        AppController.skillModel.toggleSelection(index)
                    }
                    onDoubleClicked: (mouse) => {
                        AppController.selectSkill(index)
                    }
                    onRightClicked: {
                        AppController.selectSkill(index)
                    }
                    onDeleteRequested: (name, path) => {
                        qcv_deleteConfirmDialog.confirmSingle(name, () => AppController.deleteSkill(path))
                    }
                }

                ScrollBar.vertical: ScrollBar {
                    active: true
                }
            }

            // Overlay Inspector
            SkillInspector {
                id: qcv_inspector
                Layout.fillHeight: true
                Layout.preferredWidth: qcv_inspector.targetWidth
                skill: AppController.selectedSkill
                isQuickCopy: true
                visible: qcv_inspector.targetWidth > 0
                
                Behavior on Layout.preferredWidth {
                    NumberAnimation { duration: 250; easing.type: Easing.OutQuad }
                }

                onClosed: AppController.selectSkill(-1)
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

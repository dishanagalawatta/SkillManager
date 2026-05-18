import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import App 1.0
import SkillManagerComponents 1.0
import ".."

Item {
    id: lv_root

    function focusSearch() {
        lv_searchInput.forceActiveFocus()
        lv_searchInput.selectAll()
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
                    let idx = model.indexOf(AppController.skillModel.categoryFilter);
                    return idx === -1 ? 0 : idx;
                }
                onActivated: (index) => {
                    let cat = index === 0 ? "" : currentText
                    AppController.setViewFilter("category", cat)
                }
            }

            GlassSearchInput {
                id: lv_searchInput
                Layout.preferredWidth: 250
                onTextChanged: AppController.skillModel.filterText = text
            }

            GlassToggleButton {
                text: "Show Archived"
                checked: AppController.skillModel.showArchived
                onClicked: (mouse) => AppController.skillModel.showArchived = checked
                
                iconInactive: "📁"
                iconActive: "📦"
                textActive: "Showing Archived"
            }

        }

        Flow {
            Layout.fillWidth: true
            spacing: 8
            visible: lv_searchInput.text !== "" || AppController.skillModel.categoryFilter !== "" || AppController.skillModel.projectFilter !== ""

            Repeater {
                model: [
                    { label: lv_searchInput.text ? "Search: " + lv_searchInput.text : "", clear: function() { lv_searchInput.text = ""; AppController.skillModel.filterText = "" } },
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
        
        // Multi-select Action Bar
        Rectangle {
            id: selectionBar
            Layout.fillWidth: true
            Layout.preferredHeight: 64
            Layout.leftMargin: 4
            Layout.rightMargin: 4
            visible: true
            color: Theme.accent + "10"
            radius: Theme.radiusCard
            border.color: Theme.accent + "30"
            border.width: 1
            clip: true
            
            RowLayout {
                id: lv_selectionLayout
                anchors.fill: parent
                anchors.margins: 12
                spacing: 12
                // LEFT: Toggle All
                Button {
                    id: lv_toggleAllBtn
                    Layout.preferredWidth: 32
                    Layout.preferredHeight: 32
                    flat: true
                    onClicked: (mouse) => AppController.skillModel.toggleAll()
                    contentItem: Image {
                        source: AppController.skillModel.isAllExpanded ? AppController.getAssetUri("ui/collapse.svg") : AppController.getAssetUri("ui/expand.svg")
                        sourceSize.width: 18
                        sourceSize.height: 18
                        fillMode: Image.PreserveAspectFit
                        opacity: lv_toggleAllBtn.hovered ? 1.0 : 0.7
                        horizontalAlignment: Image.AlignHCenter
                        verticalAlignment: Image.AlignVCenter
                    }
                    background: Rectangle {
                        radius: Theme.radiusSmall
                        color: lv_toggleAllBtn.hovered ? Theme.glassPill : "transparent"
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

                // LEFT: Selection Count
                RowLayout {
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
                    spacing: 8
                    
                    // Always Visible Actions
                    ActionButton {
                        id: lv_addCommandBtn
                        labelText: "Add Command"
                        iconText: "+"
                        role: "secondary"
                        onClicked: (mouse) => lv_commandDialog.openWithContext(AppController.skillModel.projectFilter, AppController.clientFormat)
                    }

                    ActionButton {
                        id: lv_selectAllBtn
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
                            id: lv_clearBtn
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

                        GlassDropdown {
                            id: lv_projectDrop
                            Layout.preferredHeight: 36
                            Layout.preferredWidth: 160
                            model: AppController.projectLabels
                            enabled: AppController.projects.length > 0
                        }
                        
                        ActionButton {
                            id: lv_tempCopyBtn
                            labelText: "Copy Temporarily"
                            role: "secondary"
                            enabled: AppController.projects.length > 0
                            tooltipText: enabled ? "Copies selected skills to the project temporarily. They will be deleted when you close this app." : "Add a project in Updates before copying skills."
                            onClicked: (mouse) => {
                                if (lv_projectDrop.currentIndex >= 0 && lv_projectDrop.currentIndex < AppController.projects.length) {
                                    let path = AppController.projects[lv_projectDrop.currentIndex]
                                    AppController.copySelectedSkillsToProjectTemporarily(path)
                                }
                            }
                        }

                        ActionButton {
                            id: lv_deleteBtn
                            labelText: "Delete Selected"
                            iconText: "🗑️"
                            role: "destructive"
                            onClicked: (mouse) => lv_deleteConfirmDialog.confirmBulk(AppController.skillModel.selectedCount, () => AppController.deleteSelectedSkills())
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
                                    AppController.copySelectedSkillsToProject(path)
                                }
                            }
                        }
                    }
                }
            }
        }

        // Library Content (Placeholder for now)
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 20

            // Skill List
            ListView {
                id: lv_listView
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.preferredWidth: 400
                model: AppController.skillModel
                clip: true
                spacing: 0
                
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
                        AppController.skillModel.toggleSelection(index)
                    }
                    onDoubleClicked: (mouse) => {
                        AppController.selectSkill(index)
                    }
                    onRightClicked: {
                        AppController.selectSkill(index)
                    }
                    onDeleteRequested: (name, path) => {
                        lv_deleteConfirmDialog.confirmSingle(name, () => AppController.deleteSkill(path))
                    }
                }
            }

            // Inspector Pane
            SkillInspector {
                id: lv_inspector
                Layout.fillHeight: true
                Layout.preferredWidth: lv_inspector.targetWidth
                skill: AppController.selectedSkill
                visible: lv_inspector.targetWidth > 0

                Behavior on Layout.preferredWidth {
                    NumberAnimation { duration: 250; easing.type: Easing.OutQuad }
                }

                onClosed: AppController.selectSkill(-1)
            }
        }
    }

    CommandCreateDialog {
        id: lv_commandDialog
    }

    DeleteConfirmDialog {
        id: lv_deleteConfirmDialog
    }
}

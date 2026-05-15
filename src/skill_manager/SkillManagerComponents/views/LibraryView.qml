import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import App 1.0
import SkillManagerComponents 1.0
import ".."

Item {
    id: lv_root
    
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
                Layout.preferredWidth: 250
                onTextChanged: AppController.skillModel.filterText = text
            }

            GlassToggleButton {
                text: "Show Archived"
                checked: AppController.skillModel.showArchived
                onClicked: AppController.skillModel.showArchived = checked
                
                iconInactive: "📁"
                iconActive: "📦"
                textActive: "Showing Archived"
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
                    onClicked: AppController.skillModel.toggleAll()
                    contentItem: Image {
                        source: AppController.skillModel.isAllExpanded ? AppController.getAssetUri("button/collapse.svg") : AppController.getAssetUri("button/expand.svg")
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
                    Button {
                        id: lv_addCommandBtn
                        Layout.preferredHeight: 36
                        onClicked: lv_commandDialog.openWithContext(AppController.skillModel.projectFilter, AppController.clientFormat)
                        contentItem: RowLayout {
                            spacing: 6
                            Text { text: "+"; font.pixelSize: 16; color: "white"; font.weight: Font.Bold }
                            Text {
                                text: "Add Command"
                                font.family: Theme.fontFamily
                                font.pixelSize: 12
                                font.weight: Font.Bold
                                color: "white"
                            }
                        }
                        background: Rectangle {
                            implicitWidth: 120
                            radius: Theme.radiusField
                            color: lv_addCommandBtn.pressed ? Theme.accent : (lv_addCommandBtn.hovered ? Theme.accent + "DD" : Theme.accent)
                        }
                    }

                    Button {
                        id: lv_selectAllBtn
                        Layout.preferredHeight: 36
                        visible: AppController.skillModel.selectedCount < AppController.skillModel.rowCount()
                        onClicked: AppController.skillModel.selectAll()
                        contentItem: Text {
                            text: "Select All"
                            font.family: Theme.fontFamily
                            font.pixelSize: 12
                            font.weight: Font.DemiBold
                            color: Theme.accent
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }
                        background: Rectangle {
                            implicitWidth: 90
                            radius: Theme.radiusField
                            color: lv_selectAllBtn.hovered ? Theme.accent + "15" : "transparent"
                            border.color: lv_selectAllBtn.hovered ? Theme.accent + "40" : "transparent"
                            border.width: 1
                        }
                    }

                    // Selection-specific actions
                    RowLayout {
                        spacing: 8
                        visible: AppController.skillModel.selectedCount > 0
                        
                        Button {
                            id: lv_clearBtn
                            Layout.preferredHeight: 36
                            onClicked: AppController.skillModel.clearSelection()
                            contentItem: Text {
                                text: "Clear Selection"
                                font.family: Theme.fontFamily
                                font.pixelSize: 12
                                color: Theme.secondaryLabel
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                            }
                            background: Rectangle {
                                implicitWidth: 110
                                radius: Theme.radiusField
                                color: lv_clearBtn.hovered ? Theme.glassHover : "transparent"
                                border.color: lv_clearBtn.hovered ? Theme.glassBorder : "transparent"
                                border.width: 1
                            }
                        }

                        Rectangle {
                            width: 1
                            height: 20
                            color: Theme.separator
                            Layout.leftMargin: 4
                            Layout.rightMargin: 4
                        }

                        GlassDropdown {
                            id: lv_targetDrop
                            Layout.preferredHeight: 36
                            Layout.preferredWidth: 160
                            model: AppController.targetLabels
                        }
                        
                        Button {
                            id: lv_copyBtn
                            Layout.preferredHeight: 36
                            onClicked: {
                                if (lv_targetDrop.currentIndex >= 0 && lv_targetDrop.currentIndex < AppController.targets.length) {
                                    let path = AppController.targets[lv_targetDrop.currentIndex]
                                    AppController.copySelectedSkillsToTarget(path)
                                }
                            }
                            contentItem: Text {
                                text: "Copy to Project"
                                color: "white"
                                font.family: Theme.fontFamily
                                font.pixelSize: 12
                                font.weight: Font.Bold
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                            }
                            background: Rectangle {
                                implicitWidth: 120
                                radius: Theme.radiusField
                                color: lv_copyBtn.pressed ? Theme.accent : (lv_copyBtn.hovered ? Theme.accent + "EE" : Theme.accent)
                            }
                        }

                        Button {
                            id: lv_deleteBtn
                            Layout.preferredHeight: 36
                            onClicked: AppController.deleteSelectedSkills()
                            contentItem: RowLayout {
                                spacing: 4
                                Text { text: "🗑️"; font.pixelSize: 14; verticalAlignment: Text.AlignVCenter }
                                Text {
                                    text: "Delete Selected"
                                    font.family: Theme.fontFamily
                                    font.pixelSize: 12
                                    color: Theme.danger
                                    font.weight: Font.DemiBold
                                }
                            }
                            background: Rectangle {
                                implicitWidth: 130
                                radius: Theme.radiusField
                                color: lv_deleteBtn.hovered ? Theme.danger + "15" : "transparent"
                                border.color: lv_deleteBtn.hovered ? Theme.danger + "30" : "transparent"
                                border.width: lv_deleteBtn.hovered ? 1 : 0
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
                
                section.property: "sectionName"
                section.criteria: ViewSection.FullString
                section.delegate: CategoryHeader {
                    sectionName: section
                    width: lv_listView.width
                }
                delegate: SkillItem {
                    width: lv_listView.width
                    isSelected: AppController.selectedSkill.local_path === model.path
                    showEssentialIcon: false
                    onClicked: {
                        AppController.selectSkill(index)
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
}

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
            
            Button {
                Layout.preferredWidth: 32
                Layout.preferredHeight: 32
                flat: true
                onClicked: AppController.skillModel.toggleAll()
                contentItem: Text {
                    text: AppController.skillModel.isAllExpanded ? "⤒" : "⤓"
                    font.pixelSize: 20
                    color: Theme.accent
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    opacity: 0.8
                }
                ToolTip.visible: hovered
                ToolTip.text: AppController.skillModel.isAllExpanded ? "Collapse All" : "Expand All"
            }

            GlassDropdown {
                id: lv_categoryDrop
                model: ["All Categories"].concat(AppController.categories)
                currentIndex: {
                    let idx = model.indexOf(AppController.skillModel.categoryFilter);
                    return idx === -1 ? 0 : idx;
                }
                onActivated: {
                    let cat = currentIndex === 0 ? "" : currentText
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
        RowLayout {
            Layout.fillWidth: true
            Layout.leftMargin: 4
            Layout.rightMargin: 4
            visible: AppController.skillModel.selectedCount > 0
            
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 50
                radius: Theme.radiusCard
                color: Theme.glassPill
                border.color: Theme.accent + "44"
                border.width: 1
                
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 16
                    anchors.rightMargin: 16
                    spacing: 12
                    
                    Text {
                        text: "📦  <b>" + AppController.skillModel.selectedCount + "</b> skills selected"
                        font.family: Theme.fontFamily
                        font.pixelSize: 14
                        color: Theme.label
                    }
                    
                    Button {
                        id: lv_clearBtn
                        text: "Clear"
                        flat: true
                        onClicked: AppController.skillModel.clearSelection()
                        contentItem: Text {
                            text: "Clear"
                            color: lv_clearBtn.hovered ? Theme.label : Theme.secondaryLabel
                            font.family: Theme.fontFamily
                            font.pixelSize: 13
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }
                    }
                    
                    Item { Layout.fillWidth: true }
                    
                    Text {
                        text: "Copy to Project:"
                        font.family: Theme.fontFamily
                        font.pixelSize: 13
                        color: Theme.secondaryLabel
                    }
                    
                    GlassDropdown {
                        id: lv_targetDrop
                        Layout.preferredWidth: 200
                        model: AppController.targetLabels
                        currentIndex: 0
                    }
                    
                    Button {
                        id: lv_copyBtn
                        Layout.preferredHeight: 32
                        Layout.preferredWidth: 120
                        onClicked: {
                            if (lv_targetDrop.currentIndex >= 0 && lv_targetDrop.currentIndex < AppController.targets.length) {
                                let path = AppController.targets[lv_targetDrop.currentIndex]
                                AppController.copySelectedSkillsToTarget(path)
                            }
                        }
                        contentItem: Text {
                            text: "Copy Skills"
                            color: "white"
                            font.family: Theme.fontFamily
                            font.pixelSize: 13
                            font.weight: Font.Bold
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }
                        background: Rectangle {
                            radius: Theme.radiusButton
                            color: lv_copyBtn.pressed ? Theme.accent : (lv_copyBtn.hovered ? Theme.accent + "EE" : Theme.accent)
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
                spacing: 2
                
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
}

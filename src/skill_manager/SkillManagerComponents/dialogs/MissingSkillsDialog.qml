/**
 * Purpose: Dialog for handling missing skills when saving a collection.
 * Shows which skills are missing from selected projects and offers copy options.
 */
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import ".."
import App 1.0

Dialog {
    id: root
    
    property string collectionName: ""
    property var missingSkills: ({})
    property var selectedProjects: []
    property var currentCallback: null
    
    x: (parent.width - width) / 2
    y: (parent.height - height) / 2
    width: 500
    modal: true
    padding: 0
    
    background: Rectangle {
        color: Theme.glassPill
        radius: Theme.radiusCard
        border.color: Theme.glassBorder
        border.width: 1
        
        layer.enabled: true
        layer.effect: DropShadow {
            radius: 20
            color: Theme.glassShadow
            verticalOffset: 8
            horizontalOffset: 0
        }
    }

    function openWithMissing(name, missing) {
        collectionName = name
        missingSkills = missing
        selectedProjects = Object.keys(missing)
        projectCheckModel.clear()
        for (let i = 0; i < selectedProjects.length; i++) {
            projectCheckModel.append({
                project: selectedProjects[i],
                skills: missing[selectedProjects[i]],
                checked: true
            })
        }
        open()
    }

    function getCheckedProjects() {
        var result = []
        for (var i = 0; i < projectCheckModel.count; i++) {
            var item = projectCheckModel.get(i)
            if (item.checked) {
                result.push(item.project)
            }
        }
        return result
    }

    ListModel {
        id: projectCheckModel
    }

    contentItem: ColumnLayout {
        spacing: 0
        
        // Header
        Rectangle {
            Layout.fillWidth: true
            height: 60
            color: "transparent"
            
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 24
                anchors.rightMargin: 16
                spacing: 12
                
                Text {
                    text: "⚠️"
                    font.pixelSize: 20
                }
                
                Text {
                    text: "Missing Skills Detected"
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.sizeSectionTitle
                    font.weight: Font.Bold
                    color: Theme.label
                    Layout.fillWidth: true
                }
                
                IconButton {
                    text: "✕"
                    flat: true
                    Layout.preferredWidth: 32
                    Layout.preferredHeight: 32
                    onClicked: root.reject()
                    
                    background: Rectangle {
                        radius: 16
                        color: parent.hovered ? Theme.glassHover : "transparent"
                    }
                    
                    contentItem: Text {
                        text: parent.text
                        font.pixelSize: 16
                        color: Theme.secondaryLabel
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                }
            }
            
            Rectangle {
                anchors.bottom: parent.bottom
                width: parent.width
                height: 1
                color: Theme.separator
            }
        }
        
        // Content
        ColumnLayout {
            Layout.fillWidth: true
            Layout.margins: 24
            spacing: 16
            
            Text {
                text: "Some skills in collection \"" + root.collectionName + "\" are not present in the selected projects."
                font.family: Theme.fontFamily
                font.pixelSize: Theme.sizeBody
                color: Theme.label
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }

            // Project list with missing skills
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: Math.min(projectCheckModel.count * 80 + 20, 250)
                radius: Theme.radiusField
                color: Theme.glassHover
                border.color: Theme.glassBorder

                SmoothListView {
                    anchors.fill: parent
                    anchors.margins: 8
                    clip: true
                    model: projectCheckModel

                    delegate: Rectangle {
                        width: parent.width
                        height: 70
                        color: "transparent"

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 8
                            spacing: 4

                            RowLayout {
                                spacing: 8
                                GlassCheckBox {
                                    id: projectCheck
                                    Layout.preferredWidth: 20
                                    Layout.preferredHeight: 20
                                    checkState: model.checked ? Qt.Checked : Qt.Unchecked
                                    iconSize: 9
                                    onToggled: {
                                        projectCheckModel.setProperty(index, "checked", checkState !== Qt.Checked)
                                    }
                                }
                                Text {
                                    text: model.project
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.sizeBody
                                    font.weight: Font.DemiBold
                                    color: Theme.label
                                    Layout.fillWidth: true
                                }
                            }

                            Text {
                                text: model.skills.length + " skill(s) missing"
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.sizeMetadata
                                color: Theme.secondaryLabel
                                Layout.leftMargin: 28
                            }
                        }
                    }
                }
            }
        }
        
        // Footer
        Rectangle {
            Layout.fillWidth: true
            height: 80
            color: "transparent"
            
            RowLayout {
                anchors.fill: parent
                anchors.margins: 24
                spacing: 12
                
                Item { Layout.fillWidth: true }
                
                ActionButton {
                    text: "Skip"
                    Layout.preferredWidth: 80
                    Layout.preferredHeight: 40
                    onClicked: root.reject()
                    
                    background: Rectangle {
                        radius: Theme.radiusButton
                        color: parent.hovered ? Theme.glassHover : "transparent"
                        border.color: Theme.glassBorder
                    }
                    
                    contentItem: Text {
                        text: parent.text
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.sizeBody
                        font.weight: Font.Medium
                        color: Theme.label
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                }

                ActionButton {
                    text: "Don't Associate"
                    Layout.preferredWidth: 130
                    Layout.preferredHeight: 40
                    onClicked: {
                        if (root.currentCallback) {
                            root.currentCallback("remove_projects", [])
                        }
                        root.accept()
                    }
                    
                    background: Rectangle {
                        radius: Theme.radiusButton
                        color: parent.hovered ? Theme.glassHover : "transparent"
                        border.color: Theme.danger
                        border.width: 1
                    }
                    
                    contentItem: Text {
                        text: parent.text
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.sizeBody
                        font.weight: Font.Medium
                        color: Theme.danger
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                }
                
                ActionButton {
                    text: "Copy Missing"
                    Layout.preferredWidth: 120
                    Layout.preferredHeight: 40
                    onClicked: {
                        let checkedProjects = root.getCheckedProjects()
                        if (root.currentCallback) {
                            root.currentCallback("copy", checkedProjects)
                        }
                        root.accept()
                    }
                    
                    background: Rectangle {
                        radius: Theme.radiusButton
                        color: parent.down ? Theme.accent : (parent.hovered ? Theme.alpha(Theme.accent, 0.93) : Theme.accent)
                    }
                    
                    contentItem: Text {
                        text: parent.text
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.sizeBody
                        font.weight: Font.Bold
                        color: "white"
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                }
            }
        }
    }
}

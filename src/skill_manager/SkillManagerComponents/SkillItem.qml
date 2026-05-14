import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import App 1.0
import SkillManagerComponents 1.0

Item {
    id: root
    width: parent.width
    height: model && model.isCollapsed ? 0 : 64
    visible: model ? !model.isCollapsed : true
    clip: true
    
    Behavior on height {
        NumberAnimation { duration: 200; easing.type: Easing.OutQuad }
    }
    
    MouseArea {
        id: mouseArea
        anchors.fill: parent
        hoverEnabled: true
        onClicked: root.clicked()
        onDoubleClicked: root.doubleClicked()
    }
    
    property bool isSelected: model && model.isSelected !== undefined ? model.isSelected : false
    property bool showEssentialIcon: true
    
    signal clicked()
    signal doubleClicked()

    Rectangle {
        id: bg
        anchors.fill: parent
        anchors.margins: 4
        radius: Theme.radiusCard
        color: root.isSelected ? Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.3) : (mouseArea.containsMouse ? Theme.glassHover : "transparent")
        border.width: (mouseArea.containsMouse || root.isSelected) ? 1 : 0
        border.color: root.isSelected ? Theme.accent : Theme.glassOuterBorder
        opacity: model && model.isArchived ? 0.5 : 1.0

        // Inner glow/highlight border (Removed for solid matte)
        Item { anchors.fill: parent }
        
        Behavior on color { ColorAnimation { duration: 150 } }
        
        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 8
            anchors.rightMargin: 12
            spacing: 8

            // Multi-select Checkbox
            Rectangle {
                width: 20
                height: 20
                radius: Theme.radiusSmall
                color: model && model.isSelected ? Theme.accent : "transparent"
                border.width: model && model.isSelected ? 0 : 1
                border.color: Theme.glassBorder
                
                Text {
                    anchors.centerIn: parent
                    text: "✓"
                    color: "white"
                    font.pixelSize: 12
                    visible: model && model.isSelected
                }
                
                MouseArea {
                    anchors.fill: parent
                    onClicked: AppController.skillModel.toggleSelection(index)
                }
            }

            // Icon Section
            Rectangle {
                width: 36
                height: 36
                radius: Theme.radiusField
                color: model && model.isEssential ? Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.3) : (model && model.isCollection ? (Theme.darkMode ? "#2D3833" : "#F3F4F6") : (model && model.isCommand ? Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.2) : Theme.glassPill))
                
                Text {
                    anchors.centerIn: parent
                    text: model ? ((model.isEssential && root.showEssentialIcon) ? "★" : (model.isCollection ? "📦" : (model.isCommand ? "⚡" : model.name.charAt(0).toUpperCase()))) : ""
                    font.family: Theme.fontFamily
                    font.pixelSize: model && (model.isEssential && root.showEssentialIcon || model.isCollection || model.isCommand) ? 18 : 14
                    font.weight: Font.Bold
                    color: model && (model.isEssential && root.showEssentialIcon || model.isCommand) ? Theme.accent : Theme.label
                }
            }

            // Text Info
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 0
                
                Text {
                    text: model ? model.name : ""
                    font.family: Theme.fontFamily
                    font.pixelSize: 14
                    font.weight: Font.DemiBold
                    color: Theme.label
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }
                
                Text {
                    text: model ? ((model.isCommand ? "Command • " : (model.isCollection ? "Collection • " : "")) + model.project + " • " + model.category) : ""
                    font.family: Theme.fontFamily
                    font.pixelSize: 11
                    color: Theme.secondaryLabel
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }
            }

            // Selection indicator for Inspector
            Rectangle {
                width: 4
                height: 24
                radius: Theme.radiusSmall
                color: Theme.accent
                visible: root.isSelected
            }

            // Delete Button
            Button {
                id: deleteBtn
                Layout.preferredWidth: 32
                Layout.preferredHeight: 32
                flat: true
                visible: mouseArea.containsMouse
                onClicked: {
                    if (model && model.path) {
                        Qt.callLater(AppController.deleteSkill, model.path)
                    }
                }
                contentItem: Text {
                    text: "🗑️"
                    font.pixelSize: 14
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    opacity: deleteBtn.hovered ? 1.0 : 0.6
                }
                background: Rectangle {
                    radius: Theme.radiusButton
                    color: deleteBtn.hovered ? Theme.glassHover : "transparent"
                    border.width: deleteBtn.hovered ? 1 : 0
                    border.color: Theme.glassBorder
                }
                ToolTip.visible: hovered
                ToolTip.text: "Delete " + (model && (model.isCommand === true) ? "Command" : "Skill")
            }
        }
    }
}

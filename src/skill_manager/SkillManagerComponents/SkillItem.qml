import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import App 1.0

Item {
    id: root
    objectName: "skillItemDelegate"
    width: parent.width

    // Model properties
    property string mainCat: model && model.mainCategoryName ? model.mainCategoryName : ""
    property string subCat: model && model.subCategoryName ? model.subCategoryName : ""
    property bool isMainCollapsed: model && model.isMainCollapsed !== undefined ? model.isMainCollapsed : false
    property bool isSubCollapsed: model && model.isSubCollapsed !== undefined ? model.isSubCollapsed : false
    property bool compactRows: AppController.ui_controller ? AppController.ui_controller.compactListRows : false

    // Provided by SkillModel to avoid per-row previous-item lookups during scrolling.
    property bool isFirstInSub: model && model.isFirstInSubcategory !== undefined ? model.isFirstInSubcategory : false

    // Dynamic height based on visibility of sub-header and item content
    height: isMainCollapsed ? 0 : (isFirstInSub ? 34 : 0) + (isSubCollapsed ? 0 : (compactRows ? 32 : 54))
    visible: height > 0
    clip: true

    Column {
        width: parent.width
        anchors.top: parent.top

        // --- SUB CATEGORY HEADER ---
        Item {
            id: subHeader
            width: parent.width
            height: 34
            visible: root.isFirstInSub && !root.isMainCollapsed

            Rectangle {
                anchors.fill: parent
                color: mouseAreaSub.containsMouse ? Theme.glassHover : "transparent"
                radius: Theme.radiusSmall
                anchors.leftMargin: 24 // Start Level 1 Background
                anchors.rightMargin: 2
                anchors.topMargin: 2
                anchors.bottomMargin: 2
            }

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 36 // Level 1 Indent
                anchors.rightMargin: 12
                spacing: 6

                Image {
                    source: root.isSubCollapsed ?
                            AppController.ui_controller.getAssetUri(Theme.darkMode ? "ui/expand-arrow-icon-dark.svg" : "ui/expand-arrow-icon-light.svg") :
                            AppController.ui_controller.getAssetUri(Theme.darkMode ? "ui/collapse-arrow-icon-dark.svg" : "ui/collapse-arrow-icon-light.svg")
                    width: 10
                    height: 10
                    Layout.preferredWidth: 10
                    Layout.preferredHeight: 10
                    Layout.alignment: Qt.AlignVCenter
                    sourceSize.width: 40
                    sourceSize.height: 40
                    fillMode: Image.PreserveAspectFit
                    opacity: 0.5
                    horizontalAlignment: Image.AlignHCenter
                    verticalAlignment: Image.AlignHCenter
                }
                
                Text {
                    text: root.subCat ? AppController.getCategoryEmoji(root.subCat) : ""
                    font.pixelSize: 14
                    opacity: root.isSubCollapsed ? 0.6 : 1.0
                    Layout.alignment: Qt.AlignVCenter
                }

                Text {
                    Layout.fillWidth: true
                    text: root.subCat || ""
                    font.family: Theme.fontFamily
                    font.pixelSize: 12
                    font.weight: Font.DemiBold
                    color: Theme.secondaryLabel
                    opacity: 0.8
                }
            }

            MouseArea {
                id: mouseAreaSub
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: (mouse) => Qt.callLater(AppController.skillModel.toggleCategory, model && model.sectionName ? model.sectionName : "")

                SleekToolTip {
                    id: subCatToolTip
                    text: root.isSubCollapsed ? "Expand " + root.subCat : "Collapse " + root.subCat
                    visible: mouseAreaSub.containsMouse
                }

                Accessible.role: Accessible.Button
                Accessible.name: root.subCat
                Accessible.description: subCatToolTip.text
            }
        }

        // --- SKILL ITEM CONTENT ---
        Item {
            width: parent.width
            height: root.compactRows ? 32 : 54
            visible: !root.isMainCollapsed && !root.isSubCollapsed

            Rectangle {
                id: bg
                anchors.fill: parent
                anchors.leftMargin: 48 // Start Level 2 Background
                anchors.rightMargin: 5
                anchors.topMargin: root.compactRows ? 2 : 4
                anchors.bottomMargin: root.compactRows ? 2 : 4
                radius: Theme.radiusCard
                color: root.isSelected ? (mouseArea.containsMouse ? Theme.selectedRowHover : Theme.selectedRow) : (mouseArea.containsMouse ? Theme.glassHover : "transparent")
                border.width: (mouseArea.containsMouse || root.isSelected) ? 1 : 0
                border.color: root.isSelected ? Theme.selectedRowBorder : Theme.glassOuterBorder
                opacity: model && model.isArchived ? 0.5 : 1.0

                Behavior on color { ColorAnimation { duration: 150 } }

                MouseArea {
                    id: mouseArea
                    anchors.fill: parent
                    hoverEnabled: true
                    acceptedButtons: Qt.LeftButton | Qt.RightButton
                    onClicked: (mouse) => {
                        if (mouse.button === Qt.RightButton) {
                            root.rightClicked()
                        } else {
                            root.clicked()
                        }
                    }
                    onDoubleClicked: (mouse) => root.doubleClicked()

                    Accessible.role: Accessible.Button
                    Accessible.name: (model && model.name ? model.name : "Item")
                    Accessible.description: "Skill item"

                    Loader {
                        active: mouseArea.containsMouse && model && model.isScreenshot && model.path
                        asynchronous: false
                        sourceComponent: ToolTip {
                            id: screenshotTooltip
                            visible: true
                            delay: 450
                            timeout: 8000
                            padding: 8
                            x: mouseArea.mouseX + 15
                            y: mouseArea.mouseY + 15

                            background: Rectangle {
                                color: Theme.glassActive
                                radius: Theme.radiusSmall
                                border.color: Theme.glassOuterBorder
                                border.width: 1
                            }

                            contentItem: Item {
                                property real maxW: 400
                                property real maxH: 400
                                property real minW: 100
                                property real minH: 100
                                
                                property real scaleFactor: previewImg.status === Image.Ready ? Math.min(1.0, maxW / Math.max(1, previewImg.implicitWidth), maxH / Math.max(1, previewImg.implicitHeight)) : 1.0
                                
                                implicitWidth: previewImg.status === Image.Ready ? Math.max(minW, previewImg.implicitWidth * scaleFactor) : minW
                                implicitHeight: previewImg.status === Image.Ready ? Math.max(minH, previewImg.implicitHeight * scaleFactor) : minH
                                
                                Image {
                                    id: previewImg
                                    anchors.fill: parent
                                    source: (model && model.isScreenshot && model.path) ? "file:///" + model.path.replace(/\\/g, "/") : ""
                                    fillMode: Image.PreserveAspectFit
                                    asynchronous: false
                                    // Setting only width preserves the original aspect ratio for the pixmap
                                    sourceSize.width: 600 
                                }
                            }
                        }
                    }

                    Loader {
                        id: textPreviewLoader
                        property string previewText: {
                            if (!model) return "";
                            if (model.isCommand && model.bodyContent) {
                                let lines = model.bodyContent.split('\n');
                                let truncated = lines.slice(0, 5).join('\n');
                                if (lines.length > 5 || truncated.length > 180) {
                                    return truncated.substring(0, 180).trim() + '\n...';
                                }
                                return truncated;
                            } else if (!model.isScreenshot && !model.isCommand && !model.isCollection && model.description) {
                                if (model.description.length > 180) {
                                    return model.description.substring(0, 180).trim() + '...';
                                }
                                return model.description;
                            }
                            return "";
                        }
                        
                        active: mouseArea.containsMouse && previewText.length > 0
                        asynchronous: false
                        sourceComponent: ToolTip {
                            id: textPreviewTooltip
                            visible: true
                            delay: 450
                            timeout: 8000
                            padding: 8
                            x: mouseArea.mouseX + 15
                            y: mouseArea.mouseY + 15

                            background: Rectangle {
                                color: Theme.glassActive
                                radius: Theme.radiusSmall
                                border.color: Theme.glassOuterBorder
                                border.width: 1
                            }

                            contentItem: Text {
                                id: textItem
                                text: textPreviewLoader.previewText
                                font.family: (model && model.isCommand) ? "Consolas, Monaco, Courier New, monospace" : Theme.fontFamily
                                font.pixelSize: 12
                                color: Theme.label
                                wrapMode: Text.Wrap
                                width: Math.min(implicitWidth, 280)
                                maximumLineCount: 8
                                elide: Text.ElideRight
                            }
                        }
                    }
                }

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 12// Level 2 Indent (Includes checkbox)
                    anchors.rightMargin: 12
                    spacing: 8

                    // Multi-select Checkbox
                    Rectangle {
                        width: root.compactRows ? 16 : 20
                        height: root.compactRows ? 16 : 20
                        radius: Theme.radiusSmall
                        color: model && model.isSelected ? Theme.selectedRowBorder : "transparent"
                        border.width: model && model.isSelected ? 0 : 1
                        border.color: Theme.glassBorder
                        
                        Text {
                            anchors.centerIn: parent
                            text: "✓"
                            color: "white"
                            font.pixelSize: root.compactRows ? 10 : 12
                            visible: model && model.isSelected
                        }

                        MouseArea {
                            id: checkboxMouseArea
                            anchors.fill: parent
                            hoverEnabled: true
                            onClicked: (mouse) => AppController.skillModel.toggleSelection(index)
                            cursorShape: Qt.PointingHandCursor

                            SleekToolTip {
                                id: selToolTip
                                text: (model && model.isSelected) ? "Deselect" : "Select"
                                visible: checkboxMouseArea.containsMouse
                            }

                            Accessible.role: Accessible.CheckBox
                            Accessible.name: (model && model.isSelected) ? "Deselect " + (model && model.name ? model.name : "Item") : "Select " + (model && model.name ? model.name : "Item")
                        }
                    }

                    // Icon Section
                    Rectangle {
                        width: root.compactRows ? 22 : 32
                        height: root.compactRows ? 22 : 32
                        radius: Theme.radiusField
                        color: model && model.isStarred ? Theme.selectedRow : (model && model.isCollection ? Theme.glassActive : (model && model.isCommand ? Theme.glassHover : Theme.glassPill))
                        
                        Text {
                            anchors.centerIn: parent
                            text: {
                                if (!model) return ""
                                if (model.isStarred && root.showStarredIcon) return "★"
                                if (model.isCollection) return "📦"
                                if (model.isCommand) return "⚡"
                                if (model.isScreenshot) return "🖼️"
                                return AppController.getCategoryEmoji(model.category)
                            }
                            font.family: Theme.fontFamily
                            font.pixelSize: root.compactRows ? ((model && model.isStarred) ? 12 : 14) : ((model && model.isStarred) ? 16 : 18)
                            font.weight: Font.Bold
                            color: (model && (model.isStarred || model.isCommand)) ? Theme.accent : Theme.label
                        }
                    }

                    // Text Info
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 0
                        
                        Text {
                            text: model ? model.name : ""
                            font.family: Theme.fontFamily
                            font.pixelSize: root.compactRows ? 11 : 14
                            font.weight: Font.DemiBold
                            color: Theme.label
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                        }
                        
                    }

                    // Selection indicator for Inspector
                    Rectangle {
                        width: 4
                        height: root.compactRows ? 16 : 24
                        radius: Theme.radiusSmall
                        color: Theme.selectedRowBorder
                        visible: root.isSelected
                    }

                    // Delete Button
                    IconButton {
                        id: deleteBtn
                        Layout.preferredWidth: 32
                        Layout.preferredHeight: 32
                        flat: true
                        visible: root.showInlineDelete && mouseArea.containsMouse
                        onClicked: (mouse) => {
                            if (model && model.path) {
                                root.deleteRequested(model.name, model.path)
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
                        SleekToolTip {
                            visible: parent.hovered
                            text: "Delete " + (model && (model.isCommand === true) ? "Command" : "Skill")
                        }
                    }
                }
            }
        }
    }

    property bool isSelected: model && model.isSelected !== undefined ? model.isSelected : false
    property bool showStarredIcon: true
    property bool showInlineDelete: true
    
    signal clicked()
    signal doubleClicked()
    signal rightClicked()
    signal deleteRequested(string name, string path)
    signal inspectImageRequested()
}

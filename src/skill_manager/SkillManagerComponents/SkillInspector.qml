import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import App 1.0
import SkillManagerComponents 1.0

Rectangle {
    id: root
    
    property var skill: ({})
    property bool isQuickCopy: false
    property bool isCollapsed: false
    
    // Calculate width based on selection and collapse state
    readonly property int targetWidth: {
        if (!root.skill || root.skill.id === undefined) return 0;
        if (isCollapsed) return 32;
        
        let dynamicWidth = parent ? parent.width * 0.5 : (isQuickCopy ? 350 : 400);
        return Math.min(800, Math.max(isQuickCopy ? 350 : 400, dynamicWidth));
    }

    function cleanBodyContent(content) {
        if (!content) return "";
        let lines = content.split('\n');
        let result = [];
        let skipPrefixes = ["Name:", "Description:", "Risk:", "Source:", "Date:", "date_added:"];
        
        for (let line of lines) {
            let trimmed = line.trim();
            if (!trimmed) {
                result.push(line);
                continue;
            }
            
            let shouldSkip = false;
            for (let prefix of skipPrefixes) {
                if (trimmed.toLowerCase().startsWith(prefix.toLowerCase())) {
                    shouldSkip = true;
                    break;
                }
            }
            if (shouldSkip) continue;
            
            // Skip the name header if it matches root.skill.name
            if (trimmed === "# " + root.skill.name || trimmed === "## " + root.skill.name) continue;
            
            result.push(line);
        }
        return result.join('\n').trim();
    }

    signal closed()

    radius: Theme.radiusCard
    color: Theme.glassPill
    border.color: Theme.glassBorder
    clip: true // Ensure content doesn't bleed out when collapsed
    
    ScrollView {
        id: mainScroll
        anchors.fill: parent
        anchors.margins: 4
        clip: true
        ScrollBar.vertical.policy: ScrollBar.AsNeeded
        
        ColumnLayout {
            width: mainScroll.width - 24
            x: 12
            y: 12
            spacing: 16
            visible: !root.isCollapsed && root.skill.id !== undefined
            opacity: visible ? 1.0 : 0.0
            
            Behavior on opacity { NumberAnimation { duration: 200 } }

            // Header
            RowLayout {
                Layout.fillWidth: true
                spacing: 8
                Text {
                    text: root.skill.name || "No Selection"
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.sizeSectionTitle
                    font.weight: Font.Bold
                    color: Theme.label
                    Layout.fillWidth: true
                    elide: Text.ElideRight
                }
                IconButton {
                    id: starButton
                    text: (root.skill && root.skill.is_starred) ? "★" : "☆"
                    flat: true
                    Layout.preferredWidth: 32
                    Layout.preferredHeight: 32
                    visible: root.skill && root.skill.id !== undefined
                    onClicked: (mouse) => AppController.toggleCurrentSkillStarred()
                    
                    contentItem: Text {
                        text: starButton.text
                        font.pixelSize: 22
                        color: (root.skill && root.skill.is_starred) ? "#FFD700" : Theme.secondaryLabel
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                        opacity: starButton.hovered ? 1.0 : 0.8
                        
                        Behavior on color { ColorAnimation { duration: 200 } }
                        Behavior on opacity { NumberAnimation { duration: 200 } }
                    }
                    
                    background: Rectangle {
                        color: starButton.hovered ? Theme.glassHover : "transparent"
                        radius: Theme.radiusPill
                    }
                    
                    ToolTip.visible: hovered
                    ToolTip.text: (root.skill && root.skill.is_starred) ? "Unstar Skill" : "Star Skill"
                }

                IconButton {
                    text: "✕"
                    flat: true
                    onClicked: (mouse) => root.closed()
                    visible: root.skill && root.skill.id !== undefined
                    ToolTip.text: "Close Inspector"
                    ToolTip.visible: hovered
                    ToolTip.delay: 400
                }
            }

            // Metadata Section
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: metaColumn.implicitHeight + 24
                radius: Theme.radiusCard
                color: Theme.glassPill
                border.color: Theme.glassBorder
                visible: root.skill.id !== undefined

                ColumnLayout {
                    id: metaColumn
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 4
                    
                    Repeater {
                        model: root.skill.id ? [
                            { label: "Location", value: root.skill.project_label || "Unknown" },
                            { label: "Type", value: root.skill.category || "Unknown" },
                            { label: "Risk", value: root.skill.risk || "Unknown" },
                            { label: "Source", value: root.skill.source || "Unknown" },
                            { label: "Date", value: root.skill.date || "Unknown" }
                        ] : []
                        
                        Text {
                            text: "<b>" + modelData.label + ":</b> " + modelData.value
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.sizeCaption
                            color: Theme.secondaryLabel
                            Layout.fillWidth: true
                            elide: Text.ElideRight
                            textFormat: Text.StyledText
                        }
                    }
                }
            }

            // Description
            ColumnLayout {
                Layout.fillWidth: true
                visible: root.skill.description !== ""
                spacing: 4
                
                Text {
                    text: "Description"
                    font.family: Theme.fontFamily
                    font.pixelSize: 10
                    font.weight: Font.Bold
                    color: Theme.secondaryLabel
                    opacity: 0.8
                }
                
                Text {
                    text: root.skill.description || ""
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.sizeBody
                    color: Theme.label
                    wrapMode: Text.Wrap
                    Layout.fillWidth: true
                }
            }

            // Documentation / Commands (Moved up for better visibility)
            ColumnLayout {
                Layout.fillWidth: true
                visible: (root.skill && root.skill.commands) ? root.skill.commands.length > 0 : false
                spacing: 4
                
                Text {
                    text: "Documentation"
                    font.family: Theme.fontFamily
                    font.pixelSize: 10
                    font.weight: Font.Bold
                    color: Theme.secondaryLabel
                    opacity: 0.8
                }

                Flow {
                    Layout.fillWidth: true
                    spacing: 6
                    Repeater {
                        model: root.skill.commands || []
                        delegate: Rectangle {
                            height: 16
                            width: tagText.implicitWidth + 10
                            radius: Theme.radiusSmall
                            color: Theme.glassHover
                            border.color: Theme.glassBorder
                            border.width: 1
                            
                            RowLayout {
                                anchors.centerIn: parent
                                spacing: 4
                                Text {
                                    id: tagText
                                    text: modelData.name
                                    color: Theme.secondaryLabel
                                    font.family: Theme.fontFamily
                                    font.pixelSize: 8
                                }
                            }
                            
                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: (mouse) => Qt.openUrlExternally("file:///" + modelData.path)
                            }
                        }
                    }
                }
            }

            // Implementation / Raw Content Section
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 8
                
                RowLayout {
                    Layout.fillWidth: true
                    Text {
                        text: "Implementation Details"
                        font.family: Theme.fontFamily
                        font.pixelSize: 12
                        font.weight: Font.Bold
                        color: Theme.secondaryLabel
                    }
                    Item { Layout.fillWidth: true }
                    Text {
                        text: root.skill.raw_content ? "Editable" : "Not Found"
                        font.family: Theme.fontFamily
                        font.pixelSize: 10
                        color: root.skill.raw_content ? Theme.accent : "#ff4444"
                        opacity: 0.7
                    }
                }
                
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 300
                    Layout.fillHeight: true
                    radius: Theme.radiusSmall
                    color: Qt.rgba(0,0,0,0.2)
                    border.color: Theme.glassBorder
                    border.width: 1
                    clip: true

                    ScrollView {
                        id: rawContentScroll
                        anchors.fill: parent
                        anchors.margins: 2
                        clip: true
                        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                        
                        ScrollBar.vertical: ScrollBar {
                            id: vScroll
                            active: true
                            width: 6
                            contentItem: Rectangle {
                                implicitWidth: 6
                                radius: 3
                                color: Theme.secondaryLabel
                                opacity: vScroll.hovered ? 0.8 : 0.4
                            }
                        }

                        TextArea {
                            id: rawContentArea
                            width: rawContentScroll.availableWidth
                            Accessible.role: Accessible.EditableText
                            Accessible.name: "Implementation Details"
                            text: cleanBodyContent((root.skill && root.skill.body_content) || "")
                            font.family: "Consolas", "Monaco", "Courier New", "monospace"
                            font.pixelSize: 12
                            color: (root.skill && root.skill.raw_content) ? Theme.label : Theme.secondaryLabel
                            wrapMode: TextEdit.Wrap
                            readOnly: true
                            selectByMouse: true
                            background: null
                            padding: 12
                            
                            // Ensure text is correctly aligned
                            verticalAlignment: Text.AlignTop
                        }
                    }
                }
            }

            // Quick Copy Argument
            ColumnLayout {
                Layout.fillWidth: true
                visible: root.isQuickCopy && root.skill.id !== undefined
                spacing: 4
                Text {
                    text: "Argument (e.g. ultra)"
                    font.family: Theme.fontFamily
                    font.pixelSize: 10
                    color: Theme.secondaryLabel
                    opacity: 0.8
                }
                TextField {
                    id: argField
                    Layout.fillWidth: true
                    placeholderText: "Optional argument..."
                    Accessible.role: Accessible.EditableText
                    Accessible.name: "Argument"
                    font.family: Theme.fontFamily
                    color: Theme.label
                    placeholderTextColor: Theme.secondaryLabel
                    background: Rectangle {
                        radius: Theme.radiusField
                        color: Theme.glassPill
                        border.color: Theme.glassBorder
                    }
                }
            }

            Item { Layout.preferredHeight: 12 } // Bottom padding
        }
    }

    // Collapse handle (vertical bar on the left when collapsed)
    Rectangle {
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        width: 32
        visible: root.isCollapsed
        color: "transparent"
        
        Text {
            anchors.centerIn: parent
            text: "›"
            rotation: 180
            font.pixelSize: 24
            color: Theme.secondaryLabel
        }
        
        MouseArea {
            id: collapseMouseArea
            anchors.fill: parent
            hoverEnabled: true
            onClicked: (mouse) => root.isCollapsed = false
            cursorShape: Qt.PointingHandCursor

            ToolTip.text: "Expand Inspector"
            ToolTip.visible: containsMouse
            ToolTip.delay: 400
        }
    }

    Behavior on width {
        NumberAnimation { duration: 300; easing.type: Easing.OutQuart }
    }

    Behavior on anchors.leftMargin {
        NumberAnimation { duration: 250; easing.type: Easing.OutQuad }
    }
}

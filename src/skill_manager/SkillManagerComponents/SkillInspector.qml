import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import App 1.0

Rectangle {
    id: root
    
    property var skill: ({})
    property bool isQuickCopy: false
    property bool isCollapsed: false

    readonly property int targetWidth: {
        if (!root.skill || root.skill.local_path === undefined) return 0;
        if (isCollapsed) return 32;

        let dynamicWidth = parent ? parent.width * 0.5 : (isQuickCopy ? 350 : 400);
        return Math.min(800, Math.max(isQuickCopy ? 350 : 400, dynamicWidth));
    }

    GlassMenu {
        id: inspectorContextMenu
        property var targetControl: null

        GlassMenuItem {
            text: "Copy"
            iconSource: AppController.ui_controller.getAssetUri("ui/copy-icon.svg")
            enabled: inspectorContextMenu.targetControl && inspectorContextMenu.targetControl.selectedText !== undefined && inspectorContextMenu.targetControl.selectedText.length > 0
            onTriggered: {
                if (inspectorContextMenu.targetControl) inspectorContextMenu.targetControl.copy()
            }
        }
        GlassMenuItem {
            text: "Select All"
            onTriggered: {
                if (inspectorContextMenu.targetControl) inspectorContextMenu.targetControl.selectAll()
            }
        }
    }

    function cleanBodyContent(content) {
        if (!content) return "";
        
        // 1. Remove YAML frontmatter if present (between first pair of ---)
        let cleaned = content.replace(/^---[\s\S]*?---/, '');
        
        // 2. Remove common metadata prefixes and the skill name header
        let lines = cleaned.split('\n');
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
            
            // Skip the name header if it matches root.skill.name (case insensitive, allowing for markdown headers)
            let headerMatch = trimmed.replace(/^#+\s+/, '').trim().toLowerCase();
            if (headerMatch === (root.skill.name || "").toLowerCase()) continue;
            
            result.push(line);
        }
        
        // 3. Join and trim leading/trailing whitespace/newlines
        return result.join('\n').trim();
    }

    signal closed()

    radius: Theme.radiusCard
    color: Theme.glassPill
    border.color: Theme.glassBorder
    clip: true // Ensure content doesn't bleed out when collapsed
    
    SmoothScrollView {
        id: mainScroll
        anchors.fill: parent
        anchors.margins: 4
        clip: true
        ScrollBar.vertical.policy: ScrollBar.AsNeeded
        
        ColumnLayout {
            width: mainScroll.width - 24
            height: Math.max(implicitHeight, mainScroll.height - 24)
            x: 12
            y: 12
            spacing: 16
            visible: !root.isCollapsed && root.skill.local_path !== undefined
            opacity: visible ? 1.0 : 0.0
            
            Behavior on opacity { NumberAnimation { duration: 200 } }

            // Header
            RowLayout {
                Layout.fillWidth: true
                spacing: 8
                TextEdit {
                    id: skillNameEdit
                    text: root.skill.name || "No Selection"
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.sizeSectionTitle
                    font.weight: Font.Bold
                    color: Theme.label
                    Layout.fillWidth: true
                    readOnly: true
                    selectByMouse: true
                    cursorVisible: false
                    wrapMode: TextEdit.Wrap

                    TapHandler {
                        acceptedButtons: Qt.RightButton
                        onTapped: {
                            inspectorContextMenu.targetControl = skillNameEdit
                            inspectorContextMenu.popup()
                        }
                    }
                }

                TextField {
                    id: argField
                    objectName: "argField"
                    visible: root.isQuickCopy && root.skill.local_path !== undefined
                    Layout.preferredWidth: 150
                    Layout.alignment: Qt.AlignVCenter
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

                    TapHandler {
                        acceptedButtons: Qt.RightButton
                        onTapped: {
                            inspectorContextMenu.targetControl = argField
                            inspectorContextMenu.popup()
                        }
                    }
                    ToolTip.text: "Argument (e.g. ultra)"
                    ToolTip.visible: hovered
                }
                IconButton {
                    id: starButton
                    text: (root.skill && root.skill.is_starred) ? "★" : "☆"
                    flat: true
                    Layout.preferredWidth: 32
                    Layout.preferredHeight: 32
                    visible: root.skill && root.skill.local_path !== undefined
                    onClicked: (mouse) => AppController.ops_controller.toggleCurrentSkillStarred()
                    
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

                    Accessible.role: Accessible.Button
                    Accessible.name: (root.skill && root.skill.is_starred) ? "Unstar Skill" : "Star Skill"
                    Accessible.description: ToolTip.text
                }

                IconButton {
                    text: "✕"
                    flat: true
                    onClicked: (mouse) => root.closed()
                    visible: root.skill && root.skill.local_path !== undefined
                    ToolTip.text: "Close Inspector"
                    ToolTip.visible: hovered
                    ToolTip.delay: 400

                    Accessible.role: Accessible.Button
                    Accessible.name: "Close Inspector"
                    Accessible.description: ToolTip.text
                }
            }

            // Metadata Section
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: metaColumn.implicitHeight + 24
                radius: Theme.radiusCard
                color: Theme.glassPill
                border.color: Theme.glassBorder
                visible: root.skill.local_path !== undefined && !root.skill.is_screenshot

                ColumnLayout {
                    id: metaColumn
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 4
                    
                    Repeater {
                        model: root.skill.local_path ? [
                            { label: "Location", value: root.skill.project_label || "Unknown" },
                            { label: "Type", value: root.skill.category || "Unknown" },
                            { label: "Risk", value: root.skill.risk || "Unknown" },
                            { label: "Source", value: root.skill.source || "Unknown" },
                            { label: "Date", value: root.skill.date || "Unknown" }
                        ] : []
                        
                        TextEdit {
                            id: metaEdit
                            text: "<b>" + modelData.label + ":</b> " + modelData.value
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.sizeCaption
                            color: Theme.secondaryLabel
                            Layout.fillWidth: true
                            readOnly: true
                            selectByMouse: true
                            cursorVisible: false
                            wrapMode: TextEdit.Wrap
                            textFormat: TextEdit.RichText

                            TapHandler {
                                acceptedButtons: Qt.RightButton
                                onTapped: {
                                    inspectorContextMenu.targetControl = metaEdit
                                    inspectorContextMenu.popup()
                                }
                            }
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
                
                TextEdit {
                    id: descriptionEdit
                    text: root.skill.description || ""
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.sizeBody
                    color: Theme.label
                    wrapMode: TextEdit.Wrap
                    Layout.fillWidth: true
                    readOnly: true
                    selectByMouse: true
                    cursorVisible: false

                    TapHandler {
                        acceptedButtons: Qt.RightButton
                        onTapped: {
                            inspectorContextMenu.targetControl = descriptionEdit
                            inspectorContextMenu.popup()
                        }
                    }
                }
            }

            // Documentation / Commands (Moved up for better visibility)
            ColumnLayout {
                Layout.fillWidth: true
                visible: (root.skill && root.skill.commands && !root.skill.is_screenshot) ? root.skill.commands.length > 0 : false
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
                                Accessible.role: Accessible.Link
                                Accessible.name: "Open file " + (modelData && modelData.name ? modelData.name : "file")
                            }
                        }
                    }
                }
            }

            // Screenshot Preview
            ColumnLayout {
                Layout.fillWidth: true
                visible: root.skill.is_screenshot === true
                spacing: 8
                
                Text {
                    text: "Screenshot Preview"
                    font.family: Theme.fontFamily
                    font.pixelSize: 12
                    font.weight: Font.Bold
                    color: Theme.secondaryLabel
                }
                
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: Math.min(600, width * (screenshotPreview.implicitHeight / Math.max(1, screenshotPreview.implicitWidth)))
                    color: Qt.rgba(0,0,0,0.2)
                    radius: Theme.radiusSmall
                    clip: true

                    Image {
                        id: screenshotPreview
                        anchors.fill: parent
                        anchors.margins: 4
                        fillMode: Image.PreserveAspectFit
                        source: {
                            if (!root.skill.is_screenshot || !root.skill.local_path) return "";
                            let p = root.skill.local_path.replace(/\\/g, "/");
                            if (p.startsWith("/")) return "file://" + p;
                            return "file:///" + p;
                        }
                        asynchronous: true
                    }
                    
                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: (mouse) => AppController.ui_controller.openPath(root.skill.local_path)
                    }
                }
            }

            // Implementation / Raw Content Section
            ColumnLayout {
                Layout.fillWidth: true
                visible: root.skill.local_path !== undefined && !root.skill.is_screenshot
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
                }
                
                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.preferredHeight: 400
                    Layout.minimumHeight: 100
                    radius: Theme.radiusSmall
                    color: Qt.rgba(0,0,0,0.2)
                    border.color: Theme.glassBorder
                    border.width: 1
                    clip: true

                    SmoothScrollView {
                        id: rawContentScroll
                        anchors.fill: parent
                        anchors.margins: 2
                        clip: true
                        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

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
                            cursorVisible: false
                            background: null
                            padding: 12
                            
                            // Ensure text is correctly aligned
                            verticalAlignment: TextArea.AlignTop

                            TapHandler {
                                acceptedButtons: Qt.RightButton
                                onTapped: {
                                    inspectorContextMenu.targetControl = rawContentArea
                                    inspectorContextMenu.popup()
                                }
                            }
                        }
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

            Accessible.role: Accessible.Button
            Accessible.name: "Expand Inspector"
        }
    }

    Behavior on width {
        NumberAnimation { duration: 300; easing.type: Easing.OutQuart }
    }

    Behavior on anchors.leftMargin {
        NumberAnimation { duration: 250; easing.type: Easing.OutQuad }
    }
}

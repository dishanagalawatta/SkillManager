import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import App 1.0

Rectangle {
    id: root
    
    readonly property var _sel: AppController.selectedSkill
    property var skill: _sel
    property bool isQuickCopy: false
    property bool isCollapsed: false
    // Controlled externally (e.g. from LibraryView overlay) to gate visibility.
    // Also gates internal ColumnLayout content. The overlay directly sets
    // `visible` on this root to bypass QML's visible binding staleness issue.
    property bool overlayVisible: true

    readonly property int targetWidth: {
        if (!root._sel || root._sel.local_path === undefined) return 0;
        if (isCollapsed) return 32;

        let dynamicWidth = parent ? parent.width * 0.5 : (isQuickCopy ? 350 : 400);
        return Math.min(800, Math.max(isQuickCopy ? 350 : 400, dynamicWidth));
    }

    function formatFileUrl(p) {
        if (!p) return "";
        if (p.startsWith("file://")) return p;
        var clean = p.replace(/\\/g, "/");
        if (clean.startsWith("/")) return "file://" + clean;
        return "file:///" + clean;
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
            
            // Skip the name header if it matches root._sel.name (case insensitive, allowing for markdown headers)
            let headerMatch = trimmed.replace(/^#+\s+/, '').trim().toLowerCase();
            let selName = root._sel ? (root._sel.name || "").toLowerCase() : "";
            if (selName && headerMatch === selName) continue;
            
            result.push(line);
        }
        
        // 3. Join and trim leading/trailing whitespace/newlines
        let finalCleaned = result.join('\n').trim();
        if (!finalCleaned) {
            return cleaned.trim() || content.trim();
        }
        return finalCleaned;
    }

    signal closed()

    radius: Theme.radiusCard
    color: Theme.glassPill
    border.color: Theme.glassBorder
    clip: true // Ensure content doesn't bleed out when collapsed
    
    Item {
        id: mainContainer
        anchors.fill: parent
        anchors.margins: 16
        clip: true
        
        ColumnLayout {
            anchors.fill: parent
            spacing: 16
            visible: root.overlayVisible && !root.isCollapsed && root._sel && root._sel.local_path !== undefined
            opacity: visible ? 1.0 : 0.0
            
            Behavior on opacity { NumberAnimation { duration: 200 } }

            // Header
            RowLayout {
                Layout.fillWidth: true
                spacing: 8
                TextEdit {
                    id: skillNameEdit
                    text: root._sel ? (root._sel.name || "No Selection") : "No Selection"
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.sizeSectionTitle
                    font.weight: Font.Bold
                    color: Theme.label
                    Layout.fillWidth: true
                    readOnly: true
                    selectByMouse: true
                    cursorVisible: false
                    wrapMode: TextEdit.Wrap

                    MouseArea {
                        anchors.fill: parent
                        acceptedButtons: Qt.RightButton
                        onClicked: (mouse) => {
                            inspectorContextMenu.targetControl = skillNameEdit
                            inspectorContextMenu.popup()
                        }
                    }
                }

                IconButton {
                    id: starButton
                    iconSource: (root._sel && root._sel.is_starred) 
                        ? AppController.ui_controller.getAssetUri("ui/star-filled.svg") 
                        : AppController.ui_controller.getAssetUri("ui/star-outline.svg")
                    customIconColor: (root._sel && root._sel.is_starred) ? "#FFD700" : Theme.secondaryLabel
                    iconSize: 22
                    flat: true
                    Layout.preferredWidth: 32
                    Layout.preferredHeight: 32
                    visible: root._sel && root._sel.local_path !== undefined
                    onClicked: (mouse) => AppController.ops_controller.toggleCurrentSkillStarred()
                    tooltipText: (root._sel && root._sel.is_starred) ? "Unstar Skill" : "Star Skill"
                    
                    background: Rectangle {
                        color: starButton.hovered ? Theme.glassHover : "transparent"
                        radius: Theme.radiusPill
                    }
                }

                IconButton {
                    text: "✕"
                    flat: true
                    onClicked: (mouse) => root.closed()
                    visible: root._sel && root._sel.local_path !== undefined
                    tooltipText: "Close Inspector"
                }
            }

            // QuickCopy Argument Input Row
            RowLayout {
                Layout.fillWidth: true
                visible: root.isQuickCopy && root._sel && root._sel.local_path !== undefined
                spacing: 8

                TextField {
                    id: argField
                    ContextMenu.menu: null
                    objectName: "argField"
                    Layout.fillWidth: true
                    placeholderText: "Optional argument (e.g. ultra)..."
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

                    MouseArea {
                        anchors.fill: parent
                        acceptedButtons: Qt.RightButton
                        onClicked: (mouse) => {
                            inspectorContextMenu.targetControl = argField
                            inspectorContextMenu.popup()
                        }
                    }
                    SleekToolTip {
                        text: "Argument (e.g. ultra)"
                        visible: argField.hovered || argField.activeFocus
                    }
                }
            }

            // Description
            ColumnLayout {
                Layout.fillWidth: true
                visible: root._sel && root._sel.description !== ""
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
                    text: (root._sel && root._sel.description) || ""
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.sizeBody
                    color: Theme.label
                    wrapMode: TextEdit.Wrap
                    Layout.fillWidth: true
                    Layout.preferredHeight: contentHeight + topPadding + bottomPadding
                    readOnly: true
                    selectByMouse: true
                    cursorVisible: false

                    onWidthChanged: {
                        if (width > 0) {
                            console.log("DESC_EDIT width=" + width + " contentW=" + contentWidth + " implicitH=" + implicitHeight + " contentH=" + contentHeight)
                        }
                    }

                    MouseArea {
                        anchors.fill: parent
                        acceptedButtons: Qt.RightButton
                        onClicked: (mouse) => {
                            inspectorContextMenu.targetControl = descriptionEdit
                            inspectorContextMenu.popup()
                        }
                    }
                }
            }

            // Metadata Section
            InspectorMetadataRow {
                id: metaFlow
                selectedSkill: root._sel
                contextMenu: inspectorContextMenu
            }

            // Documentation / Commands (Moved up for better visibility)
            ColumnLayout {
                id: docSection
                Layout.fillWidth: true
                visible: (root._sel && root._sel.commands && !root._sel.is_screenshot) ? root._sel.commands.length > 0 : false
                spacing: 4
                property bool isExpanded: true

                Item {
                    Layout.fillWidth: true
                    implicitHeight: docHeaderRow.implicitHeight

                    RowLayout {
                        id: docHeaderRow
                        anchors.fill: parent
                        spacing: 4

                        Text {
                            text: "Documentation"
                            font.family: Theme.fontFamily
                            font.pixelSize: 10
                            font.weight: Font.Bold
                            color: Theme.secondaryLabel
                            opacity: 0.8
                        }

                        Item { Layout.fillWidth: true }

                        IconButton {
                            buttonSize: 18
                            iconSize: 12
                            role: "ghost"
                            tooltipText: docSection.isExpanded ? "Collapse Documentation" : "Expand Documentation"
                            iconSource: docSection.isExpanded ?
                                AppController.ui_controller.getAssetUri("ui/collapse-arrow-up-broken.svg") :
                                AppController.ui_controller.getAssetUri("ui/collapse-arrow-down-broken.svg")
                        }
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: docSection.isExpanded = !docSection.isExpanded
                    }
                }

                Flow {
                    Layout.fillWidth: true
                    spacing: 6
                    visible: docSection.isExpanded
                    Repeater {
                        model: root._sel.commands || []
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
                                onClicked: (mouse) => Qt.openUrlExternally(root.formatFileUrl(modelData.path))
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
                visible: root._sel && root._sel.is_screenshot === true
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
                        source: (root._sel && root._sel.is_screenshot && root._sel.local_path) ? root.formatFileUrl(root._sel.local_path) : ""
                        asynchronous: true
                    }
                    
                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: (mouse) => {
                            if (root._sel && root._sel.local_path) AppController.ui_controller.openPath(root._sel.local_path)
                        }
                    }
                }
            }

            // Skill Details / Raw Content Section
            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.minimumHeight: 150
                visible: root._sel && root._sel.local_path !== undefined
                    && !root._sel.is_screenshot
                spacing: 8
                
                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
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
                            ContextMenu.menu: null
                            width: rawContentScroll.availableWidth
                            Accessible.role: Accessible.EditableText
                            Accessible.name: "Skill Details"
                            text: cleanBodyContent((root._sel && (root._sel.body_content || root._sel.raw_content)) || "")
                            font.family: "Consolas", "Monaco", "Courier New", "monospace"
                            font.pixelSize: 12
                            color: Theme.label
                            wrapMode: TextEdit.WrapAnywhere
                            readOnly: true
                            selectByMouse: true
                            cursorVisible: false
                            background: null
                            padding: 12
                            
                            // Ensure text is correctly aligned
                            verticalAlignment: TextArea.AlignTop

                            MouseArea {
                                anchors.fill: parent
                                acceptedButtons: Qt.RightButton
                                onClicked: (mouse) => {
                                    inspectorContextMenu.targetControl = rawContentArea
                                    inspectorContextMenu.popup()
                                }
                            }
                        }
                    }
                }
            }

            // Flexible spacer for screenshot mode to prevent vertical stretching
            Item {
                Layout.fillHeight: true
                visible: root._sel && root._sel.is_screenshot === true
            }
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

            SleekToolTip {
                text: "Expand Inspector"
                visible: parent.containsMouse
            }

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

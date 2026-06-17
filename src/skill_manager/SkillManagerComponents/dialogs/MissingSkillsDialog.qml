/**
 * Purpose: Dialog for handling missing skills when saving a collection.
 * Shows which skills are missing from selected projects and offers copy options.
 *
 * Uses JS array property instead of ListModel to avoid Qt 6.11.1
 * dynamicRoles bug where arrays stored in ListModel lose their type.
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
    property var projectCheckItems: []
    
    TextMetrics {
        id: _nameMetrics
        font.family: Theme.fontFamily
        font.pixelSize: Theme.sizeBody
        font.weight: Font.DemiBold
    }
    
    x: (parent.width - width) / 2
    y: (parent.height - height) / 2
    width: {
        var maxNameW = 0
        for (var i = 0; i < projectCheckItems.length; i++) {
            _nameMetrics.text = projectCheckItems[i].project
            maxNameW = Math.max(maxNameW, _nameMetrics.advanceWidth)
        }
        var contentW = maxNameW + 340
        return Math.max(600, Math.min(parent.width - 80, contentW))
    }
    height: {
        var listH = 16
        for (var i = 0; i < projectCheckItems.length; i++) {
            listH += projectCheckItems[i].detailsExpanded ? 300 : 76
        }
        var total = 224 + listH
        return Math.max(400, Math.min(parent.height - 80, total))
    }
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
        // Accept both JSON string and JS object
        if (typeof missing === "string") {
            try {
                missing = JSON.parse(missing)
            } catch (e) {
                missingSkills = {}
                projectCheckItems = []
                return
            }
        }
        missingSkills = missing
        var items = []
        var validKeys = []
        for (var k in missing) {
            var s = missing[k]
            if (Array.isArray(s) && s.length > 0) {
                items.push({
                    project: k,
                    skills: s,
                    checked: true,
                    detailsExpanded: false
                })
                validKeys.push(k)
            }
        }
        projectCheckItems = items
        selectedProjects = validKeys
        if (items.length === 0) return
        open()
    }

    function getCheckedProjects() {
        var result = []
        for (var i = 0; i < projectCheckItems.length; i++) {
            if (projectCheckItems[i].checked) {
                result.push(projectCheckItems[i].project)
            }
        }
        return result
    }

    function toggleChecked(index) {
        var items = projectCheckItems.slice()
        items[index] = Object.assign({}, items[index], {
            checked: !items[index].checked
        })
        projectCheckItems = items
    }

    function toggleDetails(index) {
        var items = projectCheckItems.slice()
        items[index] = Object.assign({}, items[index], {
            detailsExpanded: !items[index].detailsExpanded
        })
        projectCheckItems = items
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
                Layout.preferredHeight: {
                    var h = 16
                    for (var i = 0; i < root.projectCheckItems.length; i++) {
                        h += root.projectCheckItems[i].detailsExpanded ? 300 : 76
                    }
                    return h
                }
                radius: Theme.radiusField
                color: Theme.glassHover
                border.color: Theme.glassBorder

                SmoothListView {
                    anchors.fill: parent
                    anchors.margins: 8
                    clip: true
                    model: root.projectCheckItems

                    delegate: Rectangle {
                        width: parent.width
                        height: modelData.detailsExpanded ? 300 : 76
                        color: "transparent"
                        clip: true

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
                                    checkState: modelData.checked ? Qt.Checked : Qt.Unchecked
                                    iconSize: 9
                                    onToggled: root.toggleChecked(index)
                                }
                                Text {
                                    text: modelData.project
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.sizeBody
                                    font.weight: Font.DemiBold
                                    color: Theme.label
                                    Layout.fillWidth: true
                                }
                                Text {
                                    id: expandToggle
                                    text: modelData.detailsExpanded ? "▲" : "▼"
                                    font.pixelSize: 10
                                    color: Theme.secondaryLabel
                                    MouseArea {
                                        anchors.fill: parent
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: root.toggleDetails(index)
                                    }
                                }
                            }

                            Text {
                                text: {
                                    var s = modelData.skills
                                    var n = 0
                                    if (Array.isArray(s)) n = s.length
                                    else if (s && typeof s.length === "number") n = s.length
                                    return n + " skill(s) missing"
                                }
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.sizeMetadata
                                color: Theme.secondaryLabel
                                Layout.leftMargin: 28
                            }

                            Rectangle {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                Layout.leftMargin: 28
                                Layout.rightMargin: 8
                                Layout.topMargin: 4
                                radius: Theme.radiusField
                                color: Theme.glassHover
                                border.color: Theme.glassBorder
                                visible: modelData.detailsExpanded

                                ColumnLayout {
                                    anchors.fill: parent
                                    anchors.margins: 6
                                    spacing: 2

                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 4

                                        Text {
                                            text: "Raw payload"
                                            font.family: Theme.fontFamily
                                            font.pixelSize: Theme.sizeMetadata
                                            color: Theme.secondaryLabel
                                            Layout.fillWidth: true
                                        }

                                        IconButton {
                                            text: "📋"
                                            flat: true
                                            Layout.preferredWidth: 24
                                            Layout.preferredHeight: 24
                                            onClicked: {
                                                diagText.selectAll()
                                                AppController.ops_controller.copyTextToClipboard(diagText.text)
                                            }
                                            background: Rectangle {
                                                radius: 12
                                                color: parent.hovered ? Theme.glassHover : "transparent"
                                            }
                                            contentItem: Text {
                                                text: parent.text
                                                font.pixelSize: 14
                                                horizontalAlignment: Text.AlignHCenter
                                                verticalAlignment: Text.AlignVCenter
                                            }
                                        }
                                    }

                                    Flickable {
                                        Layout.fillWidth: true
                                        Layout.fillHeight: true
                                        contentHeight: diagText.implicitHeight
                                        clip: true
                                        flickableDirection: Flickable.VerticalFlick

                                        TextEdit {
                                            id: diagText
                                            width: parent.width
                                            readOnly: true
                                            selectByMouse: true
                                            cursorVisible: false
                                            persistentSelection: true
                                            wrapMode: TextEdit.Wrap
                                            text: {
                                                var s = modelData.skills
                                                if (Array.isArray(s)) {
                                                    return "skills array (" + s.length + " items):\n  " + s.join("\n  ")
                                                }
                                                return "data type: " + typeof s + "\nraw: " + JSON.stringify(s)
                                            }
                                            font.family: "Courier"
                                            font.pixelSize: Theme.sizeMetadata
                                            color: Theme.secondaryLabel
                                        }
                                    }
                                }
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

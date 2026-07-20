/**
 * Purpose: A reusable emoji picker popup for selecting command icons.
 * Usage:
 * EmojiPicker {
 *     id: emojiPicker
 *     onEmojiSelected: (emoji) => { // use emoji }
 * }
 */
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App 1.0

Popup {
    id: root

    // --- Public API ---
    signal emojiSelected(string emoji)

    // --- Dialog Properties ---
    modal: true
    width: 480
    height: 520
    parent: Overlay.overlay
    anchors.centerIn: parent
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

    // --- Background ---
    background: Rectangle {
        radius: Theme.radiusCard
        color: Theme.glassPill
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

    // --- Enter/Exit Animations (matches FontPickerDialog) ---
    enter: Transition {
        ParallelAnimation {
            NumberAnimation { property: "opacity"; from: 0.0; to: 1.0; duration: 200; easing.type: Easing.OutCubic }
            NumberAnimation { property: "scale"; from: 0.95; to: 1.0; duration: 200; easing.type: Easing.OutCubic }
        }
    }

    exit: Transition {
        ParallelAnimation {
            NumberAnimation { property: "opacity"; from: 1.0; to: 0.0; duration: 150; easing.type: Easing.InCubic }
            NumberAnimation { property: "scale"; from: 1.0; to: 0.95; duration: 150; easing.type: Easing.InCubic }
        }
    }

    onOpened: {
        searchField.text = ""
        searchField.forceActiveFocus()
        refreshRecents()
    }

    // --- Internal State ---
    property var recents: []

    function refreshRecents() {
        recents = AppController.getEmojiRecents()
    }

    // --- Emoji Dataset ---
    readonly property var emojiData: [
        { emoji: "⚡", name: "zap default" },
        { emoji: "🚀", name: "rocket launch ship" },
        { emoji: "🔥", name: "fire flame hot" },
        { emoji: "💡", name: "lightbulb idea" },
        { emoji: "⚙️", name: "gear settings config" },
        { emoji: "🤖", name: "robot ai bot" },
        { emoji: "🧠", name: "brain smart think" },
        { emoji: "💻", name: "computer laptop code" },
        { emoji: "🛠️", name: "tools wrench build" },
        { emoji: "📦", name: "package box bundle" },
        { emoji: "🎯", name: "target bullseye goal" },
        { emoji: "✅", name: "check done complete" },
        { emoji: "❌", name: "cross delete no" },
        { emoji: "⚠️", name: "warning alert caution" },
        { emoji: "🔍", name: "search magnify find" },
        { emoji: "📝", name: "memo write note" },
        { emoji: "📌", name: "pin mark important" },
        { emoji: "🔗", name: "link chain url" },
        { emoji: "📁", name: "folder file" },
        { emoji: "🗂️", name: "card index organize" },
        { emoji: "📊", name: "chart graph analytics" },
        { emoji: "📈", name: "trend up growth" },
        { emoji: "🎬", name: "movie clapperboard run" },
        { emoji: "▶️", name: "play start run execute" },
        { emoji: "⏸️", name: "pause stop" },
        { emoji: "🔄", name: "refresh cycle reload" },
        { emoji: "🔀", name: "shuffle random" },
        { emoji: "⬇️", name: "arrow down download" },
        { emoji: "⬆️", name: "arrow up upload" },
        { emoji: "➡️", name: "arrow right forward" },
        { emoji: "⬅️", name: "arrow left back" },
        { emoji: "🔀", name: "shuffle random mix" },
        { emoji: "✨", name: "sparkle star magic" },
        { emoji: "💎", name: "gem diamond premium" },
        { emoji: "🏆", name: "trophy winner award" },
        { emoji: "🎉", name: "party celebrate" },
        { emoji: "🌍", name: "earth globe world" },
        { emoji: "🔑", name: "key lock security" },
        { emoji: "🛡️", name: "shield protect safety" },
        { emoji: "🧪", name: "test tube experiment" },
        { emoji: "🐛", name: "bug insect debug" },
        { emoji: "🔨", name: "hammer build fix" },
        { emoji: "🎨", name: "art palette design color" },
        { emoji: "📸", name: "camera photo screenshot" },
        { emoji: "🔊", name: "volume sound audio" },
        { emoji: "🔔", name: "bell notification alert" },
        { emoji: "⏰", name: "clock timer schedule" },
        { emoji: "📅", name: "calendar date" },
        { emoji: "🗑️", name: "trash delete remove" },
        { emoji: "💾", name: "floppy disk save" },
        { emoji: "📤", name: "outbox send export" },
        { emoji: "📥", name: "inbox receive import" },
        { emoji: "🏷️", name: "label tag name" },
        { emoji: "🪟", name: "window app panel" },
        { emoji: "🌐", name: "globe web internet" },
        { emoji: "📡", name: "satellite signal" },
        { emoji: "🔧", name: "wrench tool fix adjust" },
        { emoji: "📋", name: "clipboard paste list" },
        { emoji: "📄", name: "document page file" },
        { emoji: "🗃️", name: "card box archive" },
        { emoji: "🧩", name: "puzzle piece plugin" },
        { emoji: "🛤️", name: "railway path track" },
        { emoji: "🏗️", name: "construction build develop" },
        { emoji: "🧪", name: "flask test experiment" },
        { emoji: "🪄", name: "magic wand auto" },
        { emoji: "🌀", name: "cyclone spin process" },
        { emoji: "💀", name: "skull danger critical" },
        { emoji: "🫧", name: "bubbles bubble chat" },
        { emoji: "🎵", name: "music note audio" },
        { emoji: "🎶", name: "music notes sound" },
        // Animals
        { emoji: "🐱", name: "cat face cute" },
        { emoji: "🐶", name: "dog face loyal" },
        { emoji: "🦊", name: "fox clever" },
        { emoji: "🐻", name: "bear strong" },
        { emoji: "🦁", name: "lion brave" },
        { emoji: "🦅", name: "eagle fast" },
        { emoji: "🐙", name: "octopus tentacles" },
        // Food
        { emoji: "🍎", name: "apple fruit health" },
        { emoji: "🍕", name: "pizza food" },
        { emoji: "☕", name: "coffee cup drink" },
        { emoji: "🧋", name: "boba tea bubble" },
        { emoji: "🍰", name: "cake dessert sweet" },
        // Faces
        { emoji: "😊", name: "smile happy face" },
        { emoji: "🤔", name: "thinking face ponder" },
        { emoji: "😎", name: "cool sunglasses awesome" },
        { emoji: "🫡", name: "salute respect" },
        { emoji: "💀", name: "skull dead lol" },
        { emoji: "🥳", name: "party face celebrate" },
        { emoji: "🫠", name: "melting face" },
        { emoji: "🤝", name: "handshake agree deal" },
        { emoji: "👍", name: "thumbs up approve good" },
        { emoji: "👎", name: "thumbs down reject bad" },
        // Hearts
        { emoji: "❤️", name: "red heart love favorite" },
        { emoji: "💚", name: "green heart" },
        { emoji: "💜", name: "purple heart" },
        { emoji: "🖤", name: "black heart" },
        // Misc symbols
        { emoji: "♾️", name: "infinity forever loop" },
        { emoji: "🔀", name: "crossed arrows shuffle" },
        { emoji: "❇️", name: "sparkle green" },
        { emoji: "🔰", name: "japanese beginner new" },
        { emoji: "📍", name: "pin location" },
        { emoji: "🚩", name: "flag milestone" },
        { emoji: "🏁", name: "checkered flag finish end" },
        { emoji: "🏴", name: "black flag" },
        { emoji: "⭐", name: "star gold important" },
        { emoji: "🌟", name: "glowing star bright" },
        { emoji: "💫", name: "dizzy star" },
        { emoji: "🔴", name: "red circle dot recording" },
        { emoji: "🟢", name: "green circle dot online" },
        { emoji: "🟡", name: "yellow circle dot warning" },
        { emoji: "🔵", name: "blue circle dot info" },
        { emoji: "🟣", name: "purple circle dot" }
    ]

    // --- Filtered list ---
    property var filteredEmojis: {
        let q = searchField.text.toLowerCase().trim()
        if (q === "") return emojiData
        let result = []
        for (let i = 0; i < emojiData.length; i++) {
            if (emojiData[i].name.toLowerCase().indexOf(q) !== -1) {
                result.push(emojiData[i])
            }
        }
        return result
    }

    contentItem: ColumnLayout {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 12

        // --- Header ---
        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            Text {
                text: "Choose Emoji"
                font.family: Theme.fontFamily
                font.pixelSize: Theme.sizeSectionTitle
                font.weight: Font.Bold
                color: Theme.label
                Layout.fillWidth: true
            }

            IconButton {
                iconSource: AppController.ui_controller.getAssetUri("ui/tool-x.svg")
                tooltipText: "Close"
                role: "ghost"
                buttonSize: 28
                iconSize: 14
                onClicked: root.close()
            }
        }

        // --- Search ---
        GlassSearchInput {
            id: searchField
            Layout.fillWidth: true
            placeholderText: "Search emojis..."
        }

        // --- Recents Row ---
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 4
            visible: root.recents.length > 0

            Text {
                text: "Recent"
                font.family: Theme.fontFamily
                font.pixelSize: Theme.sizeMetadata
                font.weight: Font.DemiBold
                color: Theme.secondaryLabel
            }

            Flow {
                Layout.fillWidth: true
                spacing: 4

                Repeater {
                    model: root.recents
                    delegate: Rectangle {
                        width: 36
                        height: 36
                        radius: Theme.radiusSmall
                        color: recentHover.containsMouse ? Theme.glassHover : Theme.glassPill
                        border.color: Theme.glassBorder
                        border.width: 1

                        Text {
                            anchors.centerIn: parent
                            text: modelData
                            font.pixelSize: 20
                        }

                        HoverHandler {
                            id: recentHover
                            cursorShape: Qt.PointingHandCursor
                        }

                        TapHandler {
                            onTapped: {
                                root.emojiSelected(modelData)
                                AppController.addEmojiRecent(modelData)
                                root.close()
                            }
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                height: 1
                color: Theme.separator
            }
        }

        // --- Emoji Grid ---
        GridView {
            id: emojiGrid
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            cellWidth: 44
            cellHeight: 44
            model: root.filteredEmojis

            ScrollBar.vertical: ScrollBar {
                policy: emojiGrid.contentHeight > emojiGrid.height ? ScrollBar.AsNeeded : ScrollBar.AlwaysOff
            }

            delegate: Item {
                width: emojiGrid.cellWidth
                height: emojiGrid.cellHeight

                Rectangle {
                    anchors.fill: parent
                    anchors.margins: 2
                    radius: Theme.radiusSmall
                    color: emojiCellHover.containsMouse ? Theme.glassHover : "transparent"

                    Text {
                        anchors.centerIn: parent
                        text: modelData.emoji
                        font.pixelSize: 22
                    }

                    HoverHandler {
                        id: emojiCellHover
                        cursorShape: Qt.PointingHandCursor
                    }

                    TapHandler {
                        onTapped: {
                            root.emojiSelected(modelData.emoji)
                            AppController.addEmojiRecent(modelData.emoji)
                            root.close()
                        }
                    }
                }
            }
        }

        // --- Footer: Reset Button ---
        Rectangle {
            Layout.fillWidth: true
            height: 1
            color: Theme.separator
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            Text {
                text: "Default: ⚡"
                font.family: Theme.fontFamily
                font.pixelSize: Theme.sizeMetadata
                color: Theme.secondaryLabel
                Layout.fillWidth: true
            }

            ActionButton {
                text: "Reset to Default"
                role: "secondary"
                onClicked: {
                    root.emojiSelected("⚡")
                    AppController.addEmojiRecent("⚡")
                    root.close()
                }
            }
        }
    }
}

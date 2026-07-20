import QtQuick
import QtQuick.Window
import QtQuick.Controls
import App 1.0

Window {
    id: overlay
    flags: Qt.Window | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
    visibility: Window.Hidden
    color: "transparent"

    onClosing: {
        try {
            AppController.screenshot_controller.cancelCapture()
        } catch (e) {
            console.error("Failed to cancel capture:", e)
        }
    }

    property real startX: 0
    property real startY: 0
    property rect selectionRect: Qt.rect(0, 0, 0, 0)
    property bool isSelecting: false
    property bool isRedacting: false
    property string mode: "selecting" // "selecting" or "redacting"
    property var redactionRects: []

    // Background freeze-frame
    Image {
        id: bg
        anchors.fill: parent
        source: "image://screenshot/current?v=" + AppController.screenshot_controller.screenshotVersion
        cache: false
    }

    // Dimming Overlay (with hole)
    Item {
        anchors.fill: parent
        visible: selectionRect.width > 0

        // Top
        Rectangle {
            x: 0; y: 0; width: parent.width; height: selectionRect.y
            color: "#80000000"
        }
        // Bottom
        Rectangle {
            x: 0; y: selectionRect.y + selectionRect.height
            width: parent.width; height: parent.height - (selectionRect.y + selectionRect.height)
            color: "#80000000"
        }
        // Left
        Rectangle {
            x: 0; y: selectionRect.y; width: selectionRect.x; height: selectionRect.height
            color: "#80000000"
        }
        // Right
        Rectangle {
            x: selectionRect.x + selectionRect.width; y: selectionRect.y
            width: parent.width - (selectionRect.x + selectionRect.width); height: selectionRect.height
            color: "#80000000"
        }
    }

    // Border around selection
    Rectangle {
        x: selectionRect.x - 1; y: selectionRect.y - 1
        width: selectionRect.width + 2; height: selectionRect.height + 2
        color: "transparent"
        border.color: Theme.info
        border.width: 1
        visible: selectionRect.width > 0
    }

    // Redaction Boxes Layer
    Item {
        id: redactionLayer
        anchors.fill: parent
        z: 10

        Repeater {
            model: redactionRects
            Rectangle {
                x: modelData.x
                y: modelData.y
                width: modelData.width
                height: modelData.height
                color: "black"
            }
        }
    }

    // Interaction Area
    MouseArea {
        anchors.fill: parent
        cursorShape: {
            if (mode === "selecting") return Qt.CrossCursor
            if (isRedacting) return Qt.CrossCursor
            return Qt.ArrowCursor
        }
        z: 20

        onPressed: (mouse) => {
            if (mode === "selecting") {
                startX = mouse.x
                startY = mouse.y
                selectionRect = Qt.rect(startX, startY, 0, 0)
                isSelecting = true
                redactionRects = []
            } else if (mode === "redacting" && isRedacting) {
                startX = mouse.x
                startY = mouse.y
                // Constrain start to selectionRect
                startX = Math.max(selectionRect.x, Math.min(startX, selectionRect.x + selectionRect.width))
                startY = Math.max(selectionRect.y, Math.min(startY, selectionRect.y + selectionRect.height))
                var newRect = { x: startX, y: startY, width: 0, height: 0 }
                redactionRects.push(newRect)
                redactionRectsChanged()
            }
        }

        onPositionChanged: (mouse) => {
            var curX = Math.max(0, Math.min(mouse.x, parent.width))
            var curY = Math.max(0, Math.min(mouse.y, parent.height))

            if (mode === "selecting" && isSelecting) {
                selectionRect = Qt.rect(
                    Math.min(startX, curX),
                    Math.min(startY, curY),
                    Math.abs(startX - curX),
                    Math.abs(startY - curY)
                )
            } else if (mode === "redacting" && isRedacting) {
                // Update last redaction box
                if (redactionRects.length > 0) {
                    var last = redactionRects[redactionRects.length - 1]
                    // Constrain redaction to selectionRect
                    var targetX = Math.min(startX, curX)
                    var targetY = Math.min(startY, curY)
                    var targetW = Math.abs(startX - curX)
                    var targetH = Math.abs(startY - curY)

                    // Clamp to selection boundary
                    targetX = Math.max(selectionRect.x, targetX)
                    targetY = Math.max(selectionRect.y, targetY)
                    targetW = Math.min(targetW, selectionRect.x + selectionRect.width - targetX)
                    targetH = Math.min(targetH, selectionRect.y + selectionRect.height - targetY)

                    last.x = targetX
                    last.y = targetY
                    last.width = targetW
                    last.height = targetH
                    redactionRectsChanged()
                }
            }
        }

        onReleased: {
            if (mode === "selecting") {
                isSelecting = false
                if (selectionRect.width > 5 && selectionRect.height > 5) {
                    mode = "redacting"
                }
            }
        }
    }

    // Toolbox
    Rectangle {
        id: toolbox
        visible: mode === "redacting" && !isSelecting
        z: 1000
        x: Math.min(Math.max(0, selectionRect.x + selectionRect.width - width), parent.width - width)
        y: selectionRect.y + selectionRect.height + 10 > parent.height - height
           ? selectionRect.y - height - 10
           : selectionRect.y + selectionRect.height + 10

        width: toolboxRow.implicitWidth + 24
        height: 40
        color: "#2D2D2D"
        radius: 6
        border.color: "#444"

        Row {
            id: toolboxRow
            anchors.centerIn: parent
            spacing: 6

            // Redact toggle button
            ActionButton {
                id: redactButton
                text: isRedacting ? "Drawing" : "Redact"
                iconText: isRedacting ? "\u270E" : "\u270E"
                role: isRedacting ? "primary" : "secondary"
                highlighted: isRedacting
                onClicked: {
                    isRedacting = !isRedacting
                    if (!isRedacting) {
                        // Reassign array to force Repeater update when toggling off
                        redactionRects = redactionRects.slice()
                    }
                }
            }

            // Separator
            Rectangle {
                width: 1; height: 24
                color: "#555"
                anchors.verticalCenter: parent.verticalCenter
            }

            ActionButton {
                text: "Cancel"
                onClicked: {
                    AppController.screenshot_controller.cancelCapture()
                    overlay.close()
                }
            }

            ActionButton {
                text: "Reset"
                onClicked: {
                    mode = "selecting"
                    isRedacting = false
                    selectionRect = Qt.rect(0,0,0,0)
                    redactionRects = []
                }
            }

            ActionButton {
                text: "Save"
                highlighted: true
                onClicked: finalize()
            }
        }
    }

    function finalize() {
        // Prepare redactions relative to the crop area
        var relativeRedactions = []
        for (var i=0; i < redactionRects.length; i++) {
            var r = redactionRects[i]
            if (r.width > 0 && r.height > 0) {
                relativeRedactions.push({
                    x: r.x - selectionRect.x,
                    y: r.y - selectionRect.y,
                    width: r.width,
                    height: r.height
                })
            }
        }

        AppController.screenshot_controller.saveScreenshot(
            Qt.rect(selectionRect.x, selectionRect.y, selectionRect.width, selectionRect.height),
            relativeRedactions
        )
        overlay.close()
    }

    Shortcut {
        enabled: overlay.visible
        sequence: "Return"
        context: Qt.ApplicationShortcut
        onActivated: if (mode === "redacting" && overlay.visible) finalize()
    }

    Shortcut {
        enabled: overlay.visible
        sequence: "Enter"
        context: Qt.ApplicationShortcut
        onActivated: if (mode === "redacting" && overlay.visible) finalize()
    }

    Shortcut {
        enabled: overlay.visible && AppController.config_controller.shortcutClearSelectionEnabled
        sequence: AppController.config_controller.shortcutClearSelection
        context: Qt.ApplicationShortcut
        onActivated: {
            if (overlay.visible) {
                AppController.screenshot_controller.cancelCapture()
                overlay.close()
            }
        }
    }

    Connections {
        target: AppController.screenshot_controller
        function onShowOverlay() {
            overlay.mode = "selecting"
            overlay.isRedacting = false
            overlay.selectionRect = Qt.rect(0,0,0,0)
            overlay.redactionRects = []
            overlay.visibility = Window.FullScreen
            overlay.raise()
            overlay.requestActivate()
        }
    }
}

import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import App 1.0

Rectangle {
    id: root

    property var skill: ({})
    property bool isCollapsed: false

    readonly property int targetWidth: {
        if (!root.skill || root.skill.local_path === undefined) return 0;
        if (isCollapsed) return 32;

        let dynamicWidth = parent ? parent.width * 0.5 : 440;
        return Math.min(800, Math.max(440, dynamicWidth));
    }

    signal closed()

    GlassMenu {
        id: inspectorContextMenu

        GlassMenuItem {
            text: "Copy Image Path"
            iconSource: AppController.ui_controller.getAssetUri("ui/copy-icon.svg")
            onTriggered: {
                AppController.clipboard.setText(root.imagePath)
            }
        }

        GlassMenuItem {
            text: "Open Externally"
            onTriggered: AppController.image_inspector_controller.openExternally(root.imagePath)
        }

        GlassMenuItem {
            text: "Zoom to Fit"
            shortcut: "Ctrl+0"
            onTriggered: zoomToFit()
        }

        GlassMenuItem {
            text: "Reset Zoom"
            shortcut: "Ctrl+1"
            onTriggered: root.zoomLevel = 1.0
        }
    }

    // --- State ---
    property string imagePath: {
        if (!root.skill || !root.skill.is_screenshot || !root.skill.local_path) return "";
        let p = root.skill.local_path.replace(/\\/g, "/");
        if (p.startsWith("/")) return "file://" + p;
        return "file:///" + p;
    }
    property string imageFileName: {
        if (!root.skill || !root.skill.local_path) return "";
        let parts = root.skill.local_path.replace(/\\/g, "/").split("/");
        return parts[parts.length - 1];
    }
    property real zoomLevel: 1.0
    property real minZoom: 0.1
    property real maxZoom: 10.0
    property point panOffset: Qt.point(0, 0)
    property string activeTool: "none"
    property color activeColor: "#FF0000"
    property real strokeWidth: 3
    property var annotations: []
    property int selectedIndex: -1
    property bool isDrawing: false
    property real drawStartX: 0
    property real drawStartY: 0
    property var currentPath: []
    property bool isFullscreen: false
    property bool isDragging: false
    property real dragOffsetX: 0
    property real dragOffsetY: 0
    property bool isResizing: false
    property int resizeHandle: -1
    property real resizeStartX: 0
    property real resizeStartY: 0
    property real resizeOrigX: 0
    property real resizeOrigY: 0
    property real resizeOrigW: 0
    property real resizeOrigH: 0
    property bool isTextInputActive: false
    property real textInputX: 0
    property real textInputY: 0
    property string textInputValue: ""

    // Preset colors for the color picker
    property var presetColors: [
        "#FF0000", "#FF6B00", "#FFD600", "#00C853",
        "#00B0FF", "#3D5AFE", "#AA00FF", "#FF4081",
        "#FFFFFF", "#000000"
    ]

    function getAnnotationAt(mx, my) {
        for (var i = annotations.length - 1; i >= 0; i--) {
            var a = annotations[i]
            if (a.type === "rect" || a.type === "redact" || a.type === "highlight") {
                if (mx >= a.x && mx <= a.x + a.width && my >= a.y && my <= a.y + a.height)
                    return i
            } else if (a.type === "arrow") {
                var dx1 = mx - a.x1, dy1 = my - a.y1
                var dx2 = mx - a.x2, dy2 = my - a.y2
                if (Math.sqrt(dx1 * dx1 + dy1 * dy1) < 10 || Math.sqrt(dx2 * dx2 + dy2 * dy2) < 10)
                    return i
            } else if (a.type === "text") {
                if (mx >= a.x - 5 && mx <= a.x + 150 && my >= a.y - 20 && my <= a.y + 5)
                    return i
            } else if (a.type === "freehand" && a.points && a.points.length > 0) {
                for (var j = 0; j < a.points.length; j++) {
                    var dx = mx - a.points[j].x, dy = my - a.points[j].y
                    if (Math.sqrt(dx * dx + dy * dy) < 12)
                        return i
                }
            }
        }
        return -1
    }

    function canvasToImage(cx, cy) {
        var imgX = (cx - panOffset.x) / zoomLevel
        var imgY = (cy - panOffset.y) / zoomLevel
        return Qt.point(imgX, imgY)
    }

    function imageToCanvas(ix, iy) {
        var cx = ix * zoomLevel + panOffset.x
        var cy = iy * zoomLevel + panOffset.y
        return Qt.point(cx, cy)
    }

    // --- Root styling (same as SkillInspector) ---
    color: Theme.glassPill
    border.color: Theme.glassBorder
    border.width: 1
    radius: Theme.radiusCard

    TapHandler {
        acceptedButtons: Qt.RightButton
        onTapped: inspectorContextMenu.popup()
    }

    // --- Collapse Handle ---
    Rectangle {
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        width: 32
        visible: root.isCollapsed
        color: "transparent"

        Text {
            anchors.centerIn: parent
            text: "\u2039"
            rotation: 180
            font.pixelSize: 24
            color: Theme.secondaryLabel
        }

        MouseArea {
            anchors.fill: parent
            onClicked: () => root.isCollapsed = false
            cursorShape: Qt.PointingHandCursor
        }
    }

    // --- Main Content (hidden when collapsed) ---
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 4
        visible: !root.isCollapsed
        spacing: 0

        // === Header ===
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 44
            color: "transparent"

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 12
                anchors.rightMargin: 8
                spacing: 6

                // Skill name
                Text {
                    Layout.fillWidth: true
                    text: root.skill ? (root.skill.name || "Untitled") : ""
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.sizeBody
                    font.weight: Font.DemiBold
                    color: Theme.label
                    elide: Text.ElideRight
                    verticalAlignment: Text.AlignVCenter
                }

                // Zoom controls
                IconButton {
                    iconText: "-"
                    tooltipText: "Zoom Out (Ctrl+-)"
                    role: "ghost"
                    buttonSize: 28
                    iconSize: 14
                    onClicked: root.zoomLevel = Math.max(root.minZoom, root.zoomLevel - 0.25)
                }

                Text {
                    text: Math.round(root.zoomLevel * 100) + "%"
                    font.family: Theme.fontFamily
                    font.pixelSize: 11
                    color: Theme.secondaryLabel
                    Layout.preferredWidth: 40
                    horizontalAlignment: Text.AlignHCenter
                }

                IconButton {
                    iconText: "+"
                    tooltipText: "Zoom In (Ctrl++)"
                    role: "ghost"
                    buttonSize: 28
                    iconSize: 14
                    onClicked: root.zoomLevel = Math.min(root.maxZoom, root.zoomLevel + 0.25)
                }

                IconButton {
                    iconText: "\u2922"
                    tooltipText: "Zoom to Fit (Ctrl+0)"
                    role: "ghost"
                    buttonSize: 28
                    iconSize: 14
                    onClicked: zoomToFit()
                }

                IconButton {
                    iconText: "1:1"
                    tooltipText: "Zoom to 100% (Ctrl+1)"
                    role: "ghost"
                    buttonSize: 28
                    iconSize: 14
                    onClicked: root.zoomLevel = 1.0
                }

                Rectangle {
                    width: 1
                    height: 20
                    color: Theme.separator
                }

                IconButton {
                    iconText: root.isFullscreen ? "\u2716" : "\u26F6"
                    tooltipText: root.isFullscreen ? "Exit Fullscreen" : "Fullscreen"
                    role: "ghost"
                    buttonSize: 28
                    iconSize: 14
                    onClicked: toggleFullscreen()
                }

                IconButton {
                    iconText: "\u2197"
                    tooltipText: "Open Externally"
                    role: "ghost"
                    buttonSize: 28
                    iconSize: 14
                    onClicked: AppController.image_inspector_controller.openExternally(root.imagePath)
                }

                IconButton {
                    iconText: "\u2716"
                    tooltipText: "Close Inspector"
                    role: "ghost"
                    buttonSize: 28
                    iconSize: 14
                    onClicked: root.closed()
                }
            }
        }

        // Separator
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 1
            Layout.leftMargin: 8
            Layout.rightMargin: 8
            color: Theme.separator
        }

        // === Image Canvas ===
        Rectangle {
            id: canvasContainer
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: Qt.rgba(0, 0, 0, 0.3)
            radius: Theme.radiusSmall
            clip: true

            Flickable {
                id: flickable
                anchors.fill: parent
                contentWidth: Math.max(imageItem.width * root.zoomLevel, canvasContainer.width)
                contentHeight: Math.max(imageItem.height * root.zoomLevel, canvasContainer.height)
                clip: true
                interactive: root.activeTool === "none" && root.selectedIndex === -1
                flickableDirection: Flickable.HorizontalAndVerticalFlick

                Image {
                    id: imageItem
                    x: root.panOffset.x
                    y: root.panOffset.y
                    width: implicitWidth * root.zoomLevel
                    height: implicitHeight * root.zoomLevel
                    source: root.imagePath
                    asynchronous: true
                    fillMode: Image.PreserveAspectFit
                    cache: false

                    onStatusChanged: {
                        if (status === Image.Ready) {
                            zoomToFit()
                        }
                    }
                }

                // Annotation overlay layer
                Item {
                    id: annotationLayer
                    anchors.fill: parent

                    Repeater {
                        model: root.annotations

                        delegate: Item {
                            id: annDelegate
                            width: flickable.width
                            height: flickable.height
                            property var annData: modelData
                            property int annIndex: index
                            property bool isSelected: root.selectedIndex === index

                            // Rect / Redact / Highlight
                            Rectangle {
                                visible: annData.type === "rect" || annData.type === "redact" || annData.type === "highlight"
                                x: annData.x * root.zoomLevel + root.panOffset.x
                                y: annData.y * root.zoomLevel + root.panOffset.y
                                width: annData.width * root.zoomLevel
                                height: annData.height * root.zoomLevel
                                color: {
                                    if (annData.type === "redact") return annData.color || "#000000"
                                    if (annData.type === "highlight") {
                                        var c = Qt.color(annData.color || "#FFFF00")
                                        return Qt.rgba(c.r, c.g, c.b, 0.3)
                                    }
                                    return "transparent"
                                }
                                border.color: annData.type === "rect" ? (annData.color || "#FF0000") : "transparent"
                                border.width: annData.type === "rect" ? annData.strokeWidth * root.zoomLevel : 0

                                // Selection outline
                                Rectangle {
                                    anchors.fill: parent
                                    anchors.margins: -2
                                    color: "transparent"
                                    border.color: Theme.accent
                                    border.width: 2
                                    visible: annDelegate.isSelected
                                }

                                // Resize handles (when selected)
                                Repeater {
                                    model: annDelegate.isSelected ? [0, 1, 2, 3, 4, 5, 6, 7] : []
                                    Rectangle {
                                        property int handleIdx: modelData
                                        width: 8; height: 8
                                        radius: 4
                                        color: Theme.accent
                                        x: {
                                            if (handleIdx === 0 || handleIdx === 6 || handleIdx === 7) return parent.x - 4
                                            if (handleIdx === 1 || handleIdx === 5) return parent.x + parent.width / 2 - 4
                                            return parent.x + parent.width - 4
                                        }
                                        y: {
                                            if (handleIdx === 0 || handleIdx === 1 || handleIdx === 2) return parent.y - 4
                                            if (handleIdx === 3 || handleIdx === 7) return parent.y + parent.height / 2 - 4
                                            return parent.y + parent.height - 4
                                        }

                                        MouseArea {
                                            anchors.fill: parent
                                            cursorShape: {
                                                if (handleIdx === 0 || handleIdx === 4) return Qt.SizeFDiagCursor
                                                if (handleIdx === 2 || handleIdx === 6) return Qt.SizeBDiagCursor
                                                if (handleIdx === 1 || handleIdx === 5) return Qt.SizeVerCursor
                                                return Qt.SizeHorCursor
                                            }
                                            onPressed: (mouse) => {
                                                root.isResizing = true
                                                root.resizeHandle = handleIdx
                                                root.resizeStartX = mouse.x
                                                root.resizeStartY = mouse.y
                                                root.resizeOrigX = annData.x
                                                root.resizeOrigY = annData.y
                                                root.resizeOrigW = annData.width
                                                root.resizeOrigH = annData.height
                                                mouse.accepted = true
                                            }
                                            onPositionChanged: (mouse) => {
                                                if (!root.isResizing) return
                                                var dx = mouse.x - root.resizeStartX
                                                var dy = mouse.y - root.resizeStartY
                                                var newAnn = JSON.parse(JSON.stringify(annData))
                                                var h = root.resizeHandle

                                                // Handle position updates based on handle index
                                                if (h === 0 || h === 6 || h === 7) {
                                                    newAnn.x = root.resizeOrigX + dx / root.zoomLevel
                                                    newAnn.width = root.resizeOrigW - dx / root.zoomLevel
                                                }
                                                if (h === 2 || h === 4 || h === 5) {
                                                    newAnn.width = root.resizeOrigW + dx / root.zoomLevel
                                                }
                                                if (h === 0 || h === 1 || h === 2) {
                                                    newAnn.y = root.resizeOrigY + dy / root.zoomLevel
                                                    newAnn.height = root.resizeOrigH - dy / root.zoomLevel
                                                }
                                                if (h === 4 || h === 5 || h === 6) {
                                                    newAnn.height = root.resizeOrigH + dy / root.zoomLevel
                                                }

                                                // Enforce minimum size
                                                if (newAnn.width < 5) newAnn.width = 5
                                                if (newAnn.height < 5) newAnn.height = 5

                                                var updated = root.annotations.slice()
                                                updated[annDelegate.annIndex] = newAnn
                                                root.annotations = updated
                                            }
                                            onReleased: {
                                                root.isResizing = false
                                                root.resizeHandle = -1
                }
            }

            // Mouse wheel zoom
            MouseArea {
                anchors.fill: parent
                z: 50
                acceptedButtons: Qt.NoButton
                onWheel: (wheel) => {
                    var delta = wheel.angleDelta.y > 0 ? 0.15 : -0.15
                    root.zoomLevel = Math.max(root.minZoom, Math.min(root.maxZoom, root.zoomLevel + delta))
                }
            }
        }
                                }
                            }

                            // Arrow
                            Canvas {
                                id: arrowCanvas
                                visible: annData.type === "arrow"
                                anchors.fill: parent
                                z: 1

                                onPaint: {
                                    var ctx = getContext("2d")
                                    ctx.clearRect(0, 0, width, height)
                                    ctx.strokeStyle = annData.color || "#FF0000"
                                    ctx.fillStyle = annData.color || "#FF0000"
                                    ctx.lineWidth = annData.strokeWidth * root.zoomLevel
                                    ctx.lineCap = "round"

                                    var x1 = annData.x1 * root.zoomLevel + root.panOffset.x
                                    var y1 = annData.y1 * root.zoomLevel + root.panOffset.y
                                    var x2 = annData.x2 * root.zoomLevel + root.panOffset.x
                                    var y2 = annData.y2 * root.zoomLevel + root.panOffset.y

                                    // Line
                                    ctx.beginPath()
                                    ctx.moveTo(x1, y1)
                                    ctx.lineTo(x2, y2)
                                    ctx.stroke()

                                    // Arrowhead
                                    var angle = Math.atan2(y2 - y1, x2 - x1)
                                    var len = 12 * root.zoomLevel
                                    var ang = Math.PI / 6
                                    ctx.beginPath()
                                    ctx.moveTo(x2, y2)
                                    ctx.lineTo(x2 - len * Math.cos(angle - ang), y2 - len * Math.sin(angle - ang))
                                    ctx.lineTo(x2 - len * Math.cos(angle + ang), y2 - len * Math.sin(angle + ang))
                                    ctx.closePath()
                                    ctx.fill()
                                }

                                Connections {
                                    target: root
                                    function onAnnotationsChanged() { arrowCanvas.requestPaint() }
                                    function onZoomLevelChanged() { arrowCanvas.requestPaint() }
                                    function onPanOffsetChanged() { arrowCanvas.requestPaint() }
                                }
                            }

                            // Freehand
                            Canvas {
                                id: freehandCanvas
                                visible: annData.type === "freehand"
                                anchors.fill: parent
                                z: 1

                                onPaint: {
                                    var ctx = getContext("2d")
                                    ctx.clearRect(0, 0, width, height)
                                    ctx.strokeStyle = annData.color || "#FF0000"
                                    ctx.lineWidth = annData.strokeWidth * root.zoomLevel
                                    ctx.lineCap = "round"
                                    ctx.lineJoin = "round"

                                    if (!annData.points || annData.points.length < 2) return

                                    ctx.beginPath()
                                    var p0 = annData.points[0]
                                    ctx.moveTo(p0.x * root.zoomLevel + root.panOffset.x, p0.y * root.zoomLevel + root.panOffset.y)
                                    for (var i = 1; i < annData.points.length; i++) {
                                        var pt = annData.points[i]
                                        ctx.lineTo(pt.x * root.zoomLevel + root.panOffset.x, pt.y * root.zoomLevel + root.panOffset.y)
                                    }
                                    ctx.stroke()
                                }

                                Connections {
                                    target: root
                                    function onAnnotationsChanged() { freehandCanvas.requestPaint() }
                                    function onZoomLevelChanged() { freehandCanvas.requestPaint() }
                                    function onPanOffsetChanged() { freehandCanvas.requestPaint() }
                                }
                            }

                            // Text
                            Text {
                                visible: annData.type === "text"
                                x: annData.x * root.zoomLevel + root.panOffset.x
                                y: (annData.y - annData.fontSize) * root.zoomLevel + root.panOffset.y
                                text: annData.text || ""
                                font.family: "Segoe UI"
                                font.pixelSize: (annData.fontSize || 16) * root.zoomLevel
                                font.weight: Font.DemiBold
                                color: annData.color || "#FF0000"

                                // Shadow
                                layer.enabled: true
                                layer.effect: null
                            }

                            // Selection outline for text
                            Rectangle {
                                visible: annData.type === "text" && isSelected
                                x: annData.x * root.zoomLevel + root.panOffset.x - 4
                                y: (annData.y - annData.fontSize) * root.zoomLevel + root.panOffset.y - 4
                                width: textLabel.implicitWidth + 8
                                height: annData.fontSize * root.zoomLevel + 8
                                color: "transparent"
                                border.color: Theme.accent
                                border.width: 2

                                Text {
                                    id: textLabel
                                    anchors.centerIn: parent
                                    text: annData.text || ""
                                    font.family: "Segoe UI"
                                    font.pixelSize: (annData.fontSize || 16) * root.zoomLevel
                                    visible: false
                                }
                            }
                        }
                    }

                    // Live drawing preview
                    Canvas {
                        id: drawPreview
                        anchors.fill: parent
                        z: 100

                        onPaint: {
                            var ctx = getContext("2d")
                            ctx.clearRect(0, 0, width, height)

                            if (!root.isDrawing) return

                            ctx.strokeStyle = root.activeColor
                            ctx.fillStyle = root.activeColor
                            ctx.lineWidth = root.strokeWidth * root.zoomLevel
                            ctx.setLineDash([5, 3])

                            var sx = root.drawStartX * root.zoomLevel + root.panOffset.x
                            var sy = root.drawStartY * root.zoomLevel + root.panOffset.y

                            if (root.activeTool === "rect" || root.activeTool === "redact" || root.activeTool === "highlight") {
                                var last = root.currentPath.length > 0 ? root.currentPath[root.currentPath.length - 1] : null
                                if (!last) return
                                var ex = last.x * root.zoomLevel + root.panOffset.x
                                var ey = last.y * root.zoomLevel + root.panOffset.y

                                var rx = Math.min(sx, ex), ry = Math.min(sy, ey)
                                var rw = Math.abs(ex - sx), rh = Math.abs(ey - sy)

                                if (root.activeTool === "redact") {
                                    ctx.setLineDash([])
                                    ctx.globalAlpha = 0.7
                                    ctx.fillRect(rx, ry, rw, rh)
                                    ctx.globalAlpha = 1.0
                                } else if (root.activeTool === "highlight") {
                                    ctx.setLineDash([])
                                    ctx.globalAlpha = 0.3
                                    ctx.fillRect(rx, ry, rw, rh)
                                    ctx.globalAlpha = 1.0
                                } else {
                                    ctx.strokeRect(rx, ry, rw, rh)
                                }
                            } else if (root.activeTool === "arrow") {
                                var lastPt = root.currentPath.length > 0 ? root.currentPath[root.currentPath.length - 1] : null
                                if (!lastPt) return
                                var ax2 = lastPt.x * root.zoomLevel + root.panOffset.x
                                var ay2 = lastPt.y * root.zoomLevel + root.panOffset.y

                                ctx.beginPath()
                                ctx.moveTo(sx, sy)
                                ctx.lineTo(ax2, ay2)
                                ctx.stroke()

                                var angle = Math.atan2(ay2 - sy, ax2 - sx)
                                var len = 12 * root.zoomLevel
                                var ang = Math.PI / 6
                                ctx.setLineDash([])
                                ctx.beginPath()
                                ctx.moveTo(ax2, ay2)
                                ctx.lineTo(ax2 - len * Math.cos(angle - ang), ay2 - len * Math.sin(angle - ang))
                                ctx.lineTo(ax2 - len * Math.cos(angle + ang), ay2 - len * Math.sin(angle + ang))
                                ctx.closePath()
                                ctx.fill()
                            } else if (root.activeTool === "freehand" && root.currentPath.length > 1) {
                                ctx.setLineDash([])
                                ctx.lineCap = "round"
                                ctx.lineJoin = "round"
                                ctx.beginPath()
                                var fp0 = root.currentPath[0]
                                ctx.moveTo(fp0.x * root.zoomLevel + root.panOffset.x, fp0.y * root.zoomLevel + root.panOffset.y)
                                for (var fi = 1; fi < root.currentPath.length; fi++) {
                                    var fp = root.currentPath[fi]
                                    ctx.lineTo(fp.x * root.zoomLevel + root.panOffset.x, fp.y * root.zoomLevel + root.panOffset.y)
                                }
                                ctx.stroke()
                            } else if (root.activeTool === "text") {
                                // Show cursor position indicator
                                ctx.setLineDash([])
                                ctx.strokeStyle = root.activeColor
                                ctx.lineWidth = 2
                                ctx.beginPath()
                                ctx.moveTo(sx - 8, sy)
                                ctx.lineTo(sx + 8, sy)
                                ctx.moveTo(sx, sy - 8)
                                ctx.lineTo(sx, sy + 8)
                                ctx.stroke()
                            }
                        }
                    }

                    // Drawing interaction area
                    MouseArea {
                        id: drawArea
                        anchors.fill: parent
                        z: 200
                        enabled: root.activeTool !== "none" || root.selectedIndex >= 0
                        cursorShape: {
                            if (root.activeTool === "text") return Qt.IBeamCursor
                            if (root.activeTool !== "none") return Qt.CrossCursor
                            return Qt.ArrowCursor
                        }

                        onPressed: (mouse) => {
                            if (root.activeTool === "none") {
                                // Check if clicking on an annotation to select it
                                var imgPt = canvasToImage(mouse.x, mouse.y)
                                var hitIdx = getAnnotationAt(imgPt.x, imgPt.y)
                                if (hitIdx >= 0) {
                                    root.selectedIndex = hitIdx
                                    // Start dragging
                                    root.isDragging = true
                                    var ann = root.annotations[hitIdx]
                                    if (ann.type === "arrow") {
                                        root.dragOffsetX = imgPt.x - ann.x1
                                        root.dragOffsetY = imgPt.y - ann.y1
                                    } else {
                                        root.dragOffsetX = imgPt.x - ann.x
                                        root.dragOffsetY = imgPt.y - ann.y
                                    }
                                } else {
                                    root.selectedIndex = -1
                                }
                                return
                            }

                            var imgPt = canvasToImage(mouse.x, mouse.y)
                            root.drawStartX = imgPt.x
                            root.drawStartY = imgPt.y
                            root.currentPath = [Qt.point(imgPt.x, imgPt.y)]
                            root.isDrawing = true

                            if (root.activeTool === "text") {
                                root.textInputX = mouse.x
                                root.textInputY = mouse.y
                                root.textInputValue = ""
                                root.isTextInputActive = true
                                root.isDrawing = false
                            }
                        }

                        onPositionChanged: (mouse) => {
                            if (root.isDragging && root.selectedIndex >= 0) {
                                var imgPt = canvasToImage(mouse.x, mouse.y)
                                var updated = root.annotations.slice()
                                var ann = JSON.parse(JSON.stringify(updated[root.selectedIndex]))
                                if (ann.type === "arrow") {
                                    var dx = imgPt.x - root.dragOffsetX - ann.x1
                                    var dy = imgPt.y - root.dragOffsetY - ann.y1
                                    ann.x1 += dx; ann.y1 += dy
                                    ann.x2 += dx; ann.y2 += dy
                                } else if (ann.type === "text") {
                                    ann.x = imgPt.x - root.dragOffsetX
                                    ann.y = imgPt.y - root.dragOffsetY
                                } else if (ann.type === "freehand" && ann.points) {
                                    var firstPt = ann.points[0]
                                    var fdx = imgPt.x - root.dragOffsetX - firstPt.x
                                    var fdy = imgPt.y - root.dragOffsetY - firstPt.y
                                    for (var fi = 0; fi < ann.points.length; fi++) {
                                        ann.points[fi] = { x: ann.points[fi].x + fdx, y: ann.points[fi].y + fdy }
                                    }
                                } else {
                                    ann.x = imgPt.x - root.dragOffsetX
                                    ann.y = imgPt.y - root.dragOffsetY
                                }
                                updated[root.selectedIndex] = ann
                                root.annotations = updated
                                return
                            }

                            if (!root.isDrawing) return
                            var imgPt = canvasToImage(mouse.x, mouse.y)

                            if (root.activeTool === "freehand") {
                                root.currentPath.push(Qt.point(imgPt.x, imgPt.y))
                            } else {
                                root.currentPath = [Qt.point(root.drawStartX, root.drawStartY), Qt.point(imgPt.x, imgPt.y)]
                            }
                            drawPreview.requestPaint()
                        }

                        onReleased: {
                            if (root.isDragging) {
                                root.isDragging = false
                                return
                            }

                            if (!root.isDrawing) return
                            root.isDrawing = false
                            drawPreview.requestPaint()

                            var newAnn = null

                            if (root.activeTool === "rect" || root.activeTool === "redact" || root.activeTool === "highlight") {
                                if (root.currentPath.length >= 2) {
                                    var p1 = root.currentPath[0], p2 = root.currentPath[1]
                                    var rx = Math.min(p1.x, p2.x), ry = Math.min(p1.y, p2.y)
                                    var rw = Math.abs(p2.x - p1.x), rh = Math.abs(p2.y - p1.y)
                                    if (rw > 3 && rh > 3) {
                                        newAnn = {
                                            type: root.activeTool,
                                            x: rx, y: ry, width: rw, height: rh,
                                            color: root.activeColor.toString(), strokeWidth: root.strokeWidth
                                        }
                                    }
                                }
                            } else if (root.activeTool === "arrow") {
                                if (root.currentPath.length >= 2) {
                                    var a1 = root.currentPath[0], a2 = root.currentPath[1]
                                    var dist = Math.sqrt((a2.x - a1.x) ** 2 + (a2.y - a1.y) ** 2)
                                    if (dist > 5) {
                                        newAnn = {
                                            type: "arrow",
                                            x1: a1.x, y1: a1.y, x2: a2.x, y2: a2.y,
                                            color: root.activeColor.toString(), strokeWidth: root.strokeWidth
                                        }
                                    }
                                }
                            } else if (root.activeTool === "freehand") {
                                if (root.currentPath.length > 2) {
                                    var pts = []
                                    for (var pi = 0; pi < root.currentPath.length; pi++) {
                                        pts.push({ x: root.currentPath[pi].x, y: root.currentPath[pi].y })
                                    }
                                    newAnn = {
                                        type: "freehand", points: pts,
                                        color: root.activeColor.toString(), strokeWidth: root.strokeWidth
                                    }
                                }
                            }

                            if (newAnn) {
                                var updated = root.annotations.slice()
                                updated.push(newAnn)
                                root.annotations = updated
                            }

                            root.currentPath = []
                        }
                    }

                    // Inline text input
                    Rectangle {
                        id: textInputOverlay
                        visible: root.isTextInputActive
                        x: root.textInputX - 4
                        y: root.textInputY - 24
                        width: Math.max(150, textInputField.implicitWidth + 16)
                        height: 32
                        color: Theme.glassPill
                        border.color: Theme.accent
                        border.width: 1
                        radius: Theme.radiusSmall
                        z: 300

                        TextInput {
                            id: textInputField
                            anchors.fill: parent
                            anchors.margins: 6
                            color: Theme.label
                            font.family: "Segoe UI"
                            font.pixelSize: 14
                            clip: true
                            focus: root.isTextInputActive
                            Keys.onReturnPressed: commitText()
                            Keys.onEnterPressed: commitText()
                            Keys.onEscapePressed: root.isTextInputActive = false

                            function commitText() {
                                if (text.length > 0) {
                                    var imgPt = canvasToImage(root.textInputX, root.textInputY)
                                    var updated = root.annotations.slice()
                                    updated.push({
                                        type: "text",
                                        x: imgPt.x, y: imgPt.y,
                                        text: text,
                                        color: root.activeColor.toString(),
                                        fontSize: 16
                                    })
                                    root.annotations = updated
                                }
                                root.isTextInputActive = false
                                text = ""
                            }
                        }
                    }
                }
            }

            // Zoom indicator overlay
            Rectangle {
                anchors.bottom: parent.bottom
                anchors.right: parent.right
                anchors.margins: 8
                width: zoomLabel.implicitWidth + 16
                height: 28
                color: Theme.alpha(Theme.glassPill, 0.8)
                radius: Theme.radiusSmall
                visible: root.zoomLevel !== 1.0

                Text {
                    id: zoomLabel
                    anchors.centerIn: parent
                    text: Math.round(root.zoomLevel * 100) + "%"
                    font.family: Theme.fontFamily
                    font.pixelSize: 11
                    color: Theme.secondaryLabel
                }
            }
        }

        // === Annotation Toolbar ===
        Rectangle {
            id: annotationToolbar
            Layout.fillWidth: true
            Layout.preferredHeight: 52
            Layout.leftMargin: 4
            Layout.rightMargin: 4
            Layout.bottomMargin: 4
            color: Theme.glassHover
            radius: Theme.radiusSmall

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 8
                anchors.rightMargin: 8
                spacing: 4

                // Tool buttons
                Repeater {
                    model: [
                        { tool: "rect", icon: "\u25A1", tip: "Rectangle" },
                        { tool: "arrow", icon: "\u2192", tip: "Arrow" },
                        { tool: "redact", icon: "\u2588", tip: "Redact" },
                        { tool: "freehand", icon: "\u270E", tip: "Freehand" },
                        { tool: "text", icon: "T", tip: "Text" },
                        { tool: "highlight", icon: "\u2593", tip: "Highlight" }
                    ]

                    IconButton {
                        required property var modelData
                        iconText: modelData.icon
                        tooltipText: modelData.tip
                        role: root.activeTool === modelData.tool ? "primary" : "ghost"
                        buttonSize: 32
                        iconSize: 14
                        onClicked: {
                            if (root.activeTool === modelData.tool) {
                                root.activeTool = "none"
                            } else {
                                root.activeTool = modelData.tool
                            }
                            root.selectedIndex = -1
                        }
                    }
                }

                Rectangle {
                    width: 1; height: 24
                    color: Theme.separator
                    Layout.leftMargin: 4
                    Layout.rightMargin: 4
                }

                // Color picker
                Repeater {
                    model: root.presetColors

                    Rectangle {
                        required property string modelData
                        required property int index
                        property bool isSelected: root.activeColor.toString().toUpperCase() === modelData

                        width: isSelected ? 24 : 20
                        height: isSelected ? 24 : 20
                        radius: isSelected ? 12 : 10
                        color: modelData
                        border.color: isSelected ? Theme.accent : Theme.glassBorder
                        border.width: isSelected ? 2 : 1
                        opacity: isSelected ? 1.0 : 0.7

                        Behavior on width { NumberAnimation { duration: 120; easing.type: Easing.OutBack } }
                        Behavior on height { NumberAnimation { duration: 120; easing.type: Easing.OutBack } }
                        Behavior on radius { NumberAnimation { duration: 120 } }

                        // Checkmark overlay when selected
                        Rectangle {
                            anchors.fill: parent
                            radius: parent.radius
                            color: "transparent"
                            visible: isSelected
                            Text {
                                anchors.centerIn: parent
                                text: "\u2713"
                                color: "white"
                                font.pixelSize: 11
                                font.bold: true
                                style: Text.Outline
                                styleColor: Qt.rgba(0, 0, 0, 0.4)
                            }
                        }

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.activeColor = Qt.color(modelData)
                        }
                    }
                }

                Rectangle {
                    width: 1; height: 24
                    color: Theme.separator
                    Layout.leftMargin: 4
                    Layout.rightMargin: 4
                }

                // Stroke width
                Text {
                    text: "Size:"
                    font.family: Theme.fontFamily
                    font.pixelSize: 11
                    color: Theme.secondaryLabel
                }

                Repeater {
                    model: [2, 3, 4, 8]

                    Rectangle {
                        required property int modelData
                        property bool isSelected: root.strokeWidth === modelData

                        width: 24; height: 24
                        radius: 4
                        color: isSelected ? Theme.accent : "transparent"
                        border.color: isSelected ? Theme.accent : Theme.glassBorder
                        border.width: isSelected ? 2 : 1

                        Rectangle {
                            anchors.centerIn: parent
                            width: modelData + 2
                            height: modelData + 2
                            radius: (modelData + 2) / 2
                            color: isSelected ? "white" : Theme.label
                        }

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.strokeWidth = modelData
                        }
                    }
                }

                Item { Layout.fillWidth: true }

                // Action buttons
                IconButton {
                    iconText: "\u21A9"
                    tooltipText: "Undo (Ctrl+Z)"
                    role: "ghost"
                    buttonSize: 32
                    iconSize: 14
                    enabled: root.annotations.length > 0
                    onClicked: {
                        if (root.selectedIndex >= 0) {
                            var updated = root.annotations.slice()
                            updated.splice(root.selectedIndex, 1)
                            root.annotations = updated
                            root.selectedIndex = -1
                        } else {
                            var updated = root.annotations.slice()
                            updated.pop()
                            root.annotations = updated
                        }
                    }
                }

                IconButton {
                    iconText: "\u2716"
                    tooltipText: "Clear All"
                    role: "ghost"
                    buttonSize: 32
                    iconSize: 14
                    enabled: root.annotations.length > 0
                    onClicked: {
                        root.annotations = []
                        root.selectedIndex = -1
                    }
                }

                ActionButton {
                    text: "Apply & Save"
                    role: "primary"
                    enabled: root.annotations.length > 0
                    buttonHeight: 32
                    onClicked: {
                        AppController.image_inspector_controller.saveAnnotations(root.imagePath, root.annotations)
                        root.annotations = []
                        root.selectedIndex = -1
                    }
                }
            }
        }
    }

    // --- Keyboard Shortcuts ---
    Shortcut {
        sequence: "Ctrl+Z"
        context: Qt.ApplicationShortcut
        onActivated: {
            if (root.annotations.length > 0) {
                if (root.selectedIndex >= 0) {
                    var updated = root.annotations.slice()
                    updated.splice(root.selectedIndex, 1)
                    root.annotations = updated
                    root.selectedIndex = -1
                } else {
                    var updated = root.annotations.slice()
                    updated.pop()
                    root.annotations = updated
                }
            }
        }
    }

    Shortcut {
        sequence: "Escape"
        context: Qt.ApplicationShortcut
        onActivated: {
            if (root.isTextInputActive) {
                root.isTextInputActive = false
            } else if (root.activeTool !== "none") {
                root.activeTool = "none"
            } else if (root.selectedIndex >= 0) {
                root.selectedIndex = -1
            } else {
                root.closed()
            }
        }
    }

    Shortcut {
        sequence: "Ctrl+0"
        context: Qt.ApplicationShortcut
        onActivated: zoomToFit()
    }

    Shortcut {
        sequence: "Ctrl+1"
        context: Qt.ApplicationShortcut
        onActivated: root.zoomLevel = 1.0
    }

    Shortcut {
        sequence: "Ctrl+Plus"
        context: Qt.ApplicationShortcut
        onActivated: root.zoomLevel = Math.min(root.maxZoom, root.zoomLevel + 0.25)
    }

    Shortcut {
        sequence: "Ctrl+Minus"
        context: Qt.ApplicationShortcut
        onActivated: root.zoomLevel = Math.max(root.minZoom, root.zoomLevel - 0.25)
    }

    // --- Helper functions ---
    function zoomToFit() {
        if (imageItem.implicitWidth <= 0 || imageItem.implicitHeight <= 0) return
        var cw = canvasContainer.width
        var ch = canvasContainer.height
        var scaleX = cw / imageItem.implicitWidth
        var scaleY = ch / imageItem.implicitHeight
        root.zoomLevel = Math.min(scaleX, scaleY) * 0.95
        root.panOffset = Qt.point(
            (cw - imageItem.implicitWidth * root.zoomLevel) / 2,
            (ch - imageItem.implicitHeight * root.zoomLevel) / 2
        )
    }

    function toggleFullscreen() {
        root.isFullscreen = !root.isFullscreen
        if (root.isFullscreen) {
            zoomToFit()
        }
    }

    // --- Width animation ---
    Behavior on width {
        NumberAnimation { duration: 300; easing.type: Easing.OutQuart }
    }
}

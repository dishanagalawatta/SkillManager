import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import QtQuick.Dialogs
import App 1.0

Rectangle {
    id: root

    readonly property var _sel: AppController.selectedSkill || ({})
    property var skill: _sel
    property bool isCollapsed: false

    readonly property int targetWidth: {
        if (!root._sel || root._sel.local_path === undefined) return 0;
        if (isCollapsed) return 32;

        let dynamicWidth = parent ? parent.width * 0.5 : 440;
        return Math.min(800, Math.max(440, dynamicWidth));
    }

    signal closed()

    FontPickerDialog {
        id: fontPickerDialog
        selectedFamily: root.activeFontFamily
        selectedSize: root.activeFontSize
        previewColor: root.activeColor
        onFontSelected: (family, style, size) => {
            root.activeFontFamily = family
            root.activeFontSize = size
        }
    }

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
        if (!root._sel || !root._sel.is_screenshot || !root._sel.local_path) return "";
        let p = root._sel.local_path.replace(/\\/g, "/");
        if (p.startsWith("/")) return "file://" + p;
        return "file:///" + p;
    }
    property bool imageLoadFailed: false
    onImagePathChanged: { imageLoadFailed = false }
    property string imageFileName: {
        if (!root._sel || !root._sel.local_path) return "";
        let parts = root._sel.local_path.replace(/\\/g, "/").split("/");
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
    property var redoStack: []
    property int selectedIndex: -1
    property bool isDrawing: false
    property real drawStartX: 0
    property real drawStartY: 0
    property var currentPath: []
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

    // Eraser properties
    property real eraserRadius: 20

    // Font properties
    property string activeFontFamily: "Segoe UI"
    property int activeFontSize: 16

    // Preset colors for the color picker
    property var presetColors: [
        "#FF0000", "#FF6B00", "#FFD600", "#00C853",
        "#00B0FF", "#3D5AFE", "#AA00FF", "#FF4081",
        "#FFFFFF", "#000000"
    ]

    function getAnnotationAt(mx, my) {
        for (var i = annotations.length - 1; i >= 0; i--) {
            var a = annotations[i]
            if (a.type === "rect" || a.type === "filledRect" || a.type === "highlight") {
                if (mx >= a.x && mx <= a.x + a.width && my >= a.y && my <= a.y + a.height)
                    return i
            } else if (a.type === "ellipse" || a.type === "filledEllipse") {
                var cx = a.x + a.width / 2
                var cy = a.y + a.height / 2
                var rx = Math.abs(a.width / 2)
                var ry = Math.abs(a.height / 2)
                if (rx > 0 && ry > 0) {
                    var dx = (mx - cx) / rx
                    var dy = (my - cy) / ry
                    if (dx * dx + dy * dy <= 1.0) return i
                }
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

    function getAnnotationsUnderEraser(mx, my, radius) {
        var indicesToRemove = []
        for (var i = annotations.length - 1; i >= 0; i--) {
            var a = annotations[i]
            if (isAnnotationHitByEraser(a, mx, my, radius)) {
                indicesToRemove.push(i)
            }
        }
        return indicesToRemove
    }

    function isAnnotationHitByEraser(ann, ex, ey, radius) {
        if (ann.type === "rect" || ann.type === "filledRect" || ann.type === "highlight") {
            return ex >= ann.x && ex <= ann.x + ann.width && ey >= ann.y && ey <= ann.y + ann.height
        } else if (ann.type === "ellipse" || ann.type === "filledEllipse") {
            var cx = ann.x + ann.width / 2
            var cy = ann.y + ann.height / 2
            var rx = Math.abs(ann.width / 2)
            var ry = Math.abs(ann.height / 2)
            if (rx === 0 || ry === 0) return false
            var dx = (ex - cx) / rx
            var dy = (ey - cy) / ry
            return (dx * dx + dy * dy) <= 1.0
        } else if (ann.type === "arrow") {
            var dist = pointToSegmentDistance(ex, ey, ann.x1, ann.y1, ann.x2, ann.y2)
            return dist < radius
        } else if (ann.type === "text") {
            var textWidth = (ann.text || "").length * (ann.fontSize || 16) * 0.6
            var textHeight = (ann.fontSize || 16) * 1.4
            return ex >= ann.x - 5 && ex <= ann.x + textWidth && ey >= ann.y - textHeight && ey <= ann.y + 5
        } else if (ann.type === "freehand" && ann.points) {
            for (var j = 0; j < ann.points.length; j++) {
                var dx = ex - ann.points[j].x
                var dy = ey - ann.points[j].y
                if (Math.sqrt(dx * dx + dy * dy) < radius) return true
            }
        }
        return false
    }

    function pointToSegmentDistance(px, py, x1, y1, x2, y2) {
        var dx = x2 - x1, dy = y2 - y1
        var lenSq = dx * dx + dy * dy
        if (lenSq === 0) return Math.sqrt((px - x1) ** 2 + (py - y1) ** 2)
        var t = Math.max(0, Math.min(1, ((px - x1) * dx + (py - y1) * dy) / lenSq))
        var projX = x1 + t * dx, projY = y1 + t * dy
        return Math.sqrt((px - projX) ** 2 + (py - projY) ** 2)
    }

    function eraseAtPoint(mx, my) {
        var indices = getAnnotationsUnderEraser(mx, my, root.eraserRadius / root.zoomLevel)
        if (indices.length > 0) {
            var updated = root.annotations.slice()
            for (var k = 0; k < indices.length; k++) {
                var removed = updated.splice(indices[k], 1)[0]
                var rs = root.redoStack.slice()
                rs.push(removed)
                root.redoStack = rs
            }
            root.annotations = updated
        }
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
                    text: root._sel ? (root._sel.name || "Untitled") : ""
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.sizeBody
                    font.weight: Font.DemiBold
                    color: Theme.label
                    elide: Text.ElideRight
                    verticalAlignment: Text.AlignVCenter
                }

                // Zoom controls
                IconButton {
                    iconSource: AppController.ui_controller.getAssetUri("ui/tool-minus.svg")
                    tooltipText: "Zoom Out (Ctrl+-)"
                    role: "ghost"
                    buttonSize: 28
                    iconSize: 14
                    onClicked: root.zoomLevel = Math.max(root.minZoom, root.zoomLevel - 0.25)
                }

                Item {
                    Layout.preferredWidth: 44
                    Layout.preferredHeight: 28

                    TextInput {
                        id: zoomInput
                        anchors.fill: parent
                        text: Math.round(root.zoomLevel * 100) + "%"
                        font.family: Theme.fontFamily
                        font.pixelSize: 11
                        color: Theme.label
                        horizontalAlignment: TextInput.AlignHCenter
                        verticalAlignment: TextInput.AlignVCenter
                        selectByMouse: true
                        
                        onEditingFinished: {
                            let val = parseInt(text.replace("%", ""))
                            if (!isNaN(val)) {
                                root.zoomLevel = Math.max(root.minZoom, Math.min(root.maxZoom, val / 100.0))
                            }
                            text = Math.round(root.zoomLevel * 100) + "%"
                            focus = false
                        }
                        
                        MouseArea {
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.IBeamCursor
                            acceptedButtons: Qt.NoButton
                            onEntered: zoomPopup.open()
                            onExited: zoomHoverTimer.restart()
                        }
                    }

                    Timer {
                        id: zoomHoverTimer
                        interval: 300
                        onTriggered: {
                            if (!popupHover.hovered) {
                                zoomPopup.close()
                            }
                        }
                    }

                    Popup {
                        id: zoomPopup
                        y: parent.height
                        x: (parent.width - width) / 2
                        width: 60
                        padding: 4
                        background: Rectangle {
                            color: Theme.glassPill
                            border.color: Theme.glassBorder
                            radius: Theme.radiusSmall
                        }

                        contentItem: Item {
                            implicitWidth: 52
                            implicitHeight: zoomColumn.implicitHeight

                            HoverHandler {
                                id: popupHover
                                onHoveredChanged: {
                                    if (hovered) zoomHoverTimer.stop()
                                    else zoomHoverTimer.restart()
                                }
                            }

                            Column {
                                id: zoomColumn
                                anchors.fill: parent
                                spacing: 2

                                Repeater {
                                    model: [25, 50, 75, 100, 150, 200, 400]
                                    Rectangle {
                                        width: parent.width
                                        height: 24
                                        color: itemMouse.containsMouse ? Theme.glassHover : "transparent"
                                        radius: Theme.radiusSmall

                                        Text {
                                            anchors.centerIn: parent
                                            text: modelData + "%"
                                            font.family: Theme.fontFamily
                                            font.pixelSize: 11
                                            color: itemMouse.containsMouse ? Theme.label : Theme.secondaryLabel
                                        }

                                        MouseArea {
                                            id: itemMouse
                                            anchors.fill: parent
                                            hoverEnabled: true
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: {
                                                root.zoomLevel = modelData / 100.0
                                                zoomPopup.close()
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                IconButton {
                    iconSource: AppController.ui_controller.getAssetUri("ui/tool-plus.svg")
                    tooltipText: "Zoom In (Ctrl++)"
                    role: "ghost"
                    buttonSize: 28
                    iconSize: 14
                    onClicked: root.zoomLevel = Math.min(root.maxZoom, root.zoomLevel + 0.25)
                }

                IconButton {
                    iconSource: AppController.ui_controller.getAssetUri("ui/tool-scan.svg")
                    tooltipText: "Zoom to Fit (Ctrl+0)"
                    role: "ghost"
                    buttonSize: 28
                    iconSize: 14
                    onClicked: zoomToFit()
                }

                Rectangle {
                    width: 1
                    height: 20
                    color: Theme.separator
                }

                // Action buttons
                IconButton {
                    iconSource: AppController.ui_controller.getAssetUri("ui/tool-undo.svg")
                    tooltipText: "Undo (Ctrl+Z)"
                    role: "ghost"
                    buttonSize: 28
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
                            var popped = updated.pop()
                            if (popped) {
                                var rs = root.redoStack.slice()
                                rs.push(popped)
                                root.redoStack = rs
                            }
                            root.annotations = updated
                        }
                    }
                }

                IconButton {
                    iconSource: AppController.ui_controller.getAssetUri("ui/tool-redo.svg")
                    tooltipText: "Redo (Ctrl+Y)"
                    role: "ghost"
                    buttonSize: 28
                    iconSize: 14
                    enabled: root.redoStack.length > 0
                    onClicked: {
                        var rs = root.redoStack.slice()
                        var item = rs.pop()
                        root.redoStack = rs
                        if (item) {
                            var updated = root.annotations.slice()
                            updated.push(item)
                            root.annotations = updated
                        }
                    }
                }

                IconButton {
                    iconSource: AppController.ui_controller.getAssetUri("ui/tool-x.svg")
                    tooltipText: "Clear All"
                    role: "ghost"
                    buttonSize: 28
                    iconSize: 14
                    enabled: root.annotations.length > 0
                    onClicked: {
                        root.annotations = []
                        root.redoStack = []
                        root.selectedIndex = -1
                    }
                }

                Rectangle {
                    width: 1
                    height: 20
                    color: Theme.separator
                }

                IconButton {
                    iconSource: AppController.ui_controller.getAssetUri("ui/tool-external-link.svg")
                    tooltipText: "Open Externally"
                    role: "ghost"
                    buttonSize: 28
                    iconSize: 14
                    onClicked: AppController.image_inspector_controller.openExternally(root.imagePath)
                }

                ActionButton {
                    text: "Apply"
                    role: "primary"
                    enabled: root.annotations.length > 0
                    buttonHeight: 28
                    onClicked: {
                        AppController.image_inspector_controller.saveAnnotations(root.imagePath, root.annotations)
                        root.annotations = []
                        root.redoStack = []
                        root.selectedIndex = -1
                    }
                }

                IconButton {
                    iconSource: AppController.ui_controller.getAssetUri("ui/tool-x.svg")
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
                            root.imageLoadFailed = false
                            zoomToFit()
                        } else if (status === Image.Error) {
                            root.imageLoadFailed = true
                        }
                    }

                    Timer {
                        id: imageReloadTimer
                        interval: 50
                        onTriggered: {
                            imageItem.source = root.imagePath
                        }
                    }

                    Connections {
                        target: AppController.image_inspector_controller
                        function onImageSaved(savedPath) {
                            imageItem.source = ""
                            root.imageLoadFailed = false
                            imageReloadTimer.restart()
                        }
                    }
                }

                // Placeholder shown when screenshot file is missing
                Rectangle {
                    visible: root.imageLoadFailed && root._sel && root._sel.is_screenshot
                    anchors.centerIn: parent
                    width: 320
                    height: 120
                    radius: 8
                    color: "#20FFFFFF"
                    border.color: "#40FFFFFF"
                    border.width: 1

                    Column {
                        anchors.centerIn: parent
                        spacing: 8

                        Text {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: "Screenshot file not found"
                            color: "#AAFFFFFF"
                            font.pixelSize: 14
                            font.bold: true
                        }
                        Text {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: root._sel ? (root._sel.local_path || "") : ""
                            color: "#66FFFFFF"
                            font.pixelSize: 11
                            width: 290
                            wrapMode: Text.Wrap
                            horizontalAlignment: Text.AlignHCenter
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

                            // Rect / FilledRect / Highlight
                            Rectangle {
                                visible: annData.type === "rect" || annData.type === "filledRect" || annData.type === "highlight"
                                x: annData.x * root.zoomLevel + root.panOffset.x
                                y: annData.y * root.zoomLevel + root.panOffset.y
                                width: annData.width * root.zoomLevel
                                height: annData.height * root.zoomLevel
                                color: {
                                    if (annData.type === "filledRect") return annData.color || "#000000"
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

                                    var angle = Math.atan2(y2 - y1, x2 - x1)
                                    var len = (12 + annData.strokeWidth * 2) * root.zoomLevel
                                    var shorten = len * 0.8
                                    var lineX2 = x2 - shorten * Math.cos(angle)
                                    var lineY2 = y2 - shorten * Math.sin(angle)

                                    // Line
                                    ctx.beginPath()
                                    ctx.moveTo(x1, y1)
                                    ctx.lineTo(lineX2, lineY2)
                                    ctx.stroke()

                                    // Arrowhead
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

                            // Ellipse
                            Canvas {
                                id: ellipseCanvas
                                visible: annData.type === "ellipse"
                                anchors.fill: parent
                                z: 1

                                onPaint: {
                                    var ctx = getContext("2d")
                                    ctx.clearRect(0, 0, width, height)
                                    ctx.strokeStyle = annData.color || "#FF0000"
                                    ctx.lineWidth = (annData.strokeWidth || 3) * root.zoomLevel

                                    var cx = (annData.x + annData.width / 2) * root.zoomLevel + root.panOffset.x
                                    var cy = (annData.y + annData.height / 2) * root.zoomLevel + root.panOffset.y
                                    var rx = Math.abs(annData.width / 2) * root.zoomLevel
                                    var ry = Math.abs(annData.height / 2) * root.zoomLevel

                                    ctx.beginPath()
                                    ctx.ellipse(cx, cy, rx, ry, 0, 0, 2 * Math.PI)
                                    ctx.stroke()
                                }

                                Connections {
                                    target: root
                                    function onAnnotationsChanged() { ellipseCanvas.requestPaint() }
                                    function onZoomLevelChanged() { ellipseCanvas.requestPaint() }
                                    function onPanOffsetChanged() { ellipseCanvas.requestPaint() }
                                }
                            }

                            // Filled Ellipse
                            Canvas {
                                id: filledEllipseCanvas
                                visible: annData.type === "filledEllipse"
                                anchors.fill: parent
                                z: 1

                                onPaint: {
                                    var ctx = getContext("2d")
                                    ctx.clearRect(0, 0, width, height)
                                    ctx.fillStyle = annData.color || "#000000"

                                    var cx = (annData.x + annData.width / 2) * root.zoomLevel + root.panOffset.x
                                    var cy = (annData.y + annData.height / 2) * root.zoomLevel + root.panOffset.y
                                    var rx = Math.abs(annData.width / 2) * root.zoomLevel
                                    var ry = Math.abs(annData.height / 2) * root.zoomLevel

                                    ctx.beginPath()
                                    ctx.ellipse(cx, cy, rx, ry, 0, 0, 2 * Math.PI)
                                    ctx.fill()
                                }

                                Connections {
                                    target: root
                                    function onAnnotationsChanged() { filledEllipseCanvas.requestPaint() }
                                    function onZoomLevelChanged() { filledEllipseCanvas.requestPaint() }
                                    function onPanOffsetChanged() { filledEllipseCanvas.requestPaint() }
                                }
                            }

                            // Text
                            Text {
                                visible: annData.type === "text"
                                x: annData.x * root.zoomLevel + root.panOffset.x
                                y: (annData.y - annData.fontSize) * root.zoomLevel + root.panOffset.y
                                text: annData.text || ""
                                font.family: annData.fontFamily || "Segoe UI"
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
                                    font.family: annData.fontFamily || "Segoe UI"
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

                            if (root.activeTool === "rect" || root.activeTool === "filledRect" || root.activeTool === "highlight") {
                                var last = root.currentPath.length > 0 ? root.currentPath[root.currentPath.length - 1] : null
                                if (!last) return
                                var ex = last.x * root.zoomLevel + root.panOffset.x
                                var ey = last.y * root.zoomLevel + root.panOffset.y

                                var rx = Math.min(sx, ex), ry = Math.min(sy, ey)
                                var rw = Math.abs(ex - sx), rh = Math.abs(ey - sy)

                                if (root.activeTool === "filledRect") {
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
                            } else if (root.activeTool === "ellipse" || root.activeTool === "filledEllipse") {
                                var lastEllipse = root.currentPath.length > 0 ? root.currentPath[root.currentPath.length - 1] : null
                                if (!lastEllipse) return
                                var eex = lastEllipse.x * root.zoomLevel + root.panOffset.x
                                var eey = lastEllipse.y * root.zoomLevel + root.panOffset.y

                                var ecx = (sx + eex) / 2
                                var ecy = (sy + eey) / 2
                                var erx = Math.abs(eex - sx) / 2
                                var ery = Math.abs(eey - sy) / 2

                                ctx.beginPath()
                                ctx.ellipse(ecx, ecy, erx, ery, 0, 0, 2 * Math.PI)
                                if (root.activeTool === "filledEllipse") {
                                    ctx.setLineDash([])
                                    ctx.globalAlpha = 0.7
                                    ctx.fill()
                                    ctx.globalAlpha = 1.0
                                } else {
                                    ctx.stroke()
                                }
                            } else if (root.activeTool === "arrow") {
                                var lastPt = root.currentPath.length > 0 ? root.currentPath[root.currentPath.length - 1] : null
                                if (!lastPt) return
                                var ax2 = lastPt.x * root.zoomLevel + root.panOffset.x
                                var ay2 = lastPt.y * root.zoomLevel + root.panOffset.y

                                var angle = Math.atan2(ay2 - sy, ax2 - sx)
                                var len = (12 + root.strokeWidth * 2) * root.zoomLevel
                                var shorten = len * 0.8
                                var lineX2 = ax2 - shorten * Math.cos(angle)
                                var lineY2 = ay2 - shorten * Math.sin(angle)

                                ctx.beginPath()
                                ctx.moveTo(sx, sy)
                                ctx.lineTo(lineX2, lineY2)
                                ctx.stroke()

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
                            } else if (root.activeTool === "eraser") {
                                // Show eraser cursor
                                ctx.setLineDash([4, 2])
                                ctx.strokeStyle = Qt.rgba(1, 0, 0, 0.8)
                                ctx.lineWidth = 2
                                ctx.beginPath()
                                ctx.arc(sx, sy, root.eraserRadius * root.zoomLevel, 0, 2 * Math.PI)
                                ctx.stroke()

                                // Crosshair
                                ctx.setLineDash([])
                                ctx.beginPath()
                                ctx.moveTo(sx - root.eraserRadius * 0.3 * root.zoomLevel, sy)
                                ctx.lineTo(sx + root.eraserRadius * 0.3 * root.zoomLevel, sy)
                                ctx.moveTo(sx, sy - root.eraserRadius * 0.3 * root.zoomLevel)
                                ctx.lineTo(sx, sy + root.eraserRadius * 0.3 * root.zoomLevel)
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
                            if (root.activeTool === "eraser") return Qt.ClosedHandCursor
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

                            if (root.activeTool === "eraser") {
                                var imgPtEraser = canvasToImage(mouse.x, mouse.y)
                                root.isDrawing = true
                                root.currentPath = [Qt.point(imgPtEraser.x, imgPtEraser.y)]
                                eraseAtPoint(imgPtEraser.x, imgPtEraser.y)
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

                            if (root.activeTool === "eraser" && root.isDrawing) {
                                var imgPtEraser = canvasToImage(mouse.x, mouse.y)
                                root.currentPath.push(Qt.point(imgPtEraser.x, imgPtEraser.y))
                                eraseAtPoint(imgPtEraser.x, imgPtEraser.y)
                                drawPreview.requestPaint()
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

                            if (root.activeTool === "eraser") {
                                root.isDrawing = false
                                root.currentPath = []
                                return
                            }

                            if (!root.isDrawing) return
                            root.isDrawing = false
                            drawPreview.requestPaint()

                            var newAnn = null

                            if (root.activeTool === "rect" || root.activeTool === "filledRect" || root.activeTool === "highlight") {
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
                            } else if (root.activeTool === "ellipse" || root.activeTool === "filledEllipse") {
                                if (root.currentPath.length >= 2) {
                                    var ep1 = root.currentPath[0], ep2 = root.currentPath[1]
                                    var erx = Math.min(ep1.x, ep2.x), ery = Math.min(ep1.y, ep2.y)
                                    var erw = Math.abs(ep2.x - ep1.x), erh = Math.abs(ep2.y - ep1.y)
                                    if (erw > 3 && erh > 3) {
                                        newAnn = {
                                            type: root.activeTool,
                                            x: erx, y: ery, width: erw, height: erh,
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
                                root.redoStack = []
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
                            font.family: root.activeFontFamily
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
                                        fontSize: root.activeFontSize,
                                        fontFamily: root.activeFontFamily
                                    })
                                    root.redoStack = []
                                    root.annotations = updated
                                }
                                root.isTextInputActive = false
                                text = ""
                            }
                        }
                    }
                }
            }

            // Mouse wheel zoom
            MouseArea {
                anchors.fill: parent
                z: 50
                acceptedButtons: Qt.NoButton
                onWheel: (wheel) => {
                    wheel.accepted = true
                    
                    var zoomFactor = 0.15 / 120.0
                    var delta = wheel.angleDelta.y * zoomFactor
                    
                    var oldZoom = root.zoomLevel
                    var newZoom = Math.max(root.minZoom, Math.min(root.maxZoom, oldZoom + delta))
                    
                    if (oldZoom === newZoom) return

                    // Zoom towards mouse cursor
                    var imgX = (wheel.x - root.panOffset.x) / oldZoom
                    var imgY = (wheel.y - root.panOffset.y) / oldZoom

                    root.zoomLevel = newZoom
                    
                    root.panOffset = Qt.point(
                        wheel.x - imgX * newZoom,
                        wheel.y - imgY * newZoom
                    )
                }
            }

            // === Annotation Toolbar ===
            Rectangle {
                id: annotationToolbar
                anchors.bottom: parent.bottom
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.bottomMargin: 24
                height: 44
                implicitWidth: toolbarLayout.implicitWidth + 24
                color: Theme.glassPill
                border.color: Theme.glassOuterBorder
                border.width: 1
                radius: 22
                z: 100

                opacity: toolbarHover.hovered ? 1.0 : 0.4
                Behavior on opacity { NumberAnimation { duration: 200 } }

                HoverHandler {
                    id: toolbarHover
                }

                RowLayout {
                    id: toolbarLayout
                    anchors.centerIn: parent
                spacing: 4

                // Tool buttons
                Repeater {
                    model: [
                        { tool: "rect", iconSource: "ui/tool-rect.svg", tip: "Rectangle" },
                        { tool: "filledRect", iconSource: "ui/tool-filled-rect.svg", tip: "Filled Rectangle" },
                        { tool: "arrow", iconSource: "ui/tool-arrow.svg", tip: "Arrow" },
                        { tool: "ellipse", iconSource: "ui/tool-ellipse.svg", tip: "Ellipse" },
                        { tool: "filledEllipse", iconSource: "ui/tool-filled-ellipse.svg", tip: "Filled Ellipse" },
                        { tool: "freehand", iconSource: "ui/tool-freehand.svg", tip: "Freehand" },
                        { tool: "text", iconSource: "ui/tool-text.svg", tip: "Text" },
                        { tool: "highlight", iconSource: "ui/tool-highlight.svg", tip: "Highlight" },
                        { tool: "eraser", iconSource: "ui/tool-eraser.svg", tip: "Eraser" }
                    ]

                    IconButton {
                        required property var modelData
                        iconSource: AppController.ui_controller.getAssetUri(modelData.iconSource)
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
                Item {
                    Layout.preferredWidth: 32
                    Layout.preferredHeight: 32

                    Rectangle {
                        anchors.centerIn: parent
                        width: 18; height: 18
                        radius: 9
                        color: root.activeColor
                        border.color: Theme.glassBorder
                        border.width: 1

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            hoverEnabled: true
                            onClicked: colorPopup.open()
                            SleekToolTip {
                            visible: parent.containsMouse
                            text: "Select Color"
                        }
                        }
                    }

                    Popup {
                        id: colorPopup
                        y: -height - 8
                        x: -width / 2 + 16
                        width: 156
                        padding: 8
                        background: Rectangle {
                            color: Theme.glassPill
                            border.color: Theme.glassBorder
                            radius: Theme.radiusCard
                        }

                        Flow {
                            width: parent.width
                            spacing: 8
                            
                            Repeater {
                                model: root.presetColors
                                Rectangle {
                                    required property string modelData
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
                                        hoverEnabled: true
                                        SleekToolTip {
                            visible: parent.containsMouse
                            text: modelData
                        }
                                        onClicked: {
                                            root.activeColor = Qt.color(modelData)
                                            colorPopup.close()
                                        }
                                    }
                                }
                            }
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
                Item {
                    Layout.preferredWidth: 32
                    Layout.preferredHeight: 32

                    Rectangle {
                        anchors.centerIn: parent
                        width: 24; height: 24
                        radius: 4
                        color: "transparent"
                        border.color: Theme.glassBorder
                        border.width: 1

                        Rectangle {
                            anchors.centerIn: parent
                            width: root.strokeWidth + 2
                            height: root.strokeWidth + 2
                            radius: (root.strokeWidth + 2) / 2
                            color: Theme.label
                        }

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            hoverEnabled: true
                            onClicked: sizePopup.open()
                            SleekToolTip {
                            visible: parent.containsMouse
                            text: "Select Size"
                        }
                        }
                    }

                    Popup {
                        id: sizePopup
                        y: -height - 8
                        x: -width / 2 + 16
                        padding: 8
                        background: Rectangle {
                            color: Theme.glassPill
                            border.color: Theme.glassBorder
                            radius: Theme.radiusCard
                        }

                        Row {
                            spacing: 8
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
                                        hoverEnabled: true
                                        SleekToolTip {
                            visible: parent.containsMouse
                            text: "Size " + modelData
                        }
                                        onClicked: {
                                            root.strokeWidth = modelData
                                            sizePopup.close()
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                Rectangle {
                    width: 1; height: 24
                    color: Theme.separator
                    Layout.leftMargin: 4
                    Layout.rightMargin: 4
                }

                // Eraser size (only visible when eraser tool is active)
                Item {
                    visible: root.activeTool === "eraser"
                    Layout.preferredWidth: 32
                    Layout.preferredHeight: 32

                    Rectangle {
                        anchors.centerIn: parent
                        width: 24; height: 24
                        radius: 12
                        color: "transparent"
                        border.color: Theme.glassBorder
                        border.width: 1
                        opacity: 0.7

                        Rectangle {
                            anchors.centerIn: parent
                            width: root.eraserRadius / 3
                            height: root.eraserRadius / 3
                            radius: root.eraserRadius / 6
                            color: Theme.label
                            opacity: 0.7
                        }

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            hoverEnabled: true
                            onClicked: eraserSizePopup.open()
                            SleekToolTip {
                            visible: parent.containsMouse
                            text: "Eraser Size"
                        }
                        }
                    }

                    Popup {
                        id: eraserSizePopup
                        y: -height - 8
                        x: -width / 2 + 16
                        padding: 8
                        background: Rectangle {
                            color: Theme.glassPill
                            border.color: Theme.glassBorder
                            radius: Theme.radiusCard
                        }

                        Row {
                            spacing: 8
                            Repeater {
                                model: [10, 20, 40, 60]
                                Rectangle {
                                    required property int modelData
                                    property bool isSelected: root.eraserRadius === modelData

                                    width: 28; height: 28
                                    radius: 4
                                    color: isSelected ? Theme.accent : "transparent"
                                    border.color: isSelected ? Theme.accent : Theme.glassBorder
                                    border.width: isSelected ? 2 : 1

                                    Rectangle {
                                        anchors.centerIn: parent
                                        width: modelData / 3
                                        height: modelData / 3
                                        radius: modelData / 6
                                        color: isSelected ? "white" : Theme.label
                                        opacity: 0.7
                                    }

                                    MouseArea {
                                        anchors.fill: parent
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: {
                                            root.eraserRadius = modelData
                                            eraserSizePopup.close()
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                // Font controls (only visible when text tool is active)
                Item {
                    visible: root.activeTool === "text"
                    Layout.preferredWidth: 32
                    Layout.preferredHeight: 32

                    Rectangle {
                        anchors.centerIn: parent
                        width: 24; height: 24
                        radius: 4
                        color: "transparent"
                        border.color: Theme.glassBorder
                        border.width: 1

                        Text {
                            anchors.centerIn: parent
                            text: root.activeFontSize
                            font.pixelSize: 11
                            font.bold: true
                            color: Theme.label
                        }

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            hoverEnabled: true
                            onClicked: fontSizePopup.open()
                            SleekToolTip {
                            visible: parent.containsMouse
                            text: "Text Size"
                        }
                        }
                    }

                    Popup {
                        id: fontSizePopup
                        y: -height - 8
                        x: -width / 2 + 16
                        padding: 8
                        background: Rectangle {
                            color: Theme.glassPill
                            border.color: Theme.glassBorder
                            radius: Theme.radiusCard
                        }

                        Row {
                            spacing: 6
                            Repeater {
                                model: [12, 14, 16, 18, 20, 24, 32, 48, 64]
                                Rectangle {
                                    required property int modelData
                                    property bool isSelected: root.activeFontSize === modelData

                                    width: 28; height: 28
                                    radius: 4
                                    color: isSelected ? Theme.accent : "transparent"
                                    border.color: isSelected ? Theme.accent : Theme.glassBorder
                                    border.width: isSelected ? 2 : 1

                                    Text {
                                        anchors.centerIn: parent
                                        text: modelData
                                        font.pixelSize: 11
                                        color: isSelected ? "white" : Theme.label
                                    }

                                    MouseArea {
                                        anchors.fill: parent
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: {
                                            root.activeFontSize = modelData
                                            fontSizePopup.close()
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                // Font family button (only visible when text tool is active)
                IconButton {
                    visible: root.activeTool === "text"
                    iconSource: AppController.ui_controller.getAssetUri("ui/tool-text.svg")
                    tooltipText: "Choose Font"
                    role: "ghost"
                    buttonSize: 32
                    iconSize: 14
                    onClicked: {
                        fontPickerDialog.selectedFamily = root.activeFontFamily
                        fontPickerDialog.selectedSize = root.activeFontSize
                        fontPickerDialog.open()
                    }
                }

                Item { Layout.fillWidth: true }
            }
        } // annotationToolbar
    } // canvasContainer
} // ColumnLayout

    // --- Keyboard Shortcuts ---
    Shortcut {
        enabled: root.visible
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
        enabled: root.visible
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
        enabled: root.visible
        sequence: "Ctrl+0"
        context: Qt.ApplicationShortcut
        onActivated: zoomToFit()
    }

    Shortcut {
        enabled: root.visible
        sequence: "Ctrl+1"
        context: Qt.ApplicationShortcut
        onActivated: root.zoomLevel = 1.0
    }

    Shortcut {
        enabled: root.visible
        sequence: "Ctrl+Plus"
        context: Qt.ApplicationShortcut
        onActivated: root.zoomLevel = Math.min(root.maxZoom, root.zoomLevel + 0.25)
    }

    Shortcut {
        enabled: root.visible
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

    // --- Width animation ---
    Behavior on width {
        NumberAnimation { duration: 300; easing.type: Easing.OutQuart }
    }
}

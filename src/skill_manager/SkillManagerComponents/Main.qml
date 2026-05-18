import QtQuick
import QtQuick.Layouts
import App 1.0
import SkillManagerComponents 1.0

Window {
    id: window
    Component.onCompleted: {
        // Set initial geometry from saved state
        x = AppController.windowX
        y = AppController.windowY
        width = AppController.windowWidth
        height = AppController.windowHeight
    }

    onWidthChanged: if (window.visibility === Window.Windowed) AppController.windowWidth = width
    onHeightChanged: if (window.visibility === Window.Windowed) AppController.windowHeight = height
    onXChanged: if (window.visibility === Window.Windowed) AppController.windowX = x
    onYChanged: if (window.visibility === Window.Windowed) AppController.windowY = y
    minimumWidth: 1050
    minimumHeight: 650

    Binding { target: Theme; property: "darkMode"; value: AppController.darkMode }
    visible: true
    title: "Skill Manager"
    flags: Qt.Window | Qt.FramelessWindowHint
    color: "transparent" // Let Mica/Acrylic show through

    // --- Window Resizing Handles (Frameless Support) ---
    // Only enabled when not maximized
    Item {
        id: resizers
        anchors.fill: parent
        visible: window.visibility !== Window.Maximized
        z: 1000 // Ensure handles are on top

        // Edges
        MouseArea { 
            height: 6; anchors { top: parent.top; left: parent.left; right: parent.right } 
            cursorShape: Qt.SizeVerCursor
            onPressed: (mouse) => window.startSystemResize(Qt.TopEdge)
        }
        MouseArea { 
            height: 6; anchors { bottom: parent.bottom; left: parent.left; right: parent.right } 
            cursorShape: Qt.SizeVerCursor
            onPressed: (mouse) => window.startSystemResize(Qt.BottomEdge)
        }
        MouseArea { 
            width: 6; anchors { left: parent.left; top: parent.top; bottom: parent.bottom } 
            cursorShape: Qt.SizeHorCursor
            onPressed: (mouse) => window.startSystemResize(Qt.LeftEdge)
        }
        MouseArea { 
            width: 6; anchors { right: parent.right; top: parent.top; bottom: parent.bottom } 
            cursorShape: Qt.SizeHorCursor
            onPressed: (mouse) => window.startSystemResize(Qt.RightEdge)
        }
        
        // Corners
        MouseArea { 
            width: 12; height: 12; anchors.top: parent.top; anchors.left: parent.left 
            cursorShape: Qt.SizeFDiagCursor
            onPressed: (mouse) => window.startSystemResize(Qt.TopEdge | Qt.LeftEdge)
        }
        MouseArea { 
            width: 12; height: 12; anchors.top: parent.top; anchors.right: parent.right 
            cursorShape: Qt.SizeBDiagCursor
            onPressed: (mouse) => window.startSystemResize(Qt.TopEdge | Qt.RightEdge)
        }
        MouseArea { 
            width: 12; height: 12; anchors.bottom: parent.bottom; anchors.left: parent.left 
            cursorShape: Qt.SizeBDiagCursor
            onPressed: (mouse) => window.startSystemResize(Qt.BottomEdge | Qt.LeftEdge)
        }
        MouseArea { 
            width: 12; height: 12; anchors.bottom: parent.bottom; anchors.right: parent.right 
            cursorShape: Qt.SizeFDiagCursor
            onPressed: (mouse) => window.startSystemResize(Qt.BottomEdge | Qt.RightEdge)
        }
    }

    property string currentView: AppController.currentView
    onCurrentViewChanged: AppController.currentView = currentView

    function navigateTo(view) {
        window.currentView = view
        let source = "views/" + view.replace(" ", "") + "View.qml"
        if (viewLoader.source.toString().indexOf(source) === -1) {
            viewLoader.source = source
        }
    }

    function focusCurrentSearch() {
        if (viewLoader.item && viewLoader.item.focusSearch) {
            viewLoader.item.focusSearch()
        }
    }

    Shortcut { sequences: ["Ctrl+F", "Meta+F"]; onActivated: window.focusCurrentSearch() }
    Shortcut { sequence: "Escape"; onActivated: AppController.clearViewFilters() }
    Shortcut { sequences: ["Ctrl+C", "Meta+C"]; onActivated: AppController.copyCurrentSelectionOrFocusedSkill() }
    Shortcut { sequences: ["Ctrl+A", "Meta+A"]; onActivated: AppController.selectAllVisibleSkills() }
    Shortcut { sequences: ["Ctrl+Shift+A", "Meta+Shift+A"]; onActivated: AppController.clearVisibleSelection() }
    Shortcut { sequences: ["Ctrl+E", "Meta+E"]; onActivated: AppController.toggleAllVisibleCategories() }
    Shortcut { sequence: "Alt+1"; onActivated: window.navigateTo("QuickCopy") }
    Shortcut { sequence: "Alt+2"; onActivated: window.navigateTo("Library") }
    Shortcut { sequence: "Alt+3"; onActivated: window.navigateTo("Updates") }
    Shortcut { sequence: "Alt+4"; onActivated: window.navigateTo("Settings") }

    Rectangle {
        anchors.fill: parent
        color: "transparent"
        radius: window.visibility === Window.Maximized ? 0 : Theme.radiusCard
        clip: true
        border.width: window.visibility === Window.Maximized ? 0 : 1
        border.color: Theme.glassBorder
        
        // Ensure child components are clipped to the radius
        layer.enabled: true
        
        FrostOverlay {
            anchors.fill: parent
            radius: parent.radius
        }

        ColumnLayout {
            anchors.fill: parent
            spacing: 0

            CustomTitleBar {
                id: customTitleBar
                Layout.fillWidth: true
            }

            TopBar {
                id: topBar
                currentView: window.currentView
                onNavigationChanged: (view) => {
                    if (!view.startsWith("Category:")) {
                        window.navigateTo(view)
                    } else if (viewLoader.source.toString().indexOf("QuickCopyView.qml") === -1 && 
                               viewLoader.source.toString().indexOf("LibraryView.qml") === -1) {
                        viewLoader.source = "views/QuickCopyView.qml"
                    }
                }
            }

            Item {
                Layout.fillWidth: true
                Layout.fillHeight: true

                Loader {
                    id: viewLoader
                    anchors.fill: parent
                    anchors.margins: 16
                    source: "views/" + window.currentView.replace(" ", "") + "View.qml"
                }
            }
        }
    }
}

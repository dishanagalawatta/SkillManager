import QtQuick
import QtQuick.Layouts
import App 1.0

Window {
    id: window
    Component.onCompleted: {
        // Set initial geometry from saved state
        x = AppController.ui_controller.windowX
        y = AppController.ui_controller.windowY
        width = AppController.ui_controller.windowWidth
        height = AppController.ui_controller.windowHeight
    }

    onWidthChanged: if (window.visibility === Window.Windowed) AppController.ui_controller.windowWidth = width
    onHeightChanged: if (window.visibility === Window.Windowed) AppController.ui_controller.windowHeight = height
    onXChanged: if (window.visibility === Window.Windowed) AppController.ui_controller.windowX = x
    onYChanged: if (window.visibility === Window.Windowed) AppController.ui_controller.windowY = y
    minimumWidth: 1050
    minimumHeight: 650

    Binding { target: Theme; property: "darkMode"; value: AppController.ui_controller.darkMode }
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
            Accessible.role: Accessible.Grip
            Accessible.name: "Resize top edge"
            Accessible.description: "Drag to resize window top edge"
            onPressed: (mouse) => window.startSystemResize(Qt.TopEdge)
        }
        MouseArea { 
            height: 6; anchors { bottom: parent.bottom; left: parent.left; right: parent.right } 
            cursorShape: Qt.SizeVerCursor
            Accessible.role: Accessible.Grip
            Accessible.name: "Resize bottom edge"
            Accessible.description: "Drag to resize window bottom edge"
            onPressed: (mouse) => window.startSystemResize(Qt.BottomEdge)
        }
        MouseArea { 
            width: 6; anchors { left: parent.left; top: parent.top; bottom: parent.bottom } 
            cursorShape: Qt.SizeHorCursor
            Accessible.role: Accessible.Grip
            Accessible.name: "Resize left edge"
            Accessible.description: "Drag to resize window left edge"
            onPressed: (mouse) => window.startSystemResize(Qt.LeftEdge)
        }
        MouseArea { 
            width: 6; anchors { right: parent.right; top: parent.top; bottom: parent.bottom } 
            cursorShape: Qt.SizeHorCursor
            Accessible.role: Accessible.Grip
            Accessible.name: "Resize right edge"
            Accessible.description: "Drag to resize window right edge"
            onPressed: (mouse) => window.startSystemResize(Qt.RightEdge)
        }
        
        // Corners
        MouseArea { 
            width: 12; height: 12; anchors.top: parent.top; anchors.left: parent.left 
            cursorShape: Qt.SizeFDiagCursor
            Accessible.role: Accessible.Grip
            Accessible.name: "Resize top-left corner"
            Accessible.description: "Drag to resize window top-left corner"
            onPressed: (mouse) => window.startSystemResize(Qt.TopEdge | Qt.LeftEdge)
        }
        MouseArea { 
            width: 12; height: 12; anchors.top: parent.top; anchors.right: parent.right 
            cursorShape: Qt.SizeBDiagCursor
            Accessible.role: Accessible.Grip
            Accessible.name: "Resize top-right corner"
            Accessible.description: "Drag to resize window top-right corner"
            onPressed: (mouse) => window.startSystemResize(Qt.TopEdge | Qt.RightEdge)
        }
        MouseArea { 
            width: 12; height: 12; anchors.bottom: parent.bottom; anchors.left: parent.left 
            cursorShape: Qt.SizeBDiagCursor
            Accessible.role: Accessible.Grip
            Accessible.name: "Resize bottom-left corner"
            Accessible.description: "Drag to resize window bottom-left corner"
            onPressed: (mouse) => window.startSystemResize(Qt.BottomEdge | Qt.LeftEdge)
        }
        MouseArea { 
            width: 12; height: 12; anchors.bottom: parent.bottom; anchors.right: parent.right 
            cursorShape: Qt.SizeFDiagCursor
            Accessible.role: Accessible.Grip
            Accessible.name: "Resize bottom-right corner"
            Accessible.description: "Drag to resize window bottom-right corner"
            onPressed: (mouse) => window.startSystemResize(Qt.BottomEdge | Qt.RightEdge)
        }
    }

    property string currentView: AppController.ui_controller.currentView
    onCurrentViewChanged: AppController.ui_controller.currentView = currentView

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

    Shortcut { enabled: !AppController.config_controller.isRecordingShortcut; sequence: AppController.config_controller.shortcutSearch; onActivated: window.focusCurrentSearch() }
    Shortcut { enabled: !AppController.config_controller.isRecordingShortcut; sequence: AppController.config_controller.shortcutClearSelection; onActivated: AppController.ui_controller.clearVisibleSelection() }
    Shortcut { enabled: !AppController.config_controller.isRecordingShortcut; sequence: AppController.config_controller.shortcutCopy; onActivated: AppController.ops_controller.copyCurrentSelectionOrFocusedSkill() }
    Shortcut { enabled: !AppController.config_controller.isRecordingShortcut; sequences: ["Ctrl+A", "Meta+A"]; onActivated: AppController.ui_controller.selectAllVisibleSkills() }
    
    Shortcut { enabled: !AppController.config_controller.isRecordingShortcut; sequence: AppController.config_controller.shortcutExpandAll; onActivated: AppController.skillModel.expandAll() }
    Shortcut { enabled: !AppController.config_controller.isRecordingShortcut; sequence: AppController.config_controller.shortcutCollapseAll; onActivated: AppController.skillModel.collapseAll() }
    Shortcut { enabled: !AppController.config_controller.isRecordingShortcut; sequence: AppController.config_controller.shortcutArchive; onActivated: AppController.ops_controller.archiveSelectedSkills() }
    Shortcut { enabled: !AppController.config_controller.isRecordingShortcut; sequence: AppController.config_controller.shortcutDelete; onActivated: AppController.ops_controller.deleteSelectedSkills() }
    Shortcut { enabled: !AppController.config_controller.isRecordingShortcut; sequence: AppController.config_controller.shortcutRefresh; onActivated: AppController.refreshSkills() }
    Shortcut { enabled: !AppController.config_controller.isRecordingShortcut; sequence: AppController.config_controller.shortcutThemeToggle; onActivated: AppController.ui_controller.darkMode = !AppController.ui_controller.darkMode }
    Shortcut { enabled: !AppController.config_controller.isRecordingShortcut; sequence: AppController.config_controller.shortcutTopOfList; onActivated: { if (viewLoader.item && viewLoader.item.scrollToTop) viewLoader.item.scrollToTop() } }

    Shortcut { enabled: !AppController.config_controller.isRecordingShortcut; sequence: AppController.config_controller.shortcutQuickCopyView; onActivated: window.navigateTo("QuickCopy") }
    Shortcut { enabled: !AppController.config_controller.isRecordingShortcut; sequence: AppController.config_controller.shortcutLibraryView; onActivated: window.navigateTo("Library") }
    Shortcut { enabled: !AppController.config_controller.isRecordingShortcut; sequence: AppController.config_controller.shortcutUpdatesView; onActivated: window.navigateTo("Updates") }
    Shortcut { enabled: !AppController.config_controller.isRecordingShortcut; sequence: AppController.config_controller.shortcutSettingsView; onActivated: window.navigateTo("Settings") }

    Rectangle {
        anchors.fill: parent
        color: "transparent"
        radius: window.visibility === Window.Maximized ? 0 : Theme.radiusCard
        clip: true
        border.width: window.visibility === Window.Maximized ? 0 : 1
        border.color: Theme.glassBorder
        
        // Ensure child components are clipped to the radius
        layer.enabled: true
        
        Loader {
            active: !AppController.isTesting
            anchors.fill: parent
            source: "FrostOverlay.qml"
            onLoaded: if (item) item.radius = window.visibility === Window.Maximized ? 0 : Theme.radiusCard
        }

        ColumnLayout {
            anchors.fill: parent
            spacing: 0

            Loader {
                active: !AppController.isTesting
                Layout.fillWidth: true
                Layout.preferredHeight: 32
                source: "CustomTitleBar.qml"
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

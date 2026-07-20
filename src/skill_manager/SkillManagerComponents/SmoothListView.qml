import QtQuick
import QtQuick.Controls
import App 1.0

ListView {
    id: root

    ScrollBar.vertical: AppScrollBar {
        interactive: true
    }

    cacheBuffer: Math.max(height * 2, 1000)
    // Optimization: reuse delegates for smoother list rendering
    reuseItems: true

    // Optimization: defer heavy layout generation while scrolling fast
    property bool isScrollingFast: false
    
    onMovementStarted: {
        isScrollingFast = true
    }
    
    onMovementEnded: {
        isScrollingFast = false
    }

    // Ensure initial scroll position is top if desired, handled by caller
}

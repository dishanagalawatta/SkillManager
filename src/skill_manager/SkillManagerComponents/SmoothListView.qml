import QtQuick
import QtQuick.Controls
import App 1.0

ListView {
    id: root

    ScrollBar.vertical: AppScrollBar {
        interactive: true
    }

    cacheBuffer: Math.max(height * 2, 1000)

    // Perf: pool and recycle delegates instead of destroying/recreating them on
    // scroll, cutting allocation and GC overhead on long lists (Library, Updates, QuickCopy).
    reuseItems: true

    // Optimization: defer heavy layout generation while scrolling fast
    property bool isScrollingFast: false
    
    onMovementStarted: {
        isScrollingFast = true
    }
    
    onMovementEnded: {
        isScrollingFast = false
    }

    WheelHandler {
        target: root
        acceptedDevices: PointerDevice.Mouse | PointerDevice.TouchPad
        onWheel: (event) => {
            let config = AppController.config_controller
            let multiplier = (config && typeof config.scrollSpeedMultiplier !== "undefined") ? config.scrollSpeedMultiplier : 1.0

            if (Math.abs(multiplier - 1.0) < 0.01) {
                event.accepted = false
                return
            }

            event.accepted = true

            if (event.pixelDelta.y !== 0) {
                let scrollAmount = event.pixelDelta.y * multiplier
                root.contentY = Math.max(root.originY,
                                         Math.min(root.contentY - scrollAmount,
                                                  root.originY + Math.max(0, root.contentHeight - root.height)))
                return
            }

            let scrollAmount = event.angleDelta.y * (multiplier * 0.5)
            root.contentY = Math.max(root.originY,
                                     Math.min(root.contentY - scrollAmount,
                                              root.originY + Math.max(0, root.contentHeight - root.height)))
        }
    }
}

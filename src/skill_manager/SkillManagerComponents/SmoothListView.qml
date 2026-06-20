import QtQuick
import QtQuick.Controls
import App 1.0

ListView {
    id: root

    ScrollBar.vertical: AppScrollBar {
        interactive: true
    }

    // Pre-render items outside viewport to prevent lag during fast scrolling
    cacheBuffer: Math.max(height * 2, 1000)

    NumberAnimation {
        id: scrollAnim
        target: root
        property: "contentY"
        duration: 150
        easing.type: Easing.OutCubic
    }

    WheelHandler {
        target: root
        acceptedDevices: PointerDevice.Mouse | PointerDevice.TouchPad
        onWheel: (event) => {
            let config = AppController.config_controller
            let multiplier = config ? config.scrollSpeedMultiplier : 1.0

            if (multiplier === 1.0) {
                // Yield to native Qt scrolling for best performance
                event.accepted = false
                return
            }

            // We are handling the scroll, so we MUST accept the event
            event.accepted = true

            // High-resolution trackpad or precision mouse
            if (event.pixelDelta.y !== 0) {
                // Already smooth, apply multiplier directly without animation
                let scrollAmount = event.pixelDelta.y * multiplier
                root.contentY = Math.max(root.originY,
                                         Math.min(root.contentY - scrollAmount,
                                                  root.originY + Math.max(0, root.contentHeight - root.height)))
                return
            }

            // Standard discrete mouse wheel (requires smoothing)
            let scrollAmount = event.angleDelta.y * multiplier * 0.5
            let base = scrollAnim.running ? scrollAnim.to : root.contentY
            let newY = Math.max(root.originY, 
                                Math.min(base - scrollAmount, 
                                         root.originY + Math.max(0, root.contentHeight - root.height)))

            scrollAnim.stop()
            scrollAnim.to = newY
            scrollAnim.start()
        }
    }

    add: Transition {
        NumberAnimation { property: "opacity"; from: 0; to: 1.0; duration: 250; easing.type: Easing.OutCubic }
    }
    remove: Transition {
        NumberAnimation { property: "opacity"; to: 0; duration: 250; easing.type: Easing.OutCubic }
    }
    move: Transition {
        NumberAnimation { properties: "x,y"; duration: 250; easing.type: Easing.OutCubic }
    }
    displaced: Transition {
        NumberAnimation { properties: "x,y"; duration: 250; easing.type: Easing.OutCubic }
    }
}

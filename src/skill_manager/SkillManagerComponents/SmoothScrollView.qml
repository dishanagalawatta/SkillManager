import QtQuick
import QtQuick.Controls
import App 1.0

ScrollView {
    id: root
    
    ScrollBar.vertical: AppScrollBar {
        interactive: true
    }
    
    // ScrollView in QtQuick.Controls 2 uses a Flickable as its contentItem
    // if it contains a single Item.
    
    NumberAnimation {
        id: scrollAnim
        target: root.contentItem
        property: "contentY"
        duration: 150
        easing.type: Easing.OutCubic
    }

    WheelHandler {
        target: root.contentItem
        acceptedDevices: PointerDevice.Mouse | PointerDevice.TouchPad
        onWheel: (event) => {
            let config = AppController.config_controller
            let multiplier = config ? config.scrollSpeedMultiplier : 1.0

            if (multiplier === 1.0 || !root.contentItem) {
                // Yield to native Qt scrolling
                event.accepted = false
                return
            }

            // Correctly accept the event to stop native interference
            event.accepted = true

            // High-resolution trackpad or precision mouse
            if (event.pixelDelta.y !== 0) {
                let scrollAmount = event.pixelDelta.y * multiplier
                root.contentItem.contentY = Math.max(root.contentItem.originY,
                                                     Math.min(root.contentItem.contentY - scrollAmount,
                                                              root.contentItem.originY + Math.max(0, root.contentItem.contentHeight - root.contentItem.height)))
                return
            }

            // Standard discrete mouse wheel
            let scrollAmount = event.angleDelta.y * multiplier * 0.5
            let base = scrollAnim.running ? scrollAnim.to : root.contentItem.contentY
            let newY = Math.max(root.contentItem.originY, 
                                Math.min(base - scrollAmount, 
                                         root.contentItem.originY + Math.max(0, root.contentItem.contentHeight - root.contentItem.height)))

            scrollAnim.stop()
            scrollAnim.to = newY
            scrollAnim.start()
        }
    }
}

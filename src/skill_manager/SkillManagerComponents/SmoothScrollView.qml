import QtQuick
import QtQuick.Controls

ScrollView {
    id: root
    
    // ScrollView in QtQuick.Controls 2 uses a Flickable as its contentItem
    // if it contains a single Item.
    
    WheelHandler {
        target: root.contentItem
        onWheel: (event) => {
            // Use global appController context property with safety check
            let ctrl = (typeof appController !== "undefined") ? appController : null
            let config = (ctrl && ctrl.config_controller) ? ctrl.config_controller : null
            let multiplier = (config && typeof config.scrollSpeedMultiplier !== "undefined") ? config.scrollSpeedMultiplier : 1.0

            if (multiplier !== 1.0 && root.contentItem) {
                // If multiplier is not 1.0, we handle the scroll entirely to avoid conflicts
                event.accepted = true
                
                // angleDelta.y is typically 120 per notch.
                let scrollAmount = event.angleDelta.y * multiplier * 0.4
                
                root.contentItem.contentY = Math.max(root.contentItem.originY, 
                                                     Math.min(root.contentItem.contentY - scrollAmount, 
                                                              root.contentItem.originY + root.contentItem.contentHeight - root.contentItem.height))
            } else {
                event.accepted = false
            }
        }
    }
}

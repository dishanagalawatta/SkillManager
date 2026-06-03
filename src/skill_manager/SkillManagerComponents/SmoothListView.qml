import QtQuick
import QtQuick.Controls

ListView {
    id: root

    WheelHandler {
        target: root
        onWheel: (event) => {
            // Use global appController context property with safety check
            let ctrl = (typeof appController !== "undefined") ? appController : null
            let config = (ctrl && ctrl.config_controller) ? ctrl.config_controller : null
            let multiplier = (config && typeof config.scrollSpeedMultiplier !== "undefined") ? config.scrollSpeedMultiplier : 1.0
            
            if (multiplier !== 1.0) {
                // If multiplier is not 1.0, we handle the scroll entirely to avoid conflicts
                event.accepted = true
                
                // angleDelta.y is typically 120 per notch.
                // Standard scroll is roughly 40-60 pixels.
                // We use a factor of 0.4 as a base and then apply the multiplier.
                let scrollAmount = event.angleDelta.y * multiplier * 0.4
                
                root.contentY = Math.max(root.originY, 
                                         Math.min(root.contentY - scrollAmount, 
                                                  root.originY + root.contentHeight - root.height))
            } else {
                event.accepted = false
            }
        }
    }
}

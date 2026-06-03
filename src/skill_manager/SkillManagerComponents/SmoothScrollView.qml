import QtQuick
import QtQuick.Controls

ScrollView {
    id: root
    
    // ScrollView in QtQuick.Controls 2 uses a Flickable as its contentItem
    // if it contains a single Item.
    
    WheelHandler {
        target: root.contentItem
        onWheel: (event) => {
            let multiplier = appController.config_mgr.scrollSpeedMultiplier
            if (multiplier !== 1.0 && root.contentItem) {
                let extra = event.angleDelta.y * (multiplier - 1.0) * 0.5
                root.contentItem.contentY = Math.max(root.contentItem.originY, 
                                                     Math.min(root.contentItem.contentY - extra, 
                                                              root.contentItem.originY + root.contentItem.contentHeight - root.contentItem.height))
            }
        }
    }
}

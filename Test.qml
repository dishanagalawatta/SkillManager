import QtQuick
import QtQuick.Controls
import App 1.0

Rectangle {
    width: 100
    height: 100
    Item {
        anchors.fill: parent
    }
    Component.onCompleted: {
        console.log("AppController status: " + AppController.statusMessage)
    }
}

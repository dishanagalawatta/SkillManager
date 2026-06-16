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
    //
    // Note: a custom WheelHandler for smooth scroll + custom speed
    // multiplier was removed because in Qt 6.11.1 ANY QQuickItem child
    // of a control (Item, WheelHandler, NumberAnimation, Timer, etc.)
    // hits the
    //   "Cannot assign object of type X to list property 'data'; expected 'QObject'"
    // strict-type-check bug, and the SmoothScrollView is used by enough
    // views (Settings, QuickCopy, Library, etc.) that the breakage was
    // cascading. The native ScrollView wheel handling is now used; the
    // `scrollSpeedMultiplier` config key is currently a no-op.
}

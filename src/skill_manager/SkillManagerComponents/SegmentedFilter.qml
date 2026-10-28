import QtQuick
import QtQuick.Layouts
import App 1.0

/*!
    \qmltype SegmentedFilter
    \inqmlmodule SkillManagerComponents
    \brief Pill-shaped segmented control for small, mutually exclusive filters.

    Replaces the hand-rolled "Repeater of Rectangles" tab strips that each view
    used to grow on its own. Callers supply the option data and own the selected
    key; the component reports intent through \l activated.

    \code
    SegmentedFilter {
        groupName: "Task filter"
        currentKey: root.filter
        options: [
            { key: "all", label: "All" },
            { key: "active", label: "Active" }
        ]
        onActivated: (key) => root.filter = key
    }
    \endcode

    \property var options
        Array of \c { key, label } objects.
    \property string currentKey
        The selected option key.
    \property string groupName
        Prefix for the accessible name, e.g. "Task filter" announces
        "Task filter: Active".
    \property int segmentHeight
        Segment height; the corner radius follows it so the pills stay circular.
*/
RowLayout {
    id: root

    property var options: []
    property string currentKey: ""
    property string groupName: ""
    property int segmentHeight: 26

    signal activated(string key)

    spacing: 6

    function _activate(key) {
        if (key === root.currentKey) return
        root.activated(key)
    }

    Repeater {
        model: root.options

        delegate: Rectangle {
            id: segment
            required property var modelData

            readonly property bool selected: root.currentKey === modelData.key

            Layout.preferredWidth: segmentLabel.implicitWidth + 20
            Layout.preferredHeight: root.segmentHeight
            radius: height / 2
            color: selected ? Theme.accent : "transparent"
            border.color: selected ? Theme.accent : Theme.glassBorder
            border.width: 1
            activeFocusOnTab: true

            Accessible.role: Accessible.PageTab
            Accessible.checked: segment.selected
            Accessible.name: (root.groupName !== "" ? root.groupName + ": " : "")
                + modelData.label

            Text {
                id: segmentLabel
                anchors.centerIn: parent
                text: modelData.label
                font.family: Theme.fontFamily
                font.pixelSize: Theme.sizeCaption
                font.weight: Font.Medium
                color: segment.selected ? "white" : Theme.secondaryLabel
            }

            TapHandler {
                onTapped: root._activate(modelData.key)
            }

            Keys.onPressed: (event) => {
                if (event.key === Qt.Key_Space || event.key === Qt.Key_Return) {
                    root._activate(modelData.key)
                    event.accepted = true
                }
            }
        }
    }
}

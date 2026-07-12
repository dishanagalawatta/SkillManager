import re

with open('src/skill_manager/SkillManagerComponents/CategoryHeader.qml', 'r') as f:
    content = f.read()

content = content.replace(
    'visible: mainCatName !== ""',
    'visible: mainCatName !== ""\n\n    activeFocusOnTab: true'
)

content = content.replace(
    'color: headerHover.hovered ? Theme.glassHover : "transparent"',
    'color: (headerHover.hovered || root.activeFocus) ? Theme.glassHover : "transparent"'
)

keys_on_pressed = """    Keys.onPressed: (event) => {
        if (event.key === Qt.Key_Space || event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
            Qt.callLater(AppController.skillModel.toggleCategory, root.mainCatName)
            event.accepted = true
        }
    }

    HoverHandler {"""

content = content.replace('    HoverHandler {', keys_on_pressed)

tooltip = """    SleekToolTip {
        id: headerToolTip
        visible: (headerHover.hovered || root.activeFocus) && text !== ""
        text: root.isMainCollapsed ? "Expand " + root.mainCatName : "Collapse " + root.mainCatName
    }"""

content = re.sub(r'    SleekToolTip \{\s+id: headerToolTip\s+text:.*?\s+\}', tooltip, content, flags=re.DOTALL)

# color replacement
content = content.replace('color: "#FFD700"', 'color: Theme.accent')
content = content.replace('color: root.mainCatName === "Special" ? "#FFD700" : Theme.label', 'color: root.mainCatName === "Special" ? Theme.accent : Theme.label')


with open('src/skill_manager/SkillManagerComponents/CategoryHeader.qml', 'w') as f:
    f.write(content)

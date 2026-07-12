import re

with open('src/skill_manager/SkillManagerComponents/CategoryHeader.qml', 'r') as f:
    content = f.read()

content = content.replace(
    'color: (headerHover.hovered || root.activeFocus) ? Theme.glassHover : "transparent"\n        radius: Theme.radiusSmall',
    'color: (headerHover.hovered || root.activeFocus) ? Theme.glassHover : "transparent"\n        border.color: root.activeFocus ? Theme.accent : "transparent"\n        border.width: root.activeFocus ? 2 : 0\n        radius: Theme.radiusSmall'
)

with open('src/skill_manager/SkillManagerComponents/CategoryHeader.qml', 'w') as f:
    f.write(content)

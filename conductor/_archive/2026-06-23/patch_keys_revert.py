import re

for filename in ["src/skill_manager/SkillManagerComponents/GlassCheckBox.qml", "src/skill_manager/SkillManagerComponents/GlassSwitch.qml"]:
    with open(filename, "r") as f:
        content = f.read()

    content = content.replace("Keys.onPressed: {", "Keys.onPressed: function(event) {")

    with open(filename, "w") as f:
        f.write(content)

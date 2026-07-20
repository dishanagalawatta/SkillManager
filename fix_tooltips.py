import re

files = [
    "src/skill_manager/SkillManagerComponents/SkillItem.qml",
    "src/skill_manager/SkillManagerComponents/GlassToggleButton.qml",
    "src/skill_manager/SkillManagerComponents/CategoryHeader.qml",
    "src/skill_manager/SkillManagerComponents/GlassCheckBox.qml",
    "src/skill_manager/SkillManagerComponents/SkillInspector.qml"
]

def analyze_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()

    # Check for duplicate Accessible.description
    print(f"--- {filepath} ---")
    desc_matches = re.finditer(r'Accessible\.description:\s*(.*?)\n', content)
    for m in desc_matches:
        print(f"Accessible.description: {m.group(1)}")

    # Check for SleekToolTip without visibility condition or with just mouse area
    tooltips = re.finditer(r'SleekToolTip\s*\{[^}]*\}', content)
    for t in tooltips:
        tt_text = t.group(0)
        if 'visible:' not in tt_text:
            print("Missing visible! " + tt_text.replace('\n', ' '))
        elif 'visualFocus' not in tt_text and 'activeFocus' not in tt_text:
            print("Missing keyboard visibility! " + tt_text.replace('\n', ' '))

for f in files:
    analyze_file(f)

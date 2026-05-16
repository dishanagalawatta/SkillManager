with open('src/skill_manager/SkillManagerComponents/CategoryHeader.qml', 'r') as f:
    lines = f.readlines()

new_lines = []
skip = False
for line in lines:
    if line.startswith('<<<<<<< HEAD'):
        skip = True
        continue
    if line.startswith('======='):
        continue
    if line.startswith('>>>>>>> origin/main'):
        skip = False
        continue
    if not skip:
        new_lines.append(line)

with open('src/skill_manager/SkillManagerComponents/CategoryHeader.qml', 'w') as f:
    f.writelines(new_lines)

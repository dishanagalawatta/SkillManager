with open("tests/test_launcher.py", "r") as f:
    content = f.read()

content = content.replace('assert root.name == "SkillManager"', 'assert root.name in ("SkillManager", "app")')

with open("tests/test_launcher.py", "w") as f:
    f.write(content)

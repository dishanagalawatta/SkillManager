import re


def get_braces(filename):
    with open(filename, encoding="utf-8") as f:
        content = f.read()
    content = re.sub(r"//.*", "", content)
    content = re.sub(r"/\*.*?\*/", "", content, flags=re.DOTALL)
    content = re.sub(r'".*?"', '""', content)
    content = re.sub(r"'.*?'", "''", content)

    braces = []
    lines = content.split("\n")
    for i, line in enumerate(lines):
        for char in line:
            if char in "{}":
                braces.append((char, i + 1))
    return braces


orig = get_braces("orig_qcv.qml")
curr = get_braces("src/skill_manager/SkillManagerComponents/views/QuickCopyView.qml")

print("Orig braces:", len(orig))
print("Curr braces:", len(curr))

# Now try to align them and find the differences
import difflib

sm = difflib.SequenceMatcher(None, [b[0] for b in orig], [b[0] for b in curr])
for tag, i1, i2, j1, j2 in sm.get_opcodes():
    if tag != "equal":
        print(f"{tag}: orig[{i1}:{i2}] curr[{j1}:{j2}]")
        if tag in ("delete", "replace"):
            print("Orig missing:", orig[i1:i2])
        if tag in ("insert", "replace"):
            print("Curr extra:", curr[j1:j2])

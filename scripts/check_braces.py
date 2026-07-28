def check_braces(filename):
    with open(filename, encoding="utf-8") as f:
        lines = f.readlines()

    stack = []
    for i, line in enumerate(lines):
        # Extremely simplified brace checking (ignores comments and strings, but good enough for a rough idea)
        # Actually let's ignore lines that start with // or inside comments
        line = line.split("//")[0]
        for char in line:
            if char == "{":
                stack.append(i + 1)
            elif char == "}":
                if stack:
                    stack.pop()
                else:
                    print(f"[{filename}] Extra closing brace at line {i + 1}")

    print(f"[{filename}] Unclosed braces opened at lines: {stack}")


check_braces("src/skill_manager/SkillManagerComponents/views/QuickCopyView.qml")
check_braces("orig_qcv.qml")

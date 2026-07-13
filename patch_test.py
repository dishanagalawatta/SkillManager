with open("tests/test_build_script.py", "r") as f:
    lines = f.readlines()

new_lines = []
skip = False
for i, line in enumerate(lines):
    if 'def extract_constants(expr_node):' in line:
        new_lines.append(line)
        new_lines.append('        constants = []\n')
        new_lines.append('        for child in ast.walk(expr_node):\n')
        new_lines.append('            if isinstance(child, ast.Constant):\n')
        new_lines.append('                constants.append(child.value)\n')
        new_lines.append('            elif type(child).__name__ == "Str":\n')
        new_lines.append('                constants.append(getattr(child, "s", None))\n')
        new_lines.append('        return [c for c in constants if c is not None]\n')
        skip = True
    elif skip and 'for keyword in analysis_call.keywords:' in line:
        skip = False
        new_lines.append('\n')
        new_lines.append(line)
    elif not skip:
        new_lines.append(line)

with open("tests/test_build_script.py", "w") as f:
    f.writelines(new_lines)

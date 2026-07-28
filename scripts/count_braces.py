def count_braces(filename):
    with open(filename, encoding="utf-8") as f:
        content = f.read()

    # Strip all comments to be safe
    import re

    content = re.sub(r"//.*", "", content)
    content = re.sub(r"/\*.*?\*/", "", content, flags=re.DOTALL)

    # Strip strings
    content = re.sub(r'".*?"', '""', content)
    content = re.sub(r"'.*?'", "''", content)

    open_count = content.count("{")
    close_count = content.count("}")
    print(f"[{filename}] {{: {open_count}, }}: {close_count}, Diff: {open_count - close_count}")


count_braces("src/skill_manager/SkillManagerComponents/views/QuickCopyView.qml")
count_braces("orig_qcv.qml")

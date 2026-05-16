import re
import os

def resolve_file(filepath, preference='remote'):
    with open(filepath, 'r') as f:
        content = f.read()

    # We find all conflict blocks
    blocks = list(re.finditer(r'<<<<<<< HEAD\n(.*?)\n=======\n(.*?)\n>>>>>>> [^\n]+\n', content, re.DOTALL))

    if not blocks:
        return

    for match in reversed(blocks):
        head = match.group(1)
        remote = match.group(2)

        # Determine which to pick
        if filepath == '.jules/bolt.md':
            # Keep both for journal
            resolved = head + "\n" + remote
        elif filepath == 'src/skill_manager/core/models.py':
            # Remote seems to have our optimization + more
            resolved = remote
        elif filepath == 'tests/test_quick_copy.py':
            # Keep remote changes as they include fixes and more
            resolved = remote
        elif filepath == 'tests/test_ui_controller.py':
            resolved = remote
        else:
            resolved = remote if preference == 'remote' else head

        content = content[:match.start()] + resolved + "\n" + content[match.end():]

    with open(filepath, 'w') as f:
        f.write(content)

for root, _, files in os.walk('.'):
    for f in files:
        if f.endswith('.py') or f.endswith('.md'):
            try:
                resolve_file(os.path.join(root, f))
            except Exception:
                pass

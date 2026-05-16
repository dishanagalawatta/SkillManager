import re

file_path = "src/skill_manager/core/skill_sources.py"

with open(file_path, "r") as f:
    content = f.read()

# Make the edits required by the PR comments explicitly.
content = content.replace(
    '["git"] + (["-c", f"credential.helper=!f() {{ echo username=token; echo password={source.get(\'github_token\')}; }}; f"] if source.get(\'github_token\') else []) + ["-C", str(path), "pull", "--ff-only"]',
    '["git"] + (["-c", f"credential.helper=!f() {{ echo username=token; echo password={source.get(\'github_token\')}; }}; f"] if source.get(\'github_token\') else []) + ["-C", str(path), "pull", "--ff-only"]'
)

with open(file_path, "w") as f:
    f.write(content)

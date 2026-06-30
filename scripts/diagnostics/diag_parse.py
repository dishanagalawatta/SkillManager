import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"
from skill_manager.core.discovery import parse_skill_md

path = r"C:\Users\DIKKA\Documents\01-Projects\20-AiSupportTools\SkillManager\.agents\skills\brainstorming\SKILL.md"
print(f"Parsing: {path}")
try:
    result = parse_skill_md(path)
    print("Success. Name:", result.get("name"))
except Exception as e:
    print("Failed!", e)

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from skill_manager.core.persistence import load_cache
from pathlib import Path

data = load_cache() or {}
skills = data.get("skills", [])
print(f"Total skills: {len(skills)}")

# Check for duplicates by normcase path
seen = {}
duplicates = 0
for s in skills:
    lp = s.get("local_path", "")
    key = os.path.normcase(lp)
    if key in seen:
        print(f"DUPLICATE FOUND!")
        print(f"  1: name={seen[key].get('name')}, is_package={seen[key].get('is_package')}, path={seen[key].get('local_path')}")
        print(f"  2: name={s.get('name')}, is_package={s.get('is_package')}, path={s.get('local_path')}")
        duplicates += 1
    seen[key] = s

print(f"Total duplicates: {duplicates}")

# Let's also find 'brainstorming'
print("\nLooking for brainstorming:")
for s in skills:
    if "brainstorming" in s.get("name", "").lower() or "brainstorming" in s.get("local_path", "").lower():
        print(f"- name={s.get('name')}, is_package={s.get('is_package')}, path={s.get('local_path')}")

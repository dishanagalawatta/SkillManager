import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from skill_manager.core.discovery import parse_skill_md
from skill_manager.core.quick_copy import is_ignored, load_ignore_spec, project_root_for_project
from pathlib import Path

resolved = Path(r"C:\Users\DIKKA\Documents\01-Projects\20-AiSupportTools\SkillManager\.agents\skills")
project_root = project_root_for_project(resolved)
ignore_spec = load_ignore_spec(project_root)

child = resolved / "brainstorming"

print("is_ignored:", is_ignored(child, resolved, ignore_spec))

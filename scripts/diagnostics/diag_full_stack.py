import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
from skill_manager.app import AppController
from skill_manager.core.discovery import get_discovery_cache, load_cache

app = QApplication([])
ctrl = AppController()
# Run sync discovery logic
result = ctrl.discovery_controller._run_discovery_sync(force_full_scan=True)

cache = load_cache()
skills = cache.get("skills", [])

print(f"Total skills: {len(skills)}")
brain_skills = [s for s in skills if "brainstorming" in s.get("local_path", "").lower() and "skillmanager" in s.get("local_path", "").lower()]
for s in brain_skills:
    print(f"FOUND: is_package={s.get('is_package')}, path={s.get('local_path')}")

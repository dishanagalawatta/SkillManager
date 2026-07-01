import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import os

os.environ["QT_QPA_PLATFORM"] = "offscreen"


from skill_manager.core.discovery import get_discovery_cache

with get_discovery_cache() as cache:
    for key in cache:
        if isinstance(key, str) and (
            key.startswith("pkg_skills:") or key.startswith("proj_skills:")
        ):
            print(f"\n--- {key} ---")
            skills = cache.get(key)
            if isinstance(skills, list):
                for s in skills:
                    print(f"  {s.get('is_package', 'N/A')} - {s.get('local_path')}")
            elif isinstance(skills, dict):
                for s in skills.get("skills", []):
                    print(f"  {s.get('is_package', 'N/A')} - {s.get('local_path')}")

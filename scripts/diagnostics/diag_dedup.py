import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
from skill_manager.app import AppController
from skill_manager.core.discovery import DiscoveryService

app = QApplication([])
ctrl = AppController()

discovery_sources = list(ctrl._sources)
for src in ctrl._update_packages:
    pkg_path = src.get("package_path") or src.get("local_path")
    if pkg_path and os.path.exists(pkg_path) and pkg_path not in discovery_sources:
        discovery_sources.append(pkg_path)

service = DiscoveryService(
    sources=discovery_sources,
    projects=ctrl._projects,
    archive_paths=ctrl._archive_paths,
    starred_paths=ctrl._starred_paths,
    project_aliases=ctrl._project_aliases,
)
    
result = service.discover_all(use_cache=False, force_full_scan=False)
skills = result.get("skills", [])

print("total skills returned:", len(skills))
for s in skills:
    lp = s.get("local_path", "")
    if "brainstorming" in lp.lower() and "skillmanager" in lp.lower():
        print(f"FOUND: is_package={s.get('is_package')}, path={lp}")

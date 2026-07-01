import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import os

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication

from skill_manager.app import AppController
from skill_manager.core.discovery import (
    DiscoveryService,
    categorize_skill,
    get_discovery_cache,
    parse_skill_md,
)

app = QApplication([])
ctrl = AppController()

service = DiscoveryService(
    sources=ctrl._sources,
    projects=ctrl._projects,
    archive_paths=ctrl._archive_paths,
    starred_paths=ctrl._starred_paths,
    project_aliases=ctrl._project_aliases,
)

with get_discovery_cache() as cache:
    proj_raw = service.discover_projects_incremental(cache, parse_skill_md, categorize_skill, False)

    print("Projects returned:", len(proj_raw))
    for p in proj_raw:
        print(f"Project: {p.get('project_label')}")
        for s in p.get("skills", []):
            if "brainstorming" in str(s).lower():
                print(f"  FOUND IN PROJECT: {s.get('local_path')}")

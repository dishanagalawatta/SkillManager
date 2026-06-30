import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"
from skill_manager.core.discovery import DiscoveryService, get_discovery_cache, parse_skill_md, categorize_skill
from skill_manager.app import AppController
from PySide6.QtWidgets import QApplication

app = QApplication([])
ctrl = AppController()
service = DiscoveryService(
    sources=ctrl._sources,
    projects=ctrl._projects,
    archive_paths=ctrl._archive_paths,
    starred_paths=ctrl._starred_paths,
    project_aliases=ctrl._project_aliases,
)

print(service.projects)

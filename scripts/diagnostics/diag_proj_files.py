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
    
with get_discovery_cache() as cache:
    # Just let it do its thing, but I want to print what is actually scanned
    for project in service.projects:
        from skill_manager.core.quick_copy import resolve_resilient_path
        resolved = resolve_resilient_path(project)
        if "SkillManager" in str(resolved):
            print(f"Scanning: {resolved}")
            for child in sorted(resolved.iterdir(), key=lambda i: i.name.lower()):
                print(f"  {child.name}: is_dir={child.is_dir()}")
                skill_md_path = child / "SKILL.md"
                print(f"    SKILL.md is_file: {skill_md_path.is_file()}")

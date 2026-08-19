import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import os

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication

from skill_manager.app import AppController
from skill_manager.core.discovery import (
    DiscoveryService,
    SkillRecord,
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
    pkg_raw = service.discover_packages_incremental(cache, parse_skill_md, categorize_skill, False)
    all_skills = []
    for s in pkg_raw:
        transformed = service.transform_skill(s, is_package=True)
        all_skills.append(SkillRecord.model_validate(transformed))

    proj_raw = service.discover_projects_incremental(cache, parse_skill_md, categorize_skill, False)
    for p in proj_raw:
        for s in p.get("skills", []):
            transformed = service.transform_skill(
                s, is_package=False, project_label=p.get("project_label")
            )
            all_skills.append(SkillRecord.model_validate(transformed))

    seen_paths = {}
    for skill in all_skills:
        lp = skill.local_path
        if "brainstorming" in lp.lower() and "skillmanager" in lp.lower():
            existing = seen_paths.get(lp)
            print(f"\nProcessing: {lp}")
            print(f"  skill.is_package = {skill.is_package}")
            print(f"  existing is None = {existing is None}")
            if existing:
                print(f"  existing.is_package = {existing.is_package}")
                print(
                    f"  condition: existing.is_package and not skill.is_package = {existing.is_package and not skill.is_package}"
                )

        if not lp:
            continue
        existing = seen_paths.get(lp)
        if existing is None or (existing.is_package and not skill.is_package):
            seen_paths[lp] = skill

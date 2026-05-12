import json
import os
import unittest
from pathlib import Path
from unittest import mock

import _bootstrap  # noqa: F401
from _bootstrap import temporary_directory
from skill_manager.app import SkillManagerApp


class SkillCategorizationTests(unittest.TestCase):
    def app_shell(self):
        app = object.__new__(SkillManagerApp)
        app.sources = []
        return app

    def test_categorizes_previously_uncategorized_agent_skills(self):
        app = self.app_shell()
        skill_paths = {
            "brainstorming": Path(".agent/skills/brainstorming/SKILL.md"),
            "caveman": Path(".agent/skills/caveman/SKILL.md"),
            "concise-planning": Path(".agent/skills/concise-planning/SKILL.md"),
            "conductor-implement": Path(".agent/skills/conductor-implement/SKILL.md"),
            "senior-architect": Path(".agent/skills/senior-architect/SKILL.md"),
        }

        categories = {}
        for skill_name, skill_path in skill_paths.items():
            skill_data = app._parse_skill_md(str(skill_path))
            categories[skill_name] = app.categorize_skill(
                skill_data.get("name", ""),
                app._skill_classification_text(skill_data),
            )

        self.assertEqual(categories["brainstorming"], "Core Workflow")
        self.assertEqual(categories["caveman"], "Communications")
        self.assertEqual(categories["concise-planning"], "Core Workflow")
        self.assertEqual(categories["conductor-implement"], "Core Workflow")
        self.assertEqual(categories["senior-architect"], "Architecture")
        self.assertNotIn("Uncategorized", categories.values())

    def test_refresh_reclassifies_cached_uncategorized_library_skills(self):
        with temporary_directory() as tmp:
            root = Path(tmp)
            skill_dir = root / "skills" / "brainstorming"
            skill_dir.mkdir(parents=True)
            skill_md = skill_dir / "SKILL.md"
            skill_md.write_text(
                """---
name: brainstorming
description: Use before creative or constructive work for features, architecture, and behavior.
---
""",
                encoding="utf-8",
            )
            stat = skill_md.stat()
            cache_key = os.path.normcase(os.path.abspath(skill_md))
            saved_caches = []

            app = self.app_shell()
            app.sources = [str(root / "skills")]
            cached_data = {
                "name": "brainstorming",
                "description": "Use before creative or constructive work for features, architecture, and behavior.",
                "category": "Uncategorized",
                "search_text": "brainstorming uncategorized",
                "metadata": {},
            }

            with mock.patch.object(app, "_load_skill_library_cache", return_value={
                "version": 1,
                "skills": {
                    cache_key: {
                        "mtime_ns": stat.st_mtime_ns,
                        "size": stat.st_size,
                        "data": cached_data,
                    }
                },
            }):
                with mock.patch.object(app, "_save_skill_library_cache", side_effect=saved_caches.append):
                    skills = app.load_local_skills()

            self.assertEqual(skills[0]["category"], "Core Workflow")
            self.assertIn("core workflow", skills[0]["search_text"])
            self.assertEqual(saved_caches[0]["skills"][cache_key]["data"]["category"], "Core Workflow")

    def test_manual_category_change_updates_skill_and_cache(self):
        with temporary_directory() as tmp:
            root = Path(tmp)
            skill_dir = root / "skills" / "alpha"
            skill_dir.mkdir(parents=True)
            skill_md = skill_dir / "SKILL.md"
            skill_md.write_text(
                """---
name: alpha
description: Small frontend helper.
---
""",
                encoding="utf-8",
            )
            stat = skill_md.stat()
            cache_key = os.path.normcase(os.path.abspath(skill_md))
            saved_caches = []

            app = self.app_shell()
            skill = {
                "name": "alpha",
                "description": "Small frontend helper.",
                "category": "Web Development",
                "local_path": str(skill_dir),
                "skill_md_path": str(skill_md),
                "search_text": "alpha web development",
            }
            app.library_skills = [skill]
            app.filtered_library_skills = [skill]

            cache = {
                "version": 1,
                "skills": {
                    cache_key: {
                        "mtime_ns": stat.st_mtime_ns,
                        "size": stat.st_size,
                        "data": dict(skill),
                    }
                },
            }

            with mock.patch.object(app, "_load_skill_library_cache", return_value=json.loads(json.dumps(cache))):
                with mock.patch.object(app, "_save_skill_library_cache", side_effect=saved_caches.append):
                    app._update_skill_category(skill, "Core Workflow")

            self.assertEqual(skill["category"], "Core Workflow")
            self.assertIn("core workflow", skill["search_text"])
            self.assertEqual(saved_caches[0]["skills"][cache_key]["data"]["category"], "Core Workflow")
            self.assertIn("core workflow", saved_caches[0]["skills"][cache_key]["data"]["search_text"])


if __name__ == "__main__":
    unittest.main()

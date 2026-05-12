import importlib
import json
import os
import unittest
from pathlib import Path

import _bootstrap  # noqa: F401
from _bootstrap import temporary_directory


class SkillUpdateSyncTests(unittest.TestCase):
    def setUp(self):
        self._old_data_dir = os.environ.get("SKILL_MANAGER_DATA_DIR")

    def tearDown(self):
        if self._old_data_dir is None:
            os.environ.pop("SKILL_MANAGER_DATA_DIR", None)
        else:
            os.environ["SKILL_MANAGER_DATA_DIR"] = self._old_data_dir

    def _reload_app(self, data_dir):
        os.environ["SKILL_MANAGER_DATA_DIR"] = str(data_dir)
        import skill_manager.core.config as config
        import skill_manager.app as app

        importlib.reload(config)
        return importlib.reload(app)

    def test_skill_source_update_syncs_configured_project_skill_targets(self):
        with temporary_directory() as tmp:
            root = Path(tmp)
            data_dir = root / "data"
            data_dir.mkdir()
            (data_dir / "config.json").write_text(
                json.dumps({"targets": [], "sources": [], "skills": []}),
                encoding="utf-8",
            )

            source_skill = root / "source" / "brainstorming"
            source_skill.mkdir(parents=True)
            (source_skill / "SKILL.md").write_text("new skill\n", encoding="utf-8")

            target_root = root / "project" / ".agent" / "skills"
            target_skill = target_root / "brainstorming"
            target_skill.mkdir(parents=True)
            (target_skill / "SKILL.md").write_text("old skill\n", encoding="utf-8")

            app_module = self._reload_app(data_dir)
            app = app_module.SkillManagerApp.__new__(app_module.SkillManagerApp)
            app.targets = [str(target_root)]
            app.sources = [str(root / "source")]
            messages = []

            result = app._sync_project_targets_after_skill_update(messages.append)

            self.assertEqual(result, "Synced project folders: 1 updated, 0 skipped.")
            self.assertEqual((target_skill / "SKILL.md").read_text(encoding="utf-8"), "new skill\n")
            self.assertTrue(any("Syncing project skills: Updating 'brainstorming'" in msg for msg in messages))


if __name__ == "__main__":
    unittest.main()

import json
import os
import tempfile
import unittest
from pathlib import Path

from skill_manager.core.config import ConfigManager


class TestRenameMigration(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_path = Path(self.temp_dir.name) / "config.json"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_migration_from_targets_to_projects(self):
        # Create a legacy config
        legacy_data = {
            "targets": ["/path/1", "/path/2"],
            "target_aliases": {"/path/1": "Project A"},
            "other_setting": True,
        }
        with open(self.config_path, "w") as f:
            json.dump(legacy_data, f)

        # Initialize ConfigManager
        os.environ["SKILL_MANAGER_DATA_DIR"] = self.temp_dir.name

        mgr = ConfigManager()

        # Check if data was migrated
        self.assertEqual(mgr.get("projects"), ["/path/1", "/path/2"])
        self.assertEqual(mgr.get("project_aliases"), {"/path/1": "Project A"})
        self.assertTrue(mgr.get("other_setting"))

        # Check if old keys are gone
        self.assertNotIn("targets", mgr.data)
        self.assertNotIn("target_aliases", mgr.data)

        # Verify it was saved
        with open(self.config_path) as f:
            saved_data = json.load(f)
            self.assertIn("projects", saved_data)
            self.assertIn("project_aliases", saved_data)
            self.assertNotIn("targets", saved_data)
            self.assertNotIn("target_aliases", saved_data)


if __name__ == "__main__":
    unittest.main()

import importlib
import json
import os
import unittest
from pathlib import Path
from unittest import mock

import _bootstrap  # noqa: F401
from _bootstrap import temporary_directory


class ConfigManagerTests(unittest.TestCase):
    def setUp(self):
        self._old_data_dir = os.environ.get("SKILL_MANAGER_DATA_DIR")
        self._old_cwd = Path.cwd()

    def tearDown(self):
        if self._old_data_dir is None:
            os.environ.pop("SKILL_MANAGER_DATA_DIR", None)
        else:
            os.environ["SKILL_MANAGER_DATA_DIR"] = self._old_data_dir
        os.chdir(self._old_cwd)

    def _reload_config(self, data_dir=None):
        if data_dir is None:
            os.environ.pop("SKILL_MANAGER_DATA_DIR", None)
        else:
            os.environ["SKILL_MANAGER_DATA_DIR"] = str(data_dir)
        import skill_manager.core.config as config

        return importlib.reload(config)

    def test_migrates_legacy_root_json_files_to_data_dir(self):
        with temporary_directory() as tmp:
            root = Path(tmp)
            workspace = root / "workspace"
            data_dir = root / "data"
            workspace.mkdir()
            data_dir.mkdir()

            (workspace / "config.json").write_text(
                json.dumps({"targets": ["target-a"], "sources": ["source-a"], "skills": []}),
                encoding="utf-8",
            )
            (workspace / "skill_library_clipboard.json").write_text(
                json.dumps({"client_format": "Codex", "skill_sets": {"daily": {"skill_keys": []}}}),
                encoding="utf-8",
            )
            (workspace / "skill_library_archive.json").write_text(
                json.dumps({"archived_skills": ["old"], "archived_categories": []}),
                encoding="utf-8",
            )
            (workspace / "skill_library_index.json").write_text(
                json.dumps({"version": 8, "skills": {}}),
                encoding="utf-8",
            )
            (workspace / "project_skill_clipboard.json").write_text(
                json.dumps({"client_format": "Codex", "skill_sets": {}}),
                encoding="utf-8",
            )
            (workspace / "skill_library_starred.json").write_text(
                json.dumps({"starred": []}),
                encoding="utf-8",
            )
            (workspace / "skills-lock.json").write_text(
                json.dumps({"version": 1, "skills": {}}),
                encoding="utf-8",
            )
            (workspace / "temp_copies.json").write_text(
                json.dumps({}),
                encoding="utf-8",
            )
            (workspace / "quick_copy.json").write_text(
                json.dumps({}),
                encoding="utf-8",
            )

            os.chdir(workspace)
            with mock.patch.dict(os.environ, {"SKILL_MANAGER_ALLOW_MIGRATION": "1"}):
                config = self._reload_config(data_dir)

                manager = config.ConfigManager()

            # Targets should be migrated to projects
            self.assertEqual(manager.get("projects"), ["target-a"])
            # Verify core files migrated
            self.assertTrue((data_dir / "config.json").is_file())
            self.assertTrue((data_dir / "skill_library_index.json").is_file())
            self.assertTrue((data_dir / "quick_copy.json").is_file())
            self.assertTrue((data_dir / "temp_copies.json").is_file())

    def test_set_persists_to_config_file(self):
        with temporary_directory() as tmp:
            data_dir = Path(tmp) / "data"
            data_dir.mkdir()
            config = self._reload_config(data_dir)

            manager = config.ConfigManager()
            manager.set("projects", ["project-a"])

            saved = json.loads((data_dir / "config.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["projects"], ["project-a"])

    def test_default_data_dir_is_stable_across_working_directories(self):
        with temporary_directory() as tmp:
            root = Path(tmp)
            local_app_data = root / "local-app-data"
            workspace_a = root / "workspace-a"
            workspace_b = root / "workspace-b"
            workspace_a.mkdir()
            workspace_b.mkdir()

            with mock.patch.dict(os.environ, {"LOCALAPPDATA": str(local_app_data)}, clear=False):
                config = self._reload_config()

                os.chdir(workspace_a)
                path_a = config.resolve_data_file("config.json")
                os.chdir(workspace_b)
                path_b = config.resolve_data_file("config.json")

            self.assertEqual(path_a, path_b)
            self.assertEqual(path_a.parent, local_app_data / "SkillManager")

    def test_resolve_data_file_respects_late_data_dir_override(self):
        with temporary_directory() as tmp:
            root = Path(tmp)
            initial_data_dir = root / "initial-data"
            late_data_dir = root / "late-data"
            initial_data_dir.mkdir()
            late_data_dir.mkdir()
            os.chdir(root)

            config = self._reload_config(initial_data_dir)
            os.environ["SKILL_MANAGER_DATA_DIR"] = str(late_data_dir)

            manager = config.ConfigManager()
            manager.set("projects", ["late-project"])

            saved = json.loads((late_data_dir / "config.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["projects"], ["late-project"])
            self.assertFalse((initial_data_dir / "config.json").exists())

    def test_migrates_repo_local_data_json_files_to_stable_data_dir(self):
        with temporary_directory() as tmp:
            root = Path(tmp)
            workspace = root / "workspace"
            data_dir = root / "stable-data"
            repo_data = workspace / "data"
            workspace.mkdir()
            repo_data.mkdir()
            data_dir.mkdir()

            (repo_data / "config.json").write_text(
                json.dumps({"targets": ["repo-data-target"], "sources": []}),
                encoding="utf-8",
            )

            os.chdir(workspace)
            with mock.patch.dict(os.environ, {"SKILL_MANAGER_ALLOW_MIGRATION": "1"}):
                config = self._reload_config(data_dir)
                manager = config.ConfigManager()

            self.assertEqual(manager.get("projects"), ["repo-data-target"])
            self.assertTrue((data_dir / "config.json").is_file())

    def test_resolve_data_file_falls_back_to_legacy_when_copy_is_blocked(self):
        with temporary_directory() as tmp:
            root = Path(tmp)
            workspace = root / "workspace"
            data_dir = root / "data"
            workspace.mkdir()
            data_dir.mkdir()
            os.chdir(workspace)

            config = self._reload_config(data_dir)

            legacy_file = workspace / "skill_library_archive.json"
            legacy_file.write_text(json.dumps({"archived_skills": []}), encoding="utf-8")

            with (
                mock.patch.object(config.shutil, "copy2", side_effect=OSError("blocked")),
                mock.patch("builtins.print"),
            ):
                resolved = config.resolve_data_file(
                    "skill_library_archive.json",
                    data_dir=data_dir,
                    legacy_dir=workspace,
                )

            self.assertEqual(resolved, legacy_file)

    def test_get_app_data_dir_fallback_to_user_data_dir(self):
        with temporary_directory() as tmp:
            env = {
                "SKILL_MANAGER_DATA_DIR": "",
                "LOCALAPPDATA": "",
                "APPDATA": "",
            }
            with mock.patch.dict(os.environ, env, clear=False):
                import importlib
                import skill_manager.core.config as cfg

                importlib.reload(cfg)
                app_dir = cfg.get_app_data_dir()
                self.assertTrue(app_dir.exists())
                self.assertEqual(app_dir.name, "SkillManager")


if __name__ == "__main__":
    unittest.main()

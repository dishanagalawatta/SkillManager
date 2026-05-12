import subprocess
import unittest
from unittest import mock

import _bootstrap  # noqa: F401

from skill_manager.core import skill_sources


class SkillSourceTests(unittest.TestCase):
    def test_normalize_preserves_legacy_command_source(self):
        source = skill_sources.normalize_skill_source_config({
            "name": "Antigravity Awesome Skills",
            "update_command": "npx --yes antigravity-awesome-skills --gemini",
            "latest_version_command": "npm show antigravity-awesome-skills version",
        })

        self.assertEqual(source["name"], "Antigravity Awesome Skills")
        self.assertEqual(source["repository_url"], "")
        self.assertEqual(source["local_path"], "")
        self.assertEqual(source["source_type"], "npm")
        self.assertEqual(source["package_name"], "antigravity-awesome-skills")
        self.assertEqual(source["install_args"], "--gemini")
        self.assertEqual(source["update_command"], "npx --yes antigravity-awesome-skills --gemini")
        self.assertEqual(source["latest_version_command"], "npm show antigravity-awesome-skills version")

    def test_normalize_builds_npm_commands_from_human_fields(self):
        source = skill_sources.normalize_skill_source_config({
            "source_type": "npm",
            "package_name": "antigravity-awesome-skills",
            "install_args": "--gemini",
            "update_command": "stale command",
            "latest_version_command": "stale latest",
        })

        self.assertEqual(source["update_command"], "npx --yes antigravity-awesome-skills --gemini")
        self.assertEqual(source["latest_version_command"], "npm show antigravity-awesome-skills version")

    def test_npm_update_runs_generated_npx_command(self):
        with (
            mock.patch.object(skill_sources, "_run_process") as run_process,
            mock.patch.object(skill_sources, "run_version_command", return_value=""),
        ):
            skill_sources.run_skill_source_update({
                "source_type": "npm",
                "package_name": "example-skills",
                "install_args": "--codex",
            })

        run_process.assert_called_once_with(
            ["npx", "--yes", "example-skills", "--codex"],
            mock.ANY,
        )

    def test_run_process_resolves_windows_command_shims(self):
        with (
            mock.patch.object(skill_sources.shutil, "which", return_value="C:/Node/npx.cmd"),
            mock.patch.object(skill_sources.subprocess, "Popen") as popen,
        ):
            process = popen.return_value
            process.stdout = []
            process.returncode = 0

            skill_sources._run_process(["npx", "--yes", "example-skills"], None)

        popen.assert_called_once()
        self.assertEqual(popen.call_args.args[0], ["C:/Node/npx.cmd", "--yes", "example-skills"])

    def test_run_process_reports_missing_executable_name(self):
        with mock.patch.object(skill_sources.shutil, "which", return_value=None):
            with self.assertRaisesRegex(FileNotFoundError, "Executable 'npx' was not found"):
                skill_sources._run_process(["npx", "--yes", "example-skills"], None)

    def test_repository_update_pulls_existing_checkout(self):
        with mock.patch.object(skill_sources.Path, "is_dir", return_value=True):
            with mock.patch.object(skill_sources, "_run_process") as run_process:
                skill_sources.run_skill_source_update({
                    "name": "Repo Skills",
                    "repository_url": "https://example.test/skills.git",
                    "local_path": "C:/skills/repo",
                })

        run_process.assert_called_once_with(
            ["git", "-C", "C:\\skills\\repo", "pull", "--ff-only"],
            mock.ANY,
        )

    def test_repository_update_requires_repo_or_command(self):
        with self.assertRaisesRegex(ValueError, "update command"):
            skill_sources.run_skill_source_update({"name": "Broken"})

    def test_check_versions_updates_current_and_latest(self):
        def fake_run(command, shell, capture_output, text, timeout):
            self.assertTrue(shell)
            output = {
                "current": "1.0.0\n",
                "latest": "1.1.0\n",
            }[command]
            return subprocess.CompletedProcess(command, 0, stdout=output, stderr="")

        with mock.patch.object(skill_sources.subprocess, "run", side_effect=fake_run):
            source = skill_sources.check_skill_source_versions({
                "name": "Versioned",
                "current_version_command": "current",
                "latest_version_command": "latest",
            })

        self.assertEqual(source["current_version"], "1.0.0")
        self.assertEqual(source["latest_version"], "1.1.0")


if __name__ == "__main__":
    unittest.main()

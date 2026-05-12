import unittest
from pathlib import Path

import _bootstrap  # noqa: F401
from _bootstrap import temporary_directory
from skill_manager.core.copier import copy_skill_folders_to_targets


class SkillCopyTests(unittest.TestCase):
    def temporary_workspace(self):
        return temporary_directory()

    def test_copies_entire_skill_folder_to_multiple_targets(self):
        with self.temporary_workspace() as tmp:
            root = Path(tmp)
            source = root / "source-skill"
            (source / "scripts").mkdir(parents=True)
            (source / "SKILL.md").write_text("# Skill\n", encoding="utf-8")
            (source / "scripts" / "tool.py").write_text("print('ok')\n", encoding="utf-8")

            target_a = root / "project-a" / ".agent" / "skills"
            target_b = root / "project-b" / ".codex" / "skills"
            target_a.mkdir(parents=True)
            target_b.mkdir(parents=True)

            result = copy_skill_folders_to_targets(
                [{"name": "Source Skill", "folder_name": "source-skill", "local_path": str(source)}],
                [str(target_a), str(target_b)]
            )

            self.assertEqual(result["copied"], 2)
            self.assertEqual(result["merged"], 0)
            self.assertEqual(result["skipped"], 0)
            self.assertEqual(result["failed"], 0)
            self.assertEqual((target_a / "source-skill" / "SKILL.md").read_text(encoding="utf-8"), "# Skill\n")
            self.assertEqual((target_b / "source-skill" / "scripts" / "tool.py").read_text(encoding="utf-8"), "print('ok')\n")

    def test_merge_overwrites_matching_files_and_keeps_extra_files(self):
        with self.temporary_workspace() as tmp:
            root = Path(tmp)
            source = root / "source-skill"
            source.mkdir()
            (source / "SKILL.md").write_text("new skill\n", encoding="utf-8")
            (source / "asset.txt").write_text("new asset\n", encoding="utf-8")

            target = root / "project" / ".agent" / "skills"
            existing = target / "source-skill"
            existing.mkdir(parents=True)
            (existing / "SKILL.md").write_text("old skill\n", encoding="utf-8")
            (existing / "old-only.txt").write_text("keep me\n", encoding="utf-8")

            result = copy_skill_folders_to_targets(
                [{"name": "Source Skill", "folder_name": "source-skill", "local_path": str(source)}],
                [str(target)]
            )

            self.assertEqual(result["copied"], 0)
            self.assertEqual(result["merged"], 1)
            self.assertEqual((existing / "SKILL.md").read_text(encoding="utf-8"), "new skill\n")
            self.assertEqual((existing / "asset.txt").read_text(encoding="utf-8"), "new asset\n")
            self.assertEqual((existing / "old-only.txt").read_text(encoding="utf-8"), "keep me\n")

    def test_skips_invalid_skill_folder(self):
        with self.temporary_workspace() as tmp:
            root = Path(tmp)
            source = root / "source-skill"
            source.mkdir()
            target = root / "project" / ".agent" / "skills"
            target.mkdir(parents=True)

            result = copy_skill_folders_to_targets(
                [{"name": "Broken Skill", "folder_name": "source-skill", "local_path": str(source)}],
                [str(target)]
            )

            self.assertEqual(result["copied"], 0)
            self.assertEqual(result["merged"], 0)
            self.assertEqual(result["skipped"], 1)
            self.assertEqual(result["failed"], 0)
            self.assertIn("missing SKILL.md", result["details"][0]["message"])


if __name__ == "__main__":
    unittest.main()

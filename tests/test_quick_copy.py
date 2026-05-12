import unittest
from pathlib import Path

import _bootstrap  # noqa: F401
from _bootstrap import temporary_directory
from skill_manager.core.quick_copy import (
    delete_project_skill_folders,
    discover_project_skills,
    format_project_skill_reference,
    merge_manual_references,
    normalize_manual_references,
)


class QuickCopyTests(unittest.TestCase):
    def parse_skill_md(self, path):
        text = Path(path).read_text(encoding="utf-8")
        name = Path(path).parent.name
        description = ""
        for line in text.splitlines():
            if line.startswith("description:"):
                description = line.split(":", 1)[1].strip().strip('"')
        return {"name": name, "description": description, "raw_content": text, "metadata": {}}

    def categorize_skill(self, name, description):
        if "architect" in f"{name} {description}".lower():
            return "Architecture"
        return "Core Workflow"

    def build_search_text(self, skill):
        return " ".join([
            skill.get("name", ""),
            skill.get("description", ""),
            skill.get("category", ""),
            skill.get("folder_name", ""),
        ]).lower()

    def test_discovers_only_projects_with_valid_skill_folders(self):
        with temporary_directory() as tmp:
            root = Path(tmp)
            target_a = root / "project-a" / ".agent" / "skills"
            target_b = root / "project-b" / ".codex" / "skills"
            empty_target = root / "empty" / ".agent" / "skills"
            missing_target = root / "missing" / ".agent" / "skills"
            (target_a / "concise-planning").mkdir(parents=True)
            (target_a / "concise-planning" / "SKILL.md").write_text("description: planning helper\n", encoding="utf-8")
            (target_a / "broken-skill").mkdir()
            (target_b / "senior-architect").mkdir(parents=True)
            (target_b / "senior-architect" / "SKILL.md").write_text("description: architect helper\n", encoding="utf-8")
            empty_target.mkdir(parents=True)

            projects = discover_project_skills(
                [target_a, empty_target, missing_target, target_b],
                self.parse_skill_md,
                self.categorize_skill,
                self.build_search_text,
            )

            self.assertEqual([project["project_label"] for project in projects], [
                "project-a (.agent/skills)",
                "project-b (.codex/skills)",
            ])
            self.assertEqual(projects[0]["skill_base_relative"], ".agent/skills")
            self.assertEqual(projects[1]["skills"][0]["category"], "Architecture")

    def test_formats_project_relative_references(self):
        skill = {
            "name": "senior-architect",
            "skill_base_relative": ".codex/skills",
            "folder_name": "senior-architect",
            "skill_md_path": "/abs/path/to/senior-architect/SKILL.md"
        }

        self.assertEqual(
            format_project_skill_reference(skill, "Codex"),
            "[$senior-architect](/abs/path/to/senior-architect/SKILL.md)",
        )
        self.assertEqual(
            format_project_skill_reference(skill, "Gemini CLI"),
            "@.codex/skills/senior-architect/SKILL.md",
        )
        self.assertEqual(
            format_project_skill_reference(skill, "Plain Path"),
            ".codex/skills/senior-architect/SKILL.md",
        )

    def test_normalizes_manual_references_for_clipboard_output(self):
        self.assertEqual(
            normalize_manual_references(
                "caveman\n@brainstorming\n.agent/skills/senior-architect/SKILL.md\n[SKILL.md](.agent/skills/concise-planning/SKILL.md)"
            ),
            [
                "@caveman",
                "@brainstorming",
                ".agent/skills/senior-architect/SKILL.md",
                "[SKILL.md](.agent/skills/concise-planning/SKILL.md)",
            ],
        )

    def test_merges_manual_references_without_duplicates(self):
        self.assertEqual(
            merge_manual_references(["@caveman", "brainstorming"], ["caveman", "@senior-architect"]),
            ["@caveman", "@brainstorming", "@senior-architect"],
        )

    def test_delete_project_skill_folders_is_scoped_to_direct_skill_children(self):
        with temporary_directory() as tmp:
            root = Path(tmp)
            target = root / "project" / ".agent" / "skills"
            valid = target / "concise-planning"
            invalid = target / "not-a-skill"
            outside = root / "outside-skill"
            valid.mkdir(parents=True)
            invalid.mkdir()
            outside.mkdir()
            (valid / "SKILL.md").write_text("# Skill\n", encoding="utf-8")
            (outside / "SKILL.md").write_text("# Skill\n", encoding="utf-8")

            result = delete_project_skill_folders([
                {"name": "Valid", "local_path": str(valid), "target_path": str(target)},
                {"name": "Invalid", "local_path": str(invalid), "target_path": str(target)},
                {"name": "Outside", "local_path": str(outside), "target_path": str(target)},
            ])

            self.assertEqual(result["deleted"], 1)
            self.assertEqual(result["skipped"], 2)
            self.assertFalse(valid.exists())
            self.assertTrue(invalid.exists())
            self.assertTrue(outside.exists())


if __name__ == "__main__":
    unittest.main()

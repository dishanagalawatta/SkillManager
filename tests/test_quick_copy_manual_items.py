import unittest
import json
from pathlib import Path
from unittest import mock

import _bootstrap  # noqa: F401
from _bootstrap import temporary_directory
from skill_manager.app import SkillManagerApp


class QuickCopyTreeStub:
    def __init__(self):
        self.rows = {}
        self.children = {"": []}
        self.counter = 0
        self.selected = ()

    def insert(self, parent, _index, text="", values=(), tags=(), open=False):
        self.counter += 1
        item_id = f"row-{self.counter}"
        self.rows[item_id] = {
            "parent": parent,
            "text": text,
            "values": values,
            "tags": tags,
            "open": open,
        }
        self.children.setdefault(parent, []).append(item_id)
        self.children.setdefault(item_id, [])
        return item_id

    def get_children(self, item=""):
        return tuple(self.children.get(item, ()))

    def delete(self, item_id):
        parent = self.rows[item_id]["parent"]
        self.children[parent].remove(item_id)
        for child_id in list(self.children.get(item_id, ())):
            self.delete(child_id)
        self.children.pop(item_id, None)
        self.rows.pop(item_id, None)

    def selection(self):
        return self.selected

    def selection_set(self, selected):
        self.selected = tuple(selected)

    def item(self, item_id, option=None, **kwargs):
        if kwargs:
            self.rows[item_id].update(kwargs)
        if option:
            return self.rows[item_id][option]
        return self.rows[item_id]


class VarStub:
    def __init__(self, value=""):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class QuickCopyManualItemsTests(unittest.TestCase):
    def build_app_shell(self):
        app = object.__new__(SkillManagerApp)
        app.quick_copy_manual_references = ["@caveman", "[SKILL.md](.agent/skills/brainstorming/SKILL.md)"]
        app.quick_copy_manual_references_by_project = {}
        app.quick_copy_essential_skill_keys = set()
        app.quick_copy_essential_skill_keys_by_project = {}
        app.quick_copy_projects = []
        app.quick_copy_selected_skill_keys = set()
        app.quick_copy_selected_project_key = ""
        app.quick_copy_selected_skill_keys_by_project = {}
        app.quick_copy_skill_arguments_by_project = {}
        app.quick_copy_project_options = []
        app.quick_copy_config = {"skill_sets": {}}

        class ClientVar:
            def get(self):
                return "Codex"

        app.quick_copy_client_var = ClientVar()
        return app

    def test_manual_references_become_skill_like_items(self):
        app = self.build_app_shell()

        skills = app._quick_copy_manual_skills()

        self.assertEqual([skill["name"] for skill in skills], ["caveman", "brainstorming"])
        self.assertTrue(all(skill["is_manual"] for skill in skills))
        self.assertEqual(app._quick_copy_skill_key(skills[0]), "manual:@caveman")
        self.assertEqual(app._quick_copy_display_category(skills[0]), "Manual")

    def test_manual_items_copy_as_original_references(self):
        app = self.build_app_shell()
        manual_skill = app._quick_copy_manual_skills()[1]
        project_skill = {"skill_base_relative": ".agent/skills", "folder_name": "senior-architect"}

        self.assertEqual(
            app._build_quick_copy_reference_output([project_skill, manual_skill]),
            "[SKILL.md](.agent/skills/senior-architect/SKILL.md)\n"
            "[SKILL.md](.agent/skills/brainstorming/SKILL.md)",
        )

    def test_selected_keys_include_manual_items(self):
        app = self.build_app_shell()
        manual_skill = app._quick_copy_manual_skills()[0]
        app.quick_copy_selected_skill_keys.add(app._quick_copy_skill_key(manual_skill))

        self.assertEqual(app._selected_quick_copy_skills(), [manual_skill])

    def test_selection_memory_is_scoped_by_selected_project(self):
        app = self.build_app_shell()
        app.quick_copy_projects = [
            {
                "project_key": "project-a",
                "skills": [{"name": "alpha", "local_path": "A", "project_key": "project-a"}],
            },
            {
                "project_key": "project-b",
                "skills": [{"name": "beta", "local_path": "B", "project_key": "project-b"}],
            },
        ]
        app.quick_copy_selected_project_key = "project-a"
        app.quick_copy_selected_skill_keys = {"a-key"}

        app._remember_quick_copy_selection_for_current_project()
        app.quick_copy_selected_project_key = "project-b"
        app.quick_copy_selected_skill_keys = {"b-key"}
        app._remember_quick_copy_selection_for_current_project()

        app.quick_copy_selected_project_key = "project-a"
        app._load_quick_copy_selection_for_current_project()
        self.assertEqual(app.quick_copy_selected_skill_keys, {"a-key"})

        app.quick_copy_selected_project_key = "project-b"
        app._load_quick_copy_selection_for_current_project()
        self.assertEqual(app.quick_copy_selected_skill_keys, {"b-key"})

    def test_selected_skills_are_limited_to_current_project(self):
        app = self.build_app_shell()
        project_a_skill = {"name": "alpha", "local_path": "A", "project_key": "project-a"}
        project_b_skill = {"name": "beta", "local_path": "B", "project_key": "project-b"}
        app.quick_copy_projects = [
            {"project_key": "project-a", "skills": [project_a_skill]},
            {"project_key": "project-b", "skills": [project_b_skill]},
        ]
        app.quick_copy_selected_project_key = "project-a"
        app.quick_copy_selected_skill_keys = {
            app._quick_copy_skill_key(project_a_skill),
            app._quick_copy_skill_key(project_b_skill),
        }

        self.assertEqual(app._selected_quick_copy_skills(), [project_a_skill])

    def test_manual_references_are_scoped_to_current_project(self):
        app = self.build_app_shell()
        app.quick_copy_manual_references_by_project = {
            "project-a": ["@alpha"],
            "project-b": ["@beta"],
        }
        app.quick_copy_selected_project_key = "project-a"
        app.quick_copy_project_options = [("Project A", "project-a"), ("Project B", "project-b")]

        app._load_quick_copy_manual_references_for_current_project()
        self.assertEqual(app.quick_copy_manual_references, ["@alpha"])
        self.assertEqual([skill["name"] for skill in app._quick_copy_skills_for_current_project()], ["alpha"])

        app.quick_copy_selected_project_key = "project-b"
        app._load_quick_copy_manual_references_for_current_project()
        self.assertEqual(app.quick_copy_manual_references, ["@beta"])
        self.assertEqual([skill["name"] for skill in app._quick_copy_skills_for_current_project()], ["beta"])

    def test_quick_copy_config_persists_project_selection_memory(self):
        with temporary_directory() as tmp:
            path = Path(tmp) / "quick_copy.json"
            path.write_text(
                json.dumps(
                    {
                        "client_format": "Codex",
                        "selected_project_key": "project-a",
                        "manual_references_by_project": {
                            "project-a": ["alpha", "alpha"],
                            "project-b": ["@beta"],
                        },
                        "selected_skill_keys_by_project": {
                            "project-a": ["a-key", "a-key"],
                            "project-b": ["b-key"],
                        },
                        "essential_skill_keys_by_project": {
                            "project-a": ["a-essential", "a-essential"],
                            "project-b": ["b-essential"],
                        },
                    }
                ),
                encoding="utf-8",
            )
            app = object.__new__(SkillManagerApp)
            app.library_clipboard_config = {}

            with mock.patch("skill_manager.app.QUICK_COPY_FILE", str(path)):
                config = app.load_quick_copy_config()

            self.assertEqual(config["selected_project_key"], "project-a")
            self.assertEqual(config["manual_references_by_project"], {
                "project-a": {"Codex": ["@alpha"]},
                "project-b": {"Codex": ["@beta"]},
            })
            self.assertEqual(config["selected_skill_keys_by_project"], {
                "project-a": ["a-key"],
                "project-b": ["b-key"],
            })
            self.assertEqual(config["essential_skill_keys_by_project"], {
                "project-a": ["a-essential"],
                "project-b": ["b-essential"],
            })

    def test_save_quick_copy_preferences_writes_project_selection_memory(self):
        with temporary_directory() as tmp:
            path = Path(tmp) / "quick_copy.json"
            app = self.build_app_shell()
            app.quick_copy_config = {"skill_sets": {}}
            app.quick_copy_selected_project_key = "project-a"
            app.quick_copy_selected_skill_keys = {"a-key"}
            app.quick_copy_selected_skill_keys_by_project = {}
            app.quick_copy_manual_references = ["alpha"]
            app.quick_copy_manual_references_by_project = {}
            app.quick_copy_essential_skill_keys = set()
            app.quick_copy_essential_skill_keys_by_project = {"project-b": {"b-essential"}}

            with mock.patch("skill_manager.app.QUICK_COPY_FILE", str(path)):
                app.save_quick_copy_preferences()

            saved = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(saved["selected_project_key"], "project-a")
            self.assertEqual(saved["selected_skill_keys_by_project"], {"project-a": ["a-key"]})
            self.assertEqual(saved["manual_references_by_project"], {"project-a": {"Codex": ["@alpha"]}})
            self.assertEqual(saved["essential_skill_keys_by_project"], {"project-a": [], "project-b": ["b-essential"]})

    def test_essentials_memory_is_scoped_to_current_project(self):
        app = self.build_app_shell()
        app.quick_copy_selected_project_key = "project-a"
        app.quick_copy_essential_skill_keys = {"a-essential"}

        app._remember_quick_copy_essentials_for_current_project()
        app.quick_copy_selected_project_key = "project-b"
        app.quick_copy_essential_skill_keys = {"b-essential"}
        app._remember_quick_copy_essentials_for_current_project()

        app.quick_copy_selected_project_key = "project-a"
        app._load_quick_copy_essentials_for_current_project()
        self.assertEqual(app.quick_copy_essential_skill_keys, {"a-essential"})

        app.quick_copy_selected_project_key = "project-b"
        app._load_quick_copy_essentials_for_current_project()
        self.assertEqual(app.quick_copy_essential_skill_keys, {"b-essential"})

    def test_essential_skills_are_limited_to_current_project(self):
        app = self.build_app_shell()
        project_a_skill = {"name": "alpha", "local_path": "A", "project_key": "project-a"}
        project_b_skill = {"name": "beta", "local_path": "B", "project_key": "project-b"}
        app.quick_copy_projects = [
            {"project_key": "project-a", "skills": [project_a_skill]},
            {"project_key": "project-b", "skills": [project_b_skill]},
        ]
        app.quick_copy_selected_project_key = "project-a"
        app.quick_copy_essential_skill_keys = {
            app._quick_copy_skill_key(project_a_skill),
            app._quick_copy_skill_key(project_b_skill),
        }

        self.assertEqual(app._quick_copy_essential_skills(), [project_a_skill])

    def test_essentials_category_sorts_before_other_categories(self):
        app = self.build_app_shell()

        categories = sorted(
            ["Manual", "Architecture", "Essentials", "Core Workflow"],
            key=app._quick_copy_category_sort_key,
        )

        self.assertEqual(categories, ["Essentials", "Architecture", "Core Workflow", "Manual"])

    def test_essential_project_and_manual_items_share_one_category_group(self):
        app = self.build_app_shell()
        project_skill = {"name": "senior-architect", "local_path": "A", "project_key": "project-a", "category": "Architecture"}
        manual_skill = app._quick_copy_manual_skill("@brainstorming")
        app.quick_copy_essential_skill_keys = {
            app._quick_copy_skill_key(project_skill),
            app._quick_copy_skill_key(manual_skill),
        }

        groups = app._quick_copy_category_groups([manual_skill, project_skill])

        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0][0], "Essentials")
        self.assertEqual([skill["name"] for skill in groups[0][1]], ["brainstorming", "senior-architect"])

    def test_essential_skill_rows_show_clean_names(self):
        app = self.build_app_shell()
        app.quick_copy_tree = QuickCopyTreeStub()
        app.quick_copy_tree_projects = {}
        app.quick_copy_tree_categories = {}
        app.quick_copy_tree_items = {}
        skill = {
            "name": "brainstorming",
            "folder_name": "brainstorming",
            "local_path": "C:/Projects/ProjectA/.agent/skills/brainstorming",
            "project_key": "project-a",
            "category": "Architecture",
        }
        app.quick_copy_essential_skill_keys = {app._quick_copy_skill_key(skill)}

        app._render_project_node({"project_key": "project-a"}, [skill])

        category_id = app.quick_copy_tree.get_children("")[0]
        skill_id = app.quick_copy_tree.get_children(category_id)[0]
        self.assertEqual(app.quick_copy_tree.rows[skill_id]["text"], "brainstorming")
        self.assertIn("essential", app.quick_copy_tree.rows[skill_id]["tags"])

        app._refresh_visible_quick_copy_prefixes()

        self.assertEqual(app.quick_copy_tree.rows[skill_id]["text"], "brainstorming")
        self.assertIn("essential", app.quick_copy_tree.rows[skill_id]["tags"])

    def test_quick_copy_render_hides_selected_project_header_row(self):
        app = self.build_app_shell()
        app.quick_copy_tree = QuickCopyTreeStub()
        app.quick_copy_tree_projects = {}
        app.quick_copy_tree_categories = {}
        app.quick_copy_tree_items = {}
        project = {
            "project_key": "project-a",
            "project_label": "Project A",
            "target_path": "C:/Projects/ProjectA/.agent/skills",
        }
        skill = {
            "name": "senior-architect",
            "folder_name": "senior-architect",
            "project_key": "project-a",
            "project_label": "Project A",
            "target_path": "C:/Projects/ProjectA/.agent/skills",
            "category": "Architecture",
        }

        app._render_project_node(project, [skill])

        top_level = app.quick_copy_tree.get_children("")
        self.assertEqual(len(top_level), 1)
        category_id = top_level[0]
        self.assertEqual(app.quick_copy_tree.rows[category_id]["text"], "Architecture (1)")
        self.assertEqual(app.quick_copy_tree.rows[category_id]["values"], ("",))
        self.assertEqual(app.quick_copy_tree.rows[category_id]["tags"], ("category",))
        self.assertEqual(app.quick_copy_tree_projects, {})

    def test_saved_bundle_detail_summarizes_contents(self):
        app = self.build_app_shell()
        app.quick_copy_config["skill_sets"] = {
            "Daily": {
                "skill_keys": ["project:one", "project:two"],
                "manual_references": ["@caveman"],
                "updated_at": "2026-04-30 17:45:00",
            }
        }

        self.assertEqual(
            app._quick_copy_set_detail_text("Daily"),
            "Daily: 2 project skill(s), 1 manual reference(s). Updated 2026-04-30 17:45:00.",
        )

    def test_bundle_selector_applies_saved_manuals_without_load_button(self):
        app = self.build_app_shell()
        project_skill = {
            "name": "senior-architect",
            "skill_base_relative": ".agent/skills",
            "folder_name": "senior-architect",
            "project_key": "project-a",
            "project_label": "Project A",
            "category": "Architecture",
        }
        app.quick_copy_projects = [{"project_key": "project-a", "skills": [project_skill]}]
        app.quick_copy_selected_project_key = "project-a"
        app.quick_copy_config["skill_sets"] = {
            "Daily": {
                "skill_keys": [app._quick_copy_skill_key(project_skill)],
                "manual_references": ["@caveman"],
            }
        }
        app.quick_copy_manual_references = []
        app.quick_copy_set_var = mock.Mock()
        app.quick_copy_set_var.get.return_value = "Daily"
        app.quick_copy_tree = QuickCopyTreeStub()
        app.quick_copy_tree_items = {}
        item_id = app.quick_copy_tree.insert("", "end", text="senior-architect")
        app.quick_copy_tree_items[item_id] = project_skill
        app.quick_copy_status_label = mock.Mock()
        app.save_quick_copy_preferences = lambda: None
        app._refresh_quick_copy_set_details = lambda: None
        app._refresh_visible_quick_copy_prefixes = lambda: None
        app._update_quick_copy_selected_count = lambda: None
        app._refresh_quick_copy_manual_label = lambda: None
        app._apply_quick_copy_filters = lambda: None

        app._change_quick_copy_set("Daily")

        self.assertEqual(app.quick_copy_manual_references, ["@caveman"])
        self.assertEqual(
            app.quick_copy_selected_skill_keys,
            {app._quick_copy_skill_key(project_skill), "manual:@caveman"},
        )
        self.assertEqual(app.quick_copy_tree.selection(), (item_id,))

    def test_quick_copy_render_does_not_show_passive_scope_count(self):
        app = self.build_app_shell()
        project_skill = {
            "name": "senior-architect",
            "description": "Architecture helper",
            "local_path": "C:/Projects/ProjectA/.agent/skills/senior-architect",
            "project_key": "project-a",
            "project_label": "Project A",
            "category": "Architecture",
        }
        app.quick_copy_projects = [{"project_key": "project-a", "skills": [project_skill]}]
        app.filtered_quick_copy_projects = app.quick_copy_projects
        app.filtered_quick_copy_manual_skills = []
        app.quick_copy_selected_project_key = "project-a"
        app.quick_copy_tree = QuickCopyTreeStub()
        app.quick_copy_tree_projects = {}
        app.quick_copy_tree_categories = {}
        app.quick_copy_tree_items = {}
        app.quick_copy_status_label = mock.Mock()
        app._description_peek_after_id = None
        app._description_peek_window = None
        app._description_peek_key = None
        app._remember_quick_copy_selection_for_current_project = lambda: None

        app._render_quick_copy_tree()

        app.quick_copy_status_label.configure.assert_called_with(text="")
        status_texts = [
            call.kwargs.get("text", "")
            for call in app.quick_copy_status_label.configure.call_args_list
        ]
        self.assertNotIn("1/1 shown in Project A (.agent/skills).", status_texts)

    def test_bundle_menu_always_includes_deselect_option(self):
        app = self.build_app_shell()
        app.quick_copy_config["skill_sets"] = {"Daily": {}, "Core": {}}

        self.assertEqual(
            app._quick_copy_set_menu_values(),
            ["No Bundle Selected", "Core", "Daily"],
        )

    def test_manual_skill_selection_clears_selected_bundle(self):
        app = self.build_app_shell()
        skill = {"name": "senior-architect", "local_path": "A", "project_key": "project-a"}
        app.quick_copy_config["skill_sets"] = {"Daily": {"skill_keys": [app._quick_copy_skill_key(skill)]}}
        app.quick_copy_set_var = VarStub("Daily")
        app._refresh_quick_copy_set_details = lambda: None

        app.toggle_quick_copy_skill_selection(skill)

        self.assertEqual(app.quick_copy_set_var.get(), "No Bundle Selected")

    def test_edit_bundle_renames_and_replaces_contents_from_selection(self):
        app = self.build_app_shell()
        project_skill = {
            "name": "senior-architect",
            "skill_base_relative": ".agent/skills",
            "folder_name": "senior-architect",
            "project_key": "project-a",
            "project_label": "Project A",
            "category": "Architecture",
        }
        manual_skill = app._quick_copy_manual_skill("@caveman")
        app.quick_copy_projects = [{"project_key": "project-a", "skills": [project_skill]}]
        app.quick_copy_selected_project_key = "project-a"
        app.quick_copy_config["skill_sets"] = {"Daily": {"skill_keys": ["old"], "manual_references": []}}
        app.quick_copy_selected_skill_keys = {
            app._quick_copy_skill_key(project_skill),
            app._quick_copy_skill_key(manual_skill),
        }
        app.quick_copy_set_var = mock.Mock()
        app.quick_copy_set_var.get.return_value = "Daily"
        app.quick_copy_status_label = mock.Mock()
        app.save_quick_copy_preferences = lambda: None
        app._refresh_quick_copy_set_menu = lambda: None
        app._refresh_quick_copy_set_details = lambda: None

        dialog = mock.Mock()
        dialog.get_input.return_value = "Core"
        with mock.patch("skill_manager.app.ctk.CTkInputDialog", return_value=dialog):
            app.edit_quick_copy_set()

        self.assertNotIn("Daily", app.quick_copy_config["skill_sets"])
        self.assertEqual(
            app.quick_copy_config["skill_sets"]["Core"]["skill_keys"],
            [app._quick_copy_skill_key(project_skill)],
        )
        self.assertEqual(app.quick_copy_config["skill_sets"]["Core"]["manual_references"], ["@caveman"])
        app.quick_copy_set_var.set.assert_called_with("Core")


if __name__ == "__main__":
    unittest.main()

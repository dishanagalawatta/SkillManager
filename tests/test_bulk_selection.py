import unittest

import _bootstrap  # noqa: F401
from skill_manager.app import SkillManagerApp


class Var:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value


class TreeDisclosureStub:
    def __init__(self):
        self.children = {
            "": ["project-1", "project-2"],
            "project-1": ["category-1", "category-2"],
            "project-2": ["category-3"],
            "category-1": ["skill-1"],
            "category-2": [],
            "category-3": ["skill-2"],
        }
        self.open_state = {}

    def get_children(self, item=""):
        return self.children.get(item, [])

    def item(self, item_id, option=None, **kwargs):
        if option == "open":
            return self.open_state.get(item_id, False)
        if "open" in kwargs:
            self.open_state[item_id] = kwargs["open"]


class TreeInsertStub:
    def __init__(self):
        self.rows = []
        self.children = {"": []}
        self.deleted = []
        self.counter = 0

    def get_children(self, item=""):
        return list(self.children.get(item, []))

    def delete(self, item):
        self.deleted.append(item)

    def insert(self, parent, index, text="", values=(), tags=(), open=False):
        self.counter += 1
        item_id = f"item-{self.counter}"
        self.rows.append({
            "id": item_id,
            "parent": parent,
            "text": text,
            "values": values,
            "tags": tags,
            "open": open,
        })
        self.children.setdefault(parent, []).append(item_id)
        self.children.setdefault(item_id, [])
        return item_id


class BulkSelectionTests(unittest.TestCase):
    def build_app_shell(self):
        app = object.__new__(SkillManagerApp)
        app.quick_copy_selected_project_key = "project-a"
        app.quick_copy_selected_skill_keys = set()
        app.quick_copy_selected_skill_keys_by_project = {}
        app.quick_copy_essential_skill_keys = set()
        app.quick_copy_category_var = Var("Architecture")
        app.filtered_quick_copy_manual_skills = []

        app.library_selected_skill_keys = set()
        app.library_category_var = Var("Workflow")
        return app

    def test_quick_copy_bulk_selection_can_select_and_deselect_category(self):
        app = self.build_app_shell()
        alpha = {"name": "alpha", "local_path": "A", "project_key": "project-a", "category": "Architecture"}
        beta = {"name": "beta", "local_path": "B", "project_key": "project-a", "category": "Workflow"}
        app.filtered_quick_copy_projects = [{"project_key": "project-a", "skills": [alpha, beta]}]

        app.select_current_quick_copy_category()

        self.assertEqual(app.quick_copy_selected_skill_keys, {app._quick_copy_skill_key(alpha)})

        app.select_all_visible_project_skills()
        self.assertEqual(
            app.quick_copy_selected_skill_keys,
            {app._quick_copy_skill_key(alpha), app._quick_copy_skill_key(beta)},
        )

        app.deselect_current_quick_copy_category()
        self.assertEqual(app.quick_copy_selected_skill_keys, {app._quick_copy_skill_key(beta)})

        app.clear_quick_copy_selection()
        self.assertEqual(app.quick_copy_selected_skill_keys, set())

    def test_quick_copy_category_row_toggle_selects_then_deselects_category(self):
        app = self.build_app_shell()
        alpha = {"name": "alpha", "local_path": "A", "project_key": "project-a", "category": "Architecture"}
        beta = {"name": "beta", "local_path": "B", "project_key": "project-a", "category": "Architecture"}
        other = {"name": "other", "local_path": "C", "project_key": "project-a", "category": "Workflow"}
        app.filtered_quick_copy_projects = [{"project_key": "project-a", "skills": [alpha, beta, other]}]

        app._toggle_quick_copy_category_selection("Architecture")

        self.assertEqual(
            app.quick_copy_selected_skill_keys,
            {app._quick_copy_skill_key(alpha), app._quick_copy_skill_key(beta)},
        )

        app._toggle_quick_copy_category_selection("Architecture")
        self.assertEqual(app.quick_copy_selected_skill_keys, set())

    def test_library_bulk_selection_can_select_and_deselect_category(self):
        app = self.build_app_shell()
        alpha = {"name": "alpha", "local_path": "A", "category": "Workflow"}
        beta = {"name": "beta", "local_path": "B", "category": "Architecture"}
        app.filtered_library_skills = [alpha, beta]

        app.select_current_library_category()

        self.assertEqual(app.library_selected_skill_keys, {app._skill_archive_key(alpha)})

        app.select_all_visible_library_skills()
        self.assertEqual(
            app.library_selected_skill_keys,
            {app._skill_archive_key(alpha), app._skill_archive_key(beta)},
        )

        app.deselect_current_library_category()
        self.assertEqual(app.library_selected_skill_keys, {app._skill_archive_key(beta)})

        app.deselect_all_library_skills()
        self.assertEqual(app.library_selected_skill_keys, set())

    def test_library_category_row_toggle_selects_then_deselects_category(self):
        app = self.build_app_shell()
        alpha = {"name": "alpha", "local_path": "A", "category": "Workflow"}
        beta = {"name": "beta", "local_path": "B", "category": "Workflow"}
        other = {"name": "other", "local_path": "C", "category": "Architecture"}
        app.filtered_library_skills = [alpha, beta, other]

        app._toggle_library_category_selection("Workflow")

        self.assertEqual(
            app.library_selected_skill_keys,
            {app._skill_archive_key(alpha), app._skill_archive_key(beta)},
        )

        app._toggle_library_category_selection("Workflow")
        self.assertEqual(app.library_selected_skill_keys, set())

    def test_library_show_archived_renders_muted_bottom_section(self):
        app = self.build_app_shell()
        active = {"name": "active", "local_path": "A", "category": "Workflow"}
        archived = {"name": "archived", "local_path": "B", "category": "Architecture"}
        app.library_skills = [archived, active]
        app.library_archive = {"archived_skills": {app._skill_archive_key(archived)}, "archived_categories": set()}
        app.library_show_archived_var = Var(True)
        app.library_search_var = Var("")
        app.library_category_var = Var("All Categories")
        app.library_category_state_loaded = False
        app.library_expanded_categories = set()
        app.library_tree = TreeInsertStub()
        app.library_tree_items = {}
        app.library_tree_categories = {}
        app.library_status_label = type("Label", (), {"configure": lambda self, **kwargs: None})()
        app._hide_description_peek = lambda: None
        app._hide_skill_detail_in_inspector = lambda *args, **kwargs: None
        app._prune_library_selected_keys = lambda: None
        app._sync_library_disclosure_button = lambda: None
        app._update_library_selected_count = lambda: None

        app._apply_skill_library_filters()

        root_rows = [row for row in app.library_tree.rows if row["parent"] == ""]
        self.assertEqual([row["text"] for row in root_rows], ["Workflow (1)", "Archived (1)"])
        self.assertIn("archived", root_rows[-1]["tags"])
        archived_children = [row for row in app.library_tree.rows if row["parent"] == root_rows[-1]["id"]]
        self.assertEqual(archived_children[0]["text"], "archived [Archived]")
        self.assertIn("archived", archived_children[0]["tags"])

    def test_quick_copy_expand_and_collapse_all_disclosure_rows(self):
        app = self.build_app_shell()
        app.quick_copy_tree = TreeDisclosureStub()
        app._sync_quick_copy_disclosure_button = lambda: None

        app.expand_all_quick_copy_categories()

        self.assertEqual(
            app.quick_copy_tree.open_state,
            {"project-1": True, "project-2": True, "category-1": True, "category-3": True},
        )

        app.collapse_all_quick_copy_categories()

        self.assertEqual(
            app.quick_copy_tree.open_state,
            {"project-1": False, "project-2": False, "category-1": False, "category-3": False},
        )

    def test_library_expand_and_collapse_all_disclosure_rows(self):
        app = self.build_app_shell()
        app.library_tree = TreeDisclosureStub()
        app._sync_library_disclosure_button = lambda: None
        app._capture_library_category_state = lambda: None
        app.save_library_clipboard_preferences = lambda: None

        app.expand_all_library_categories()

        self.assertEqual(
            app.library_tree.open_state,
            {"project-1": True, "project-2": True, "category-1": True, "category-3": True},
        )

        app.collapse_all_library_categories()

        self.assertEqual(
            app.library_tree.open_state,
            {"project-1": False, "project-2": False, "category-1": False, "category-3": False},
        )

    def test_quick_copy_single_disclosure_button_toggles_current_tree_state(self):
        app = self.build_app_shell()
        app.quick_copy_tree = TreeDisclosureStub()
        app._sync_quick_copy_disclosure_button = lambda: None

        app.toggle_all_quick_copy_categories()

        self.assertTrue(all(app.quick_copy_tree.open_state.values()))

        app.toggle_all_quick_copy_categories()

        self.assertTrue(app.quick_copy_tree.open_state)
        self.assertFalse(any(app.quick_copy_tree.open_state.values()))

    def test_directory_selection_helpers_remove_and_restore_multiple_rows(self):
        app = self.build_app_shell()
        paths = ["target-a", "target-b", "target-c", "target-d"]

        removed = app._remove_directory_rows(paths, [1, 3])

        self.assertEqual(paths, ["target-a", "target-c"])
        self.assertEqual(removed, [(1, "target-b"), (3, "target-d")])
        self.assertEqual(app._directory_selection_label(removed), "2 directories")

        app._restore_directory_rows(paths, removed)

        self.assertEqual(paths, ["target-a", "target-b", "target-c", "target-d"])

    def test_directory_selection_helpers_move_selected_block(self):
        app = self.build_app_shell()
        paths = ["source-a", "source-b", "source-c", "source-d"]

        next_indices = app._move_selected_rows(paths, [1, 2], -1)

        self.assertEqual(paths, ["source-b", "source-c", "source-a", "source-d"])
        self.assertEqual(next_indices, [0, 1])

        next_indices = app._move_selected_rows(paths, [0, 1], 1)

        self.assertEqual(paths, ["source-a", "source-b", "source-c", "source-d"])
        self.assertEqual(next_indices, [1, 2])


if __name__ == "__main__":
    unittest.main()

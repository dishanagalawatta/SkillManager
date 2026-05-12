import importlib
import json
import os
import threading
import tkinter as tk
import unittest
from pathlib import Path
from tkinter import ttk
from unittest import mock

import _bootstrap  # noqa: F401
from _bootstrap import temporary_directory


class SkillManagerAppStartupTests(unittest.TestCase):
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

    def _destroy_app(self, app):
        try:
            app.destroy()
        except tk.TclError:
            pass

    def test_app_builds_library_ui_and_saves_with_native_window_handle(self):
        with temporary_directory() as tmp:
            data_dir = Path(tmp) / "data"
            data_dir.mkdir()
            (data_dir / "config.json").write_text(
                json.dumps({
                    "targets": ["target-a"],
                    "sources": ["source-a"],
                    "skills": [{
                        "name": "Antigravity Awesome Skills",
                        "current_version": "10.7.0",
                        "latest_version": "10.8.0",
                        "last_updated": "2026-04-29 16:53:26",
                    }],
                }),
                encoding="utf-8",
            )
            (data_dir / "skill_library_clipboard.json").write_text(
                json.dumps({"client_format": "Codex", "skill_sets": {}, "expanded_categories": []}),
                encoding="utf-8",
            )
            app_module = self._reload_app(data_dir)

            handles = []

            def fake_get_window_placement(hwnd):
                handles.append(hwnd)
                self.assertIsInstance(hwnd, int)
                return [0, 1, [-1, -1], [-1, -1], [10, 10, 400, 300]]

            with (
                mock.patch.object(app_module.SkillManagerApp, "check_all_skill_updates", lambda self: None),
                mock.patch.object(app_module.SkillManagerApp, "load_skill_library", lambda self: None),
                mock.patch.object(app_module.SkillManagerApp, "load_quick_copy", lambda self: None),
                mock.patch.object(app_module, "get_window_placement", fake_get_window_placement),
            ):
                try:
                    app = app_module.SkillManagerApp()
                except tk.TclError as exc:
                    self.skipTest(f"Tk is not available: {exc}")

                try:
                    self.assertIn("Quick Copy", app.tabview._name_list)
                    self.assertIn("Library", app.tabview._name_list)
                    self.assertNotIn("Projects", app.tabview._name_list)
                    self.assertIn("Updates", app.tabview._name_list)
                    root_color = app.cget("fg_color")
                    if isinstance(root_color, (list, tuple)):
                        root_color = root_color[0]
                    self.assertEqual(root_color, app_module.CTK_COLORS["window_bg"][0])
                    self.assertEqual(app.tabview.cget("fg_color"), app_module.GLASS_BG_STRONG)
                    self.assertEqual(app.tabview.cget("border_color"), app_module.GLASS_BORDER)
                    self.assertEqual(app.tabview._segmented_button.cget("unselected_color"), app_module.GLASS_CONTROL)
                    self.assertEqual(app.status_label.cget("text_color"), app_module.TEXT_MUTED)
                    self.assertIsNone(app._toast_frame)
                    self.assertIsNone(app._toast_after_id)
                    self.assertEqual(app.grid_columnconfigure(0)["weight"], 1)
                    self.assertEqual(app.grid_rowconfigure(0)["weight"], 1)
                    self.assertFalse(hasattr(app, "app_logo_label"))
                    for attr in (
                        "library_header_frame",
                        "library_top_bar",
                        "library_selection_bar",
                        "library_project_bar",
                        "library_skills_frame",
                        "library_skills_header",
                        "library_skills_title_label",
                        "library_disclosure_btn",
                        "library_select_visible_check",
                        "library_refresh_btn",
                        "library_search_entry",
                        "library_category_menu",
                        "library_copy_to_projects_btn",
                        "library_tree",
                        "library_inspector_frame",
                        "library_inspector_title",
                        "library_inspector_meta",
                        "library_inspector_content_label",
                        "library_inspector_description",
                        "library_inspector_back_btn",
                        "library_inspector_category_menu",
                        "library_inspector_apply_category_btn",
                        "library_inspector_archive_btn",
                        "quick_copy_header_frame",
                        "quick_copy_top_bar",
                        "quick_copy_action_bar",
                        "quick_copy_skills_frame",
                        "quick_copy_skills_header",
                        "quick_copy_skills_title_label",
                        "quick_copy_disclosure_btn",
                        "quick_copy_select_visible_check",
                        "quick_copy_refresh_btn",
                        "quick_copy_search_entry",
                        "quick_copy_category_menu",
                        "quick_copy_copy_btn",
                        "quick_copy_delete_btn",
                        "quick_copy_bundle_cluster",
                        "quick_copy_set_menu",
                        "quick_copy_save_set_btn",
                        "quick_copy_bundle_dropdown_frame",
                        "quick_copy_set_detail_label",
                        "quick_copy_essentials_bar",
                        "quick_copy_essentials_label",
                        "quick_copy_manual_bar",
                        "quick_copy_manual_summary_label",
                        "quick_copy_manual_composer_frame",
                        "quick_copy_manual_entry",
                        "quick_copy_manual_add_btn",
                        "quick_copy_manual_commit_btn",
                        "quick_copy_manual_cancel_btn",
                        "quick_copy_manual_label",
                        "quick_copy_tree",
                        "quick_copy_inspector_frame",
                        "quick_copy_inspector_title",
                        "quick_copy_inspector_meta",
                        "quick_copy_inspector_content_label",
                        "quick_copy_inspector_description",
                        "quick_copy_inspector_back_btn",
                        "quick_copy_inspector_category_menu",
                        "quick_copy_inspector_apply_category_btn",
                        "quick_copy_inspector_essentials_btn",
                        "updates_header_frame",
                        "project_update_frame",
                        "skill_update_frame",
                    ):
                        self.assertTrue(hasattr(app, attr), attr)
                    self.assertEqual(app.library_header_frame.grid_columnconfigure(0)["weight"], 1)
                    self.assertEqual(app.library_top_bar.grid_columnconfigure(0)["weight"], 1)
                    self.assertEqual(app.library_project_bar.grid_columnconfigure(0)["weight"], 1)
                    self.assertTrue(hasattr(app, "source_listbox"))
                    self.assertEqual(app.source_listbox.grid_info()["column"], 0)
                    self.assertEqual(app.source_listbox.cget("selectmode"), "extended")
                    self.assertEqual(str(app.source_listbox.cget("exportselection")), "0")
                    self.assertEqual(app.skill_update_frame.grid_info()["column"], 1)
                    self.assertEqual(app.skill_scrollable_frame.grid_info()["column"], 0)
                    self.assertEqual(app.target_listbox.grid_info()["column"], 0)
                    self.assertEqual(app.target_listbox.cget("selectmode"), "extended")
                    self.assertEqual(str(app.target_listbox.cget("exportselection")), "0")
                    self.assertEqual(app.quick_copy_header_frame.grid_columnconfigure(0)["weight"], 1)
                    self.assertEqual(app.quick_copy_top_bar.grid_columnconfigure(0)["weight"], 1)
                    self.assertEqual(app.quick_copy_action_bar.grid_columnconfigure(1)["weight"], 1)
                    self.assertEqual(app.quick_copy_essentials_bar.grid_columnconfigure(0)["weight"], 1)
                    self.assertEqual(app.quick_copy_manual_bar.grid_columnconfigure(0)["weight"], 1)
                    self.assertEqual(app.quick_copy_refresh_btn.master, app.quick_copy_skills_header)
                    self.assertEqual(app.quick_copy_refresh_btn.cget("text"), "\u21bb")
                    self.assertEqual(app.quick_copy_refresh_btn.cget("width"), 36)
                    self.assertEqual(app.quick_copy_refresh_btn.cget("corner_radius"), 17)
                    self.assertEqual(app.quick_copy_search_entry.master, app.quick_copy_skills_header)
                    self.assertEqual(app.quick_copy_search_entry.grid_info()["column"], 1)
                    self.assertEqual(app.quick_copy_search_entry.grid_info()["sticky"], "w")
                    self.assertEqual(app.quick_copy_search_entry.cget("width"), 240)
                    self.assertEqual(app.quick_copy_search_entry.cget("corner_radius"), 18)
                    self.assertEqual(app.quick_copy_search_entry.cget("placeholder_text"), "Ask skills...")
                    self.assertEqual(app.quick_copy_category_menu.master, app.quick_copy_skills_header)
                    self.assertEqual(app.quick_copy_category_menu.grid_info()["column"], 6)
                    self.assertEqual(app.quick_copy_category_menu.cget("corner_radius"), 17)
                    self.assertEqual(app.quick_copy_set_menu.master, app.quick_copy_skills_header)
                    self.assertEqual(app.quick_copy_set_menu.grid_info()["column"], 7)
                    self.assertEqual(app.quick_copy_set_menu.grid_info()["row"], 0)
                    self.assertEqual(app.quick_copy_set_menu.cget("corner_radius"), 17)
                    self.assertTrue(hasattr(app, "quick_copy_bundle_dropdown_frame"))
                    self.assertEqual(app.quick_copy_bundle_dropdown_frame.master, app)
                    self.assertTrue(hasattr(app, "quick_copy_bundle_name_entry"))
                    self.assertFalse(hasattr(app, "quick_copy_save_set_btn"))
                    self.assertEqual(app.quick_copy_disclosure_btn.master, app.quick_copy_skills_header)
                    self.assertEqual(app.quick_copy_disclosure_btn.cget("text"), "\u25b8")
                    self.assertEqual(app.quick_copy_disclosure_btn.cget("width"), 36)
                    self.assertEqual(app.quick_copy_disclosure_btn.cget("corner_radius"), 17)
                    self.assertEqual(app.quick_copy_disclosure_btn.grid_info()["column"], 3)
                    self.assertEqual(app.quick_copy_select_visible_check.grid_info()["column"], 4)
                    self.assertFalse(hasattr(app, "quick_copy_delete_set_btn"))
                    self.assertFalse(hasattr(app, "quick_copy_select_set_btn"))
                    self.assertFalse(hasattr(app, "quick_copy_copy_set_btn"))
                    self.assertFalse(hasattr(app, "quick_copy_expand_btn"))
                    self.assertFalse(hasattr(app, "quick_copy_collapse_btn"))
                    app.quick_copy_config["skill_sets"] = {
                        "Daily": {"skill_keys": [], "manual_references": []},
                        "Core": {"skill_keys": [], "manual_references": []},
                    }
                    app._refresh_quick_copy_set_menu()
                    app._toggle_quick_copy_bundle_dropdown()
                    self.assertNotEqual(app.quick_copy_bundle_dropdown_frame.grid_info(), {})
                    bundle_rows = app.quick_copy_bundle_dropdown_frame.winfo_children()
                    self.assertEqual(len(bundle_rows), 3)
                    self.assertEqual(
                        [child.cget("text") for child in bundle_rows[1].winfo_children()],
                        ["Core", "\u270e", "\u232b"],
                    )
                    app._toggle_quick_copy_bundle_dropdown()
                    self.assertEqual(app.quick_copy_bundle_dropdown_frame.grid_info(), {})
                    self.assertEqual(app.library_refresh_btn.master, app.library_skills_header)
                    self.assertEqual(app.library_refresh_btn.cget("text"), "\u21bb")
                    self.assertEqual(app.library_refresh_btn.cget("width"), 36)
                    self.assertEqual(app.library_refresh_btn.cget("corner_radius"), 17)
                    self.assertEqual(app.library_search_entry.master, app.library_skills_header)
                    self.assertEqual(app.library_search_entry.grid_info()["column"], 2)
                    self.assertEqual(app.library_search_entry.grid_info()["sticky"], "w")
                    self.assertEqual(app.library_search_entry.cget("width"), 240)
                    self.assertEqual(app.library_search_entry.cget("corner_radius"), 18)
                    self.assertEqual(app.library_search_entry.cget("placeholder_text"), "Ask skills...")
                    self.assertEqual(app.library_category_menu.master, app.library_skills_header)
                    self.assertEqual(app.library_category_menu.grid_info()["column"], 3)
                    self.assertEqual(app.library_category_menu.cget("corner_radius"), 17)
                    self.assertEqual(app.library_disclosure_btn.master, app.library_skills_header)
                    self.assertEqual(app.library_disclosure_btn.cget("text"), "\u25b8")
                    self.assertEqual(app.library_disclosure_btn.cget("width"), 36)
                    self.assertEqual(app.library_disclosure_btn.cget("corner_radius"), 17)
                    self.assertEqual(app.library_disclosure_btn.grid_info()["column"], 5)
                    self.assertEqual(app.library_select_visible_check.grid_info()["column"], 6)
                    self.assertFalse(hasattr(app, "library_expand_btn"))
                    self.assertFalse(hasattr(app, "library_collapse_btn"))
                    self.assertEqual(app.quick_copy_delete_btn.cget("text"), "Remove Selected")
                    self.assertEqual(app.quick_copy_manual_add_btn.cget("text"), "Add Manuals")
                    self.assertFalse(hasattr(app, "quick_copy_show_essentials_btn"))
                    self.assertFalse(hasattr(app, "quick_copy_add_essentials_btn"))
                    self.assertFalse(hasattr(app, "quick_copy_remove_essentials_btn"))
                    self.assertFalse(hasattr(app, "quick_copy_copy_essentials_btn"))
                    self.assertFalse(hasattr(app, "quick_copy_manual_paste_btn"))
                    self.assertFalse(hasattr(app, "quick_copy_manual_browse_btn"))
                    self.assertFalse(hasattr(app, "quick_copy_manual_remove_btn"))
                    self.assertEqual(app.quick_copy_manual_entry.grid_info()["row"], 0)
                    self.assertEqual(app.quick_copy_manual_composer_frame.grid_info(), {})
                    app.show_quick_copy_manual_composer()
                    self.assertNotEqual(app.quick_copy_manual_composer_frame.grid_info(), {})
                    app.hide_quick_copy_manual_composer()
                    self.assertEqual(app.quick_copy_manual_composer_frame.grid_info(), {})
                    self.assertEqual(app.library_tree.column("#0", option="width"), 300)
                    self.assertEqual(app.library_tree.heading("description", option="text"), "Summary")
                    self.assertEqual(app.library_tree.column("description", option="width"), 420)
                    self.assertEqual(app.library_tree.column("description", option="minwidth"), 220)
                    self.assertEqual(app.quick_copy_tree.column("#0", option="width"), 360)
                    self.assertEqual(app.quick_copy_tree.heading("description", option="text"), "Summary")
                    self.assertEqual(app.quick_copy_tree.column("description", option="width"), 520)
                    self.assertEqual(app.quick_copy_tree.column("description", option="minwidth"), 220)
                    tree_style = ttk.Style()
                    self.assertEqual(tree_style.lookup("SkillLibrary.Treeview", "background"), app_module.BG_SURFACE)
                    self.assertEqual(tree_style.lookup("SkillLibrary.Treeview", "foreground"), app_module.TEXT_MAIN)
                    self.assertEqual(tree_style.lookup("SkillLibrary.Treeview", "fieldbackground"), app_module.BG_SURFACE)
                    self.assertEqual(tree_style.lookup("SkillLibrary.Treeview.Heading", "background"), app_module.BG_SURFACE_SOFT)
                    self.assertEqual(tree_style.lookup("SkillLibrary.Treeview.Heading", "foreground"), app_module.TEXT_MAIN)
                    self.assertEqual(app.library_tree.tag_configure("skill")["foreground"], app_module.TREE_SKILL_TEXT)
                    self.assertEqual(app.library_tree.tag_configure("category")["foreground"], app_module.TREE_CATEGORY_TEXT)
                    self.assertEqual(app.library_tree.tag_configure("archived")["foreground"], app_module.TREE_ARCHIVED_TEXT)
                    self.assertEqual(app.quick_copy_tree.tag_configure("project")["foreground"], app_module.TREE_PROJECT_TEXT)
                    self.assertEqual(app.quick_copy_tree.tag_configure("essential")["foreground"], app_module.TREE_ESSENTIAL_TEXT)
                    self.assertEqual(app.quick_copy_tree.tag_configure("selected_skill")["background"], app_module.ROW_SELECTED_BG)
                    self.assertEqual(app.quick_copy_inspector_frame.grid_info(), {})
                    self.assertEqual(app.library_inspector_frame.grid_info(), {})
                    self.assertEqual(app.quick_copy_inspector_parent.grid_columnconfigure(2)["weight"], 0)
                    self.assertEqual(app.library_inspector_parent.grid_columnconfigure(2)["weight"], 0)
                    self.assertEqual(app.library_inspector_meta.cget("text"), "No skill open.")
                    self.assertEqual(app.library_inspector_back_btn.cget("text"), "Back")
                    self.assertFalse(hasattr(app, "library_inspector_add_btn"))
                    self.assertEqual(app.library_inspector_apply_category_btn.cget("text"), "Apply")
                    self.assertEqual(app.library_inspector_archive_btn.cget("text"), "Archive")
                    self.assertEqual(app.library_inspector_archive_btn.cget("state"), "disabled")
                    self.assertEqual(app.library_inspector_description.get("1.0", "end").strip(), "Double-click a skill to open it here.")
                    app._show_skill_detail_in_inspector(
                        {"name": "Demo Skill", "category": "Testing", "raw_content": "Full skill body."},
                        "library",
                    )
                    self.assertEqual(app.library_inspector_frame.grid_info()["column"], 2)
                    self.assertEqual(app.library_inspector_parent.grid_columnconfigure(2)["weight"], 1)
                    self.assertEqual(app.library_inspector_title.cget("text"), "Demo Skill")
                    self.assertEqual(app.library_inspector_category_var.get(), "Testing")
                    self.assertEqual(app.library_inspector_archive_btn.cget("text"), "Archive")
                    self.assertEqual(app.library_inspector_archive_btn.cget("state"), "normal")
                    self.assertIn("Full skill body.", app.library_inspector_description.get("1.0", "end"))
                    app._hide_skill_detail_in_inspector("library")
                    self.assertEqual(app.library_inspector_frame.grid_info(), {})
                    self.assertEqual(app.library_inspector_parent.grid_columnconfigure(2)["weight"], 0)
                    app._show_skill_detail_in_inspector(
                        {
                            "name": "Quick Skill",
                            "category": "Testing",
                            "raw_content": "Quick body.",
                            "project_key": "project-a",
                            "folder_name": "quick-skill",
                        },
                        "quick_copy",
                    )
                    self.assertEqual(app.quick_copy_inspector_essentials_btn.cget("text"), "Add to Essentials")
                    app.quick_copy_essential_skill_keys.add("project-a:quick-skill")
                    app._update_quick_copy_inspector_essentials_button()
                    self.assertEqual(app.quick_copy_inspector_essentials_btn.cget("text"), "Remove from Essentials")
                    app._hide_skill_detail_in_inspector("quick_copy")
                    self.assertIsNone(app._description_peek_after_id)
                    self.assertIsNone(app._description_peek_window)
                    self.assertEqual(app._description_peek_delay_ms, 450)
                    self.assertTrue(app.library_tree.bind("<Motion>"))
                    self.assertTrue(app.quick_copy_tree.bind("<Motion>"))
                    summary = app_module.SkillManagerApp._row_description_summary(" ".join(["long"] * 40))
                    self.assertLessEqual(len(summary), 96)
                    self.assertTrue(summary.endswith("..."))
                    self.assertFalse(hasattr(app, "library_copy_btn"))
                    self.assertFalse(hasattr(app, "library_skill_set_menu"))

                    app.save_config()
                    saved = json.loads((data_dir / "config.json").read_text(encoding="utf-8"))
                    self.assertEqual(saved["targets"], ["target-a"])
                    self.assertEqual(saved["sources"], ["source-a"])
                    self.assertTrue(handles)
                finally:
                    self._destroy_app(app)

    def test_open_selected_library_skill_uses_inspector_not_tabs(self):
        with temporary_directory() as tmp:
            app_module = self._reload_app(Path(tmp) / "data")

        class TreeStub:
            def selection(self):
                return ("row-1",)

        app = object.__new__(app_module.SkillManagerApp)
        skill = {"name": "Example", "raw_content": "body"}
        calls = []
        app.library_tree = TreeStub()
        app.library_tree_items = {"row-1": skill}
        app._show_skill_detail_in_inspector = lambda selected, prefix: calls.append((selected, prefix))

        app_module.SkillManagerApp._open_selected_library_skill(app)

        self.assertEqual(calls, [(skill, "library")])

    def test_toast_message_renders_without_modal_dialog(self):
        with temporary_directory() as tmp:
            data_dir = Path(tmp) / "data"
            data_dir.mkdir()
            (data_dir / "config.json").write_text(
                json.dumps({"targets": [], "sources": [], "skills": []}),
                encoding="utf-8",
            )
            app_module = self._reload_app(data_dir)

            with (
                mock.patch.object(app_module.SkillManagerApp, "check_all_skill_updates", lambda self: None),
                mock.patch.object(app_module.SkillManagerApp, "load_skill_library", lambda self: None),
                mock.patch.object(app_module.SkillManagerApp, "load_quick_copy", lambda self: None),
            ):
                try:
                    app = app_module.SkillManagerApp()
                except tk.TclError as exc:
                    self.skipTest(f"Tk is not available: {exc}")

                try:
                    app.show_toast("Saved", "Settings updated.", "success", duration=1000)
                    app.update_idletasks()

                    self.assertIsNotNone(app._toast_frame)
                    self.assertIsNotNone(app._toast_after_id)
                    self.assertTrue(app._toast_frame.winfo_exists())
                    self.assertIs(getattr(app, "_active_toast_frame"), app._toast_frame)
                    self.assertEqual(app._toast_frame.winfo_manager(), "place")
                finally:
                    self._destroy_app(app)

    def test_skill_updater_rows_include_visible_update_action(self):
        with temporary_directory() as tmp:
            data_dir = Path(tmp) / "data"
            data_dir.mkdir()
            (data_dir / "config.json").write_text(
                json.dumps({
                    "targets": [],
                    "sources": [],
                    "skills": [{
                        "name": "Example Skill",
                        "current_version": "1.0.0",
                        "latest_version": "1.1.0",
                        "last_updated": "Never",
                    }],
                }),
                encoding="utf-8",
            )
            app_module = self._reload_app(data_dir)

            with (
                mock.patch.object(app_module.SkillManagerApp, "check_all_skill_updates", lambda self: None),
                mock.patch.object(app_module.SkillManagerApp, "load_skill_library", lambda self: None),
                mock.patch.object(app_module.SkillManagerApp, "load_quick_copy", lambda self: None),
            ):
                try:
                    app = app_module.SkillManagerApp()
                except tk.TclError as exc:
                    self.skipTest(f"Tk is not available: {exc}")

                try:
                    self.assertEqual(len(app.skill_action_buttons), 1)
                    buttons = app.skill_action_buttons[0]
                    self.assertEqual(buttons["update"].cget("text"), "Update")
                    self.assertEqual(buttons["update"].winfo_manager(), "pack")
                    self.assertEqual(app.skill_scrollable_frame.grid_columnconfigure(0)["weight"], 1)
                finally:
                    self._destroy_app(app)

    def test_projects_list_remove_and_reorder_use_selected_rows(self):
        with temporary_directory() as tmp:
            data_dir = Path(tmp) / "data"
            data_dir.mkdir()
            (data_dir / "config.json").write_text(
                json.dumps({
                    "targets": ["target-a", "target-b"],
                    "sources": ["source-a", "source-b", "source-c"],
                    "skills": [],
                }),
                encoding="utf-8",
            )
            app_module = self._reload_app(data_dir)

            with (
                mock.patch.object(app_module.SkillManagerApp, "check_all_skill_updates", lambda self: None),
                mock.patch.object(app_module.SkillManagerApp, "load_skill_library", lambda self: None),
                mock.patch.object(app_module.SkillManagerApp, "load_quick_copy", lambda self: None),
            ):
                try:
                    app = app_module.SkillManagerApp()
                except tk.TclError as exc:
                    self.skipTest(f"Tk is not available: {exc}")

                try:
                    app.source_listbox.selection_set(1)
                    app.move_source_up()
                    self.assertEqual(app.sources, ["source-b", "source-a", "source-c"])
                    self.assertEqual(app.source_listbox.curselection(), (0,))

                    app.source_listbox.selection_clear(0, "end")
                    app.source_listbox.selection_set(1, 2)
                    app.move_source_up()
                    self.assertEqual(app.sources, ["source-a", "source-c", "source-b"])
                    self.assertEqual(app.source_listbox.curselection(), (0, 1))

                    app.source_listbox.selection_clear(0, "end")
                    app.source_listbox.selection_set(0, 1)
                    app.remove_source()
                    self.assertEqual(app.sources, ["source-b"])

                    app.target_listbox.selection_set(0, 1)
                    app.remove_target()
                    self.assertEqual(app.targets, [])
                finally:
                    self._destroy_app(app)

    def test_saved_set_delete_is_undoable_without_native_confirm(self):
        with temporary_directory() as tmp:
            data_dir = Path(tmp) / "data"
            data_dir.mkdir()
            (data_dir / "config.json").write_text(
                json.dumps({"targets": [], "sources": [], "skills": []}),
                encoding="utf-8",
            )
            app_module = self._reload_app(data_dir)

            with (
                mock.patch.object(app_module.SkillManagerApp, "check_all_skill_updates", lambda self: None),
                mock.patch.object(app_module.SkillManagerApp, "load_skill_library", lambda self: None),
                mock.patch.object(app_module.SkillManagerApp, "load_quick_copy", lambda self: None),
            ):
                try:
                    app = app_module.SkillManagerApp()
                except tk.TclError as exc:
                    self.skipTest(f"Tk is not available: {exc}")

                try:
                    app.quick_copy_config["skill_sets"] = {"Daily": {"skill_keys": ["skill-a"], "manual_references": []}}
                    app.quick_copy_set_var.set("Daily")
                    app._refresh_quick_copy_set_menu()

                    app.delete_quick_copy_set()
                    self.assertNotIn("Daily", app.quick_copy_config["skill_sets"])
                    self.assertIsNotNone(getattr(app, "_active_toast_frame"))
                    undo_buttons = []
                    for child in app._active_toast_frame.winfo_children():
                        if not hasattr(child, "cget"):
                            continue
                        try:
                            if child.cget("text") == "Undo":
                                undo_buttons.append(child)
                        except (tk.TclError, ValueError):
                            continue
                    self.assertEqual(len(undo_buttons), 1)

                    undo_buttons[0].invoke()
                    self.assertIn("Daily", app.quick_copy_config["skill_sets"])
                finally:
                    self._destroy_app(app)

    def test_save_config_from_worker_thread_does_not_touch_tk_window_state(self):
        with temporary_directory() as tmp:
            data_dir = Path(tmp) / "data"
            data_dir.mkdir()
            app_module = self._reload_app(data_dir)
            app = object.__new__(app_module.SkillManagerApp)
            app.targets = ["target-a"]
            app.sources = ["source-a"]
            app.skills = [{"name": "Example"}]
            app._config_lock = threading.Lock()
            app.config_manager = app_module.ConfigManager()

            def fail_if_tk_window_is_touched():
                raise AssertionError("Tk window state should not be read from a worker thread")

            app.state = fail_if_tk_window_is_touched
            app.geometry = fail_if_tk_window_is_touched
            errors = []

            def run_save():
                try:
                    app.save_config()
                except Exception as exc:
                    errors.append(exc)

            thread = threading.Thread(target=run_save)
            thread.start()
            thread.join()

            self.assertEqual(errors, [])
            saved = json.loads((data_dir / "config.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["targets"], ["target-a"])
            self.assertEqual(saved["sources"], ["source-a"])
            self.assertEqual(saved["skills"], [{"name": "Example"}])


if __name__ == "__main__":
    unittest.main()

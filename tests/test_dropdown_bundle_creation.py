import unittest
import tkinter as tk
import customtkinter as ctk
import os
import sys
from pathlib import Path

# Add src to path via _bootstrap pattern
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from skill_manager.app import SkillManagerApp

class TestDropdownBundleCreation(unittest.TestCase):
    def setUp(self):
        # Mocking to avoid filesystem issues
        os.environ["SKILL_MANAGER_DATA_DIR"] = "."
        self.app = SkillManagerApp()

    def tearDown(self):
        self.app.destroy()


    def test_dropdown_toggle_and_add_mode(self):
        """Verify clicking bundle button shows dropdown, and clicking Add Bundle shifts to entry."""
        # 1. Initially hidden
        self.assertFalse(self.app.quick_copy_bundle_dropdown_frame.winfo_viewable())
        
        # 2. Toggle on
        self.app._toggle_quick_copy_bundle_dropdown()
        self.app.update()
        self.assertTrue(self.app.quick_copy_bundle_dropdown_frame.place_info(), "Dropdown should be placed")

        
        # 3. Initially not in add mode
        self.assertFalse(self.app._quick_copy_is_adding_bundle)
        
        # 4. Find the "Add New Bundle..." button inside the dropdown and click it
        # Note: We need to find the child button. 
        # Since we use Full Re-render, we can just trigger the method directly or find the widget.
        self.app._on_add_bundle_click()
        self.app.update_idletasks()
        
        # 5. Verify Add Mode
        self.assertTrue(self.app._quick_copy_is_adding_bundle)
        self.assertIsNotNone(self.app.quick_copy_bundle_name_entry)
        self.assertTrue(self.app.quick_copy_bundle_name_entry.winfo_viewable())

if __name__ == "__main__":

    unittest.main()

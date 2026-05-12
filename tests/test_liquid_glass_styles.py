import unittest

import _bootstrap  # noqa: F401

from skill_manager.gui import styles


class LiquidGlassStyleTokenTests(unittest.TestCase):
    def test_design_tokens_expose_light_dark_values_and_tk_fallbacks(self):
        self.assertEqual(styles.tk_color("window_bg"), "#F5F5F7")
        self.assertEqual(styles.tk_color("window_bg", appearance="dark"), "#1E1E1E")
        self.assertEqual(styles.css_color("glass_bg"), "rgba(255,255,255,0.72)")
        self.assertEqual(styles.css_color("glass_bg", appearance="dark"), "rgba(44,44,46,0.72)")
        self.assertEqual(styles.ctk_color("accent"), ("#007AFF", "#0A84FF"))

    def test_reduced_transparency_collapses_glass_to_opaque_surfaces(self):
        self.assertEqual(
            styles.tk_color("glass_bg", reduced_transparency=True),
            styles.tk_color("content_raised"),
        )
        self.assertEqual(
            styles.ctk_color("glass_bg_strong", reduced_transparency=True),
            styles.ctk_color("content_bg"),
        )
        self.assertEqual(styles.TOAST_STYLE["fg_color"], styles.ctk_color("content_bg"))

    def test_shared_style_manager_uses_semantic_tokens(self):
        self.assertEqual(styles.StyleManager.get_button_style()["fg_color"], styles.ctk_color("accent"))
        self.assertEqual(styles.StyleManager.get_card_style()["fg_color"], styles.ctk_color("content_bg"))
        tree_tokens = styles.StyleManager.get_tree_style_tokens()
        self.assertEqual(tree_tokens["background"], styles.BG_SURFACE)
        self.assertEqual(tree_tokens["foreground"], styles.TEXT_MAIN)
        self.assertEqual(tree_tokens["selected_background"], styles.ROW_SELECTED_BG)


if __name__ == "__main__":
    unittest.main()

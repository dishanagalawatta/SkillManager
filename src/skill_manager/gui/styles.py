"""Shared Liquid Glass theme tokens for the Skill Manager UI.

Tk widgets need solid colors, while CustomTkinter can use light/dark tuples.
The semantic token table below keeps both forms in one place.
"""

from dataclasses import dataclass
from typing import Optional, Union
import customtkinter as ctk


@dataclass
class ColorToken:
    name: str
    light: str
    dark: str
    high_contrast_light: Optional[str] = None
    high_contrast_dark: Optional[str] = None
    opaque_light: Optional[str] = None
    opaque_dark: Optional[str] = None

    def for_tk(self, appearance: str = "light", *, high_contrast: bool = False, reduced_transparency: bool = False) -> str:
        if high_contrast:
            if appearance == "light":
                return self.high_contrast_light or self.light
            return self.high_contrast_dark or self.dark
        if reduced_transparency:
            if appearance == "light":
                return self.opaque_light or self.light
            return self.opaque_dark or self.dark
        return self.light if appearance == "light" else self.dark

    def for_ctk(self, *, high_contrast: bool = False, reduced_transparency: bool = False) -> tuple[str, str]:
        light = self.light
        dark = self.dark
        if high_contrast:
            light = self.high_contrast_light or light
            dark = self.high_contrast_dark or dark
        if reduced_transparency:
            light = self.opaque_light or light
            dark = self.opaque_dark or dark
        return (light, dark)


LIQUID_GLASS_TOKENS = {
    # Core Surfaces
    "window_bg": ColorToken("window_bg", "#F2F2F7", "#000001"), # #000001 is used for DWM bleed in dark mode
    "content_bg": ColorToken("content_bg", "#FFFFFF", "#1C1C1E"),
    "content_raised": ColorToken("content_raised", "#F9F9FB", "#2C2C2E"),
    
    # Glass Effects (Fallback to opaque if reduced_transparency=True)
    # Using more subtle/translucent colors to complement native materials
    "glass_bg": ColorToken("glass_bg", "#FAFAFA", "#1A1A1A", opaque_light="#FFFFFF", opaque_dark="#2C2C2E"),
    "glass_bg_strong": ColorToken("glass_bg_strong", "#F0F0F0", "#252525", opaque_light="#F2F2F7", opaque_dark="#3A3A3C"),
    "glass_border": ColorToken("glass_border", "#E0E0E0", "#404040"), # Higher contrast border
    "glass_control": ColorToken("glass_control", "#E5E5EA", "#333333"),
    "glass_control_hover": ColorToken("glass_control_hover", "#D1D1D6", "#444444"),
    
    # Labels
    "label": ColorToken("label", "#1D1D1F", "#FFFFFF", high_contrast_light="#000000", high_contrast_dark="#FFFFFF"),
    "secondary_label": ColorToken("secondary_label", "#6E6E73", "#A1A1A6"),
    "separator": ColorToken("separator", "#D8D8DC", "#38383A"),
    
    # Selection
    "accent": ColorToken("accent", "#007AFF", "#0A84FF"),
    "accent_hover": ColorToken("accent_hover", "#0056B3", "#409CFF"),
    "accent_selection": ColorToken("accent_selection", "#D6E8FF", "#264D77"),
    
    # Status
    "success": ColorToken("success", "#28CD41", "#32D74B"),
    "success_hover": ColorToken("success_hover", "#20A835", "#3BE554"),
    "warning": ColorToken("warning", "#FF9500", "#FF9F0A"),
    "warning_hover": ColorToken("warning_hover", "#CC7700", "#FFAD33"),
    "danger": ColorToken("danger", "#FF3B30", "#FF453A"),
    "danger_hover": ColorToken("danger_hover", "#D70015", "#FF6961"),
    
    # Special Tree Tags
    "tree_category": ColorToken("tree_category", "#004080", "#64B5F6"),
    "tree_project": ColorToken("tree_project", "#006400", "#81C784"),
    "tree_essential": ColorToken("tree_essential", "#8B4513", "#FFB74D"),
    "tree_archived": ColorToken("tree_archived", "#8E8E93", "#636366"),
    
    # Inspector Peek
    "peek_bg": ColorToken("peek_bg", "#1C1C1E", "#1C1C1E"), # Always dark
    "peek_label": ColorToken("peek_label", "#FFFFFF", "#FFFFFF"),
    "peek_secondary_label": ColorToken("peek_secondary_label", "#A1A1A6", "#A1A1A6"),
}


def _resolved_name(name: str, reduced_transparency: bool = False) -> str:
    return name


def tk_color(name: str, appearance: str = "light", *, high_contrast: bool = False, reduced_transparency: bool = False) -> str:
    token = LIQUID_GLASS_TOKENS[_resolved_name(name, reduced_transparency=reduced_transparency)]
    return token.for_tk(appearance, high_contrast=high_contrast, reduced_transparency=reduced_transparency)


def ctk_color(name: str, *, high_contrast: bool = False, reduced_transparency: bool = False) -> tuple[str, str]:
    token = LIQUID_GLASS_TOKENS[_resolved_name(name, reduced_transparency=reduced_transparency)]
    return token.for_ctk(high_contrast=high_contrast, reduced_transparency=reduced_transparency)


# --- Global CTK Tuples ---
SKILL_BLUE = ctk_color("accent")
SKILL_BLUE_DEEP = ctk_color("accent_hover")

BG_MAIN = ctk_color("window_bg")
BG_SURFACE = ctk_color("content_bg")
BG_SURFACE_SOFT = ctk_color("content_raised")
GLASS_BG = ctk_color("glass_bg")
GLASS_BG_STRONG = ctk_color("glass_bg_strong")
GLASS_BORDER = ctk_color("glass_border")
GLASS_CONTROL = ctk_color("glass_control")
GLASS_CONTROL_HOVER = ctk_color("glass_control_hover")
GLASS_SEARCH_BG = ctk_color("content_bg")
GLASS_SEARCH_BORDER = ctk_color("separator")
GLASS_SEARCH_TEXT = ctk_color("label")
GLASS_SEARCH_PLACEHOLDER = ctk_color("secondary_label")
TEXT_MAIN = ctk_color("label")
TEXT_MUTED = ctk_color("secondary_label")
BORDER_SOFT = ctk_color("separator")
ROW_SELECTED_BG = ctk_color("accent_selection")
TREE_CATEGORY_TEXT = ctk_color("tree_category")
TREE_PROJECT_TEXT = ctk_color("tree_project")
TREE_SKILL_TEXT = TEXT_MAIN
TREE_ESSENTIAL_TEXT = ctk_color("tree_essential")
TREE_ARCHIVED_TEXT = ctk_color("tree_archived")

# --- Global TK Strings ---
TK_BG_SURFACE = tk_color("content_bg")
TK_BG_SURFACE_SOFT = tk_color("content_raised")
TK_TEXT_MAIN = tk_color("label")
TK_TEXT_MUTED = tk_color("secondary_label")
TK_BORDER_SOFT = tk_color("separator")
TK_TREE_CATEGORY_TEXT = tk_color("tree_category")
TK_TREE_PROJECT_TEXT = tk_color("tree_project")
TK_TREE_SKILL_TEXT = TK_TEXT_MAIN
TK_TREE_ESSENTIAL_TEXT = tk_color("tree_essential")
TK_TREE_ARCHIVED_TEXT = tk_color("tree_archived")
TK_ROW_SELECTED_BG = tk_color("accent_selection")

# Popovers
POPOVER_BG = tk_color("glass_bg_strong", "dark")
POPOVER_TEXT = tk_color("peek_label")
POPOVER_MUTED_TEXT = tk_color("peek_secondary_label")

# --- Shared Collections ---
STATUS_COLORS = {
    "info": tk_color("accent", appearance="dark"),
    "success": tk_color("success", appearance="dark"),
    "warning": tk_color("warning", appearance="dark"),
    "error": tk_color("danger", appearance="dark"),
}

CTK_STATUS_COLORS = {
    "info": ctk_color("accent"),
    "info_hover": ctk_color("accent_hover"),
    "success": ctk_color("success"),
    "success_hover": ctk_color("success_hover"),
    "warning": ctk_color("warning"),
    "warning_hover": ctk_color("warning_hover"),
    "error": ctk_color("danger"),
    "error_hover": ctk_color("danger_hover"),
}

CTK_COLORS = {
    name: ctk_color(name) for name in LIQUID_GLASS_TOKENS
}

TOAST_STYLE = {
    "fg_color": ctk_color("glass_bg_strong", reduced_transparency=True),
    "border_color": ctk_color("glass_border"),
    "border_width": 1,
    "corner_radius": 16,
}


def apply_theme(appearance: str = "system"):
    ctk.set_appearance_mode(appearance)
    ctk.set_default_color_theme("blue")


class StyleManager:
    @staticmethod
    def get_button_style():
        return {
            "fg_color": ctk_color("accent"),
            "hover_color": ctk_color("accent_hover"),
            "text_color": ("#FFFFFF", "#FFFFFF"),
            "corner_radius": 8,
        }

    @staticmethod
    def get_card_style():
        return {
            "fg_color": ctk_color("content_bg"),
            "border_color": ctk_color("separator"),
            "border_width": 1,
            "corner_radius": 12,
        }

    @staticmethod
    def get_glass_shell_style(strong: bool = False):
        token_name = "glass_bg_strong" if strong else "glass_bg"
        return {
            "fg_color": ctk_color(token_name, reduced_transparency=True),
            "border_color": ctk_color("glass_border"),
            "border_width": 1,
            "corner_radius": 18,
        }

    @staticmethod
    def refresh_constants(actual_mode: str, high_contrast: bool, reduced_transparency: bool):
        """Refreshes all global module constants based on new settings."""
        global TK_BG_SURFACE, TK_BG_SURFACE_SOFT, TK_TEXT_MAIN, TK_TEXT_MUTED
        global TK_BORDER_SOFT, TK_TREE_CATEGORY_TEXT, TK_TREE_PROJECT_TEXT
        global TK_TREE_SKILL_TEXT, TK_TREE_ESSENTIAL_TEXT, TK_TREE_ARCHIVED_TEXT
        global TK_ROW_SELECTED_BG, POPOVER_BG, POPOVER_TEXT, POPOVER_MUTED_TEXT
        global BG_SURFACE, BG_SURFACE_SOFT, TEXT_MAIN, TEXT_MUTED, BORDER_SOFT
        global ROW_SELECTED_BG, SKILL_BLUE, SKILL_BLUE_DEEP

        # Update strings (mode-specific)
        TK_BG_SURFACE = tk_color("content_bg", actual_mode, high_contrast=high_contrast, reduced_transparency=reduced_transparency)
        TK_BG_SURFACE_SOFT = tk_color("content_raised", actual_mode, high_contrast=high_contrast, reduced_transparency=reduced_transparency)
        TK_TEXT_MAIN = tk_color("label", actual_mode, high_contrast=high_contrast, reduced_transparency=reduced_transparency)
        TK_TEXT_MUTED = tk_color("secondary_label", actual_mode, high_contrast=high_contrast, reduced_transparency=reduced_transparency)
        TK_BORDER_SOFT = tk_color("separator", actual_mode, high_contrast=high_contrast, reduced_transparency=reduced_transparency)
        TK_TREE_CATEGORY_TEXT = tk_color("tree_category", actual_mode, high_contrast=high_contrast, reduced_transparency=reduced_transparency)
        TK_TREE_PROJECT_TEXT = tk_color("tree_project", actual_mode, high_contrast=high_contrast, reduced_transparency=reduced_transparency)
        TK_TREE_SKILL_TEXT = TK_TEXT_MAIN
        TK_TREE_ESSENTIAL_TEXT = tk_color("tree_essential", actual_mode, high_contrast=high_contrast, reduced_transparency=reduced_transparency)
        TK_TREE_ARCHIVED_TEXT = tk_color("tree_archived", actual_mode, high_contrast=high_contrast, reduced_transparency=reduced_transparency)
        TK_ROW_SELECTED_BG = tk_color("accent_selection", actual_mode, high_contrast=high_contrast, reduced_transparency=reduced_transparency)
        
        # Popovers always dark
        POPOVER_BG = tk_color("glass_bg_strong", "dark")
        POPOVER_TEXT = tk_color("peek_label")
        POPOVER_MUTED_TEXT = tk_color("peek_secondary_label")

        # Update tuples (high-contrast specific)
        BG_SURFACE = ctk_color("content_bg", high_contrast=high_contrast, reduced_transparency=reduced_transparency)
        BG_SURFACE_SOFT = ctk_color("content_raised", high_contrast=high_contrast, reduced_transparency=reduced_transparency)
        TEXT_MAIN = ctk_color("label", high_contrast=high_contrast, reduced_transparency=reduced_transparency)
        TEXT_MUTED = ctk_color("secondary_label", high_contrast=high_contrast, reduced_transparency=reduced_transparency)
        BORDER_SOFT = ctk_color("separator", high_contrast=high_contrast, reduced_transparency=reduced_transparency)
        ROW_SELECTED_BG = ctk_color("accent_selection", high_contrast=high_contrast, reduced_transparency=reduced_transparency)
        SKILL_BLUE = ctk_color("accent", high_contrast=high_contrast, reduced_transparency=reduced_transparency)
        SKILL_BLUE_DEEP = ctk_color("accent_hover", high_contrast=high_contrast, reduced_transparency=reduced_transparency)

        # Update dictionaries
        CTK_COLORS.update({
            name: ctk_color(name, high_contrast=high_contrast, reduced_transparency=reduced_transparency) 
            for name in LIQUID_GLASS_TOKENS
        })
        
        CTK_STATUS_COLORS.update({
            "info": ctk_color("accent", high_contrast=high_contrast, reduced_transparency=reduced_transparency),
            "info_hover": ctk_color("accent_hover", high_contrast=high_contrast, reduced_transparency=reduced_transparency),
            "success": ctk_color("success", high_contrast=high_contrast, reduced_transparency=reduced_transparency),
            "success_hover": ctk_color("success_hover", high_contrast=high_contrast, reduced_transparency=reduced_transparency),
            "warning": ctk_color("warning", high_contrast=high_contrast, reduced_transparency=reduced_transparency),
            "warning_hover": ctk_color("warning_hover", high_contrast=high_contrast, reduced_transparency=reduced_transparency),
            "error": ctk_color("danger", high_contrast=high_contrast, reduced_transparency=reduced_transparency),
            "error_hover": ctk_color("danger_hover", high_contrast=high_contrast, reduced_transparency=reduced_transparency),
        })

    @staticmethod
    def get_tree_style_tokens(appearance: str = "light", high_contrast: bool = False, reduced_transparency: bool = False):
        return {
            "background": tk_color("content_bg", appearance, high_contrast=high_contrast, reduced_transparency=reduced_transparency),
            "foreground": tk_color("label", appearance, high_contrast=high_contrast, reduced_transparency=reduced_transparency),
            "disabled_foreground": tk_color("secondary_label", appearance, high_contrast=high_contrast, reduced_transparency=reduced_transparency),
            "fieldbackground": tk_color("content_bg", appearance, high_contrast=high_contrast, reduced_transparency=reduced_transparency),
            "heading_background": tk_color("content_raised", appearance, high_contrast=high_contrast, reduced_transparency=reduced_transparency),
            "heading_foreground": tk_color("label", appearance, high_contrast=high_contrast, reduced_transparency=reduced_transparency),
            "selected_background": tk_color("accent_selection", appearance, high_contrast=high_contrast, reduced_transparency=reduced_transparency),
            "category_foreground": tk_color("tree_category", appearance, high_contrast=high_contrast, reduced_transparency=reduced_transparency),
            "project_foreground": tk_color("tree_project", appearance, high_contrast=high_contrast, reduced_transparency=reduced_transparency),
            "skill_foreground": tk_color("label", appearance, high_contrast=high_contrast, reduced_transparency=reduced_transparency),
            "essential_foreground": tk_color("tree_essential", appearance, high_contrast=high_contrast, reduced_transparency=reduced_transparency),
            "archived_foreground": tk_color("tree_archived", appearance, high_contrast=high_contrast, reduced_transparency=reduced_transparency),
        }

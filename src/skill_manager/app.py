import json
import os
import struct
import threading
import re
import queue
import sys
import tempfile
import ctypes
from datetime import datetime
from pathlib import Path

import tkinter as tk
from tkinter import ttk
import customtkinter as ctk
from tkinter import filedialog
from tkinterdnd2 import TkinterDnD, DND_FILES

from .core.updater import update_projects
from .core.copier import copy_skill_folders_to_targets
from .core.quick_copy import (
    CLIENT_FORMATS,
    delete_project_skill_folders,
    discover_project_skills,
    format_project_skill_reference,
    merge_manual_references,
    normalize_manual_reference,
    normalize_manual_references,
)
from .core.skill_sources import (
    check_skill_source_versions,
    detect_git_remote,
    normalize_skill_source_config,
    run_skill_source_update,
)
from .core.config import (
    ConfigManager, 
    SKILL_LIBRARY_CACHE_FILE, 
    SKILL_LIBRARY_ARCHIVE_FILE, 
    SKILL_LIBRARY_CLIPBOARD_FILE,
    QUICK_COPY_FILE,
    SKILL_LIBRARY_CACHE_VERSION
)
from .gui.dialogs import SkillEditDialog
from .gui.components import GlassPill, SkillInspectorOverlay, SidebarFrame
from .gui.styles import (
    BG_SURFACE,
    BG_SURFACE_SOFT,
    BORDER_SOFT,
    CTK_COLORS,
    GLASS_BG,
    GLASS_BG_STRONG,
    GLASS_BORDER,
    GLASS_CONTROL,
    GLASS_CONTROL_HOVER,
    GLASS_SEARCH_BG,
    GLASS_SEARCH_BORDER,
    GLASS_SEARCH_PLACEHOLDER,
    GLASS_SEARCH_TEXT,
    ROW_SELECTED_BG,
    SKILL_BLUE,
    SKILL_BLUE_DEEP,
    STATUS_COLORS,
    CTK_STATUS_COLORS,
    POPOVER_BG,
    POPOVER_MUTED_TEXT,
    POPOVER_TEXT,
    TEXT_MAIN,
    TEXT_MUTED,
    TOAST_STYLE,
    TREE_ARCHIVED_TEXT,
    TREE_CATEGORY_TEXT,
    TREE_ESSENTIAL_TEXT,
    TREE_PROJECT_TEXT,
    TREE_SKILL_TEXT,
    apply_theme,
    StyleManager,
)
import pywinstyles
from .gui import styles
from .utils.win32 import get_window_placement, set_window_placement, apply_native_style

QUICK_COPY_ESSENTIALS_CATEGORY = "Essentials"
QUICK_COPY_MANUAL_PROJECT = "Manuals"
QUICK_COPY_MANUAL_CATEGORY = "Manual"
DISCLOSURE_EXPAND_ICON = "\u25b8"
DISCLOSURE_COLLAPSE_ICON = "\u25be"
COPY_ICON = "\u2398"
TRASH_ICON = "\U0001F5D1"
SKILL_CATEGORY_NAMES = [
    "Agents",
    "AI",
    "Analytics",
    "Architecture",
    "Backend Development",
    "Background Jobs",
    "Billing",
    "Build Systems",
    "Business Strategy",
    "Careers",
    "Cloud Infrastructure",
    "Code Quality",
    "Communications",
    "Compliance",
    "Content",
    "Core Workflow",
    "Data",
    "Databases",
    "Debugging",
    "Design",
    "Desktop Development",
    "Developer Tools",
    "DevOps",
    "Diagrams",
    "Documentation",
    "Embedded Systems",
    "ERP",
    "Finance",
    "Fitness",
    "Game Development",
    "Health",
    "Human Resources",
    "Inventory",
    "Knowledge Management",
    "Legal",
    "Linting",
    "Localization",
    "Logistics",
    "Manufacturing",
    "Marketing",
    "Mental Health",
    "Migration",
    "Mobile Development",
    "Observability",
    "Occupational Health",
    "Oral Health",
    "Payments",
    "Performance",
    "Procurement",
    "Product Management",
    "Programming Languages",
    "Psychology",
    "Quality Control",
    "Rehabilitation",
    "Security",
    "Sexual Health",
    "Shell Scripting",
    "Sleep",
    "Social Media",
    "Testing",
    "Traditional Medicine",
    "Travel Health",
    "Uncategorized",
    "Web Development",
    "Web3",
]

try:
    import yaml
except ImportError:
    yaml = None

# Set Windows AppUserModelID at module level to ensure taskbar icon visibility
if sys.platform == "win32":
    try:
        myappid = 'google.gemini.skillmanager.v1'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception:
        pass

class SkillManagerApp(ctk.CTk, TkinterDnD.DnDWrapper):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.TkdndVersion = TkinterDnD._require(self)

        self.config_manager = ConfigManager()

        self.geometry("1300x650")
        self.title("Skill Manager")
        
        self.appearance_mode = self.config_manager.get("appearance_mode", "System")
        self.high_contrast = self.config_manager.get("high_contrast", False)
        self.reduced_transparency = self.config_manager.get("reduced_transparency", False)
        self.default_client_format = self.config_manager.get("default_client_format", "Codex")

        apply_theme(self.appearance_mode)
        self.configure(fg_color=CTK_COLORS["window_bg"])
        
        # Apply native Windows effects (Mica on Win11, Acrylic on Win10)
        # Fallback to opaque if reduced_transparency is enabled
        if not self.reduced_transparency:
            style = "mica" if sys.platform == "win32" else "transparent"
            # We use "mica" by default, pywinstyles will fallback to "acrylic" or others if needed
            apply_native_style(self, style)

        self.targets = self.config_manager.get("targets", [])
        self.target_aliases = self.config_manager.get("target_aliases", {})
        self.sources = self.config_manager.get("sources", [])
        self.skills = [normalize_skill_source_config(skill) for skill in self.config_manager.get("skills", [])]

        # Initialize data structures with defaults for async loading
        self.library_archive = {"archived_skills": set(), "archived_categories": set()}
        self.library_clipboard_config = {"client_format": "Codex", "expanded_categories": []}
        self.quick_copy_config = {"selected_project_key": "", "manual_references_by_project": {}}
        self.skill_cache = {"version": SKILL_LIBRARY_CACHE_VERSION, "skills": {}}
        self._data_ready = threading.Event()
        self._library_search_after_id = None
        self._library_result_queue = None
        self._library_render_after_id = None
        self._quick_copy_search_after_id = None
        self._quick_copy_result_queue = None
        self._quick_copy_render_after_id = None
        self.library_category_state_loaded = False
        self.library_expanded_categories = set()
        self.library_selected_skill_keys = set()
        self.quick_copy_selected_skill_keys = set()
        self.library_skills = []
        self.filtered_library_skills = []
        self.quick_copy_projects = []
        self.filtered_quick_copy_projects = []
        self.quick_copy_manual_references_by_project = {}
        self.quick_copy_manual_references = []
        self.filtered_quick_copy_manual_skills = []
        self.quick_copy_selected_project_key = ""
        self.quick_copy_essential_skill_keys_by_project = {}
        self.quick_copy_essential_skill_keys = set()
        self.quick_copy_skill_arguments_by_project = {}
        self.quick_copy_selected_skill_keys_by_project = {}
        
        # UI Component Initialization (Prevents RecursionError/AttributeError)
        self.source_listbox = None
        self.target_listbox = None
        self.skill_action_buttons = []
        self.skill_widgets = []
        self.quick_copy_tree = None
        self.library_tree = None
        self.quick_copy_skills_header = None
        self.quick_copy_bundle_cluster = None
        self.quick_copy_set_menu = None
        self.quick_copy_add_bundle_frame = None
        self.quick_copy_bundle_name_entry = None
        self.quick_copy_disclosure_btn = None
        self.quick_copy_select_visible_check = None
        self.quick_copy_bundle_dropdown_frame = None
        self.quick_copy_selection_indicator = None
        self.quick_copy_status_label = None
        self.quick_copy_client_var = None
        self.quick_copy_select_visible_var = None
        
        self.library_tree_items = {}
        self.library_tree_categories = {}
        self.quick_copy_tree_projects = {}
        self.quick_copy_tree_categories = {}
        self.quick_copy_tree_items = {}
        self._normal_geometry = "1300x650"
        self._config_lock = threading.Lock()
        self._toast_after_id = None
        self._toast_frame = None
        self._description_peek_after_id = None
        self._description_peek_window = None
        self._description_peek_key = None
        self._description_peek_delay_ms = 450

        self._ui_queue = queue.Queue()
        self._built_tabs = set() # Track lazy-loaded tabs

        self.create_widgets()
        self.load_ui_state()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        # Track normal window geometry for persistence
        self.bind("<Configure>", self._on_configure)

        # Start UI queue processor
        self._process_ui_queue()

        # Defer heavy tasks: Brand assets and Async Data Loading
        self.after(100, self._load_brand_assets)
        threading.Thread(target=self._async_load_data, daemon=True).start()

        # Safely trigger background version check after UI is ready
        self.after(500, self.check_all_skill_updates)

    def _async_load_data(self):
        """Loads large configuration and cache files in a background thread."""
        try:
            library_archive = self.load_library_archive()
            library_clipboard_config = self.load_library_clipboard_config()
            quick_copy_config = self.load_quick_copy_config()
            skill_cache = self._load_skill_library_cache()

            # Process Quick Copy config (complex migration logic)
            manual_refs_by_project = {}
            for project_key, data in quick_copy_config.get("manual_references_by_project", {}).items():
                if isinstance(data, dict):
                    manual_refs_by_project[str(project_key)] = {
                        str(client): list(refs) for client, refs in data.items()
                    }
                else:
                    manual_refs_by_project[str(project_key)] = {
                        quick_copy_config.get("client_format", "Codex"): list(data)
                    }
            
            legacy_manuals = quick_copy_config.get("manual_references", [])
            if legacy_manuals:
                initial_project = quick_copy_config.get("selected_project_key", "")
                if initial_project not in manual_refs_by_project:
                    manual_refs_by_project[initial_project] = {}
                
                client_format = quick_copy_config.get("client_format", "Codex")
                existing = manual_refs_by_project[initial_project].get(client_format, [])
                manual_refs_by_project[initial_project][client_format] = merge_manual_references(
                    existing, legacy_manuals
                )
            
            essential_keys = {
                str(project_key): set(keys)
                for project_key, keys in quick_copy_config.get("essential_skill_keys_by_project", {}).items()
            }
            selected_keys = {
                str(project_key): set(keys)
                for project_key, keys in quick_copy_config.get("selected_skill_keys_by_project", {}).items()
            }

            def apply_data():
                self.library_archive = library_archive
                self.library_clipboard_config = library_clipboard_config
                self.quick_copy_config = quick_copy_config
                self.skill_cache = skill_cache
                self.library_expanded_categories = set(library_clipboard_config.get("expanded_categories", []))
                self.quick_copy_manual_references_by_project = manual_refs_by_project
                self.quick_copy_selected_project_key = quick_copy_config.get("selected_project_key", "")
                self.quick_copy_essential_skill_keys_by_project = essential_keys
                self.quick_copy_skill_arguments_by_project = quick_copy_config.get("skill_arguments_by_project", {})
                self.quick_copy_selected_skill_keys_by_project = selected_keys
                
                # Update UI elements that depend on this data
                if hasattr(self, "quick_copy_client_var"):
                    self.quick_copy_client_var.set(quick_copy_config.get("client_format", "Codex"))
                
                self._data_ready.set()
                self.load_quick_copy()

            self._ui_queue.put(apply_data)
        except Exception as e:
            print(f"Error in _async_load_data: {e}")
            self._data_ready.set() # Don't block forever


    def _load_brand_assets(self):
        logo_path = Path(__file__).resolve().parents[2] / "assets" / "logo" / "logo.png"
        self._window_icon_image = None
        self._app_logo_image = None
        self._window_icon_path = None
        
        if not logo_path.is_file():
            print(f"Brand asset not found: {logo_path}")
            return

        try:
            # 1. Main Window Icon (Taskbar & Window Frame)
            # iconphoto is the modern, cross-platform way. With AppUserModelID set at module level, 
            # this is highly effective on Windows 10/11.
            icon_image = tk.PhotoImage(file=str(logo_path))
            self.iconphoto(True, icon_image)
            self._window_icon_image = icon_image  # Keep reference alive

            # 2. In-App Logo (UI Header)
            logo_image = tk.PhotoImage(file=str(logo_path))
            max_size = 42
            shrink = max(1, (max(logo_image.width(), logo_image.height()) + max_size - 1) // max_size)
            if shrink > 1:
                logo_image = logo_image.subsample(shrink, shrink)
            self._app_logo_image = logo_image
        except tk.TclError as e:
            print(f"Error loading brand assets: {e}")
            self._window_icon_image = None
            self._app_logo_image = None

    def _create_windows_icon_file(self, image):
        if sys.platform != "win32":
            return None

        max_size = 256
        shrink = max(1, (max(image.width(), image.height()) + max_size - 1) // max_size)
        icon_image = image.subsample(shrink, shrink) if shrink > 1 else image
        png_path = Path(tempfile.gettempdir()) / "skill-manager-logo-icon.png"
        ico_path = Path(tempfile.gettempdir()) / "skill-manager-logo.ico"

        icon_image.write(str(png_path), format="png")
        png_data = png_path.read_bytes()
        width = icon_image.width() if icon_image.width() < max_size else 0
        height = icon_image.height() if icon_image.height() < max_size else 0
        header = struct.pack("<HHH", 0, 1, 1)
        entry = struct.pack("<BBBBHHII", width, height, 0, 0, 1, 32, len(png_data), 22)
        ico_path.write_bytes(header + entry + png_data)
        return ico_path

    def _process_ui_queue(self):
        """Processes any pending UI update tasks in the main thread."""
        try:
            # Drain the queue
            while True:
                task = self._ui_queue.get_nowait()
                task()
        except queue.Empty:
            pass
        finally:
            # Reschedule itself
            self.after(100, self._process_ui_queue)

    def show_toast(self, title, message="", kind="info", duration=3600, parent=None, action_text=None, action_callback=None):
        parent = parent or self
        if not getattr(parent, "winfo_exists", lambda: False)():
            return

        if parent is self and self._toast_after_id is not None:
            try:
                self.after_cancel(self._toast_after_id)
            except tk.TclError:
                pass
            self._toast_after_id = None

        existing = getattr(parent, "_active_toast_frame", None)
        if existing is not None:
            try:
                existing.destroy()
            except tk.TclError:
                pass

        accent = CTK_STATUS_COLORS.get(kind, CTK_STATUS_COLORS["info"])
        toast = ctk.CTkFrame(parent, **TOAST_STYLE)
        toast.grid_columnconfigure(1, weight=1)
        toast.grid_columnconfigure(2, weight=0)

        ctk.CTkFrame(toast, width=4, fg_color=accent, corner_radius=4).grid(
            row=0, column=0, rowspan=2, padx=(10, 8), pady=10, sticky="ns"
        )
        ctk.CTkLabel(
            toast,
            text=title,
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=TEXT_MAIN,
            anchor="w",
        ).grid(row=0, column=1, padx=(0, 12), pady=(10, 0), sticky="ew")

        if message:
            ctk.CTkLabel(
                toast,
                text=message,
                text_color=TEXT_MUTED,
                anchor="w",
                justify="left",
                wraplength=520,
            ).grid(row=1, column=1, padx=(0, 12), pady=(2, 10), sticky="ew")

        if action_text and action_callback:
            def run_action():
                action_callback()
                dismiss()

            ctk.CTkButton(
                toast,
                text=action_text,
                width=72,
                fg_color="transparent",
                hover_color=GLASS_CONTROL_HOVER,
                text_color=accent,
                command=run_action,
            ).grid(row=0, column=2, rowspan=2, padx=(0, 12), pady=10, sticky="e")

        toast.place(relx=1.0, rely=1.0, x=-24, y=-24, anchor="se")
        toast.lift()
        setattr(parent, "_active_toast_frame", toast)
        if parent is self:
            self._toast_frame = toast

        def dismiss():
            if getattr(parent, "_active_toast_frame", None) is toast:
                setattr(parent, "_active_toast_frame", None)
            if parent is self:
                self._toast_after_id = None
                self._toast_frame = None
            try:
                toast.destroy()
            except tk.TclError:
                pass

        after_id = parent.after(duration, dismiss)
        if parent is self:
            self._toast_after_id = after_id

    def confirm_destructive_action(self, title, message, details, confirm_text, on_confirm):
        dialog = ctk.CTkToplevel(self)
        dialog.title(title)
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(False, False)
        dialog.grid_columnconfigure(0, weight=1)

        content = ctk.CTkFrame(dialog, fg_color="transparent")
        content.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        content.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(content, text=title, font=ctk.CTkFont(size=16, weight="bold"), anchor="w").grid(
            row=0, column=0, sticky="ew"
        )
        ctk.CTkLabel(content, text=message, text_color=TEXT_MUTED, anchor="w", justify="left", wraplength=520).grid(
            row=1, column=0, pady=(8, 12), sticky="ew"
        )
        if details:
            detail_box = ctk.CTkTextbox(content, width=560, height=150)
            detail_box.grid(row=2, column=0, sticky="ew")
            detail_box.insert("1.0", details)
            detail_box.configure(state="disabled")

        button_frame = ctk.CTkFrame(content, fg_color="transparent")
        button_frame.grid(row=3, column=0, pady=(16, 0), sticky="e")

        def confirm():
            dialog.grab_release()
            dialog.destroy()
            on_confirm()

        ctk.CTkButton(button_frame, text="Cancel", width=92, fg_color=GLASS_CONTROL, hover_color=GLASS_CONTROL_HOVER, corner_radius=14, command=dialog.destroy).grid(
            row=0, column=0, padx=(0, 8)
        )
        ctk.CTkButton(
            button_frame,
            text=confirm_text,
            width=120,
            fg_color=CTK_STATUS_COLORS["error"],
            hover_color=CTK_STATUS_COLORS["error_hover"],
            command=confirm,
        ).grid(row=0, column=1)

        dialog.update_idletasks()
        x = self.winfo_rootx() + max(0, (self.winfo_width() - dialog.winfo_width()) // 2)
        y = self.winfo_rooty() + max(0, (self.winfo_height() - dialog.winfo_height()) // 2)
        dialog.geometry(f"+{x}+{y}")

    def create_widgets(self):
        # Configure grid for sidebar layout
        self.grid_columnconfigure(0, weight=0) # Sidebar
        self.grid_columnconfigure(1, weight=1) # Main content
        self.grid_rowconfigure(0, weight=1)

        # 1. Sidebar (Layer 1: High-opacity glass)
        self.sidebar_frame = SidebarFrame(self, on_navigate=self._on_nav_change)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        
        # 2. Main Content Area (Layer 0: Native material background)
        self.main_content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_content_frame.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
        self.main_content_frame.grid_columnconfigure(0, weight=1)
        self.main_content_frame.grid_rowconfigure(0, weight=1)

        # View container to hold our different "tabs"
        self.views = {}

        # Global Inspector Overlay (hidden initially)
        self.inspector_overlay = SkillInspectorOverlay(self, on_close=lambda: self.quick_copy_tree.selection_remove(self.quick_copy_tree.selection()) if hasattr(self, "quick_copy_tree") else None)
        
        # Connect Overlay Controls
        def _apply_overlay_category():
            prefix = getattr(self, "_current_inspector_prefix", "library")
            self._apply_current_inspector_category(prefix)
            
        def _toggle_overlay_action():
            prefix = getattr(self, "_current_inspector_prefix", "library")
            if prefix == "quick_copy":
                self.toggle_current_inspector_essential()
            elif prefix == "library":
                self.toggle_current_inspector_archive()
                
        self.inspector_overlay.apply_category_btn.configure(command=_apply_overlay_category)
        self.inspector_overlay.action_btn.configure(command=_toggle_overlay_action)
        
        def _on_overlay_arg_change(*_args):
            skill = getattr(self, "_current_inspector_skill", None)
            prefix = getattr(self, "_current_inspector_prefix", None)
            if skill and prefix == "quick_copy":
                self._set_quick_copy_skill_argument(skill, self.inspector_overlay.argument_var.get().strip())
        
        self.inspector_overlay.argument_var.trace_add("write", _on_overlay_arg_change)

        # Initial View
        self._on_nav_change("Quick Copy")

        # Progressive Background Loading (non-blocking)
        self.after(200, lambda: self._progressive_build_view("Library"))
        self.after(400, lambda: self._progressive_build_view("Updates"))
        self.after(600, lambda: self._progressive_build_view("Settings"))

        # --- Global Status & Progress ---
        self.status_frame = ctk.CTkFrame(self.main_content_frame, fg_color="transparent")
        self.status_frame.place(relx=0.5, rely=1.0, y=-25, anchor="s", relwidth=0.8)
        self.status_frame.grid_columnconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(self.status_frame, text="", text_color=TEXT_MUTED)
        self.status_label.grid(row=0, column=0, pady=(0, 2))

        self.progress_bar = ctk.CTkProgressBar(self.status_frame, mode="determinate")
        self.progress_bar.grid(row=1, column=0, sticky="ew")
        self.progress_bar.set(0)
        self.progress_bar.grid_remove() # Hide initially

    def _on_nav_change(self, view_name: str):
        """Navigation controller for swapping views."""
        self.sidebar_frame.set_active(view_name)
        self._progressive_build_view(view_name)
        
        # Hide all views
        for name, frame in self.views.items():
            frame.grid_remove()
            
        # Show active view
        if view_name in self.views:
            self.views[view_name].grid(row=0, column=0, sticky="nsew")

    def _progressive_build_view(self, view_name: str):
        if view_name in self.views and view_name in self._built_tabs:
            return

        # Create the frame for the view
        if view_name not in self.views:
            frame = ctk.CTkFrame(self.main_content_frame, fg_color="transparent")
            self.views[view_name] = frame

        # Map name to creation method
        if view_name == "Quick Copy":
            self.create_quick_copy_tab(self.views[view_name])
        elif view_name == "Library":
            self.create_library_tab(self.views[view_name])
        elif view_name == "Updates":
            self.create_updates_tab(self.views[view_name])
        elif view_name == "Settings":
            self.create_settings_tab(self.views[view_name])
        
        self._built_tabs.add(view_name)
        self._update_dynamic_theme()
    def create_settings_tab(self, parent=None):
        tab = parent if parent else self.tabview.tab("Settings")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(0, weight=1)

        scroll_frame = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll_frame.grid(row=0, column=0, sticky="nsew")
        scroll_frame.grid_columnconfigure(0, weight=1)

        # --- Appearance Section ---
        appearance_pill, appearance_content = self._create_settings_section(scroll_frame, "Appearance", "Configure how the application looks.")
        appearance_pill.pack(fill="x", padx=15, pady=(15, 8))

        ctk.CTkLabel(appearance_content, text="Appearance Mode", font=("Segoe UI", 13, "bold"), text_color=TEXT_MAIN).grid(row=0, column=0, padx=16, pady=(16, 4), sticky="w")
        ctk.CTkLabel(appearance_content, text="Choose between Light, Dark, or System (matches your OS) themes.", text_color=TEXT_MUTED).grid(row=1, column=0, padx=16, pady=(0, 16), sticky="w")

        self.appearance_mode_var = ctk.StringVar(value=self.appearance_mode)
        appearance_menu = ctk.CTkOptionMenu(
            appearance_content,
            variable=self.appearance_mode_var,
            values=["System", "Light", "Dark"],
            command=self._on_appearance_mode_change,
            width=200,
            fg_color=GLASS_CONTROL,
            button_color=GLASS_CONTROL,
            button_hover_color=GLASS_CONTROL_HOVER,
            text_color=TEXT_MAIN,
            corner_radius=14,
        )
        appearance_menu.grid(row=0, column=1, rowspan=2, padx=16, pady=16, sticky="e")

        # --- Accessibility Section ---
        accessibility_pill, accessibility_content = self._create_settings_section(scroll_frame, "Accessibility", "Adjust visual effects for better visibility.")
        accessibility_pill.pack(fill="x", padx=15, pady=8)

        # High Contrast
        self.high_contrast_var = tk.BooleanVar(value=self.high_contrast)
        hc_check = ctk.CTkCheckBox(
            accessibility_content,
            text="High Contrast",
            variable=self.high_contrast_var,
            command=self._on_high_contrast_change,
            checkbox_width=20,
            checkbox_height=20,
            corner_radius=6,
            border_width=2,
            fg_color=SKILL_BLUE,
            hover_color=SKILL_BLUE_DEEP,
            border_color=GLASS_BORDER,
            text_color=TEXT_MAIN,
        )
        hc_check.grid(row=0, column=0, padx=16, pady=(16, 4), sticky="w")
        ctk.CTkLabel(accessibility_content, text="Increases contrast of text, borders, and selection outlines.", text_color=TEXT_MUTED).grid(row=1, column=0, padx=16, pady=(0, 8), sticky="w")

        # Reduced Transparency
        self.reduced_transparency_var = tk.BooleanVar(value=self.reduced_transparency)
        rt_check = ctk.CTkCheckBox(
            accessibility_content,
            text="Reduced Transparency",
            variable=self.reduced_transparency_var,
            command=self._on_reduced_transparency_change,
            checkbox_width=20,
            checkbox_height=20,
            corner_radius=6,
            border_width=2,
            fg_color=SKILL_BLUE,
            hover_color=SKILL_BLUE_DEEP,
            border_color=GLASS_BORDER,
            text_color=TEXT_MAIN,
        )
        rt_check.grid(row=2, column=0, padx=16, pady=(8, 4), sticky="w")
        ctk.CTkLabel(accessibility_content, text="Replaces glass-like surfaces with opaque colors.", text_color=TEXT_MUTED).grid(row=3, column=0, padx=16, pady=(0, 16), sticky="w")

        # --- Defaults Section ---
        defaults_pill, defaults_content = self._create_settings_section(scroll_frame, "Application Defaults", "Set initial values for new sessions.")
        defaults_pill.pack(fill="x", padx=15, pady=8)

        ctk.CTkLabel(defaults_content, text="Default Client Format", font=("Segoe UI", 13, "bold"), text_color=TEXT_MAIN).grid(row=0, column=0, padx=16, pady=(16, 4), sticky="w")
        ctk.CTkLabel(defaults_content, text="The reference style used when copying skills.", text_color=TEXT_MUTED).grid(row=1, column=0, padx=16, pady=(0, 16), sticky="w")

        self.default_client_format_var = ctk.StringVar(value=self.default_client_format)
        client_menu = ctk.CTkOptionMenu(
            defaults_content,
            variable=self.default_client_format_var,
            values=["Codex", "Gemini CLI", "Antigravity", "Plain Path"],
            command=self._on_default_client_format_change,
            width=200,
            fg_color=GLASS_CONTROL,
            button_color=GLASS_CONTROL,
            button_hover_color=GLASS_CONTROL_HOVER,
            text_color=TEXT_MAIN,
            corner_radius=14,
        )
        client_menu.grid(row=0, column=1, rowspan=2, padx=16, pady=16, sticky="e")

        # --- About Section ---
        about_pill, about_content = self._create_settings_section(scroll_frame, "About", f"Skill Manager v1.1.0")
        about_pill.pack(fill="x", padx=15, pady=(8, 15))

        about_text = "A productivity tool for discovering and organizing agent skills.\nFollowing Liquid Glass design guidelines."
        ctk.CTkLabel(about_content, text=about_text, text_color=TEXT_MUTED, justify="left").grid(row=0, column=0, padx=16, pady=16, sticky="w")

    def _create_settings_section(self, parent, title, subtitle):
        pill = GlassPill(parent)
        pill.grid_columnconfigure(0, weight=1)

        # Glass Header internal to pill
        header = ctk.CTkFrame(pill, fg_color=GLASS_BG_STRONG, corner_radius=16, height=50)
        header.grid(row=0, column=0, columnspan=2, sticky="ew")
        header.grid_columnconfigure(0, weight=1)
        header.grid_propagate(False)

        ctk.CTkLabel(header, text=title, font=("Segoe UI", 16, "bold"), text_color=TEXT_MAIN).grid(row=0, column=0, padx=16, pady=0, sticky="w")

        # Content area
        content_container = ctk.CTkFrame(pill, fg_color="transparent")
        content_container.grid(row=1, column=0, columnspan=2, sticky="ew")
        content_container.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(content_container, text=subtitle, text_color=TEXT_MUTED).grid(row=0, column=0, padx=16, pady=(8, 4), sticky="w")

        # Separator
        sep = ctk.CTkFrame(content_container, height=1, fg_color=BORDER_SOFT)
        sep.grid(row=1, column=0, columnspan=2, sticky="ew", padx=16, pady=(0, 4))

        return pill, content_container
    def _on_appearance_mode_change(self, mode):
        self.appearance_mode = mode
        self.config_manager.set("appearance_mode", mode)
        self._update_dynamic_theme()
        self.show_toast("Appearance Updated", f"Theme set to {mode}.", "success")

    def _on_high_contrast_change(self):
        val = self.high_contrast_var.get()
        self.high_contrast = val
        self.config_manager.set("high_contrast", val)
        self._update_dynamic_theme()
        self.show_toast("Setting Saved", "High Contrast enabled. Please restart the app for full effect.", "info")

    def _on_reduced_transparency_change(self):
        val = self.reduced_transparency_var.get()
        self.reduced_transparency = val
        self.config_manager.set("reduced_transparency", val)
        self._update_dynamic_theme()
        self.show_toast("Setting Saved", "Reduced Transparency updated. Please restart the app for full effect.", "info")

    def _on_default_client_format_change(self, format_name):
        self.default_client_format = format_name
        self.config_manager.set("default_client_format", format_name)
        # Update current var in Quick Copy tab if it exists
        if hasattr(self, "quick_copy_client_var"):
            self.quick_copy_client_var.set(format_name)
        self.show_toast("Default Updated", f"Default client format set to {format_name}.", "success")

    def create_updates_tab(self, parent=None):
        tab = parent if parent else self.tabview.tab("Updates")
        tab.grid_columnconfigure(0, weight=1, uniform="updates")
        tab.grid_columnconfigure(1, weight=2, uniform="updates")
        tab.grid_rowconfigure(1, weight=1)

        self.updates_header_pill = GlassPill(tab, height=80)
        self.updates_header_pill.grid(row=0, column=0, columnspan=2, padx=15, pady=(15, 8), sticky="ew")
        self.updates_header_pill.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self.updates_header_pill,
            text="Updates",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=TEXT_MAIN,
        ).grid(row=0, column=0, padx=16, pady=(12, 2), sticky="w")
        ctk.CTkLabel(
            self.updates_header_pill,
            text="Configure project folders, then update skill sources and sync linked targets.",
            text_color=TEXT_MUTED,
        ).grid(row=1, column=0, padx=16, pady=(0, 12), sticky="w")

        self.project_update_pill = GlassPill(tab)
        self.project_update_pill.grid(row=1, column=0, padx=(15, 8), pady=8, sticky="nsew")
        self.project_update_pill.grid_columnconfigure(0, weight=1)
        self.project_update_pill.grid_rowconfigure(1, weight=1)
        self.project_update_pill.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(
            self.project_update_pill,
            text="Project Folders",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=TEXT_MAIN,
        ).grid(row=0, column=0, padx=14, pady=(14, 6), sticky="w")

        source_frame = self._create_directory_section(
            self.project_update_pill,
            title="Source Directories",
            subtitle="Priority top-down. Drag folders here.",
            listbox_attr="source_listbox",
            add_text="Add Source",
            add_command=self.add_source,
            remove_text="Remove",
            remove_command=self.remove_source,
            include_reorder=True,
        )
        source_frame.grid(row=1, column=0, padx=12, pady=6, sticky="nsew")
        self.source_listbox.drop_target_register(DND_FILES)
        self.source_listbox.dnd_bind('<<Drop>>', self.drop_source)
        self._bind_directory_listbox(self.source_listbox, self.remove_source)

        target_frame = self._create_directory_section(
            self.project_update_pill,
            title="Target Directories",
            subtitle="Project skill folders to sync.",
            listbox_attr="target_listbox",
            add_text="Add Target",
            add_command=self.add_target,
            remove_text="Remove",
            remove_command=self.remove_target,
            include_reorder=False,
            rename_command=self.rename_target,
        )
        target_frame.grid(row=2, column=0, padx=12, pady=(6, 12), sticky="nsew")
        self.target_listbox.drop_target_register(DND_FILES)
        self.target_listbox.dnd_bind('<<Drop>>', self.drop_target)
        self._bind_directory_listbox(self.target_listbox, self.remove_target)

        self.skill_update_pill = GlassPill(tab)
        self.skill_update_pill.grid(row=1, column=1, padx=(8, 15), pady=8, sticky="nsew")
        self.skill_update_pill.grid_columnconfigure(0, weight=1)
        self.skill_update_pill.grid_rowconfigure(1, weight=1)

        skill_header = ctk.CTkFrame(self.skill_update_pill, fg_color="transparent")
        skill_header.grid(row=0, column=0, padx=12, pady=(12, 8), sticky="ew")
        skill_header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            skill_header,
            text="Skill Sources",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=TEXT_MAIN,
        ).grid(row=0, column=0, padx=14, pady=(10, 2), sticky="w")
        ctk.CTkLabel(
            skill_header,
            text="Repository, package, and custom update configurations.",
            text_color=TEXT_MUTED,
        ).grid(row=1, column=0, padx=14, pady=(0, 10), sticky="w")

        self.skill_scrollable_frame = ctk.CTkScrollableFrame(self.skill_update_pill, fg_color=BG_SURFACE_SOFT)
        self.skill_scrollable_frame.grid(row=1, column=0, padx=12, pady=(0, 8), sticky="nsew")
        self.skill_scrollable_frame.grid_columnconfigure(0, weight=1)

        skill_btn_frame = ctk.CTkFrame(self.skill_update_pill, fg_color="transparent")
        skill_btn_frame.grid(row=2, column=0, padx=12, pady=(0, 12), sticky="ew")
        skill_btn_frame.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkButton(skill_btn_frame, text="Add Update Source", command=self.add_skill, corner_radius=10).grid(row=0, column=0, padx=(10, 5), pady=10, sticky="ew")
        ctk.CTkButton(skill_btn_frame, text="Check Updates", command=self.check_all_skill_updates, fg_color=GLASS_CONTROL, hover_color=GLASS_CONTROL_HOVER, text_color=TEXT_MAIN, corner_radius=10).grid(row=0, column=1, padx=(5, 10), pady=10, sticky="ew")

        self.update_now_btn = ctk.CTkButton(
            tab,
            text="Update Now",
            height=44,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self.run_full_update,
            fg_color=SKILL_BLUE,
            hover_color=SKILL_BLUE_DEEP,
            corner_radius=12,
        )
        self.update_now_btn.grid(row=2, column=0, columnspan=2, padx=15, pady=(8, 15), sticky="ew")

        self.skill_widgets = [] # Keep references to update UI
        self.skill_action_buttons = []
        
        # Initialize UI data once widgets are built
        self.refresh_target_list()
        self.refresh_source_list()
        self.refresh_skill_ui()

    def _create_directory_section(
        self,
        parent,
        title,
        subtitle,
        listbox_attr,
        add_text,
        add_command,
        remove_text,
        remove_command,
        include_reorder=False,
        rename_command=None,
    ):
        frame = ctk.CTkFrame(
            parent,
            fg_color=BG_SURFACE_SOFT,
            border_color=BORDER_SOFT,
            border_width=1,
            corner_radius=14,
        )
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            frame,
            text=title,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=TEXT_MAIN,
        ).grid(row=0, column=0, padx=12, pady=(10, 0), sticky="w")
        ctk.CTkLabel(frame, text=subtitle, text_color=TEXT_MUTED).grid(row=0, column=1, padx=12, pady=(10, 0), sticky="e")

        listbox = self._create_directory_listbox(frame)
        listbox.grid(row=1, column=0, columnspan=2, padx=10, pady=(8, 8), sticky="nsew")
        setattr(self, listbox_attr, listbox)

        button_frame = ctk.CTkFrame(frame, fg_color="transparent")
        button_frame.grid(row=2, column=0, columnspan=2, padx=6, pady=(0, 8), sticky="ew")

        columns = 2 + (1 if rename_command else 0) + (2 if include_reorder else 0)
        button_frame.grid_columnconfigure(tuple(range(columns)), weight=1)

        ctk.CTkButton(button_frame, text=add_text, command=add_command, corner_radius=8).grid(row=0, column=0, padx=4, sticky="ew")
        ctk.CTkButton(
            button_frame,
            text=remove_text,
            command=remove_command,
            fg_color=GLASS_CONTROL,
            hover_color=GLASS_CONTROL_HOVER,
            text_color=CTK_STATUS_COLORS["error"],
            corner_radius=8,
        ).grid(row=0, column=1, padx=4, sticky="ew")

        col_offset = 2
        if rename_command:
            ctk.CTkButton(
                button_frame,
                text="Rename",
                command=rename_command,
                fg_color=GLASS_CONTROL,
                hover_color=GLASS_CONTROL_HOVER,
                text_color=TEXT_MAIN,
                corner_radius=8,
            ).grid(row=0, column=col_offset, padx=4, sticky="ew")
            col_offset += 1

        if include_reorder:
            ctk.CTkButton(button_frame, text="Move Up", command=self.move_source_up, fg_color=GLASS_CONTROL, hover_color=GLASS_CONTROL_HOVER, text_color=TEXT_MAIN, corner_radius=8).grid(row=0, column=col_offset, padx=4, sticky="ew")
            ctk.CTkButton(button_frame, text="Move Down", command=self.move_source_down, fg_color=GLASS_CONTROL, hover_color=GLASS_CONTROL_HOVER, text_color=TEXT_MAIN, corner_radius=8).grid(row=0, column=col_offset+1, padx=4, sticky="ew")

        return frame

    def refresh_skill_ui(self):
        if not hasattr(self, "skill_scrollable_frame"):
            return
        for widget in self.skill_scrollable_frame.winfo_children():
            widget.destroy()
        self.skill_widgets.clear()
        self.skill_action_buttons.clear()

        for idx, skill in enumerate(self.skills):
            frame = ctk.CTkFrame(self.skill_scrollable_frame)
            frame.grid(row=idx, column=0, padx=5, pady=5, sticky="ew")
            frame.grid_columnconfigure(0, weight=1)

            # Left side: Info
            info_frame = ctk.CTkFrame(frame, fg_color="transparent")
            info_frame.grid(row=0, column=0, padx=14, pady=12, sticky="ew")
            info_frame.grid_columnconfigure(0, weight=1)
            
            name_lbl = ctk.CTkLabel(info_frame, text=skill.get("name", "Unnamed Source"), font=ctk.CTkFont(weight="bold", size=16))
            name_lbl.grid(row=0, column=0, sticky="w")

            source_parts = []
            if skill.get("source_type"):
                source_parts.append(f"Type: {skill.get('source_type')}")
            if skill.get("repository_url"):
                source_parts.append(f"Repo: {skill.get('repository_url')}")
            if skill.get("local_path"):
                source_parts.append(f"Path: {skill.get('local_path')}")
            if skill.get("package_name"):
                source_parts.append(f"Package: {skill.get('package_name')}")
            source_text = " | ".join(source_parts) or "Command source"
            source_lbl = ctk.CTkLabel(info_frame, text=source_text, text_color=TEXT_MUTED, anchor="w", justify="left", wraplength=820)
            source_lbl.grid(row=1, column=0, pady=(8, 0), sticky="w")

            ver_text = f"Current: {skill.get('current_version', 'Unknown')} | Latest: {skill.get('latest_version', 'Unknown')}"
            ver_lbl = ctk.CTkLabel(info_frame, text=ver_text, text_color=TEXT_MUTED)
            ver_lbl.grid(row=2, column=0, pady=(8, 0), sticky="w")
            
            last_upd = skill.get("last_updated", "Never")
            upd_lbl = ctk.CTkLabel(info_frame, text=f"Last Updated: {last_upd}", text_color=TEXT_MUTED)
            upd_lbl.grid(row=3, column=0, pady=(8, 0), sticky="w")

            # Right side: Actions
            action_frame = ctk.CTkFrame(frame, fg_color="transparent")
            action_frame.grid(row=0, column=1, padx=14, pady=12, sticky="e")

            # Add spacing and align buttons
            edit_btn = ctk.CTkButton(action_frame, text="Edit", width=76, command=lambda i=idx: self.edit_skill(i))
            edit_btn.pack(side="left", padx=5)
            update_btn = ctk.CTkButton(action_frame, text="Update", width=92, fg_color=CTK_STATUS_COLORS["success"], hover_color=SKILL_BLUE_DEEP, command=lambda i=idx: self.run_skill_update(i))

            update_btn.pack(side="left", padx=5)
            delete_btn = ctk.CTkButton(action_frame, text="Remove", width=76, fg_color=GLASS_CONTROL, hover_color=GLASS_CONTROL_HOVER, text_color=CTK_STATUS_COLORS["error"], corner_radius=14, command=lambda i=idx: self.remove_skill(i))
            delete_btn.pack(side="left", padx=5)
            
            self.skill_widgets.append((ver_lbl, upd_lbl))
            self.skill_action_buttons.append({
                "edit": edit_btn,
                "update": update_btn,
                "delete": delete_btn,
            })

    def on_close(self):
        self.save_config()
        self.destroy()

    def _on_configure(self, event):
        if self.state() == "normal":
            self._normal_geometry = self.geometry()

    def load_ui_state(self):
        placement = self.config_manager.get("window_placement")
        if sys.platform == 'win32' and placement:
            self.after(50, lambda p=placement: self._restore_window_placement(p))
        else:
            geometry = self.config_manager.get("window_geometry")
            if geometry:
                self.geometry(geometry)
                self._normal_geometry = geometry
            state = self.config_manager.get("window_state")
            if state:
                self.after(10, lambda: self.state(state))

    def save_config(self):
        if threading.current_thread() is not threading.main_thread():
            self.save_config_data_only()
            return

        try:
            window_state = self.state()
            window_geometry = getattr(self, "_normal_geometry", self.geometry())
            window_handle = self._native_window_handle()
            window_placement = get_window_placement(window_handle) if window_handle is not None else None

            self._save_config_values({
                "targets": self.targets,
                "target_aliases": self.target_aliases,
                "sources": self.sources,
                "skills": self.skills,
                "window_geometry": window_geometry,
                "window_state": window_state,
                "window_placement": window_placement,
            })
        except Exception as e:
            print(f"Error saving config: {e}")

    def save_config_data_only(self):
        try:
            self._save_config_values({
                "targets": self.targets,
                "target_aliases": self.target_aliases,
                "sources": self.sources,
                "skills": self.skills,
            })
        except Exception as e:
            print(f"Error saving config: {e}")

    def _save_config_values(self, values):
        with self._config_lock:
            self.config_manager.data.update(values)
            self.config_manager.save()

    def _native_window_handle(self):
        if sys.platform != 'win32':
            return None
        try:
            frame_id = self.wm_frame()
            if isinstance(frame_id, str):
                base = 16 if frame_id.lower().startswith("0x") else 10
                return int(frame_id, base)
            return int(frame_id)
        except (tk.TclError, TypeError, ValueError):
            return None

    def _restore_window_placement(self, placement):
        window_handle = self._native_window_handle()
        if window_handle is None:
            return
        set_window_placement(window_handle, placement)

    def _parse_drop_data(self, data):
        paths = []
        if '{' in data:
            import re
            parts = re.findall(r'\{.*?\}|\S+', data)
            paths = [p.strip('{}') for p in parts]
        else:
            paths = data.split()
        return paths

    def _create_directory_listbox(self, parent):
        listbox = tk.Listbox(
            parent,
            activestyle="none",
            background=styles.TK_BG_SURFACE,
            borderwidth=0,
            exportselection=False,
            foreground=styles.TK_TEXT_MAIN,
            highlightbackground=styles.TK_BORDER_SOFT,
            highlightcolor=STATUS_COLORS["info"],
            highlightthickness=1,
            relief="flat",
            selectbackground=STATUS_COLORS["info"],
            selectforeground="#FFFFFF",
            selectmode="extended",
            font=("Segoe UI", 10),
        )
        listbox.configure(
            disabledforeground=styles.TK_TEXT_MUTED,
            selectborderwidth=0,
        )
        return listbox

    def _bind_directory_listbox(self, listbox, delete_command):
        listbox.bind("<Delete>", lambda _event: delete_command(), add="+")
        listbox.bind("<BackSpace>", lambda _event: delete_command(), add="+")
        listbox.bind("<Control-a>", lambda event: self._select_all_directory_rows(event.widget), add="+")
        listbox.bind("<Control-A>", lambda event: self._select_all_directory_rows(event.widget), add="+")
        
        # Attach Tooltip for Target Directories
        if listbox == getattr(self, "target_listbox", None):
            self._attach_listbox_tooltip(listbox, self.targets)

    def _attach_listbox_tooltip(self, listbox, paths):
        tooltip = [None]
        
        def show_tip(event):
            index = listbox.nearest(event.y)
            if index < 0 or index >= len(paths):
                hide_tip(None)
                return
                
            path = paths[index]
            if tooltip[0]:
                tooltip[0].destroy()
                
            x, y, cx, cy = listbox.bbox(index)
            x = x + listbox.winfo_rootx() + 25
            y = y + cy + listbox.winfo_rooty() + 2
            
            tw = tk.Toplevel(listbox)
            tooltip[0] = tw
            tw.wm_overrideredirect(True)
            tw.wm_geometry(f"+{x}+{y}")
            
            label = tk.Label(
                tw, text=path, justify='left',
                background=styles.TK_BG_SURFACE_SOFT,
                foreground=styles.TK_TEXT_MAIN,
                relief='flat', borderwidth=1,
                font=("Segoe UI", 9)
            )
            label.pack(ipadx=4, ipady=1)
            
        def hide_tip(event):
            if tooltip[0]:
                tooltip[0].destroy()
                tooltip[0] = None
                
        listbox.bind("<Motion>", show_tip)
        listbox.bind("<Leave>", hide_tip)

    def _select_all_directory_rows(self, listbox):
        listbox.selection_set(0, "end")
        return "break"

    # --- Target Methods ---
    def rename_target(self):
        index = self._selected_listbox_index(self.target_listbox, len(self.targets), "No target directories to rename.")
        if index is None:
            return

        path = self.targets[index]
        current_name = self._get_alias(path, self.target_aliases) or path

        dialog = ctk.CTkInputDialog(text=f"Enter new name for:\n{path}", title="Rename Target")
        new_name = dialog.get_input()

        if new_name:
            # Normalize path for storage
            norm_path = self._normalize_path(path)
            self.target_aliases[path] = new_name
            self.target_aliases[norm_path] = new_name
            
            # If the path in self.targets isn't identical to norm_path, 
            # store it there too just in case
            if path != norm_path:
                self.target_aliases[norm_path] = new_name

            self.refresh_target_list()
            self.save_config()
            self.load_quick_copy()

    def add_target(self):
        directory = filedialog.askdirectory(title="Select Target Directory")
        if directory:
            directory = directory.replace("\\", "/")
            alias = None
            agents_skills_path = os.path.join(directory, ".agents", "skills").replace("\\", "/")
            if os.path.isdir(agents_skills_path):
                alias = os.path.basename(directory)
                directory = agents_skills_path
                
            if directory not in self.targets:
                self.targets.append(directory)
                if alias:
                    self.target_aliases[directory] = alias
                    self.target_aliases[self._normalize_path(directory)] = alias
                self.refresh_target_list()
                self.save_config()
                self.load_quick_copy()
            
    def drop_target(self, event):
        paths = self._parse_drop_data(event.data)
        for path in paths:
            path = path.replace("\\", "/")
            if os.path.isdir(path):
                alias = None
                agents_skills_path = os.path.join(path, ".agents", "skills").replace("\\", "/")
                if os.path.isdir(agents_skills_path):
                    alias = os.path.basename(path)
                    path = agents_skills_path
                    
                if path not in self.targets:
                    self.targets.append(path)
                    if alias:
                        self.target_aliases[path] = alias
                        self.target_aliases[self._normalize_path(path)] = alias
        self.refresh_target_list()
        self.save_config()
        self.load_quick_copy()

    def _selected_listbox_indices(self, listbox, count, empty_message, require_single=False):
        if count == 0:
            self.show_toast("Nothing to select", empty_message, "info")
            return []
        try:
            indices = [int(index) for index in listbox.curselection()]
            if not indices:
                self.show_toast("Select a row", "Highlight a list row first, then use this command.", "info")
                return []
        except (tk.TclError, TypeError, ValueError):
            self.show_toast("Select a row", "Highlight a list row first, then use this command.", "info")
            return []
        indices = sorted(index for index in indices if 0 <= index < count)
        if not indices:
            self.show_toast("Invalid selection", "Select visible list rows.", "error")
            return []
        if require_single and len(indices) != 1:
            self.show_toast("Choose one row", "Select one source row before moving it.", "info")
            return []
        return indices

    def _selected_listbox_index(self, listbox, count, empty_message):
        indices = self._selected_listbox_indices(listbox, count, empty_message, require_single=True)
        if indices:
            return indices[0]
        return None

    def _select_listbox_indices(self, listbox, indices):
        try:
            listbox.selection_clear(0, "end")
            for index in indices:
                if index >= 0:
                    listbox.selection_set(index)
            if indices:
                first = min(indices)
                listbox.activate(first)
                listbox.see(first)
        except (tk.TclError, ValueError):
            pass

    def _normalize_path(self, path):
        if not path:
            return ""
        return os.path.normcase(os.path.normpath(path)).replace("\\", "/")

    def _get_alias(self, path, aliases):
        if not aliases:
            return None
        # Normalize the path we are looking up
        norm_target = self._normalize_path(path)
        
        # Check all alias keys using the same normalization
        for alias_key, alias_val in aliases.items():
            if self._normalize_path(alias_key) == norm_target:
                return alias_val
        return None

    def _refresh_directory_listbox(self, listbox, paths, aliases=None):
        listbox.delete(0, "end")
        for path in paths:
            display_name = self._get_alias(path, aliases) or path
            
            if display_name == path:
                if display_name.endswith("/.agents/skills"):
                    display_name = display_name[:-15]
                elif display_name.endswith("\\.agents\\skills"):
                    display_name = display_name[:-15]
            listbox.insert("end", display_name)
        if not paths:
            listbox.insert("end", "Drop folders here or use Add.")
            listbox.itemconfig(0, foreground=styles.TK_TEXT_MUTED, background=styles.TK_BG_SURFACE_SOFT)

    def _remove_directory_rows(self, paths, indices):
        removed = [(index, paths[index]) for index in indices]
        for index in sorted(indices, reverse=True):
            del paths[index]
        return removed

    def _restore_directory_rows(self, paths, removed):
        for index, value in sorted(removed, key=lambda item: item[0]):
            paths.insert(min(index, len(paths)), value)

    def _move_selected_rows(self, paths, indices, direction):
        selected = set(indices)
        if direction < 0:
            if 0 in selected:
                return indices
            ordered = sorted(indices)
            for index in ordered:
                paths[index - 1], paths[index] = paths[index], paths[index - 1]
            return [index - 1 for index in ordered]
        if len(paths) - 1 in selected:
            return indices
        ordered = sorted(indices, reverse=True)
        for index in ordered:
            paths[index + 1], paths[index] = paths[index], paths[index + 1]
        return sorted(index + 1 for index in ordered)

    def _directory_selection_label(self, removed):
        if len(removed) == 1:
            return removed[0][1]
        return f"{len(removed)} directories"

    def _selected_numbered_textbox_index(self, textbox, count, empty_message):
        return self._selected_listbox_index(textbox, count, empty_message)

    def _select_numbered_textbox_line(self, textbox, index):
        self._select_listbox_indices(textbox, [index])

    def _show_undo_toast(self, title, message, undo_callback):
        self.show_toast(
            title,
            message,
            "info",
            duration=7000,
            action_text="Undo",
            action_callback=undo_callback,
        )

    def remove_target(self):
        indices = self._selected_listbox_indices(self.target_listbox, len(self.targets), "No target directories to remove.")
        if not indices:
            return
        removed = self._remove_directory_rows(self.targets, indices)
        self.refresh_target_list()
        self.save_config()
        self.load_quick_copy()

        def undo():
            self._restore_directory_rows(self.targets, removed)
            self.refresh_target_list()
            self._select_listbox_indices(self.target_listbox, [index for index, _value in removed])
            self.save_config()
            self.load_quick_copy()

        self._show_undo_toast("Target removed", self._directory_selection_label(removed), undo)

    def refresh_target_list(self):
        if hasattr(self, "target_listbox"):
            self._refresh_directory_listbox(self.target_listbox, self.targets, self.target_aliases)

    # --- Source Methods ---
    def add_source(self):
        directory = filedialog.askdirectory(title="Select Source Directory")
        if directory and directory not in self.sources:
            self.sources.append(directory)
            self.refresh_source_list()
            self.save_config()
            
    def drop_source(self, event):
        paths = self._parse_drop_data(event.data)
        for path in paths:
            if os.path.isdir(path) and path not in self.sources:
                self.sources.append(path)
        self.refresh_source_list()
        self.save_config()

    def remove_source(self):
        indices = self._selected_listbox_indices(self.source_listbox, len(self.sources), "No source directories to remove.")
        if not indices:
            return
        removed = self._remove_directory_rows(self.sources, indices)
        self.refresh_source_list()
        self.save_config()

        def undo():
            self._restore_directory_rows(self.sources, removed)
            self.refresh_source_list()
            self._select_listbox_indices(self.source_listbox, [index for index, _value in removed])
            self.save_config()

        self._show_undo_toast("Source removed", self._directory_selection_label(removed), undo)

    def move_source_up(self):
        if not self.sources or len(self.sources) < 2:
            self.show_toast("Move source", "Add at least two source directories first.", "info")
            return
        indices = self._selected_listbox_indices(self.source_listbox, len(self.sources), "No source directories to move.")
        if not indices:
            return
        if min(indices) == 0:
            self.show_toast("Move source", "Selected source is already first.", "info")
            return
        next_indices = self._move_selected_rows(self.sources, indices, -1)
        self.refresh_source_list()
        self._select_listbox_indices(self.source_listbox, next_indices)
        self.save_config()

    def move_source_down(self):
        if not self.sources or len(self.sources) < 2:
            self.show_toast("Move source", "Add at least two source directories first.", "info")
            return
        indices = self._selected_listbox_indices(self.source_listbox, len(self.sources), "No source directories to move.")
        if not indices:
            return
        if max(indices) >= len(self.sources) - 1:
            self.show_toast("Move source", "Selected source is already last.", "info")
            return
        next_indices = self._move_selected_rows(self.sources, indices, 1)
        self.refresh_source_list()
        self._select_listbox_indices(self.source_listbox, next_indices)
        self.save_config()

    def refresh_source_list(self):
        if hasattr(self, "source_listbox"):
            self._refresh_directory_listbox(self.source_listbox, self.sources)

    # --- Update Execution ---
    def run_full_update(self):
        if not self.targets:
            self.show_toast("Missing targets", "Add at least one target directory.", "warning")
            return
        if not self.sources:
            self.show_toast("Missing sources", "Add at least one source directory.", "warning")
            return

        self.update_now_btn.configure(state="disabled", text="Running...")
        self.status_label.configure(text="Updating skills and folders... Please wait.")
        
        thread = threading.Thread(target=self._run_full_update_thread, daemon=True)
        thread.start()

    def _run_full_update_thread(self):
        try:
            self._ui_queue.put(lambda: self.progress_bar.grid())
            
            # 1. Update all skill sources
            total_skills = len(self.skills)
            for idx, skill in enumerate(self.skills):
                self._ui_queue.put(lambda i=idx, s=skill: self.update_progress(i, total_skills + 1, f"Updating skill source '{s.get('name')}'..."))
                
                def progress(message):
                    display_line = message if len(message) < 80 else message[:77] + "..."
                    self._ui_queue.put(lambda l=display_line, i=idx: self.update_progress(i, total_skills + 1, f"Updating: {l}"))
                
                try:
                    self.skills[idx] = run_skill_source_update(skill, progress)
                except Exception as e:
                    print(f"Error updating skill source {skill.get('name')}: {e}")

            self.save_config()
            self._ui_queue.put(self.refresh_skill_ui)
            
            # 2. Update projects
            self._ui_queue.put(lambda: self.update_progress(total_skills, total_skills + 1, "Syncing project folders..."))
            
            def progress_cb(current, total, msg):
                sub_progress = (current / total) if total > 0 else 1.0
                self._ui_queue.put(lambda p=sub_progress: self.update_progress(total_skills + p, total_skills + 1, msg))

            result = update_projects(self.targets, self.sources, progress_callback=progress_cb)
            
            if result:
                updated_count, skipped_count = result
                msg = f"Sources updated. Folders updated: {updated_count}. Folders skipped: {skipped_count}."
                self._ui_queue.put(lambda: self.show_toast("Update complete", msg, "success"))
            else:
                self._ui_queue.put(lambda: self.show_toast("Update finished", "Sources updated, but no folders were synced.", "warning"))
        except Exception as e:
            self._ui_queue.put(lambda error=str(e): self.show_toast("Unexpected error", error, "error"))
        finally:
            self._ui_queue.put(self._restore_ui_state)

    def update_progress(self, current, total, text=""):
        if total > 0:
            self.progress_bar.set(current / total)
        else:
            self.progress_bar.set(1.0)
        self.status_label.configure(text=text)

    def _restore_ui_state(self):
        if hasattr(self, "update_now_btn"):
            self.update_now_btn.configure(state="normal", text="Update Now")
        self.status_label.configure(text="")
        self.progress_bar.grid_remove()

    # --- Skill Update Methods ---
    def add_skill(self):
        def on_save(data):
            self.skills.append(normalize_skill_source_config(data))
            self.save_config()
            self.refresh_skill_ui()
        SkillEditDialog(self, "Add Skill Source", callback=on_save)

    def edit_skill(self, idx):
        def on_save(data):
            data = normalize_skill_source_config(data)
            # preserve versions and timestamp
            data['current_version'] = self.skills[idx].get('current_version', 'Unknown')
            data['latest_version'] = self.skills[idx].get('latest_version', 'Unknown')
            data['last_updated'] = self.skills[idx].get('last_updated', '')
            self.skills[idx] = data
            self.save_config()
            self.refresh_skill_ui()
        SkillEditDialog(self, "Edit Skill Source", skill_data=self.skills[idx], callback=on_save)

    def remove_skill(self, idx):
        if not (0 <= idx < len(self.skills)):
            return
        removed = self.skills.pop(idx)
        self.save_config()
        self.refresh_skill_ui()

        def undo():
            self.skills.insert(min(idx, len(self.skills)), removed)
            self.save_config()
            self.refresh_skill_ui()

        self._show_undo_toast("Update source removed", removed.get("name", "Unnamed Source"), undo)

    def run_skill_update(self, idx):
        skill = self.skills[idx]
        
        def run_thread():
            try:
                self._ui_queue.put(lambda: self.progress_bar.grid())
                self._ui_queue.put(lambda: self.update_progress(0, 2, f"Starting update for '{skill.get('name')}'..."))

                def progress(message):
                    display_line = message if len(message) < 80 else message[:77] + "..."
                    self._ui_queue.put(lambda l=display_line: self.update_progress(1, 2, f"Updating: {l}"))

                self.skills[idx] = run_skill_source_update(skill, progress)
                sync_message = ""
                sync_error = ""
                try:
                    sync_message = self._sync_project_targets_after_skill_update(progress)
                except Exception as exc:
                    sync_error = str(exc)
                self._ui_queue.put(lambda: self.update_progress(2, 2, "Update complete."))
                self.save_config()
                self._ui_queue.put(self.refresh_skill_ui)
                if sync_error:
                    self._ui_queue.put(lambda error=sync_error: self.show_toast("Source updated, sync failed", error, "warning"))
                else:
                    message = f"Successfully updated '{skill.get('name')}'."
                    if sync_message:
                        message = f"{message} {sync_message}"
                    self._ui_queue.put(lambda m=message: self.show_toast("Source updated", m, "success"))
                
            except Exception as e:
                self._ui_queue.put(lambda error=str(e): self.show_toast("Update error", error, "error"))
            finally:
                self._ui_queue.put(self._restore_ui_state)

        thread = threading.Thread(target=run_thread, daemon=True)
        thread.start()

    def _sync_project_targets_after_skill_update(self, progress_callback=None):
        if not self.targets or not self.sources:
            return ""

        def progress(current, total, message):
            if progress_callback:
                progress_callback(f"Syncing project skills: {message}")

        result = update_projects(self.targets, self.sources, progress_callback=progress)
        if not result:
            return "No project targets synced."

        updated_count, skipped_count = result
        return f"Synced project folders: {updated_count} updated, {skipped_count} skipped."

    def check_all_skill_updates(self):
        def check_thread():
            try:
                total = len(self.skills)
                if total == 0:
                    return
                    
                self._ui_queue.put(lambda: self.progress_bar.grid())
                
                for idx, skill in enumerate(self.skills):
                    self._ui_queue.put(lambda i=idx, s=skill: self.update_progress(i, total, f"Checking versions for '{s.get('name')}'..."))
                    try:
                        self.skills[idx] = check_skill_source_versions(skill)
                    except Exception as e:
                        print(f"Error checking versions for {skill.get('name')}: {e}")
                        
                self._ui_queue.put(lambda: self.update_progress(total, total, "Version check complete."))
                self.save_config()
                self._ui_queue.put(self.refresh_skill_ui)
                self._ui_queue.put(self._restore_ui_state)
            except Exception as main_e:
                print(f"Critical error in check_thread: {main_e}")

        thread = threading.Thread(target=check_thread, daemon=True)
        thread.start()

    def create_quick_copy_tab(self, parent=None):
        tab = parent if parent else self.tabview.tab("Quick Copy")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(0, weight=1)

        # Main scrollable container for pills
        self.quick_copy_scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        self.quick_copy_scroll.grid(row=0, column=0, sticky="nsew")
        self.quick_copy_scroll.grid_columnconfigure(0, weight=1)

        # 2. Configuration Pill (Format & Actions)
        self.quick_copy_config_pill = GlassPill(self.quick_copy_scroll, height=60)
        self.quick_copy_config_pill.pack(fill="x", padx=15, pady=(15, 8))
        self.quick_copy_config_pill.grid_columnconfigure(2, weight=1)

        # Project Selector (Left)
        self.quick_copy_project_var = ctk.StringVar(value="No Projects")
        self.quick_copy_project_menu = ctk.CTkOptionMenu(
            self.quick_copy_config_pill,
            variable=self.quick_copy_project_var,
            values=["No Projects"],
            command=self._change_quick_copy_project,
            fg_color=GLASS_CONTROL,
            button_color=GLASS_CONTROL,
            button_hover_color=GLASS_CONTROL_HOVER,
            text_color=TEXT_MAIN,
            corner_radius=14,
            width=140
        )
        self.quick_copy_project_menu.grid(row=0, column=0, padx=(15, 5), pady=12, sticky="w")

        # Client Format Selector (Next to Project)
        self.quick_copy_client_var = ctk.StringVar(value=self.quick_copy_config.get("client_format", "Codex"))
        self.quick_copy_client_menu = ctk.CTkOptionMenu(
            self.quick_copy_config_pill,
            variable=self.quick_copy_client_var,
            values=["Codex", "Gemini CLI", "Antigravity", "Plain Path"],
            command=self._change_quick_copy_client,
            fg_color=GLASS_CONTROL,
            button_color=GLASS_CONTROL,
            button_hover_color=GLASS_CONTROL_HOVER,
            text_color=TEXT_MAIN,
            corner_radius=14,
            width=120
        )
        self.quick_copy_client_menu.grid(row=0, column=1, padx=5, pady=12, sticky="w")

        # Add Manuals Button (Next to Client)
        self.quick_copy_manual_add_btn = ctk.CTkButton(
            self.quick_copy_config_pill,
            text="Add Manuals",
            width=110,
            corner_radius=14,
            command=self.show_quick_copy_manual_composer,
        )
        self.quick_copy_manual_add_btn.grid(row=0, column=2, padx=5, pady=12, sticky="w")

        # Status Label
        self.quick_copy_status_label = ctk.CTkLabel(self.quick_copy_config_pill, text="Status: Ready", text_color=TEXT_MUTED)
        self.quick_copy_status_label.grid(row=0, column=3, padx=10, pady=12, sticky="w")

        action_frame = ctk.CTkFrame(self.quick_copy_config_pill, fg_color="transparent")
        action_frame.grid(row=0, column=4, padx=15, pady=12, sticky="e")

        self.quick_copy_selection_indicator = ctk.CTkLabel(
            action_frame,
            text="00/00 Selected",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=TEXT_MUTED
        )
        self.quick_copy_selection_indicator.pack(side="left", padx=(0, 10))

        self.quick_copy_copy_btn = ctk.CTkButton(
            action_frame, 
            text="\u23cd Copy", 
            width=80, 
            corner_radius=14, 
            command=self.copy_selected_project_skill_references
        )
        self.quick_copy_copy_btn.pack(side="left", padx=5)

        self.quick_copy_delete_btn = ctk.CTkButton(
            action_frame,
            text="\ud83d\uddd1",
            width=36,
            fg_color=GLASS_CONTROL,
            hover_color=GLASS_CONTROL_HOVER,
            corner_radius=14,
            text_color=CTK_STATUS_COLORS["error"],
            command=self.delete_selected_project_skills,
        )
        self.quick_copy_delete_btn.pack(side="left", padx=5)

        # Manual Composer (Internal to scroll area)
        self.quick_copy_manual_composer_frame = ctk.CTkFrame(
            self.quick_copy_scroll,
            fg_color=GLASS_BG_STRONG,
            border_width=1,
            border_color=GLASS_BORDER,
            corner_radius=16,
        )
        # Hidden by default, will use pack() when shown
        self.quick_copy_manual_composer_frame.grid_columnconfigure(0, weight=1)

        self.quick_copy_manual_var = ctk.StringVar(value="")
        self.quick_copy_manual_entry = ctk.CTkEntry(
            self.quick_copy_manual_composer_frame,
            textvariable=self.quick_copy_manual_var,
            placeholder_text="Add @caveman, skill name, path, or Markdown link.",
            fg_color=GLASS_SEARCH_BG,
            border_color=GLASS_SEARCH_BORDER,
            text_color=GLASS_SEARCH_TEXT,
            placeholder_text_color=GLASS_SEARCH_PLACEHOLDER,
            corner_radius=18,
            height=34,
        )
        self.quick_copy_manual_entry.grid(row=0, column=0, padx=(10, 8), pady=10, sticky="ew")
        self.quick_copy_manual_entry.bind("<Return>", lambda _event: self.add_quick_copy_manual_reference())

        self.quick_copy_manual_commit_btn = ctk.CTkButton(
            self.quick_copy_manual_composer_frame,
            text="Add",
            width=72,
            corner_radius=14,
            command=self.add_quick_copy_manual_reference,
        )
        self.quick_copy_manual_commit_btn.grid(row=0, column=1, padx=4, pady=10, sticky="e")

        self.quick_copy_manual_cancel_btn = ctk.CTkButton(
            self.quick_copy_manual_composer_frame,
            text="Done",
            width=72,
            fg_color=GLASS_CONTROL,
            hover_color=GLASS_CONTROL_HOVER,
            corner_radius=14,
            command=self.hide_quick_copy_manual_composer,
        )
        self.quick_copy_manual_cancel_btn.grid(row=0, column=2, padx=(4, 10), pady=10, sticky="e")
        self.quick_copy_manual_composer_frame.grid_remove()

        # 5. Skill List Pill
        self.quick_copy_list_pill = GlassPill(self.quick_copy_scroll)
        self.quick_copy_list_pill.pack(fill="both", expand=True, padx=15, pady=(8, 15))
        self.quick_copy_list_pill.grid_columnconfigure(0, weight=1)
        self.quick_copy_list_pill.grid_rowconfigure(1, weight=1)

        # List Header
        self.quick_copy_skills_header = ctk.CTkFrame(self.quick_copy_list_pill, fg_color="transparent")
        self.quick_copy_skills_header.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        self.quick_copy_skills_header.grid_columnconfigure(2, weight=1)

        self.quick_copy_refresh_btn = ctk.CTkButton(
            self.quick_copy_skills_header,
            text="\u21bb",
            width=36,
            height=34,
            font=("Segoe UI", 15, "bold"),
            fg_color=GLASS_CONTROL,
            hover_color=GLASS_CONTROL_HOVER,
            text_color=TEXT_MAIN,
            corner_radius=17,
            command=self.load_quick_copy
        )
        self.quick_copy_refresh_btn.grid(row=0, column=0, padx=(0, 4))

        # quick_copy_add_bundle_frame is no longer in the header directly, but will be in the dropdown
        self.quick_copy_add_bundle_frame = None 
        
        # The entry logic will be moved to the dropdown render method
        self.quick_copy_bundle_name_entry = None
        self._quick_copy_is_adding_bundle = False

        self.quick_copy_search_var = ctk.StringVar(value="")
        self.quick_copy_search_entry = ctk.CTkEntry(
            self.quick_copy_skills_header,
            textvariable=self.quick_copy_search_var,
            placeholder_text="Ask skills...",
            fg_color=GLASS_SEARCH_BG,
            border_color=GLASS_SEARCH_BORDER,
            text_color=GLASS_SEARCH_TEXT,
            placeholder_text_color=GLASS_SEARCH_PLACEHOLDER,
            corner_radius=18,
            width=240,
            height=34
        )
        self.quick_copy_search_entry.grid(row=0, column=1, padx=4, sticky="w")
        self.quick_copy_search_var.trace_add("write", lambda *args: self._schedule_quick_copy_filter())

        # Disclosure button for bulk actions/details
        self.quick_copy_disclosure_btn = ctk.CTkButton(
            self.quick_copy_skills_header,
            text=DISCLOSURE_EXPAND_ICON,
            width=36,
            height=34,
            fg_color=GLASS_CONTROL,
            hover_color=GLASS_CONTROL_HOVER,
            text_color=TEXT_MAIN,
            corner_radius=17,
            command=self.toggle_all_quick_copy_categories
        )
        self.quick_copy_disclosure_btn.grid(row=0, column=3, padx=4)

        self.quick_copy_select_visible_var = ctk.BooleanVar(value=False)
        self.quick_copy_select_visible_check = ctk.CTkCheckBox(
            self.quick_copy_skills_header,
            variable=self.quick_copy_select_visible_var,
            text="",
            width=24,
            height=24,
            corner_radius=6,
            command=self._toggle_quick_copy_select_visible_from_check
        )
        self.quick_copy_select_visible_check.grid(row=0, column=4, padx=4)

        # Flexible Spacer
        self.quick_copy_skills_header.grid_columnconfigure(5, weight=1)

        self.quick_copy_category_var = ctk.StringVar(value="All Categories")
        self.quick_copy_category_menu = ctk.CTkOptionMenu(
            self.quick_copy_skills_header,
            variable=self.quick_copy_category_var,
            values=["All Categories"] + SKILL_CATEGORY_NAMES,
            command=lambda _: self._apply_quick_copy_filters(),
            fg_color=GLASS_CONTROL,
            button_color=GLASS_CONTROL,
            button_hover_color=GLASS_CONTROL_HOVER,
            text_color=TEXT_MAIN,
            corner_radius=17,
            width=140
        )
        self.quick_copy_category_menu.grid(row=0, column=6, padx=8, sticky="w")

        self.quick_copy_set_var = ctk.StringVar(value="No Bundle Selected")
        self.quick_copy_set_menu = ctk.CTkButton(
            self.quick_copy_skills_header,
            text=f"{self.quick_copy_set_var.get()}  \u25be",
            command=self._toggle_quick_copy_bundle_dropdown,
            fg_color=GLASS_CONTROL,
            hover_color=GLASS_CONTROL_HOVER,
            text_color=TEXT_MAIN,
            corner_radius=17,
            width=160,
            height=34
        )
        self.quick_copy_set_menu.grid(row=0, column=7, padx=8, sticky="w")


        # Bundle Dropdown Frame (Overlay)
        self.quick_copy_bundle_dropdown_frame = ctk.CTkFrame(
            self,
            fg_color=POPOVER_BG,
            border_width=1,
            border_color=GLASS_BORDER,
            corner_radius=12
        )
        # Positioned via place() when toggled
        self.quick_copy_bundle_dropdown_frame.grid_columnconfigure(0, weight=1)
        self.quick_copy_bundle_dropdown_frame.grid_columnconfigure(0, weight=1)

        # Spacer
        self.quick_copy_skills_header.grid_columnconfigure(7, weight=1)

        # Treeview in Skill List Pill
        tree_container = ctk.CTkFrame(self.quick_copy_list_pill, fg_color="transparent")
        tree_container.grid(row=1, column=0, sticky="nsew", padx=10, pady=(5, 10))
        tree_container.grid_columnconfigure(0, weight=1)
        tree_container.grid_rowconfigure(0, weight=1)

        self.quick_copy_tree = ttk.Treeview(
            tree_container,
            columns=("summary",),
            show="tree headings",
            selectmode="extended",
            style="LiquidGlass.Treeview"
        )
        self.quick_copy_tree.heading("#0", text="Project / Category / Skill", anchor="w")
        self.quick_copy_tree.heading("summary", text="Summary", anchor="w")
        self.quick_copy_tree.column("#0", width=350, minwidth=200)
        self.quick_copy_tree.column("summary", width=400, minwidth=200)
        self.quick_copy_tree.grid(row=0, column=0, sticky="nsew")

        scrollbar = ctk.CTkScrollbar(tree_container, orientation="vertical", command=self.quick_copy_tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.quick_copy_tree.configure(yscrollcommand=scrollbar.set)

        self.quick_copy_tree.bind("<ButtonRelease-1>", self._toggle_quick_copy_skill_from_click)
        self.quick_copy_tree.bind("<Double-Button-1>", self._show_skill_detail_in_inspector_from_quick_copy)
        self.quick_copy_tree.bind("<Return>", self._show_skill_detail_in_inspector_from_quick_copy)

        # Pre-Redesign variables cleanup/mapping
        self.quick_copy_header_frame = tab # Map legacy reference if any
        self._refresh_quick_copy_manual_label()
        self._refresh_quick_copy_set_details()
        self._create_inspector_ui(self.quick_copy_list_pill, "quick_copy")

    def create_library_tab(self, parent=None):
        tab = parent if parent else self.tabview.tab("Library")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(0, weight=1)

        # Main scrollable container for pills
        self.library_scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        self.library_scroll.grid(row=0, column=0, sticky="nsew")
        self.library_scroll.grid_columnconfigure(0, weight=1)

        # 1. Toolbar Pill (Search & Filter)
        self.library_toolbar_pill = GlassPill(self.library_scroll, height=60)
        self.library_toolbar_pill.pack(fill="x", padx=15, pady=(15, 8))
        self.library_toolbar_pill.grid_columnconfigure(3, weight=1)

        self.library_refresh_btn = ctk.CTkButton(
            self.library_toolbar_pill,
            text="\u21bb",
            width=36,
            height=34,
            font=("Segoe UI", 15, "bold"),
            fg_color=GLASS_CONTROL,
            hover_color=GLASS_CONTROL_HOVER,
            text_color=TEXT_MAIN,
            corner_radius=10,
            command=self.load_skill_library
        )
        self.library_refresh_btn.grid(row=0, column=0, padx=(15, 8), pady=12)

        self.library_search_var = ctk.StringVar(value="")
        self.library_search_entry = ctk.CTkEntry(
            self.library_toolbar_pill,
            textvariable=self.library_search_var,
            placeholder_text="Ask skills...",
            fg_color=GLASS_SEARCH_BG,
            border_color=GLASS_SEARCH_BORDER,
            text_color=GLASS_SEARCH_TEXT,
            placeholder_text_color=GLASS_SEARCH_PLACEHOLDER,
            corner_radius=12,
            width=200,
            height=34
        )
        self.library_search_entry.grid(row=0, column=1, padx=4, pady=12)
        self.library_search_entry.bind("<KeyRelease>", self._schedule_skill_library_filter)

        self.library_category_var = ctk.StringVar(value="All Categories")
        self.library_category_menu = ctk.CTkOptionMenu(
            self.library_toolbar_pill,
            variable=self.library_category_var,
            values=["All Categories"],
            command=lambda _: self._apply_skill_library_filters(),
            fg_color=GLASS_CONTROL,
            button_color=GLASS_CONTROL,
            button_hover_color=GLASS_CONTROL_HOVER,
            text_color=TEXT_MAIN,
            corner_radius=12,
            width=140
        )
        self.library_category_menu.grid(row=0, column=2, padx=8, pady=12, sticky="w")

        self.library_show_archived_var = tk.BooleanVar(value=False)
        self.library_show_archived_check = ctk.CTkCheckBox(
            self.library_toolbar_pill,
            text="Show Archived",
            variable=self.library_show_archived_var,
            command=self._apply_skill_library_filters,
            checkbox_width=18,
            checkbox_height=18,
            corner_radius=6,
            border_width=2,
            fg_color=CTK_STATUS_COLORS["info"],
            hover_color=CTK_STATUS_COLORS["info"],
            border_color=GLASS_BORDER,
            text_color=TEXT_MAIN,
        )
        self.library_show_archived_check.grid(row=0, column=4, padx=15, pady=12, sticky="e")

        # 2. Action Pill (Bulk Operations)
        self.library_action_pill = GlassPill(self.library_scroll, height=60)
        self.library_action_pill.pack(fill="x", padx=15, pady=8)
        self.library_action_pill.grid_columnconfigure(0, weight=1)

        self.library_status_label = ctk.CTkLabel(self.library_action_pill, text="", text_color=TEXT_MUTED)
        self.library_status_label.grid(row=0, column=0, padx=15, pady=12, sticky="w")

        action_frame = ctk.CTkFrame(self.library_action_pill, fg_color="transparent")
        action_frame.grid(row=0, column=1, padx=15, pady=12, sticky="e")

        self.library_copy_to_projects_btn = ctk.CTkButton(
            action_frame,
            text="Copy to Projects",
            width=125,
            corner_radius=14,
            command=self.copy_selected_skill_folders_to_projects
        )
        self.library_copy_to_projects_btn.pack(side="left", padx=5)

        # 3. Skill List Pill
        self.library_list_pill = GlassPill(self.library_scroll)
        self.library_list_pill.pack(fill="both", expand=True, padx=15, pady=(8, 15))
        self.library_list_pill.grid_columnconfigure(0, weight=1)
        self.library_list_pill.grid_rowconfigure(1, weight=1)

        # List Header (internal)
        list_header = ctk.CTkFrame(self.library_list_pill, fg_color="transparent")
        list_header.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        list_header.grid_columnconfigure(0, weight=1)

        self.library_selected_count_label = ctk.CTkLabel(list_header, text="0 selected", text_color=TEXT_MUTED)
        self.library_selected_count_label.grid(row=0, column=0, padx=10, sticky="w")

        self.library_disclosure_btn = ctk.CTkButton(
            list_header,
            text=DISCLOSURE_EXPAND_ICON,
            width=36,
            height=34,
            font=("Segoe UI", 15, "bold"),
            fg_color=GLASS_CONTROL,
            hover_color=GLASS_CONTROL_HOVER,
            text_color=TEXT_MAIN,
            corner_radius=10,
            command=self.toggle_all_library_categories
        )
        self.library_disclosure_btn.grid(row=0, column=1, padx=5)

        self.library_select_visible_var = tk.BooleanVar(value=False)
        self.library_select_visible_check = ctk.CTkCheckBox(
            list_header,
            text="Select visible",
            variable=self.library_select_visible_var,
            command=self._toggle_library_select_visible_from_check,
            checkbox_width=18,
            checkbox_height=18,
            corner_radius=6,
            border_width=2,
            fg_color=CTK_STATUS_COLORS["info"],
            hover_color=CTK_STATUS_COLORS["info"],
            border_color=GLASS_BORDER,
            text_color=TEXT_MAIN,
        )
        self.library_select_visible_check.grid(row=0, column=2, padx=10)

        # Treeview in Skill List Pill
        tree_container = ctk.CTkFrame(self.library_list_pill, fg_color="transparent")
        tree_container.grid(row=1, column=0, sticky="nsew", padx=10, pady=(5, 10))
        tree_container.grid_columnconfigure(0, weight=1)
        tree_container.grid_rowconfigure(0, weight=1)

        self._configure_library_tree_style()
        self.library_tree = ttk.Treeview(
            tree_container,
            columns=("description",),
            show="tree headings",
            selectmode="extended",
            style="LiquidGlass.Treeview"
        )
        self.library_tree.heading("#0", text="Category / Skill", anchor="w")
        self.library_tree.heading("description", text="Summary", anchor="w")
        self.library_tree.column("#0", width=350, minwidth=200)
        self.library_tree.column("description", width=400, minwidth=200)
        self.library_tree.grid(row=0, column=0, sticky="nsew")

        scrollbar = ctk.CTkScrollbar(tree_container, orientation="vertical", command=self.library_tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.library_tree.configure(yscrollcommand=scrollbar.set)

        self.library_tree.bind("<ButtonRelease-1>", self._toggle_library_skill_from_click)
        self.library_tree.bind("<Double-Button-1>", self._show_skill_detail_in_inspector_from_library)
        self.library_tree.bind("<Return>", self._show_skill_detail_in_inspector_from_library)

        # Pre-Redesign variables cleanup/mapping
        self.library_header_frame = tab
        self.after(150, self.load_skill_library)
        self._create_inspector_ui(self.library_list_pill, "library")

    def _create_inspector_ui(self, parent, prefix):
        inspector_frame = ctk.CTkFrame(
            parent,
            fg_color=GLASS_BG_STRONG,
            border_width=1,
            border_color=GLASS_BORDER,
            corner_radius=16,
        )
        inspector_frame.grid(row=0, column=2, sticky="nsew", padx=(0, 8), pady=8)
        inspector_frame.grid_remove()
        parent.grid_columnconfigure(2, weight=0)
        inspector_frame.grid_columnconfigure(0, weight=1)
        inspector_frame.grid_rowconfigure(3, weight=1)

        header = ctk.CTkFrame(inspector_frame, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 6))
        header.grid_columnconfigure(1, weight=1)

        back_btn = ctk.CTkButton(
            header,
            text="Back",
            width=64,
            fg_color=GLASS_CONTROL,
            hover_color=GLASS_CONTROL_HOVER,
            corner_radius=14,
            command=lambda active_prefix=prefix: self._hide_skill_detail_in_inspector(active_prefix),
        )

        title = ctk.CTkLabel(header, text="Skill Details", text_color=TEXT_MAIN, font=("Segoe UI", 14, "bold"), anchor="w")
        title.grid(row=0, column=1, sticky="ew")

        meta = ctk.CTkLabel(
            inspector_frame,
            text="No skill open.",
            text_color=TEXT_MUTED,
            anchor="w",
            justify="left",
            wraplength=300,
        )
        meta.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 10))

        argument_var = None
        argument_entry = None
        if prefix == "quick_copy":
            arg_frame = ctk.CTkFrame(inspector_frame, fg_color="transparent")
            arg_frame.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 10))
            arg_frame.grid_columnconfigure(1, weight=1)

            ctk.CTkLabel(
                arg_frame, 
                text="Argument:", 
                text_color=TEXT_MUTED, 
                font=("Segoe UI", 11, "bold"),
                anchor="w"
            ).grid(row=0, column=0, padx=(0, 8), sticky="w")

            argument_var = ctk.StringVar(value="")
            argument_entry = ctk.CTkEntry(
                arg_frame,
                textvariable=argument_var,
                placeholder_text="e.g. ultra",
                height=28,
                corner_radius=8,
                fg_color=GLASS_SEARCH_BG,
                border_color=GLASS_SEARCH_BORDER,
                text_color=GLASS_SEARCH_TEXT,
                border_width=1
            )
            argument_entry.grid(row=0, column=1, sticky="ew")

            def _on_arg_change(*_args):
                skill = getattr(self, "_current_inspector_skill", None)
                if skill and getattr(self, "_current_inspector_prefix", None) == "quick_copy":
                    self._set_quick_copy_skill_argument(skill, argument_var.get().strip())

            trace_id = argument_var.trace_add("write", _on_arg_change)
            setattr(self, f"{prefix}_arg_trace_id", trace_id)

            inspector_frame.grid_rowconfigure(3, weight=0)
            inspector_frame.grid_rowconfigure(4, weight=1)
        else:
            inspector_frame.grid_rowconfigure(3, weight=1)

        content_label = ctk.CTkLabel(
            inspector_frame,
            text="Full Content",
            text_color=TEXT_MUTED,
            font=("Segoe UI", 11, "bold"),
            anchor="w",
        )
        content_label.grid(row=2 if prefix != "quick_copy" else 3, column=0, sticky="ew", padx=12, pady=(0, 6))
        content_label.grid_remove()

        description = ctk.CTkTextbox(inspector_frame, wrap="word", border_width=0)
        description.grid(row=3 if prefix != "quick_copy" else 4, column=0, sticky="nsew", padx=12, pady=(0, 8))
        description.insert("1.0", "Double-click a skill to open it here.")
        description.configure(state="disabled")

        footer = ctk.CTkFrame(inspector_frame, fg_color="transparent")
        footer.grid_columnconfigure(0, weight=1)
        category_var = ctk.StringVar(value="Uncategorized")
        category_menu = ctk.CTkOptionMenu(
            footer,
            variable=category_var,
            values=self._skill_category_options(),
            width=190,
            fg_color=GLASS_CONTROL,
            button_color=GLASS_CONTROL,
            button_hover_color=GLASS_CONTROL_HOVER,
            text_color=TEXT_MAIN,
            corner_radius=14,
        )
        category_menu.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        apply_category_btn = ctk.CTkButton(
            footer,
            text="Apply",
            width=72,
            fg_color=CTK_STATUS_COLORS["info"],
            hover_color=CTK_STATUS_COLORS["info_hover"],
            corner_radius=14,
            command=lambda active_prefix=prefix: self._apply_current_inspector_category(active_prefix),
        )
        apply_category_btn.grid(row=0, column=1, sticky="e")

        essentials_btn = None
        archive_btn = None
        if prefix == "quick_copy":
            essentials_btn = ctk.CTkButton(
                footer,
                text="Add to Essentials",
                width=180,
                fg_color=GLASS_CONTROL,
                hover_color=GLASS_CONTROL_HOVER,
                corner_radius=14,
                command=self.toggle_current_inspector_essential,
            )
            essentials_btn.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        elif prefix == "library":
            archive_btn = ctk.CTkButton(
                footer,
                text="Archive",
                width=180,
                fg_color=GLASS_CONTROL,
                hover_color=GLASS_CONTROL_HOVER,
                text_color=TEXT_MAIN,
                corner_radius=14,
                state="disabled",
                command=self.toggle_current_inspector_archive,
            )
            archive_btn.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))

        # IMPORTANT: Footer placement was missing
        footer.grid(row=4 if prefix != "quick_copy" else 5, column=0, sticky="ew", padx=12, pady=(0, 12))

        setattr(self, f"{prefix}_inspector_frame", inspector_frame)
        setattr(self, f"{prefix}_inspector_parent", parent)
        setattr(self, f"{prefix}_inspector_title", title)
        setattr(self, f"{prefix}_inspector_meta", meta)
        setattr(self, f"{prefix}_inspector_content_label", content_label)
        setattr(self, f"{prefix}_inspector_description", description)
        setattr(self, f"{prefix}_inspector_back_btn", back_btn)
        setattr(self, f"{prefix}_inspector_footer", footer)
        setattr(self, f"{prefix}_inspector_category_var", category_var)
        setattr(self, f"{prefix}_inspector_category_menu", category_menu)
        setattr(self, f"{prefix}_inspector_apply_category_btn", apply_category_btn)
        setattr(self, f"{prefix}_inspector_essentials_btn", essentials_btn)
        setattr(self, f"{prefix}_inspector_archive_btn", archive_btn)
        setattr(self, f"{prefix}_inspector_argument_var", argument_var)
        setattr(self, f"{prefix}_inspector_argument_entry", argument_entry)

    def _update_dynamic_theme(self):
        """Updates ttk styles and treeview tags based on current appearance mode."""
        # Use the configured appearance mode
        apply_theme(self.appearance_mode)

        # Determine actual mode for ttk (since it doesn't support "System")
        actual_mode = self.appearance_mode.lower()
        if actual_mode == "system":
            try:
                import darkdetect
                sys_theme = darkdetect.theme()
                actual_mode = sys_theme.lower() if sys_theme else ctk.get_appearance_mode().lower()
            except Exception:
                actual_mode = ctk.get_appearance_mode().lower()
        elif actual_mode not in ("light", "dark"):
            actual_mode = ctk.get_appearance_mode().lower()

        # Refresh all module constants in styles.py
        StyleManager.refresh_constants(actual_mode, self.high_contrast, self.reduced_transparency)

        # Update local globals in app.py with refreshed values from styles module
        g = globals()
        for k in [
            "TK_BG_SURFACE", "TK_BG_SURFACE_SOFT", "TK_TEXT_MAIN", "TK_TEXT_MUTED",
            "TK_BORDER_SOFT", "TK_TREE_CATEGORY_TEXT", "TK_TREE_PROJECT_TEXT",
            "TK_TREE_SKILL_TEXT", "TK_TREE_ESSENTIAL_TEXT", "TK_TREE_ARCHIVED_TEXT",
            "TK_ROW_SELECTED_BG", "POPOVER_BG", "POPOVER_TEXT", "POPOVER_MUTED_TEXT",
            "BG_SURFACE", "BG_SURFACE_SOFT", "TEXT_MAIN", "TEXT_MUTED", "BORDER_SOFT",
            "ROW_SELECTED_BG", "SKILL_BLUE", "SKILL_BLUE_DEEP", "STATUS_COLORS",
            "TREE_CATEGORY_TEXT", "TREE_PROJECT_TEXT", "TREE_SKILL_TEXT",
            "TREE_ESSENTIAL_TEXT", "TREE_ARCHIVED_TEXT"
        ]:
            if hasattr(styles, k):
                g[k] = getattr(styles, k)

        # Update main app window background
        self.configure(fg_color=styles.CTK_COLORS["window_bg"])

        tokens = StyleManager.get_tree_style_tokens(
            appearance=actual_mode,
            high_contrast=self.high_contrast,
            reduced_transparency=self.reduced_transparency
        )

        style = ttk.Style()
        # Ensure we are using the 'default' theme as a base for our customizations
        if style.theme_use() != "default":
            style.theme_use("default")

        style.configure(
            "LiquidGlass.Treeview",
            background=tokens["background"],
            foreground=tokens["foreground"],
            fieldbackground=tokens["fieldbackground"],
            borderwidth=0,
            rowheight=32
        )
        style.configure(
            "LiquidGlass.Treeview.Heading",
            background=tokens["heading_background"],
            foreground=tokens["heading_foreground"],
            relief="flat",
            font=("Segoe UI", 10, "bold")
        )
        # Fix for selection background
        style.map(
            "LiquidGlass.Treeview",
            background=[("selected", tokens["selected_background"])],
            foreground=[("selected", tokens["foreground"])]
        )

        # Update tags for all trees
        for tree_attr in ["library_tree", "quick_copy_skills_tree", "quick_copy_tree"]:
            tree = getattr(self, tree_attr, None)
            if tree and tree.winfo_exists():
                tree.tag_configure("project", foreground=tokens["project_foreground"])
                tree.tag_configure("category", foreground=tokens["category_foreground"])
                tree.tag_configure("skill", foreground=tokens["skill_foreground"])
                tree.tag_configure("essential", foreground=tokens["essential_foreground"])
                tree.tag_configure("archived", foreground=tokens["archived_foreground"])
                tree.tag_configure("selected_skill", background=tokens["selected_background"])

        # Update Listboxes
        for listbox_attr in ["source_listbox", "target_listbox"]:
            listbox = getattr(self, listbox_attr, None)
            if listbox and listbox.winfo_exists():
                listbox.configure(
                    background=tokens["background"],
                    foreground=tokens["foreground"],
                    disabledforeground=tokens["disabled_foreground"],
                    highlightcolor=STATUS_COLORS["info"],
                    selectbackground=STATUS_COLORS["info"]
                )

        # Refresh listbox items to apply colors to existing special rows (like empty state)
        if getattr(self, "source_listbox", None):
            self.refresh_source_list()
        if getattr(self, "target_listbox", None):
            self.refresh_target_list()
    def _configure_library_tree_style(self):
        # This is now handled by _update_dynamic_theme
        self._update_dynamic_theme()

    def load_quick_copy(self):
        if self._quick_copy_search_after_id is not None:
            self.after_cancel(self._quick_copy_search_after_id)
            self._quick_copy_search_after_id = None

        self._clear_quick_copy_tree()
        self._set_quick_copy_controls("disabled")
        self.quick_copy_category_menu.configure(values=["All Categories"])
        self.quick_copy_status_label.configure(text="Scanning configured projects...")
        self.quick_copy_tree.insert("", "end", text="Scanning project skills...", values=("",), tags=("project",), open=True)

        self._quick_copy_result_queue = queue.Queue(maxsize=1)
        thread = threading.Thread(target=self._load_quick_copy_thread, daemon=True)
        thread.start()
        self.after(50, self._poll_quick_copy_result)

    def _load_quick_copy_thread(self):
        try:
            projects = discover_project_skills(
                self.targets,
                self._parse_skill_md,
                self.categorize_skill,
                self._build_skill_search_text,
                target_aliases=self.target_aliases,
            )
            self._quick_copy_result_queue.put(("success", projects))
        except Exception as exc:
            self._quick_copy_result_queue.put(("error", exc))

    def _poll_quick_copy_result(self):
        if self._quick_copy_result_queue is None:
            return

        try:
            status, payload = self._quick_copy_result_queue.get_nowait()
        except queue.Empty:
            self.after(50, self._poll_quick_copy_result)
            return

        self._quick_copy_result_queue = None
        if status == "success":
            self._render_quick_copy(payload)
        else:
            self._show_quick_copy_error(payload)

    def _render_quick_copy(self, projects):
        self._clear_quick_copy_tree()
        self.quick_copy_projects = projects
        self.filtered_quick_copy_projects = projects
        self._set_quick_copy_controls("normal")

        self._refresh_quick_copy_project_menu(projects)
        self._load_quick_copy_manual_references_for_current_project()
        self._migrate_legacy_quick_copy_manual_references()
        self._load_quick_copy_essentials_for_current_project()
        self._migrate_legacy_quick_copy_essentials()

        categories = ["All Categories"] + sorted({
            self._quick_copy_display_category(skill)
            for skill in self._quick_copy_skills_for_current_project()
        }, key=self._quick_copy_category_sort_key)
        self.quick_copy_category_menu.configure(values=categories)
        if self.quick_copy_category_var.get() not in categories:
            self.quick_copy_category_var.set("All Categories")
        self._load_quick_copy_selection_for_current_project()
        self._update_quick_copy_essentials_label()

        if not projects:
            self.quick_copy_status_label.configure(text="No available project skills found.")
            self.quick_copy_tree.insert(
                "",
                "end",
                text="No configured project target contains skill folders with SKILL.md.",
                values=("",),
                tags=("project",),
                open=True,
            )
            self._update_quick_copy_selected_count()
            return

        self._apply_quick_copy_filters()

    def _set_quick_copy_controls(self, state):
        for widget_name in (
            "quick_copy_refresh_btn",
            "quick_copy_search_entry",
            "quick_copy_category_menu",
            "quick_copy_project_menu",
            "quick_copy_client_menu",
            "quick_copy_clear_btn",
            "quick_copy_copy_btn",
            "quick_copy_delete_btn",
            "quick_copy_set_menu",
            "quick_copy_save_set_btn",
            "quick_copy_edit_set_btn",
            "quick_copy_delete_set_btn",
            "quick_copy_manual_add_btn",
            "quick_copy_manual_entry",
            "quick_copy_manual_commit_btn",
            "quick_copy_manual_cancel_btn",
            "quick_copy_inspector_essentials_btn",
        ):
            widget = getattr(self, widget_name, None)
            if widget is not None:
                widget.configure(state=state)

    def show_quick_copy_manual_composer(self):
        composer = getattr(self, "quick_copy_manual_composer_frame", None)
        if composer is None:
            return
        
        # Reposition composer before the skill list pill using pack
        # By default, packing without 'after' or 'before' puts it at the end.
        # Since we want it between the config bar and the list, we forget the list, pack composer, then repack list.
        if hasattr(self, "quick_copy_list_pill"):
            self.quick_copy_list_pill.pack_forget()
            
        composer.pack(fill="x", padx=15, pady=8)
        
        if hasattr(self, "quick_copy_list_pill"):
            self.quick_copy_list_pill.pack(fill="both", expand=True, padx=15, pady=(8, 15))

        try:
            self.quick_copy_manual_entry.focus_set()
        except tk.TclError:
            pass

    def hide_quick_copy_manual_composer(self):
        composer = getattr(self, "quick_copy_manual_composer_frame", None)
        if composer is not None:
            composer.pack_forget()

    def _show_quick_copy_error(self, error):
        self._set_quick_copy_controls("normal")
        self.quick_copy_status_label.configure(text="Failed to scan project skills.")
        self._clear_quick_copy_tree()
        self.quick_copy_tree.insert("", "end", text=f"Failed to scan project skills: {error}", values=("",), tags=("project",), open=True)

    def _schedule_quick_copy_filter(self, _event=None):
        if self._quick_copy_search_after_id is not None:
            self.after_cancel(self._quick_copy_search_after_id)
        self._quick_copy_search_after_id = self.after(200, self._apply_quick_copy_filters)

    def _apply_quick_copy_filters(self):
        self._quick_copy_search_after_id = None
        query = self.quick_copy_search_var.get().strip().lower()
        category = self.quick_copy_category_var.get()
        selected_project_key = self._current_quick_copy_project_key()

        filtered_projects = []
        for project in self.quick_copy_projects:
            if selected_project_key and project.get("project_key") != selected_project_key:
                continue
            filtered_skills = []
            for skill in project.get("skills", []):
                display_category = self._quick_copy_display_category(skill)
                if category != "All Categories" and display_category != category:
                    continue
                searchable = " ".join([
                    skill.get("search_text", ""),
                    skill.get("project_label", ""),
                    skill.get("target_path", ""),
                    display_category,
                ]).lower()
                if query and query not in searchable:
                    continue
                filtered_skills.append(skill)

            if filtered_skills:
                next_project = dict(project)
                next_project["skills"] = sorted(
                    filtered_skills,
                    key=lambda item: (
                        self._quick_copy_category_sort_key(self._quick_copy_display_category(item)),
                        item.get("name", "").lower(),
                    ),
                )
                filtered_projects.append(next_project)

        self.filtered_quick_copy_projects = filtered_projects
        
        # Use all manual references if in cross-project mode, otherwise just current project's
        manual_source = self._all_quick_copy_manual_skills() if not selected_project_key else self._quick_copy_manual_skills()
        
        self.filtered_quick_copy_manual_skills = sorted([
            skill for skill in manual_source
            if self._quick_copy_skill_matches_filter(skill, query, category)
        ], key=lambda item: (
            self._quick_copy_category_sort_key(self._quick_copy_display_category(item)),
            item.get("name", "").lower(),
        ))
        self._render_quick_copy_tree()

    def _quick_copy_skill_matches_filter(self, skill, query, category):
        display_category = self._quick_copy_display_category(skill)
        if category != "All Categories" and display_category != category:
            return False
        searchable = " ".join([
            skill.get("search_text", ""),
            skill.get("project_label", ""),
            skill.get("target_path", ""),
            display_category,
        ]).lower()
        return not query or query in searchable

    def _quick_copy_category_groups(self, skills):
        grouped = {}
        for skill in sorted(
            skills,
            key=lambda item: (
                self._quick_copy_category_sort_key(self._quick_copy_display_category(item)),
                item.get("name", "").lower(),
            ),
        ):
            grouped.setdefault(self._quick_copy_display_category(skill), []).append(skill)
        return [
            (category, grouped[category])
            for category in sorted(grouped, key=self._quick_copy_category_sort_key)
        ]

    def _render_quick_copy_tree(self):
        # Cancel any existing rendering operation
        if hasattr(self, "_quick_copy_render_after_id") and self._quick_copy_render_after_id:
            try:
                self.after_cancel(self._quick_copy_render_after_id)
            except tk.TclError:
                pass
            self._quick_copy_render_after_id = None

        self._clear_quick_copy_tree()
        self._prune_quick_copy_selected_keys()

        if not self.filtered_quick_copy_projects and not self.filtered_quick_copy_manual_skills:
            self.quick_copy_status_label.configure(text="")
            self.quick_copy_tree.insert("", "end", text="No matching project skills or manuals.", values=("",), tags=("project",), open=True)
            self._sync_quick_copy_disclosure_button()
            self._update_quick_copy_selected_count()
            return

        # Group manual skills by project for consistent rendering
        manuals_by_project = {}
        for skill in self.filtered_quick_copy_manual_skills:
            p_key = skill.get("project_key", "")
            if p_key not in manuals_by_project:
                manuals_by_project[p_key] = []
            manuals_by_project[p_key].append(skill)

        # Collect all render tasks
        tasks = []
        rendered_project_keys = set()
        
        # 1. Projects from filtered_quick_copy_projects
        for project in self.filtered_quick_copy_projects:
            project_key = project.get("project_key")
            rendered_project_keys.add(project_key)
            project_skills = list(project.get("skills", []))
            project_manuals = manuals_by_project.get(project_key, [])
            combined_skills = project_skills + project_manuals
            
            if combined_skills:
                tasks.append(("project", (project, combined_skills)))

        # 2. Projects that ONLY have manual skills
        for project_key, project_manuals in manuals_by_project.items():
            if project_key in rendered_project_keys:
                continue
            
            virtual_project = {
                "project_key": project_key,
                "project_label": project_manuals[0].get("project_label", project_key),
                "target_path": "Manual references only",
                "skills": []
            }
            tasks.append(("project", (virtual_project, project_manuals)))

        self._run_quick_copy_render_batch(tasks)

    def _run_quick_copy_render_batch(self, tasks, batch_size=60):
        if not tasks:
            self._quick_copy_render_after_id = None
            self.quick_copy_status_label.configure(text="")
            self._sync_quick_copy_disclosure_button()
            self._update_quick_copy_selected_count()
            return

        batch = tasks[:batch_size]
        remaining = tasks[batch_size:]

        for task_type, data in batch:
            if task_type == "project":
                project, combined_skills = data
                for category, category_skills in self._quick_copy_category_groups(combined_skills):
                    category_tags = ("category", "manual") if all(skill.get("is_manual") for skill in category_skills) else ("category",)
                    category_id = self.quick_copy_tree.insert(
                        "",
                        "end",
                        text=f"{category} ({len(category_skills)})",
                        values=("",),
                        tags=category_tags,
                        open=True,
                    )
                    self.quick_copy_tree_categories[category_id] = {"project": project, "category": category}
                    for skill in category_skills:
                        self._insert_quick_copy_skill(category_id, skill)

        self._quick_copy_render_after_id = self.after(5, lambda: self._run_quick_copy_render_batch(remaining))

    def _render_project_node(self, project, combined_skills):
        if not combined_skills:
            return

        for category, category_skills in self._quick_copy_category_groups(combined_skills):
            category_tags = ("category", "manual") if all(skill.get("is_manual") for skill in category_skills) else ("category",)
            category_id = self.quick_copy_tree.insert(
                "",
                "end",
                text=f"{category} ({len(category_skills)})",
                values=("",),
                tags=category_tags,
                open=True,
            )
            self.quick_copy_tree_categories[category_id] = {"project": project, "category": category}
            for skill in category_skills:
                self._insert_quick_copy_skill(category_id, skill)

    def _insert_quick_copy_skill(self, parent_id, skill):
        desc_text = self._row_description_summary(skill.get("description"))
        selected = self._quick_copy_skill_key(skill) in self.quick_copy_selected_skill_keys
        essential = self._is_quick_copy_skill_essential(skill)
        label = skill.get("name", "Unknown")
            
        tags = ["skill"]
        if skill.get("is_manual"):
            tags.append("manual")
        if essential:
            tags.append("essential")
        if selected:
            tags.append("selected_skill")

        item_id = self.quick_copy_tree.insert(
            parent_id,
            "end",
            text=label,
            values=(desc_text,),
            tags=tuple(tags),
        )
        self.quick_copy_tree_items[item_id] = skill

    def _bind_description_peek(self, tree, item_lookup):
        tree.bind("<Motion>", lambda event: self._schedule_description_peek(event, tree, item_lookup), add="+")
        tree.bind("<Leave>", lambda _event: self._hide_description_peek(), add="+")
        tree.bind("<ButtonPress>", lambda _event: self._hide_description_peek(), add="+")
        tree.bind("<MouseWheel>", lambda _event: self._hide_description_peek(), add="+")

    def _schedule_description_peek(self, event, tree, item_lookup):
        row_id = tree.identify_row(event.y)
        skill = item_lookup().get(row_id) if row_id else None
        if not skill:
            self._hide_description_peek()
            return

        peek_key = (str(tree), row_id)
        if self._description_peek_key == peek_key and self._description_peek_window is not None:
            return

        self._cancel_description_peek_after()
        self._description_peek_key = peek_key
        self._description_peek_after_id = self.after(
            self._description_peek_delay_ms,
            lambda: self._show_description_peek(tree, row_id, item_lookup, event.x_root, event.y_root),
        )

    def _show_description_peek(self, tree, row_id, item_lookup, x_root, y_root):
        self._description_peek_after_id = None
        skill = item_lookup().get(row_id)
        if not skill or not tree.winfo_exists():
            self._hide_description_peek()
            return

        description = skill.get("description") or "No description available."
        title = skill.get("name", "Unknown")
        self._destroy_description_peek_window()

        popup = tk.Toplevel(self)
        popup.overrideredirect(True)
        popup.attributes("-topmost", True)
        popup.configure(background=POPOVER_BG)

        frame = tk.Frame(popup, background=POPOVER_BG, borderwidth=1, relief="solid")
        frame.pack(fill="both", expand=True)
        title_label = tk.Label(
            frame,
            text=title,
            anchor="w",
            justify="left",
            background=POPOVER_BG,
            foreground=POPOVER_TEXT,
            font=("Segoe UI", 10, "bold"),
            padx=10,
            pady=4,
        )
        title_label.pack(fill="x")
        desc_label = tk.Label(
            frame,
            text=description,
            anchor="w",
            justify="left",
            wraplength=460,
            background=POPOVER_BG,
            foreground=POPOVER_MUTED_TEXT,
            font=("Segoe UI", 10),
            padx=10,
            pady=8,
        )
        desc_label.pack(fill="both", expand=True)
        popup.update_idletasks()

        width = popup.winfo_reqwidth()
        height = popup.winfo_reqheight()
        screen_width = popup.winfo_screenwidth()
        screen_height = popup.winfo_screenheight()
        x = min(x_root + 16, max(0, screen_width - width - 12))
        y = min(y_root + 18, max(0, screen_height - height - 48))
        popup.geometry(f"+{x}+{y}")
        self._description_peek_window = popup

    def _cancel_description_peek_after(self):
        if self._description_peek_after_id is not None:
            try:
                self.after_cancel(self._description_peek_after_id)
            except tk.TclError:
                pass
            self._description_peek_after_id = None

    def _destroy_description_peek_window(self):
        if self._description_peek_window is not None:
            try:
                self._description_peek_window.destroy()
            except tk.TclError:
                pass
            self._description_peek_window = None

    def _hide_description_peek(self):
        self._cancel_description_peek_after()
        self._destroy_description_peek_window()
        self._description_peek_key = None

    def _clear_quick_copy_tree(self):
        self._hide_description_peek()
        for item in self.quick_copy_tree.get_children():
            self.quick_copy_tree.delete(item)
        self.quick_copy_tree_projects = {}
        self.quick_copy_tree_categories = {}
        self.quick_copy_tree_items = {}

    def _toggle_quick_copy_skill_from_click(self, event):
        if self.quick_copy_tree.identify("region", event.x, event.y) not in {"tree", "cell"}:
            return
        item_id = self.quick_copy_tree.identify_row(event.y)
        category_data = self.quick_copy_tree_categories.get(item_id)
        if category_data:
            self._toggle_quick_copy_category_selection(category_data.get("category"))
            return
        skill = self.quick_copy_tree_items.get(item_id)
        if skill:
            self.toggle_quick_copy_skill_selection(skill)

    def toggle_quick_copy_skill_selection(self, skill):
        key = self._quick_copy_skill_key(skill)
        if key in self.quick_copy_selected_skill_keys:
            self.quick_copy_selected_skill_keys.remove(key)
        else:
            self.quick_copy_selected_skill_keys.add(key)
        self._clear_quick_copy_bundle_selection()
        self._remember_quick_copy_selection_for_current_project()
        self._refresh_visible_quick_copy_prefixes()
        self._sync_quick_copy_tree_selection()
        self._update_quick_copy_selected_count()

    def _refresh_visible_quick_copy_prefixes(self):
        if "quick_copy_tree" not in self.__dict__:
            return
        for item_id, skill in self.quick_copy_tree_items.items():
            selected = self._quick_copy_skill_key(skill) in self.quick_copy_selected_skill_keys
            label = skill.get("name", "Unknown")
            self.quick_copy_tree.item(item_id, text=label)
            
            tags = list(self.quick_copy_tree.item(item_id, "tags"))
            if selected:
                if "selected_skill" not in tags:
                    tags.append("selected_skill")
            else:
                if "selected_skill" in tags:
                    tags.remove("selected_skill")
            self.quick_copy_tree.item(item_id, tags=tuple(tags))

        for category_id, category_data in self.quick_copy_tree_categories.items():
            child_skills = [
                self.quick_copy_tree_items[skill_id]
                for skill_id in self.quick_copy_tree.get_children(category_id)
                if skill_id in self.quick_copy_tree_items
            ]
            selected = bool(child_skills) and all(
                self._quick_copy_skill_key(skill) in self.quick_copy_selected_skill_keys
                for skill in child_skills
            )
            tags = list(self.quick_copy_tree.item(category_id, "tags"))
            if selected:
                if "selected_skill" not in tags:
                    tags.append("selected_skill")
            else:
                if "selected_skill" in tags:
                    tags.remove("selected_skill")
            self.quick_copy_tree.item(category_id, tags=tuple(tags))

    def _update_quick_copy_selected_count(self):
        total_skills = self._quick_copy_skills_for_current_project()
        total_count = len(total_skills)
        selected_count = len(self.quick_copy_selected_skill_keys)

        if "quick_copy_selection_indicator" in self.__dict__:
            indicator_text = f"{selected_count:02d}/{total_count:02d} Selected"
            self.quick_copy_selection_indicator.configure(text=indicator_text)
            self.quick_copy_selection_indicator.configure(
                text_color=styles.TEXT_MAIN if selected_count > 0 else styles.TEXT_MUTED
            )

        self._sync_quick_copy_select_visible_check()

    def _sync_quick_copy_select_visible_check(self):
        visible_skills = self._visible_quick_copy_skills()
        selected = bool(visible_skills) and all(
            self._quick_copy_skill_key(skill) in self.quick_copy_selected_skill_keys
            for skill in visible_skills
        )
        if "quick_copy_select_visible_var" in self.__dict__:
            self.quick_copy_select_visible_var.set(selected)
        if "quick_copy_select_visible_check" in self.__dict__:
            state = "normal" if visible_skills else "disabled"
            self.quick_copy_select_visible_check.configure(state=state)

    def _prune_quick_copy_selected_keys(self):
        available_keys = {
            self._quick_copy_skill_key(skill)
            for skill in self._all_quick_copy_skills(self.quick_copy_projects) + self._all_quick_copy_manual_skills()
        }
        self.quick_copy_selected_skill_keys.intersection_update(available_keys)
        self._remember_quick_copy_selection_for_current_project()

    def _quick_copy_project_options(self, projects):
        options = [(project.get("project_label"), project.get("project_key")) for project in projects]
        return [(label, key) for label, key in options if label and key]

    def _refresh_quick_copy_project_menu(self, projects):
        options = self._quick_copy_project_options(projects)
        self.quick_copy_project_options = options
        labels = [label for label, _key in options] or ["No Projects"]
        selected_key = self.quick_copy_selected_project_key
        valid_keys = {key for _label, key in options}
        if selected_key not in valid_keys:
            selected_key = options[0][1] if options else ""
        self.quick_copy_selected_project_key = selected_key
        selected_label = self._quick_copy_project_label_for_key(selected_key) or labels[0]
        self.quick_copy_project_menu.configure(values=labels)
        self.quick_copy_project_var.set(selected_label)

    def _change_quick_copy_project(self, label):
        self._remember_quick_copy_selection_for_current_project()
        self._remember_quick_copy_manual_references_for_current_project()
        self._remember_quick_copy_essentials_for_current_project()
        self.quick_copy_selected_project_key = self._quick_copy_project_key_for_label(label)
        self._load_quick_copy_selection_for_current_project()
        self._load_quick_copy_manual_references_for_current_project()
        self._load_quick_copy_essentials_for_current_project()
        self.save_quick_copy_preferences()
        self._apply_quick_copy_filters()


    def _current_quick_copy_project_key(self):
        return self.quick_copy_selected_project_key

    def _current_quick_copy_project_label(self):
        return self._quick_copy_project_label_for_key(self._current_quick_copy_project_key()) or "No Project"

    def _quick_copy_project_key_for_label(self, label):
        for option_label, option_key in self.__dict__.get("quick_copy_project_options", []):
            if option_label == label:
                return option_key
        return ""

    def _quick_copy_project_label_for_key(self, key):
        for option_label, option_key in self.__dict__.get("quick_copy_project_options", []):
            if option_key == key:
                return option_label
        return ""

    def _remember_quick_copy_selection_for_current_project(self):
        key = self._current_quick_copy_project_key()
        if key is None:
            return
        self.quick_copy_selected_skill_keys_by_project[key] = set(self.quick_copy_selected_skill_keys)

    def _load_quick_copy_selection_for_current_project(self):
        key = self._current_quick_copy_project_key()
        self.quick_copy_selected_skill_keys = set(
            self.quick_copy_selected_skill_keys_by_project.get(key, set())
        )

    def _remember_quick_copy_manual_references_for_current_project(self):
        project_key = self._current_quick_copy_project_key()
        if project_key is None:
            return
        
        client_format = self.quick_copy_client_var.get()
        project_data = self.quick_copy_manual_references_by_project.get(project_key, {})
        if isinstance(project_data, list):
            project_data = {client_format: merge_manual_references([], project_data)}
        elif not isinstance(project_data, dict):
            project_data = {}
        self.quick_copy_manual_references_by_project[project_key] = project_data
        
        self.quick_copy_manual_references_by_project[project_key][client_format] = merge_manual_references(
            [],
            getattr(self, "quick_copy_manual_references", []),
        )

    def _load_quick_copy_manual_references_for_current_project(self):
        project_key = self._current_quick_copy_project_key()
        client_format = self.quick_copy_client_var.get()
        
        project_data = self.quick_copy_manual_references_by_project.get(project_key, {})
        if isinstance(project_data, list):
            references = project_data
        elif isinstance(project_data, dict):
            references = project_data.get(client_format, [])
        else:
            references = []
        self.quick_copy_manual_references = list(references)
        self._refresh_quick_copy_manual_label()

    def _change_quick_copy_client(self, _value):
        """Handle change in the client output format for Quick Copy."""
        # Save manuals for the old client before switching
        self._remember_quick_copy_manual_references_for_current_project()

        # Save preferences to persist the client format change
        self.save_quick_copy_preferences()

        # Load manuals for the new client format
        self._load_quick_copy_manual_references_for_current_project()

        # Update the argument field if a skill is currently selected
        if getattr(self, "_current_inspector_prefix", None) == "quick_copy" and getattr(self, "_current_inspector_skill", None):
            skill = self._current_inspector_skill
            widgets = self._inspector_widgets("quick_copy")
            arg_var = widgets.get("argument_var")
            if arg_var:
                # Disconnect trace temporarily to prevent overriding config
                trace_id = getattr(self, "quick_copy_arg_trace_id", None)
                if trace_id:
                    try:
                        arg_var.trace_remove("write", trace_id)
                    except Exception:
                        pass

                arg_var.set(self._get_quick_copy_skill_argument(skill))

                # Reconnect trace
                def _on_arg_change(*_args):
                    s = getattr(self, "_current_inspector_skill", None)
                    if s and getattr(self, "_current_inspector_prefix", None) == "quick_copy":
                        self._set_quick_copy_skill_argument(s, arg_var.get().strip())
                self.quick_copy_arg_trace_id = arg_var.trace_add("write", _on_arg_change)

        # Re-apply filters which will refresh the UI tree
        self._apply_quick_copy_filters()
    def _migrate_legacy_quick_copy_manual_references(self):
        # Migration is now handled during load_quick_copy_config and __init__
        # This keeps the method signature for compatibility
        pass

    def _remember_quick_copy_essentials_for_current_project(self):
        key = self._current_quick_copy_project_key()
        if key is None:
            return
        self.quick_copy_essential_skill_keys_by_project[key] = set(self.quick_copy_essential_skill_keys)

    def _load_quick_copy_essentials_for_current_project(self):
        key = self._current_quick_copy_project_key()
        self.quick_copy_essential_skill_keys = set(
            self.quick_copy_essential_skill_keys_by_project.get(key, set())
        )
        self._update_quick_copy_essentials_label()

    def _migrate_legacy_quick_copy_essentials(self):
        legacy_keys = {
            str(key)
            for key in self.quick_copy_config.get("essential_skill_keys", [])
            if str(key).strip()
        }
        key = self._current_quick_copy_project_key()
        if not legacy_keys or key is None:
            return
        self.quick_copy_essential_skill_keys_by_project[key] = set(
            self.quick_copy_essential_skill_keys_by_project.get(key, set())
        ) | legacy_keys
        self.quick_copy_essential_skill_keys = set(self.quick_copy_essential_skill_keys_by_project[key])
        self.quick_copy_config["essential_skill_keys"] = []
        self.save_quick_copy_preferences()

    def _quick_copy_skills_for_current_project(self):
        key = self._current_quick_copy_project_key()
        if key is None:
            return self._all_quick_copy_skills(self.quick_copy_projects) + self._all_quick_copy_manual_skills()
        skills = [
            skill for skill in self._all_quick_copy_skills(self.quick_copy_projects)
            if skill.get("project_key") == key
        ]
        return skills + self._quick_copy_manual_skills()

    def _filter_quick_copy_skills_to_current_project(self, skills):
        if not self._current_quick_copy_project_key():
            return list(skills)
        allowed_keys = {self._quick_copy_skill_key(skill) for skill in self._quick_copy_skills_for_current_project()}
        return [skill for skill in skills if self._quick_copy_skill_key(skill) in allowed_keys]

    def _quick_copy_display_category(self, skill):
        if self._is_quick_copy_skill_essential(skill):
            return QUICK_COPY_ESSENTIALS_CATEGORY
        if skill.get("is_manual"):
            return QUICK_COPY_MANUAL_CATEGORY
        return skill.get("category", "Uncategorized")

    def _quick_copy_category_sort_key(self, category):
        category = str(category or "Uncategorized")
        if category == QUICK_COPY_ESSENTIALS_CATEGORY:
            return (0, "")
        return (1, category.lower())

    def _is_quick_copy_skill_essential(self, skill):
        return self._quick_copy_skill_key(skill) in self.quick_copy_essential_skill_keys

    def _quick_copy_essential_skills(self):
        key_set = set(self.quick_copy_essential_skill_keys)
        return [
            skill for skill in self._quick_copy_skills_for_current_project()
            if self._quick_copy_skill_key(skill) in key_set
        ]

    def _update_quick_copy_essentials_label(self):
        if self.__dict__.get("_current_inspector_prefix") == "quick_copy":
            self._update_quick_copy_inspector_essentials_button()

    def show_quick_copy_essentials(self):
        self.quick_copy_category_var.set(QUICK_COPY_ESSENTIALS_CATEGORY)
        self._apply_quick_copy_filters()

    def add_selected_project_skills_to_essentials(self):
        skills = self._selected_quick_copy_skills()
        if not skills:
            self.show_toast("Essentials", "Select project skills before adding them to Essentials.", "info")
            return
        before = len(self.quick_copy_essential_skill_keys)
        self.quick_copy_essential_skill_keys.update(self._quick_copy_skill_key(skill) for skill in skills)
        added = len(self.quick_copy_essential_skill_keys) - before
        self._remember_quick_copy_essentials_for_current_project()
        self.save_quick_copy_preferences()
        self._render_quick_copy(self.quick_copy_projects)
        self.quick_copy_status_label.configure(text=f"Added {added} skill(s) to Essentials.")

    def remove_selected_project_skills_from_essentials(self):
        skills = self._selected_quick_copy_skills()
        if not skills:
            self.show_toast("Essentials", "Select essential project skills before removing them.", "info")
            return
        before = len(self.quick_copy_essential_skill_keys)
        for skill in skills:
            self.quick_copy_essential_skill_keys.discard(self._quick_copy_skill_key(skill))
        removed = before - len(self.quick_copy_essential_skill_keys)
        self._remember_quick_copy_essentials_for_current_project()
        self.save_quick_copy_preferences()
        self._render_quick_copy(self.quick_copy_projects)
        self.quick_copy_status_label.configure(text=f"Removed {removed} skill(s) from Essentials.")

    def toggle_current_inspector_essential(self):
        skill = self.__dict__.get("_current_inspector_skill")
        if not skill or self.__dict__.get("_current_inspector_prefix") != "quick_copy":
            return
        key = self._quick_copy_skill_key(skill)
        if key in self.quick_copy_essential_skill_keys:
            self.quick_copy_essential_skill_keys.discard(key)
            action = "Removed"
        else:
            self.quick_copy_essential_skill_keys.add(key)
            action = "Added"
        self._remember_quick_copy_essentials_for_current_project()
        self.save_quick_copy_preferences()
        self._render_quick_copy(self.quick_copy_projects)
        self._update_quick_copy_inspector_essentials_button(skill)
        self.quick_copy_status_label.configure(text=f"{action} '{skill.get('name', 'Skill')}' in Essentials.")

    def _update_quick_copy_inspector_essentials_button(self, skill=None):
        button = self.__dict__.get("quick_copy_inspector_essentials_btn")
        if button is None:
            return
        skill = skill or self.__dict__.get("_current_inspector_skill")
        if not skill or self.__dict__.get("_current_inspector_prefix") != "quick_copy":
            button.grid_remove()
            return
        button.grid()
        is_essential = self._is_quick_copy_skill_essential(skill)
        button.configure(text="Remove from Essentials" if is_essential else "Add to Essentials")

    def copy_quick_copy_essentials(self):
        skills = sorted(
            self._quick_copy_essential_skills(),
            key=lambda item: (item.get("project_label", "").lower(), item.get("name", "").lower()),
        )
        if not skills:
            self.show_toast("Essentials", "No Essentials are saved in selected project.", "info")
            return
        text = self._build_quick_copy_reference_output(skills)
        self.clipboard_clear()
        self.clipboard_append(text)
        self.update()
        self.save_quick_copy_preferences()
        self.quick_copy_status_label.configure(text=f"Copied {len(skills)} Essentials reference(s).")

    def select_all_visible_project_skills(self):
        visible_skills = self._visible_quick_copy_skills()
        self._set_quick_copy_skills_selected(visible_skills, True)
        if "quick_copy_status_label" in self.__dict__:
            self.quick_copy_status_label.configure(text=f"Selected {len(visible_skills)} visible skill(s).")

    def clear_quick_copy_selection(self):
        self.quick_copy_selected_skill_keys.clear()
        self._clear_quick_copy_bundle_selection()
        self._remember_quick_copy_selection_for_current_project()
        self._sync_quick_copy_tree_selection()
        if "quick_copy_status_label" in self.__dict__:
            self.quick_copy_status_label.configure(text="Deselected all project skills.")

    def _toggle_quick_copy_select_visible_from_check(self):
        if self.quick_copy_select_visible_var.get():
            self.select_all_visible_project_skills()
        else:
            self.clear_quick_copy_selection()

    def select_current_quick_copy_category(self):
        self._set_current_quick_copy_category_selected(True)

    def deselect_current_quick_copy_category(self):
        self._set_current_quick_copy_category_selected(False)

    def _toggle_quick_copy_category_selection(self, category):
        skills = self._visible_quick_copy_skills_for_category(category)
        if not skills:
            return
        should_select = not all(
            self._quick_copy_skill_key(skill) in self.quick_copy_selected_skill_keys
            for skill in skills
        )
        self._set_quick_copy_skills_selected(skills, should_select)
        action = "Selected" if should_select else "Deselected"
        if "quick_copy_status_label" in self.__dict__:
            self.quick_copy_status_label.configure(text=f"{action} {len(skills)} skill(s) in {category}.")

    def _set_current_quick_copy_category_selected(self, selected):
        category = self._current_quick_copy_action_category()
        if not category:
            self.show_toast("Category selection", "Choose or select a category first.", "info")
            return
        skills = self._visible_quick_copy_skills_for_category(category)
        self._set_quick_copy_skills_selected(skills, selected)
        action = "Selected" if selected else "Deselected"
        if "quick_copy_status_label" in self.__dict__:
            self.quick_copy_status_label.configure(text=f"{action} {len(skills)} skill(s) in {category}.")

    def _visible_quick_copy_skills(self):
        visible_skills = self._all_quick_copy_skills(self.__dict__.get("filtered_quick_copy_projects", []))
        visible_skills += list(self.__dict__.get("filtered_quick_copy_manual_skills", []))
        return visible_skills

    def _visible_quick_copy_skills_for_category(self, category):
        return [
            skill for skill in self._visible_quick_copy_skills()
            if self._quick_copy_display_category(skill) == category
        ]

    def _current_quick_copy_action_category(self):
        tree = self.__dict__.get("quick_copy_tree")
        if tree is not None:
            for item_id in tree.selection():
                category_data = self.quick_copy_tree_categories.get(item_id)
                if category_data:
                    return category_data.get("category")
                skill = self.quick_copy_tree_items.get(item_id)
                if skill:
                    return self._quick_copy_display_category(skill)
        category = self.quick_copy_category_var.get() if "quick_copy_category_var" in self.__dict__ else ""
        return "" if category == "All Categories" else category

    def _set_quick_copy_skills_selected(self, skills, selected):
        for skill in skills:
            key = self._quick_copy_skill_key(skill)
            if selected:
                self.quick_copy_selected_skill_keys.add(key)
            else:
                self.quick_copy_selected_skill_keys.discard(key)
        self._clear_quick_copy_bundle_selection()
        self._remember_quick_copy_selection_for_current_project()
        self._sync_quick_copy_tree_selection()

    def _sync_quick_copy_tree_selection(self):
        if "quick_copy_tree" in self.__dict__:
            selected_items = [
                item_id for item_id, skill in self.quick_copy_tree_items.items()
                if self._quick_copy_skill_key(skill) in self.quick_copy_selected_skill_keys
            ]
            for category_id in self.quick_copy_tree_categories:
                child_skills = [
                    self.quick_copy_tree_items[skill_id]
                    for skill_id in self.quick_copy_tree.get_children(category_id)
                    if skill_id in self.quick_copy_tree_items
                ]
                if child_skills and all(
                    self._quick_copy_skill_key(skill) in self.quick_copy_selected_skill_keys
                    for skill in child_skills
                ):
                    selected_items.append(category_id)
            self.quick_copy_tree.selection_set(selected_items)
        self._refresh_visible_quick_copy_prefixes()
        self._update_quick_copy_selected_count()

    def add_quick_copy_manual_reference(self):
        if self._current_quick_copy_project_key() is None:
            self.show_toast("Manual references", "Select a project before adding manuals.", "info")
            return
        references = normalize_manual_references(self.quick_copy_manual_var.get())
        if not references:
            self.show_toast("Manual references", "Enter a skill name, @reference, path, or Markdown link.", "info")
            return
        self._set_quick_copy_manual_references(
            merge_manual_references(self.quick_copy_manual_references, references)
        )
        self.quick_copy_manual_var.set("")
        self.hide_quick_copy_manual_composer()
        self.quick_copy_status_label.configure(text=f"Added {len(references)} manual clipboard reference(s).")

    def paste_quick_copy_manual_references(self):
        if self._current_quick_copy_project_key() is None:
            self.show_toast("Manual references", "Select a project before adding manuals.", "info")
            return
        try:
            clipboard_text = self.clipboard_get()
        except tk.TclError:
            clipboard_text = ""
        references = normalize_manual_references(clipboard_text)
        if not references:
            self.show_toast("Manual references", "Clipboard does not contain any manual references.", "info")
            return
        self._set_quick_copy_manual_references(
            merge_manual_references(self.quick_copy_manual_references, references)
        )
        self.quick_copy_status_label.configure(text=f"Pasted {len(references)} manual clipboard reference(s).")

    def browse_quick_copy_manual_reference(self):
        if self._current_quick_copy_project_key() is None:
            self.show_toast("Manual references", "Select a project before adding manuals.", "info")
            return
        path = filedialog.askopenfilename(
            title="Choose SKILL.md",
            filetypes=(("Skill files", "SKILL.md"), ("Markdown files", "*.md"), ("All files", "*.*")),
        )
        if not path:
            return
        reference = normalize_manual_reference(path)
        self._set_quick_copy_manual_references(
            merge_manual_references(self.quick_copy_manual_references, [reference])
        )
        self.quick_copy_status_label.configure(text="Added manual file reference.")

    def remove_last_quick_copy_manual_reference(self):
        if not self.quick_copy_manual_references:
            self.show_toast("Manual references", "No manual references to remove.", "info")
            return
        removed = self.quick_copy_manual_references[-1]
        self._set_quick_copy_manual_references(self.quick_copy_manual_references[:-1])
        self.quick_copy_status_label.configure(text=f"Removed manual reference: {removed}")

    def remove_selected_quick_copy_manual_references(self):
        manual_skills = [skill for skill in self._selected_quick_copy_skills() if skill.get("is_manual")]
        if not manual_skills:
            self.show_toast("Manual references", "Select one or more manuals to remove.", "info")
            return
        self._remove_quick_copy_manual_skills(manual_skills)
        self.quick_copy_status_label.configure(text=f"Removed {len(manual_skills)} manual(s).")

    def _set_quick_copy_manual_references(self, references):
        self.quick_copy_manual_references = merge_manual_references([], references)
        self._remember_quick_copy_manual_references_for_current_project()
        self._refresh_quick_copy_manual_label()
        self.save_quick_copy_preferences()
        if hasattr(self, "quick_copy_tree"):
            self._apply_quick_copy_filters()

    def _remove_quick_copy_manual_skills(self, manual_skills):
        client_format = self.quick_copy_client_var.get()
        current_project_key = self._current_quick_copy_project_key()
        
        for skill in manual_skills:
            p_key = skill.get("project_key", current_project_key)
            ref = skill.get("manual_reference")
            
            if p_key in self.quick_copy_manual_references_by_project:
                project_data = self.quick_copy_manual_references_by_project[p_key]
                if isinstance(project_data, list):
                    self.quick_copy_manual_references_by_project[p_key] = [
                        r for r in project_data
                        if r != ref
                    ]
                elif client_format in project_data:
                    project_data[client_format] = [
                        r for r in project_data[client_format]
                        if r != ref
                    ]
            
            # If it matches current project, update the active list too
            if p_key == current_project_key:
                self.quick_copy_manual_references = [
                    r for r in self.quick_copy_manual_references
                    if r != ref
                ]
        
        self._refresh_quick_copy_manual_label()
        self.save_quick_copy_preferences()
        if hasattr(self, "quick_copy_tree"):
            self._apply_quick_copy_filters()
        for skill in manual_skills:
            self.quick_copy_selected_skill_keys.discard(self._quick_copy_skill_key(skill))
        self._remember_quick_copy_selection_for_current_project()

    def _refresh_quick_copy_manual_label(self):
        if "quick_copy_manual_label" not in self.__dict__:
            return
        self.quick_copy_manual_label.configure(text="")

    def copy_selected_project_skill_references(self):
        skills = self._selected_quick_copy_skills()
        skills = self._filter_quick_copy_skills_to_current_project(skills)
        if not skills:
            self.show_toast("Copy project skills", "Select skills in the selected project before copying.", "info")
            return
        text = self._build_quick_copy_reference_output(skills)
        self.clipboard_clear()
        self.clipboard_append(text)
        self.update()
        self.save_quick_copy_preferences()
        manual_count = len([skill for skill in skills if skill.get("is_manual")])
        project_count = len(skills) - manual_count
        self.quick_copy_status_label.configure(
            text=f"Copied {project_count} project skill reference(s) and {manual_count} manual(s)."
        )

    def delete_selected_project_skills(self):
        skills = self._selected_quick_copy_skills()
        skills = self._filter_quick_copy_skills_to_current_project(skills)
        if not skills:
            self.show_toast("Delete project skills", "Select one or more skills in the selected project.", "info")
            return

        manual_skills = [skill for skill in skills if skill.get("is_manual")]
        project_skills = [skill for skill in skills if not skill.get("is_manual")]

        if not project_skills:
            self._remove_quick_copy_manual_skills(manual_skills)
            self.quick_copy_status_label.configure(text=f"Removed {len(manual_skills)} manual(s).")
            return

        preview_lines = [
            f"- {skill.get('project_label')}: {skill.get('folder_name')}"
            for skill in project_skills[:12]
        ]
        suffix = ""
        if len(project_skills) > len(preview_lines):
            suffix = f"\n...and {len(project_skills) - len(preview_lines)} more."
        def delete_confirmed():
            if manual_skills:
                self._remove_quick_copy_manual_skills(manual_skills)

            result = delete_project_skill_folders(project_skills)
            deleted = result.get("deleted", 0)
            skipped = result.get("skipped", 0)
            failed = result.get("failed", 0)
            problem_lines = [
                f"- {item.get('skill')}: {item.get('message')}"
                for item in result.get("details", [])
                if item.get("status") in {"skipped", "failed"}
            ][:8]
            message = f"Deleted: {deleted}\nSkipped: {skipped}\nFailed: {failed}\nManuals removed: {len(manual_skills)}"
            if problem_lines:
                message += "\n\nIssues:\n" + "\n".join(problem_lines)
            self.show_toast("Delete project skills", message, "success" if failed == 0 else "warning")
            self.quick_copy_selected_skill_keys.clear()
            self._remember_quick_copy_selection_for_current_project()
            self.load_quick_copy()

        self.confirm_destructive_action(
            "Delete Project Skills",
            "This permanently removes skill folders from selected project targets. Manual references are only removed from this list.",
            "\n".join(preview_lines) + suffix,
            "Delete Folders",
            delete_confirmed,
        )

    def _selected_quick_copy_skills(self):
        if self.quick_copy_selected_skill_keys:
            key_set = set(self.quick_copy_selected_skill_keys)
            return [
                skill for skill in self._quick_copy_skills_for_current_project()
                if self._quick_copy_skill_key(skill) in key_set
            ]

        selected = set(self.quick_copy_tree.selection())
        if not selected:
            return []

        result = []
        seen = set()
        for row_id in self.quick_copy_tree.get_children(""):
            if row_id in selected:
                if row_id in self.quick_copy_tree_categories:
                    self._append_quick_copy_category_skills(row_id, result, seen)
                else:
                    self._append_quick_copy_project_skills(row_id, result, seen)
                continue
            for category_id in self.quick_copy_tree.get_children(row_id):
                if category_id in selected:
                    self._append_quick_copy_category_skills(category_id, result, seen)
                    continue
                for skill_id in self.quick_copy_tree.get_children(category_id):
                    if skill_id in selected:
                        self._append_quick_copy_skill(skill_id, result, seen)
        return result

    def _append_quick_copy_project_skills(self, project_id, result, seen):
        for category_id in self.quick_copy_tree.get_children(project_id):
            self._append_quick_copy_category_skills(category_id, result, seen)

    def _append_quick_copy_category_skills(self, category_id, result, seen):
        for skill_id in self.quick_copy_tree.get_children(category_id):
            self._append_quick_copy_skill(skill_id, result, seen)

    def _append_quick_copy_skill(self, item_id, result, seen):
        skill = self.quick_copy_tree_items.get(item_id)
        if not skill:
            return
        key = self._quick_copy_skill_key(skill)
        if key in seen:
            return
        seen.add(key)
        result.append(skill)

    def _get_quick_copy_skill_argument(self, skill):
        project_key = self._current_quick_copy_project_key()
        client_format = self.quick_copy_client_var.get()
        skill_key = self._quick_copy_skill_key(skill)
        return self.quick_copy_skill_arguments_by_project.get(project_key, {}).get(client_format, {}).get(skill_key, "")

    def _set_quick_copy_skill_argument(self, skill, argument):
        project_key = self._current_quick_copy_project_key()
        if not project_key:
            return
        client_format = self.quick_copy_client_var.get()
        skill_key = self._quick_copy_skill_key(skill)
        
        project_args = self.quick_copy_skill_arguments_by_project.setdefault(project_key, {})
        client_args = project_args.setdefault(client_format, {})
        
        if argument:
            client_args[skill_key] = argument
        elif skill_key in client_args:
            del client_args[skill_key]
            
        self.quick_copy_config["skill_arguments_by_project"] = self.quick_copy_skill_arguments_by_project
        self.save_quick_copy_preferences()

    def _build_quick_copy_reference_output(self, skills, manual_references=None):
        lines = []
        for skill in skills:
            if skill.get("is_manual"):
                ref = skill.get("manual_reference")
            else:
                ref = format_project_skill_reference(skill, self.quick_copy_client_var.get())
                arg = self._get_quick_copy_skill_argument(skill)
                if arg:
                    ref = f"{ref} {arg}"
            lines.append(ref)
        lines.extend(manual_references or [])
        return "\n".join(lines)

    def save_current_quick_copy_set(self, set_name=None):
        skills = self._selected_quick_copy_skills()
        skills = self._filter_quick_copy_skills_to_current_project(skills)
        manual_references = [skill.get("manual_reference") for skill in skills if skill.get("is_manual")]
        project_skills = [skill for skill in skills if not skill.get("is_manual")]
        if not skills:
            self.show_toast("Save project skill set", "Select project skills or manuals before saving a set.", "info")
            return

        if set_name is None and self.quick_copy_bundle_name_entry:
            set_name = self.quick_copy_bundle_name_entry.get().strip()

        if not set_name:
            dialog = ctk.CTkInputDialog(text="Name this project skill set:", title="Save Project Skill Set")
            set_name = (dialog.get_input() or "").strip()
            if not set_name:
                return

        self.quick_copy_config.setdefault("skill_sets", {})[set_name] = {
            "skill_keys": [self._quick_copy_skill_key(skill) for skill in project_skills],
            "manual_references": manual_references,
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        self.quick_copy_set_var.set(set_name)
        
        # Hide inline frame if it was visible
        if self.quick_copy_add_bundle_frame:
            self.quick_copy_add_bundle_frame.grid_remove()
            self.quick_copy_search_entry.grid()

        self._refresh_quick_copy_set_menu()
        self._refresh_quick_copy_set_details()
        self.save_quick_copy_preferences()
        self.quick_copy_status_label.configure(
            text=f"Saved bundle '{set_name}' with {len(project_skills)} project skill(s) and {len(manual_references)} manual(s)."
        )


    def edit_quick_copy_set(self, set_name=None):
        if set_name is not None:
            self.quick_copy_set_var.set(set_name)
        set_name = self._selected_quick_copy_set_name()
        if not set_name:
            self.show_toast("Edit project skill bundle", "Select a saved bundle before editing.", "info")
            return

        skills = self._selected_quick_copy_skills()
        skills = self._filter_quick_copy_skills_to_current_project(skills)
        if not skills:
            self.show_toast("Edit project skill bundle", "Select project skills or manuals to update this bundle.", "info")
            return

        dialog = ctk.CTkInputDialog(text="Bundle name:", title="Edit Project Skill Bundle")
        raw_name = dialog.get_input()
        if raw_name is None:
            return
        next_name = raw_name.strip() or set_name
        if not next_name:
            return

        skill_sets = self.quick_copy_config.setdefault("skill_sets", {})
        if next_name != set_name:
            skill_sets.pop(set_name, None)

        manual_references = [skill.get("manual_reference") for skill in skills if skill.get("is_manual")]
        project_skills = [skill for skill in skills if not skill.get("is_manual")]
        skill_sets[next_name] = {
            "skill_keys": [self._quick_copy_skill_key(skill) for skill in project_skills],
            "manual_references": manual_references,
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        self.quick_copy_set_var.set(next_name)
        self._refresh_quick_copy_set_menu()
        self._refresh_quick_copy_set_details()
        self.save_quick_copy_preferences()
        self.quick_copy_status_label.configure(
            text=f"Edited bundle '{next_name}' with {len(project_skills)} project skill(s) and {len(manual_references)} manual(s)."
        )

    def _change_quick_copy_set(self, _value=None):
        if _value is not None:
            self.quick_copy_set_var.set(_value)
        self._hide_quick_copy_bundle_dropdown()
        self._refresh_quick_copy_set_menu()
        self._refresh_quick_copy_set_details()
        if self._selected_quick_copy_set_name():
            self.select_quick_copy_set()

    def select_quick_copy_set(self):
        set_name = self._selected_quick_copy_set_name()
        if not set_name:
            self.show_toast("Select project skill bundle", "No saved project skill bundle is selected.", "info")
            return

        selected_set = self.quick_copy_config.get("skill_sets", {}).get(set_name, {})
        keys = set(selected_set.get("skill_keys", []))
        self._set_quick_copy_manual_references(selected_set.get("manual_references", []))
        keys.update(self._quick_copy_manual_key(reference) for reference in selected_set.get("manual_references", []))
        visible_keys = {self._quick_copy_skill_key(skill) for skill in self._quick_copy_skills_for_current_project()}
        self.quick_copy_selected_skill_keys = set(keys & visible_keys)
        self._remember_quick_copy_selection_for_current_project()
        selected_items = [
            item_id for item_id, skill in self.quick_copy_tree_items.items()
            if self._quick_copy_skill_key(skill) in self.quick_copy_selected_skill_keys
        ]
        self.quick_copy_tree.selection_set(selected_items)
        self._refresh_visible_quick_copy_prefixes()
        self._update_quick_copy_selected_count()
        self._refresh_quick_copy_set_details()
        hidden_count = len(keys - visible_keys)
        if hidden_count:
            self.quick_copy_status_label.configure(text=f"{hidden_count} bundle item(s) hidden by filters or missing.")
        else:
            self.quick_copy_status_label.configure(text="")

    def delete_quick_copy_set(self, set_name=None):
        if set_name is not None:
            self.quick_copy_set_var.set(set_name)
        set_name = self._selected_quick_copy_set_name()
        if not set_name:
            self.show_toast("Delete project skill bundle", "No saved project skill bundle is selected.", "info")
            return

        deleted_set = self.quick_copy_config.get("skill_sets", {}).pop(set_name, None)
        self.quick_copy_set_var.set(self._default_quick_copy_set_label())
        self._refresh_quick_copy_set_menu()
        self._refresh_quick_copy_set_details()
        self.save_quick_copy_preferences()
        self.quick_copy_status_label.configure(text=f"Deleted project skill bundle '{set_name}'.")

        def undo():
            if deleted_set is None:
                return
            self.quick_copy_config.setdefault("skill_sets", {})[set_name] = deleted_set
            self.quick_copy_set_var.set(set_name)
            self._refresh_quick_copy_set_menu()
            self._refresh_quick_copy_set_details()
            self.save_quick_copy_preferences()
            self.quick_copy_status_label.configure(text=f"Restored project skill bundle '{set_name}'.")

        self._show_undo_toast("Deleted project skill bundle", set_name, undo)

    def _selected_quick_copy_set_name(self):
        set_name = self.quick_copy_set_var.get()
        if set_name == self._default_quick_copy_set_label():
            return ""
        if set_name not in self.quick_copy_config.get("skill_sets", {}):
            return ""
        return set_name

    def _default_quick_copy_set_label(self):
        return "No Bundle Selected"

    def _quick_copy_set_menu_values(self):
        names = sorted(self.quick_copy_config.get("skill_sets", {}).keys(), key=str.lower)
        return [self._default_quick_copy_set_label(), *names]

    def _refresh_quick_copy_set_menu(self):
        names = sorted(self.quick_copy_config.get("skill_sets", {}).keys(), key=str.lower)
        values = [self._default_quick_copy_set_label()] + names + ["Add New Bundle...", "Manage Bundles..."]
        
        current = self.quick_copy_set_var.get()
        if current not in values:
            current = values[0]
            self.quick_copy_set_var.set(current)
            
        if hasattr(self, "quick_copy_set_menu"):
            self.quick_copy_set_menu.configure(text=f"{current}  \u25be")
            
        self._refresh_quick_copy_set_details()

    def _toggle_quick_copy_bundle_dropdown(self, _event=None):
        if self.quick_copy_bundle_dropdown_frame.place_info():
            self._hide_quick_copy_bundle_dropdown()
        else:
            self._show_quick_copy_bundle_dropdown()

    def _show_quick_copy_bundle_dropdown(self):
        # Reset adding state when opening
        self._quick_copy_is_adding_bundle = False
        self._render_quick_copy_bundle_dropdown()
        
        # Position dropdown below the bundle button
        self.update_idletasks()
        
        # Calculate position relative to the root window (self)
        btn = self.quick_copy_set_menu
        root_x = btn.winfo_rootx() - self.winfo_rootx()
        root_y = btn.winfo_rooty() - self.winfo_rooty() + btn.winfo_height() + 5
        
        self.quick_copy_bundle_dropdown_frame.configure(width=280)
        self.quick_copy_bundle_dropdown_frame.place(x=root_x, y=root_y)
        self.quick_copy_bundle_dropdown_frame.lift()
        
        # Bind click outside to hide
        self.bind_all("<Button-1>", self._check_hide_quick_copy_dropdown)

    def _hide_quick_copy_bundle_dropdown(self):
        self.quick_copy_bundle_dropdown_frame.place_forget()
        self.unbind_all("<Button-1>")
        self._quick_copy_is_adding_bundle = False

    def _check_hide_quick_copy_dropdown(self, event):
        if not self.quick_copy_bundle_dropdown_frame.place_info():
            return
            
        # First check if the clicked widget is a descendant of the dropdown frame
        widget = event.widget
        try:
            current = widget
            is_descendant = False
            while current:
                if current == self.quick_copy_bundle_dropdown_frame:
                    is_descendant = True
                    break
                # CustomTkinter widgets sometimes use internal tk widgets
                if hasattr(current, "master"):
                    current = current.master
                else:
                    break
            if is_descendant:
                return
        except (AttributeError, tk.TclError):
            pass

        # Fallback to coordinate check
        x, y = event.x_root, event.y_root
        
        df = self.quick_copy_bundle_dropdown_frame
        dx = df.winfo_rootx()
        dy = df.winfo_rooty()
        dw = df.winfo_width()
        dh = df.winfo_height()
        
        btn = self.quick_copy_set_menu
        bx = btn.winfo_rootx()
        by = btn.winfo_rooty()
        bw = btn.winfo_width()
        bh = btn.winfo_height()
        
        if not (dx <= x <= dx + dw and dy <= y <= dy + dh) and \
           not (bx <= x <= bx + bw and by <= y <= by + bh):
            self._hide_quick_copy_bundle_dropdown()

    def _render_quick_copy_bundle_dropdown(self):
        # Clear existing children
        for child in self.quick_copy_bundle_dropdown_frame.winfo_children():
            child.destroy()
            
        container = ctk.CTkFrame(self.quick_copy_bundle_dropdown_frame, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=2, pady=2)
        
        # Bundle List
        bundles = sorted(self.quick_copy_config.get("skill_sets", {}).keys(), key=str.lower)
        
        # Calculate list height based on number of items (max 300)
        list_height = min(len(bundles) * 35, 300) if bundles else 0
        scroll_frame = ctk.CTkScrollableFrame(container, fg_color="transparent", height=list_height)
        scroll_frame.pack(fill="x", expand=False)
        
        current_bundle = self._selected_quick_copy_set_name()
        
        for name in bundles:
            is_active = (name == current_bundle)
            btn = ctk.CTkButton(
                scroll_frame,
                text=name,
                anchor="w",
                fg_color="transparent" if not is_active else GLASS_CONTROL_HOVER,
                hover_color=GLASS_CONTROL_HOVER,
                text_color=TEXT_MAIN if not is_active else CTK_STATUS_COLORS["success"],
                height=30,
                corner_radius=6,
                command=lambda n=name: self._select_bundle_from_dropdown(n)
            )
            btn.pack(fill="x", pady=1)

        # Separator
        ctk.CTkFrame(container, height=1, fg_color=GLASS_BORDER).pack(fill="x", pady=4)
        
        # Bottom Actions
        if not self._quick_copy_is_adding_bundle:
            # Add Bundle Button
            ctk.CTkButton(
                container,
                text="+ Add New Bundle...",
                anchor="w",
                fg_color="transparent",
                hover_color=GLASS_CONTROL_HOVER,
                text_color=TEXT_MAIN,
                height=34,
                corner_radius=6,
                command=self._on_add_bundle_click
            ).pack(fill="x", pady=2)
            
            # Manage Bundles Button
            ctk.CTkButton(
                container,
                text="\u2699 Manage Bundles...",
                anchor="w",
                fg_color="transparent",
                hover_color=GLASS_CONTROL_HOVER,
                text_color=TEXT_MUTED,
                height=34,
                corner_radius=6,
                command=self._show_bundle_manager
            ).pack(fill="x", pady=2)
        else:
            # Inline Creation Row
            creation_frame = ctk.CTkFrame(container, fg_color="transparent")
            creation_frame.pack(fill="x", pady=2)
            
            self.quick_copy_bundle_name_entry = ctk.CTkEntry(
                creation_frame,
                placeholder_text="Bundle Name...",
                fg_color=GLASS_SEARCH_BG,
                border_color=GLASS_SEARCH_BORDER,
                text_color=GLASS_SEARCH_TEXT,
                placeholder_text_color=GLASS_SEARCH_PLACEHOLDER,
                corner_radius=17,
                height=34
            )
            self.quick_copy_bundle_name_entry.pack(side="left", fill="x", expand=True, padx=(0, 4))
            self.quick_copy_bundle_name_entry.focus_set()
            
            # Binds
            self.quick_copy_bundle_name_entry.bind("<Return>", lambda _: self._confirm_inline_bundle())
            self.quick_copy_bundle_name_entry.bind("<Escape>", lambda _: self._cancel_inline_bundle())

            ctk.CTkButton(
                creation_frame,
                text="\u2713", # Checkmark
                width=36,
                height=34,
                fg_color=GLASS_CONTROL,
                hover_color=GLASS_CONTROL_HOVER,
                text_color=CTK_STATUS_COLORS["success"],
                corner_radius=17,
                command=self._confirm_inline_bundle
            ).pack(side="left", padx=2)

            ctk.CTkButton(
                creation_frame,
                text="\u2715", # Cross
                width=36,
                height=34,
                fg_color=GLASS_CONTROL,
                hover_color=GLASS_CONTROL_HOVER,
                text_color=CTK_STATUS_COLORS["error"],
                corner_radius=17,
                command=self._cancel_inline_bundle
            ).pack(side="left", padx=2)

    def _select_bundle_from_dropdown(self, name):
        self.quick_copy_set_var.set(name)
        self._change_quick_copy_set(name)
        self._hide_quick_copy_bundle_dropdown()

    def _on_add_bundle_click(self):
        self._quick_copy_is_adding_bundle = True
        self._render_quick_copy_bundle_dropdown()

    def _confirm_inline_bundle(self):
        if not self.quick_copy_bundle_name_entry:
            return
        name = self.quick_copy_bundle_name_entry.get().strip()
        if not name:
            self.show_toast("Add Bundle", "Please enter a bundle name.", "info")
            return
        
        self.save_current_quick_copy_set(name)
        self._quick_copy_is_adding_bundle = False
        self._render_quick_copy_bundle_dropdown()

    def _cancel_inline_bundle(self):
        self._quick_copy_is_adding_bundle = False
        self._render_quick_copy_bundle_dropdown()


    def _show_bundle_manager(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Manage Skill Bundles")
        dialog.geometry("450x550")
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(False, False)
        
        # Center dialog
        self.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() - 450) // 2
        y = self.winfo_rooty() + (self.winfo_height() - 550) // 2
        dialog.geometry(f"+{x}+{y}")

        content = ctk.CTkFrame(dialog, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(content, text="Project Skill Bundles", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(0, 15), anchor="w")
        
        scroll = ctk.CTkScrollableFrame(content, fg_color=GLASS_BG, border_width=1, border_color=GLASS_BORDER)
        scroll.pack(fill="both", expand=True)

        def refresh_list():
            for child in scroll.winfo_children():
                child.destroy()
            
            names = sorted(self.quick_copy_config.get("skill_sets", {}).keys(), key=str.lower)
            if not names:
                ctk.CTkLabel(scroll, text="No saved bundles.", text_color=TEXT_MUTED).pack(pady=40)
                return

            for name in names:
                row = ctk.CTkFrame(scroll, fg_color="transparent")
                row.pack(fill="x", pady=4, padx=5)
                
                ctk.CTkLabel(row, text=name, font=ctk.CTkFont(weight="bold")).pack(side="left", padx=5)
                
                # Delete
                def do_delete(n=name):
                    self.delete_quick_copy_set(n)
                    refresh_list()
                
                ctk.CTkButton(
                    row, text="\u232b", width=34, height=32, 
                    fg_color=GLASS_CONTROL, hover_color=GLASS_CONTROL_HOVER,
                    text_color=CTK_STATUS_COLORS["error"], command=do_delete
                ).pack(side="right", padx=2)
                
                # Edit
                def do_edit(n=name):
                    self.edit_quick_copy_set(n)
                    # No refresh needed as edit opens its own dialog
                
                ctk.CTkButton(
                    row, text="\u270e", width=34, height=32,
                    fg_color=GLASS_CONTROL, hover_color=GLASS_CONTROL_HOVER,
                    command=do_edit
                ).pack(side="right", padx=2)

        refresh_list()
        
        ctk.CTkButton(content, text="Close", command=dialog.destroy).pack(pady=(15, 0))

    def _clear_quick_copy_bundle_selection(self):
        if "quick_copy_set_var" not in self.__dict__:
            return
        if not self._selected_quick_copy_set_name():
            return
        self.quick_copy_set_var.set(self._default_quick_copy_set_label())
        self._refresh_quick_copy_set_menu()
        self._refresh_quick_copy_set_details()

    def _refresh_quick_copy_set_details(self):
        label = self.__dict__.get("quick_copy_set_detail_label")
        if label is None:
            return
        set_name = self._selected_quick_copy_set_name()
        if not set_name:
            total = len(self.quick_copy_config.get("skill_sets", {}))
            noun = "bundle" if total == 1 else "bundles"
            label.configure(text=f"{total} saved {noun}. Save current selection to reuse skills and manuals together.")
            return
        label.configure(text=self._quick_copy_set_detail_text(set_name))

    def _quick_copy_set_detail_text(self, set_name):
        selected_set = self.quick_copy_config.get("skill_sets", {}).get(set_name, {})
        skill_count = len(selected_set.get("skill_keys", []))
        manual_count = len(selected_set.get("manual_references", []))
        updated_at = selected_set.get("updated_at") or "not dated"
        return f"{set_name}: {skill_count} project skill(s), {manual_count} manual reference(s). Updated {updated_at}."

    def _quick_copy_skill_key(self, skill):
        if skill.get("is_manual"):
            return self._quick_copy_manual_key(skill.get("manual_reference", ""))
        path = skill.get("local_path") or skill.get("skill_md_path") or ""
        if path:
            return os.path.normcase(os.path.abspath(path))
        return f"{skill.get('project_key', '')}:{skill.get('folder_name', '')}"

    def _quick_copy_manual_key(self, reference):
        return f"manual:{normalize_manual_reference(reference).casefold()}"

    def _quick_copy_manual_skills(self):
        return [
            self._quick_copy_manual_skill(reference)
            for reference in self.quick_copy_manual_references
        ]

    def _all_quick_copy_manual_skills(self):
        skills = []
        client_format = self.quick_copy_client_var.get()
        for project_key, data in self.quick_copy_manual_references_by_project.items():
            if not isinstance(data, dict):
                continue
            references = data.get(client_format, [])
            for reference in references:
                skill = self._quick_copy_manual_skill(reference)
                skill["project_key"] = project_key
                skill["project_label"] = self._quick_copy_project_label_for_key(project_key) or project_key
                skills.append(skill)
        return skills

    def _quick_copy_manual_skill(self, reference):
        reference = normalize_manual_reference(reference)
        name = self._quick_copy_manual_name(reference)
        return {
            "name": name,
            "description": reference,
            "folder_name": name,
            "manual_reference": reference,
            "is_manual": True,
            "project_key": self._current_quick_copy_project_key(),
            "project_label": self._current_quick_copy_project_label(),
            "target_path": "User-added references",
            "category": QUICK_COPY_MANUAL_CATEGORY,
            "search_text": f"{name} {reference} {QUICK_COPY_MANUAL_CATEGORY}".lower(),
        }

    def _quick_copy_manual_name(self, reference):
        text = normalize_manual_reference(reference)
        markdown_match = re.search(r"\]\(([^)]+)\)", text)
        if markdown_match:
            return Path(markdown_match.group(1)).parent.name or text
        stripped = text.lstrip("@").rstrip("/\\")
        if "/" in stripped or "\\" in stripped:
            return Path(stripped).parent.name or Path(stripped).stem or text
        return stripped or text

    def _all_quick_copy_skills(self, projects):
        return [skill for project in projects for skill in project.get("skills", [])]

    def load_skill_library(self):
        if self._library_search_after_id is not None:
            self.after_cancel(self._library_search_after_id)
            self._library_search_after_id = None
            
        self._clear_library_tree()
            
        self.library_refresh_btn.configure(state="disabled")
        self.library_search_entry.configure(state="disabled")
        self.library_category_menu.configure(state="disabled", values=["All Categories"])
        self.library_copy_to_projects_btn.configure(state="disabled")
        self.library_status_label.configure(text="Loading local skills...")
        self.library_tree.insert("", "end", text="Loading Library...", values=("",), tags=("category",), open=True)
        
        self._library_result_queue = queue.Queue(maxsize=1)
        thread = threading.Thread(target=self._load_skill_library_thread, daemon=True)
        thread.start()
        self.after(50, self._poll_skill_library_result)

    def _load_skill_library_thread(self):
        try:
            skills = self.load_local_skills()
            self._library_result_queue.put(("success", skills))
        except Exception as exc:
            self._library_result_queue.put(("error", exc))

    def _poll_skill_library_result(self):
        if self._library_result_queue is None:
            return
            
        try:
            status, payload = self._library_result_queue.get_nowait()
        except queue.Empty:
            self.after(50, self._poll_skill_library_result)
            return
            
        self._library_result_queue = None
        if status == "success":
            self._render_skill_library(payload)
        else:
            self._show_skill_library_error(payload)

    def _render_skill_library(self, skills):
        self._clear_library_tree()
            
        self.library_skills = skills
        self.filtered_library_skills = skills
        self.library_refresh_btn.configure(state="normal")
        self.library_search_entry.configure(state="normal")
        self.library_category_menu.configure(state="normal")
        self.library_copy_to_projects_btn.configure(state="normal")
        
        if not skills:
            self.library_status_label.configure(text="No skills found in configured source directories.")
            self.library_tree.insert("", "end", text="No skills found in source directories.", values=("",), tags=("category",), open=True)
            return
        
        categories = ["All Categories"] + sorted({skill.get("category", "Uncategorized") for skill in skills})
        self.library_category_menu.configure(values=categories)
        if self.library_category_var.get() not in categories:
            self.library_category_var.set("All Categories")
            
        self._apply_skill_library_filters()

    def _schedule_skill_library_filter(self, _event=None):
        if self._library_search_after_id is not None:
            self.after_cancel(self._library_search_after_id)
        self._library_search_after_id = self.after(200, self._apply_skill_library_filters)

    def _apply_skill_library_filters(self):
        self._library_search_after_id = None
        query = self.library_search_var.get().strip().lower()
        category = self.library_category_var.get()
        show_archived = self.library_show_archived_var.get()
        
        active_skills = []
        archived_skills = []
        for skill in self.library_skills:
            archived = self._is_skill_archived(skill)
            if not show_archived and archived:
                continue
            if category != "All Categories" and skill.get("category") != category:
                continue
            if query and query not in skill.get("search_text", ""):
                continue
            if archived:
                archived_skills.append(skill)
            else:
                active_skills.append(skill)
            
        active_skills = sorted(
            active_skills,
            key=lambda item: (item.get("category", "Uncategorized").lower(), item.get("name", "").lower())
        )
        archived_skills = sorted(
            archived_skills,
            key=lambda item: (item.get("category", "Uncategorized").lower(), item.get("name", "").lower())
        )
        self.filtered_library_skills = active_skills + archived_skills
        self.filtered_library_archived_skills = archived_skills
        self._render_skill_library_tree()

    def _render_skill_library_tree(self):
        # Cancel any existing library rendering operation
        if hasattr(self, "_library_render_after_id") and self._library_render_after_id:
            try:
                self.after_cancel(self._library_render_after_id)
            except tk.TclError:
                pass
            self._library_render_after_id = None

        self._clear_library_tree()
        self._hide_skill_detail_in_inspector()
        self._prune_library_selected_keys()
        
        if not self.filtered_library_skills:
            self.library_status_label.configure(text=f"0 shown ({self._archived_skill_count()} archived).")
            self.library_tree.insert("", "end", text="No matching skills.", values=("",), tags=("category",), open=True)
            self._sync_library_disclosure_button()
            self._update_library_selected_count()
            return
        
        archived_keys = {
            self._skill_archive_key(skill)
            for skill in getattr(self, "filtered_library_archived_skills", [])
        }
        
        # Prepare tasks: categories and their skills
        tasks = []
        category_map = {}
        for skill in self.filtered_library_skills:
            if self._skill_archive_key(skill) in archived_keys:
                continue
            category = skill.get("category", "Uncategorized")
            if category not in category_map:
                category_map[category] = []
            category_map[category].append(skill)
            
        # Add tasks for active categories
        for category in sorted(category_map.keys()):
            tasks.append(("category", (category, category_map[category])))

        # Add task for archived category if needed
        if archived_keys:
            tasks.append(("archived_category", ("Archived", getattr(self, "filtered_library_archived_skills", []))))

        self._run_library_render_batch(tasks)

    def _run_library_render_batch(self, tasks, batch_size=40):
        if not tasks:
            self._library_render_after_id = None
            total = len(self.filtered_library_skills)
            archived_count = self._archived_skill_count()
            self.library_status_label.configure(text=f"{total}/{len(self.library_skills)} shown, {archived_count} archived.")
            self._sync_library_disclosure_button()
            self._update_library_selected_count()
            return

        batch = tasks[:batch_size]
        remaining = tasks[batch_size:]

        for task_type, data in batch:
            if task_type == "category":
                category, category_skills = data
                category_id = self._insert_library_category(category)
                for skill in category_skills:
                    self._insert_library_skill(category_id, skill)
            elif task_type == "archived_category":
                category, archived_skills = data
                archived_id = self._insert_library_category(category, archived=True, count=len(archived_skills), selectable=False)
                for skill in archived_skills:
                    self._insert_library_skill(archived_id, skill)

        self._library_render_after_id = self.after(5, lambda: self._run_library_render_batch(remaining))

    def _clear_library_tree(self):
        self._hide_description_peek()
        for item in self.library_tree.get_children():
            self.library_tree.delete(item)
        self.library_tree_items = {}
        self.library_tree_categories = {}

    def _insert_library_category(self, category, archived=None, count=None, selectable=True):
        if count is None:
            count = sum(1 for skill in self.filtered_library_skills if skill.get("category", "Uncategorized") == category)
        if archived is None:
            archived = category in self.library_archive.get("archived_categories", set())
        label = f"{category} ({count})"
        if archived:
            label += " [Archived]" if category != "Archived" else ""
        is_open = category == "Archived" or (not self.library_category_state_loaded) or category in self.library_expanded_categories
        item_id = self.library_tree.insert(
            "",
            "end",
            text=label,
            values=("",),
            tags=("category", "archived") if archived else ("category",),
            open=is_open
        )
        if selectable:
            self.library_tree_categories[item_id] = category
        return item_id

    def _insert_library_skill(self, parent_id, skill):
        desc_text = self._row_description_summary(skill.get("description"))
        name = skill.get("name", "Unknown")
        selected = self._skill_archive_key(skill) in self.library_selected_skill_keys
        archived = self._is_skill_archived(skill)
        label = name
        if archived:
            label += " [Archived]"
            
        tags = ["skill"]
        if archived:
            tags.append("archived")
        if selected:
            tags.append("selected_skill")

        item_id = self.library_tree.insert(
            parent_id,
            "end",
            text=label,
            values=(desc_text,),
            tags=tuple(tags)
        )
        self.library_tree_items[item_id] = skill

    @staticmethod
    def _row_description_summary(description, max_chars=96):
        text = re.sub(r"\s+", " ", (description or "").strip())
        if not text:
            return "No description available."
        if len(text) <= max_chars:
            return text
        return text[: max_chars - 3].rstrip() + "..."

    def _inspector_widgets(self, prefix):
        return {
            "title": getattr(self, f"{prefix}_inspector_title"),
            "meta": getattr(self, f"{prefix}_inspector_meta"),
            "content_label": getattr(self, f"{prefix}_inspector_content_label"),
            "description": getattr(self, f"{prefix}_inspector_description"),
            "back_btn": getattr(self, f"{prefix}_inspector_back_btn"),
            "footer": getattr(self, f"{prefix}_inspector_footer"),
            "frame": getattr(self, f"{prefix}_inspector_frame"),
            "parent": getattr(self, f"{prefix}_inspector_parent"),
            "category_var": getattr(self, f"{prefix}_inspector_category_var"),
            "category_menu": getattr(self, f"{prefix}_inspector_category_menu"),
            "apply_category_btn": getattr(self, f"{prefix}_inspector_apply_category_btn"),
            "essentials_btn": getattr(self, f"{prefix}_inspector_essentials_btn", None),
            "archive_btn": getattr(self, f"{prefix}_inspector_archive_btn", None),
            "argument_var": getattr(self, f"{prefix}_inspector_argument_var", None),
            "argument_entry": getattr(self, f"{prefix}_inspector_argument_entry", None),
        }

    def _set_inspector_text(self, prefix, text):
        description = self._inspector_widgets(prefix)["description"]
        description.configure(state="normal")
        description.delete("1.0", "end")
        description.insert("1.0", text)
        description.configure(state="disabled")

    def _set_library_inspector_text(self, text):
        self._set_inspector_text("library", text)

    def _toggle_library_skill_from_click(self, event):
        if self.library_tree.identify("region", event.x, event.y) not in {"tree", "cell"}:
            return
        item_id = self.library_tree.identify_row(event.y)
        if not item_id:
            return
        if item_id in self.library_tree_categories:
            self._toggle_library_category_selection(self.library_tree_categories[item_id])
            self._remember_library_category_state()
            return
        skill = self.library_tree_items.get(item_id)
        if not skill:
            return
        self.toggle_library_skill_selection(skill)

    def toggle_library_skill_selection(self, skill):
        key = self._skill_archive_key(skill)
        if key in self.library_selected_skill_keys:
            self.library_selected_skill_keys.remove(key)
        else:
            self.library_selected_skill_keys.add(key)
        self._refresh_visible_skill_prefixes()
        self._update_library_selected_count()

    def _refresh_visible_skill_prefixes(self):
        if "library_tree" not in self.__dict__:
            return
        for item_id, skill in self.library_tree_items.items():
            name = skill.get("name", "Unknown")
            selected = self._skill_archive_key(skill) in self.library_selected_skill_keys
            archived = self._is_skill_archived(skill)
            label = name
            if archived:
                label += " [Archived]"
            self.library_tree.item(item_id, text=label)
            
            # Use tags for modern selection background
            tags = list(self.library_tree.item(item_id, "tags"))
            if selected:
                if "selected_skill" not in tags:
                    tags.append("selected_skill")
            else:
                if "selected_skill" in tags:
                    tags.remove("selected_skill")
            self.library_tree.item(item_id, tags=tuple(tags))

        for category_id, category in self.library_tree_categories.items():
            child_skills = [
                self.library_tree_items[skill_id]
                for skill_id in self.library_tree.get_children(category_id)
                if skill_id in self.library_tree_items
            ]
            selected = bool(child_skills) and all(
                self._skill_archive_key(skill) in self.library_selected_skill_keys
                for skill in child_skills
            )
            tags = list(self.library_tree.item(category_id, "tags"))
            if selected:
                if "selected_skill" not in tags:
                    tags.append("selected_skill")
            else:
                if "selected_skill" in tags:
                    tags.remove("selected_skill")
            self.library_tree.item(category_id, tags=tuple(tags))

    def _update_library_selected_count(self):
        if "library_selected_count_label" in self.__dict__:
            count = len(self.library_selected_skill_keys)
            noun = "skill" if count == 1 else "skills"
            self.library_selected_count_label.configure(text=f"{count} selected {noun}")
        self._sync_library_select_visible_check()

    def _update_library_inspector_archive_button(self, skill=None):
        button = self.__dict__.get("library_inspector_archive_btn")
        if not button:
            return
        skill = skill or self.__dict__.get("_current_inspector_skill")
        if not skill or self.__dict__.get("_current_inspector_prefix") != "library":
            button.configure(text="Archive", state="disabled", fg_color=GLASS_CONTROL, text_color=TEXT_MAIN)
            return
        archived = self._is_skill_archived(skill)
        button.configure(
            text="Unarchive" if archived else "Archive",
            state="normal",
            fg_color=GLASS_CONTROL if archived else CTK_STATUS_COLORS["info"],
            text_color=TEXT_MAIN,
        )

    def toggle_current_inspector_archive(self):
        skill = self.__dict__.get("_current_inspector_skill")
        if not skill or self.__dict__.get("_current_inspector_prefix") != "library":
            self.show_toast("Archive", "Open a Library skill first.", "info")
            return

        key = self._skill_archive_key(skill)
        category = skill.get("category", "Uncategorized")
        if self._is_skill_archived(skill):
            changed = False
            if key in self.library_archive["archived_skills"]:
                self.library_archive["archived_skills"].remove(key)
                changed = True
            elif category in self.library_archive["archived_categories"]:
                self.library_archive["archived_categories"].remove(category)
                changed = True
            if changed:
                self.save_library_archive()
                self.show_toast("Unarchived", skill.get("name", "Skill"), "success")
        else:
            self.library_archive["archived_skills"].add(key)
            self.save_library_archive()
            self.show_toast("Archived", skill.get("name", "Skill"), "success")

        self._update_library_inspector_archive_button(skill)
        self._apply_skill_library_filters()

    def _sync_library_select_visible_check(self):
        visible_skills = list(self.__dict__.get("filtered_library_skills", []))
        selected = bool(visible_skills) and all(
            self._skill_archive_key(skill) in self.library_selected_skill_keys
            for skill in visible_skills
        )
        if "library_select_visible_var" in self.__dict__:
            self.library_select_visible_var.set(selected)
        if "library_select_visible_check" in self.__dict__:
            state = "normal" if visible_skills else "disabled"
            self.library_select_visible_check.configure(state=state)

    def _show_skill_detail_in_inspector_from_library(self, _event=None):
        selection = self.library_tree.selection()
        if not selection:
            self._hide_skill_detail_in_inspector("library")
            return
        skill = self.library_tree_items.get(selection[0])
        if skill:
            self._show_skill_detail_in_inspector(skill, "library")

    def _show_skill_detail_in_inspector_from_quick_copy(self, _event=None):
        selection = self.quick_copy_tree.selection()
        if not selection:
            self._hide_skill_detail_in_inspector("quick_copy")
            return
        skill = self.quick_copy_tree_items.get(selection[0])
        if skill and skill.get("is_manual"):
            self.clipboard_clear()
            self.clipboard_append(skill.get("manual_reference", ""))
            self.update()
            self.quick_copy_status_label.configure(text=f"Copied manual: {skill.get('name', 'Manual')}")
        if skill:
            self._show_skill_detail_in_inspector(skill, "quick_copy")

    def _apply_overlay_category(self):
        prefix = getattr(self, "_current_inspector_prefix", "library")
        new_category = self.inspector_overlay.category_var.get()
        if not new_category:
            self.show_toast("Category", "Please select a category.", "warning")
            return
            
        skill = getattr(self, "_current_inspector_skill", None)
        if not skill:
            return
            
        # Perform the actual save logic
        self._save_skill_category(skill, new_category)
        
        # Then reload depending on prefix
        if prefix == "library":
            self._load_skill_library()
            self._refresh_library_category_options()
        elif prefix == "quick_copy":
            self.load_quick_copy()
            self._apply_quick_copy_filters()
            self._update_quick_copy_category_options()
            
    def _toggle_overlay_action(self):
        prefix = getattr(self, "_current_inspector_prefix", "library")
        if prefix == "quick_copy":
            self.toggle_current_inspector_essential()
        else:
            self.archive_selected_library_item()

    def _save_skill_category(self, skill, new_category):
        skill_file = skill.get("skill_md_path")
        if not skill_file or not os.path.exists(skill_file):
            self.show_toast("Category", f"SKILL.md not found for '{skill.get('name')}'.", "error")
            return
            
        try:
            with open(skill_file, "r", encoding="utf-8") as f:
                lines = f.readlines()

            category_updated = False
            in_frontmatter = False

            for i, line in enumerate(lines):
                if i == 0 and line.startswith("---"):
                    in_frontmatter = True
                    continue
                if in_frontmatter and line.startswith("---"):
                    in_frontmatter = False
                    if not category_updated:
                        lines.insert(i, f"category: {new_category}\n")
                    break

                if in_frontmatter and line.startswith("category:"):
                    lines[i] = f"category: {new_category}\n"
                    category_updated = True

            with open(skill_file, "w", encoding="utf-8") as f:
                f.writelines(lines)
            
            skill["category"] = new_category
            self.show_toast("Category", f"Category for '{skill.get('name')}' updated to '{new_category}'.", "success")
        except OSError as exc:
            self.show_toast("Category", f"Failed to write updated category: {exc}", "error")

    def _show_skill_detail_in_inspector(self, skill_data, prefix="library"):
        self._hide_description_peek()
        if not skill_data.get("raw_content") and skill_data.get("skill_md_path"):
            try:
                with open(skill_data["skill_md_path"], "r", encoding="utf-8") as f:
                    skill_data["raw_content"] = f.read()
            except OSError as exc:
                skill_data["raw_content"] = f"Unable to read SKILL.md: {exc}"

        self._current_inspector_skill = skill_data
        self._current_inspector_prefix = prefix
        
        name = skill_data.get("name", "Unknown")
        category = skill_data.get("category", "Uncategorized")
        source = skill_data.get("local_path") or skill_data.get("target_path") or ""
        
        # Prepare metadata for overlay
        display_metadata = {
            "Category": category,
            "Path": source
        }
        raw_metadata = skill_data.get("metadata") or {}
        for key in ("source", "version", "date_added", "risk"):
            if raw_metadata.get(key):
                display_metadata[key.replace("_", " ").title()] = raw_metadata.get(key)
        
        content = skill_data.get("raw_content") or skill_data.get("description") or "No content available."
        
        # Update overlay core content
        self.inspector_overlay.set_content(name, display_metadata, content, prefix=prefix)
        
        # Configure overlay interactive controls
        self.inspector_overlay.category_menu.configure(values=self._skill_category_options())
        self.inspector_overlay.category_var.set(category)

        if prefix == "quick_copy":
            is_essential = self._is_quick_copy_skill_essential(skill_data)
            self.inspector_overlay.action_btn.configure(
                text="Remove from Essentials" if is_essential else "Add to Essentials",
                state="normal"
            )
            arg_val = self._get_quick_copy_skill_argument(skill_data)
            self.inspector_overlay.argument_var.set(arg_val)
        else:
            is_archived = self._is_skill_archived(skill_data)
            self.inspector_overlay.action_btn.configure(
                text="Restore" if is_archived else "Archive",
                state="disabled" if getattr(self, "library_archive_loading", False) else "normal"
            )

        # Show overlay
        # relwidth is 0.4 in peek mode, maybe 0.6 if we wanted "expanded"
        self.inspector_overlay.show(x_rel=0.55, y_rel=0.05, width_rel=0.4, height_rel=0.9)

    def _hide_skill_detail_in_inspector(self, prefix="library"):
        self._current_inspector_skill = None
        self._current_inspector_prefix = None
        widgets = self._inspector_widgets(prefix)
        widgets["title"].configure(text="Skill Details")
        widgets["meta"].configure(text="No skill open.")
        self._set_inspector_text(prefix, "Double-click a skill to open it here.")
        widgets["back_btn"].grid_forget()
        widgets["content_label"].grid_remove()
        widgets["footer"].grid_forget()
        if prefix == "quick_copy":
            self._update_quick_copy_inspector_essentials_button(None)
            arg_var = widgets.get("argument_var")
            if arg_var:
                arg_var.set("")
        elif prefix == "library":
            self._update_library_inspector_archive_button(None)
        widgets["frame"].grid_remove()
        widgets["parent"].grid_columnconfigure(2, weight=0)

    def _skill_category_options(self, *extra_categories):
        categories = set(SKILL_CATEGORY_NAMES)
        for skill in self.__dict__.get("library_skills", []):
            category = skill.get("category")
            if category:
                categories.add(str(category))
        for category in extra_categories:
            if category:
                categories.add(str(category))
        return sorted(categories, key=str.casefold)

    def _apply_current_inspector_category(self, prefix="library"):
        skill = self.__dict__.get("_current_inspector_skill")
        if not skill or skill.get("is_manual"):
            return
        widgets = self._inspector_widgets(prefix)
        new_category = widgets["category_var"].get().strip() or "Uncategorized"
        old_category = skill.get("category", "Uncategorized")
        if new_category == old_category:
            self.show_toast("Category", f"'{skill.get('name', 'Skill')}' is already in {new_category}.", "info")
            return

        self._update_skill_category(skill, new_category)
        self.show_toast("Category updated", f"Moved '{skill.get('name', 'Skill')}' to {new_category}.", "success")
        if prefix == "quick_copy" and callable(getattr(self, "load_quick_copy", None)):
            self.load_quick_copy()
        if "library_tree" in self.__dict__:
            self._apply_skill_library_filters()

    def _update_skill_category(self, skill, new_category):
        new_category = str(new_category or "Uncategorized").strip() or "Uncategorized"
        target_keys = {
            self._skill_archive_key(skill),
            os.path.normcase(os.path.abspath(skill.get("skill_md_path", ""))) if skill.get("skill_md_path") else "",
            os.path.normcase(os.path.abspath(skill.get("local_path", ""))) if skill.get("local_path") else "",
        }
        target_keys.discard("")

        updated = False
        for collection_name in ("library_skills", "filtered_library_skills"):
            for candidate in self.__dict__.get(collection_name, []):
                candidate_keys = {
                    self._skill_archive_key(candidate),
                    os.path.normcase(os.path.abspath(candidate.get("skill_md_path", ""))) if candidate.get("skill_md_path") else "",
                    os.path.normcase(os.path.abspath(candidate.get("local_path", ""))) if candidate.get("local_path") else "",
                }
                candidate_keys.discard("")
                if target_keys & candidate_keys:
                    candidate["category"] = new_category
                    candidate["search_text"] = self._build_skill_search_text(candidate)
                    updated = True

        skill["category"] = new_category
        skill["search_text"] = self._build_skill_search_text(skill)
        self._save_skill_category_to_cache(skill, new_category)
        return updated

    def _save_skill_category_to_cache(self, skill, new_category):
        skill_md_path = skill.get("skill_md_path")
        if not skill_md_path:
            return
        cache_key = os.path.normcase(os.path.abspath(skill_md_path))
        cache = self._load_skill_library_cache()
        entry = cache.get("skills", {}).get(cache_key)
        if not entry:
            return
        data = dict(entry.get("data", {}))
        data["category"] = new_category
        data["search_text"] = self._build_skill_search_text(data)
        entry["data"] = data
        cache["skills"][cache_key] = entry
        self._save_skill_library_cache(cache)

    def _add_current_inspector_skill_to_updater(self):
        if self._current_inspector_skill:
            self.add_skill_to_updater_from_library(self._current_inspector_skill)

    def _prune_library_selected_keys(self):
        available_keys = {self._skill_archive_key(skill) for skill in self.library_skills}
        self.library_selected_skill_keys.intersection_update(available_keys)

    def select_all_visible_library_skills(self):
        visible_skills = list(self.__dict__.get("filtered_library_skills", []))
        self._set_library_skills_selected(visible_skills, True)
        if "library_status_label" in self.__dict__:
            self.library_status_label.configure(text=f"Selected {len(visible_skills)} visible skill(s).")

    def deselect_all_library_skills(self):
        self.library_selected_skill_keys.clear()
        self._sync_library_tree_selection()
        if "library_status_label" in self.__dict__:
            self.library_status_label.configure(text="Deselected all library skills.")

    def _toggle_library_select_visible_from_check(self):
        if self.library_select_visible_var.get():
            self.select_all_visible_library_skills()
        else:
            self.deselect_all_library_skills()

    def select_current_library_category(self):
        self._set_current_library_category_selected(True)

    def deselect_current_library_category(self):
        self._set_current_library_category_selected(False)

    def _toggle_library_category_selection(self, category):
        skills = [
            skill for skill in self.__dict__.get("filtered_library_skills", [])
            if skill.get("category", "Uncategorized") == category
        ]
        if not skills:
            return
        should_select = not all(
            self._skill_archive_key(skill) in self.library_selected_skill_keys
            for skill in skills
        )
        self._set_library_skills_selected(skills, should_select)
        action = "Selected" if should_select else "Deselected"
        if "library_status_label" in self.__dict__:
            self.library_status_label.configure(text=f"{action} {len(skills)} skill(s) in {category}.")

    def _set_current_library_category_selected(self, selected):
        category = self._current_library_action_category()
        if not category:
            self.show_toast("Category selection", "Choose or select a category first.", "info")
            return
        skills = [
            skill for skill in self.__dict__.get("filtered_library_skills", [])
            if skill.get("category", "Uncategorized") == category
        ]
        self._set_library_skills_selected(skills, selected)
        action = "Selected" if selected else "Deselected"
        if "library_status_label" in self.__dict__:
            self.library_status_label.configure(text=f"{action} {len(skills)} skill(s) in {category}.")

    def _current_library_action_category(self):
        tree = self.__dict__.get("library_tree")
        if tree is not None:
            for item_id in tree.selection():
                category = self.library_tree_categories.get(item_id)
                if category:
                    return category
                skill = self.library_tree_items.get(item_id)
                if skill:
                    return skill.get("category", "Uncategorized")
        category = self.library_category_var.get() if "library_category_var" in self.__dict__ else ""
        return "" if category == "All Categories" else category

    def _set_library_skills_selected(self, skills, selected):
        for skill in skills:
            key = self._skill_archive_key(skill)
            if selected:
                self.library_selected_skill_keys.add(key)
            else:
                self.library_selected_skill_keys.discard(key)
        self._sync_library_tree_selection()

    def _sync_library_tree_selection(self):
        if "library_tree" in self.__dict__:
            selected_items = [
                item_id for item_id, skill in self.library_tree_items.items()
                if self._skill_archive_key(skill) in self.library_selected_skill_keys
            ]
            for category_id in self.library_tree_categories:
                child_skills = [
                    self.library_tree_items[skill_id]
                    for skill_id in self.library_tree.get_children(category_id)
                    if skill_id in self.library_tree_items
                ]
                if child_skills and all(
                    self._skill_archive_key(skill) in self.library_selected_skill_keys
                    for skill in child_skills
                ):
                    selected_items.append(category_id)
            self.library_tree.selection_set(selected_items)
        self._refresh_visible_skill_prefixes()
        self._update_library_selected_count()

    def _open_selected_library_skill(self, _event=None):
        selection = self.library_tree.selection()
        if not selection:
            return
        skill = self.library_tree_items.get(selection[0])
        if skill:
            self._show_skill_detail_in_inspector(skill, "library")

    def _set_tree_disclosure_state(self, tree, is_open):
        for item_id in self._tree_disclosure_rows(tree):
            tree.item(item_id, open=is_open)

    def _tree_disclosure_rows(self, tree):
        rows = []

        def collect(parent_id):
            for item_id in tree.get_children(parent_id):
                children = tree.get_children(item_id)
                if children:
                    rows.append(item_id)
                    collect(item_id)

        collect("")
        return rows

    def _tree_has_collapsed_disclosure(self, tree):
        return any(not bool(tree.item(item_id, "open")) for item_id in self._tree_disclosure_rows(tree))

    def _sync_tree_disclosure_button(self, tree, button):
        rows = self._tree_disclosure_rows(tree)
        if not rows:
            button.configure(text=DISCLOSURE_EXPAND_ICON, state="disabled")
            return
        icon = DISCLOSURE_EXPAND_ICON if self._tree_has_collapsed_disclosure(tree) else DISCLOSURE_COLLAPSE_ICON
        button.configure(text=icon, state="normal")

    def _sync_quick_copy_disclosure_button(self):
        if "quick_copy_disclosure_btn" in self.__dict__:
            self._sync_tree_disclosure_button(self.quick_copy_tree, self.quick_copy_disclosure_btn)

    def _sync_library_disclosure_button(self):
        if "library_disclosure_btn" in self.__dict__:
            self._sync_tree_disclosure_button(self.library_tree, self.library_disclosure_btn)

    def toggle_all_quick_copy_categories(self):
        if self._tree_has_collapsed_disclosure(self.quick_copy_tree):
            self.expand_all_quick_copy_categories()
        else:
            self.collapse_all_quick_copy_categories()

    def toggle_all_library_categories(self):
        if self._tree_has_collapsed_disclosure(self.library_tree):
            self.expand_all_library_categories()
        else:
            self.collapse_all_library_categories()

    def expand_all_quick_copy_categories(self):
        self._set_tree_disclosure_state(self.quick_copy_tree, True)
        self._sync_quick_copy_disclosure_button()

    def collapse_all_quick_copy_categories(self):
        self._set_tree_disclosure_state(self.quick_copy_tree, False)
        self._sync_quick_copy_disclosure_button()

    def expand_all_library_categories(self):
        self._set_tree_disclosure_state(self.library_tree, True)
        self._sync_library_disclosure_button()
        self._capture_library_category_state()
        self.save_library_clipboard_preferences()

    def collapse_all_library_categories(self):
        self._set_tree_disclosure_state(self.library_tree, False)
        self._sync_library_disclosure_button()
        self._capture_library_category_state()
        self.save_library_clipboard_preferences()

    def _remember_library_category_state(self, _event=None):
        self.after(50, self._save_library_category_state_after_tree_update)

    def _save_library_category_state_after_tree_update(self):
        self._capture_library_category_state()
        self.save_library_clipboard_preferences()

    def _save_library_category_state_on_destroy(self, event):
        if event.widget is getattr(self, "library_tree", None):
            try:
                self._capture_library_category_state()
                self.save_library_clipboard_preferences()
            except tk.TclError:
                pass

    def _capture_library_category_state(self):
        self.library_category_state_loaded = True
        self.library_clipboard_config["category_state_saved"] = True
        tree_categories = getattr(self, "library_tree_categories", {})
        self.library_expanded_categories = {
            category for item_id, category in tree_categories.items()
            if self.library_tree.item(item_id, "open")
        }

    def copy_selected_skill_folders_to_projects(self):
        skills = self._selected_library_skills()
        if not skills:
            self.show_toast("Copy skills", "Select one or more skills before copying to projects.", "info")
            return
        if not self.targets:
            self.show_toast("Missing targets", "Add one or more target directories in Projects first.", "warning")
            return

        selected_targets = self._choose_library_copy_targets(skills)
        if not selected_targets:
            return

        self._set_library_copy_running(True)
        thread = threading.Thread(
            target=self._copy_selected_skill_folders_thread,
            args=(skills, selected_targets),
            daemon=True
        )
        thread.start()

    def _choose_library_copy_targets(self, skills):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Copy Skills to Projects")
        dialog.geometry("720x460")
        dialog.minsize(560, 360)
        dialog.transient(self)
        dialog.grab_set()

        dialog.grid_columnconfigure(0, weight=1)
        dialog.grid_rowconfigure(1, weight=1)

        header_text = f"Copy {len(skills)} selected skill folder(s) to project target directories."
        ctk.CTkLabel(dialog, text=header_text, font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, padx=16, pady=(16, 8), sticky="w"
        )

        target_frame = ctk.CTkScrollableFrame(dialog)
        target_frame.grid(row=1, column=0, padx=16, pady=8, sticky="nsew")
        target_frame.grid_columnconfigure(0, weight=1)

        target_vars = []
        for idx, target in enumerate(self.targets):
            var = tk.BooleanVar(value=True)
            target_vars.append((target, var))
            ctk.CTkCheckBox(target_frame, text=target, variable=var).grid(
                row=idx, column=0, padx=8, pady=6, sticky="w"
            )

        selected_targets = []

        def cancel():
            dialog.destroy()

        def confirm():
            chosen = [target for target, var in target_vars if var.get()]
            if not chosen:
                self.show_toast("Copy skills", "Select at least one project target.", "info", parent=dialog)
                return
            selected_targets.extend(chosen)
            dialog.destroy()

        button_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        button_frame.grid(row=2, column=0, padx=16, pady=(8, 16), sticky="ew")
        button_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkButton(button_frame, text="Cancel", width=100, command=cancel).grid(row=0, column=1, padx=6, sticky="e")
        ctk.CTkButton(button_frame, text="Copy Folders", width=120, command=confirm).grid(row=0, column=2, padx=6, sticky="e")

        self.wait_window(dialog)
        return selected_targets

    def _copy_selected_skill_folders_thread(self, skills, targets):
        try:
            result = copy_skill_folders_to_targets(skills, targets)
            self.after(0, lambda: self._show_library_copy_result(result))
        except Exception as exc:
            self.after(0, lambda error=str(exc): self.show_toast("Copy failed", error, "error"))
        finally:
            self.after(0, lambda: self._set_library_copy_running(False))

    def _set_library_copy_running(self, is_running):
        state = "disabled" if is_running else "normal"
        self.library_copy_to_projects_btn.configure(state=state, text="Copying..." if is_running else "Copy to Projects")

    def _show_library_copy_result(self, result):
        copied = result.get("copied", 0)
        merged = result.get("merged", 0)
        skipped = result.get("skipped", 0)
        failed = result.get("failed", 0)
        total_done = copied + merged
        self.library_status_label.configure(
            text=f"Copied {copied}, merged {merged}, skipped {skipped}, failed {failed}."
        )

        problem_lines = [
            f"- {item.get('skill')}: {item.get('message')}"
            for item in result.get("details", [])
            if item.get("status") in {"skipped", "failed"}
        ][:8]
        suffix = ""
        if problem_lines:
            suffix = "\n\nIssues:\n" + "\n".join(problem_lines)
            remaining = skipped + failed - len(problem_lines)
            if remaining > 0:
                suffix += f"\n...and {remaining} more."

        self.show_toast(
            "Copy skills complete",
            f"Copied: {copied}. Merged: {merged}. Skipped: {skipped}. Failed: {failed}. Total copied/merged: {total_done}.{suffix}",
            "success" if failed == 0 else "warning",
            duration=6000,
        )

    def _selected_library_skills(self):
        if self.library_selected_skill_keys:
            result = []
            seen = set()
            for category_id in self.library_tree.get_children(""):
                for skill_id in self.library_tree.get_children(category_id):
                    skill = self.library_tree_items.get(skill_id)
                    if not skill:
                        continue
                    key = self._skill_archive_key(skill)
                    if key in self.library_selected_skill_keys and key not in seen:
                        seen.add(key)
                        result.append(skill)
            return result

        selected = set(self.library_tree.selection())
        if not selected:
            return []

        result = []
        seen = set()

        for category_id in self.library_tree.get_children(""):
            if category_id in selected:
                for skill_id in self.library_tree.get_children(category_id):
                    self._append_selected_skill(skill_id, result, seen)
                continue

            for skill_id in self.library_tree.get_children(category_id):
                if skill_id in selected:
                    self._append_selected_skill(skill_id, result, seen)

        return result

    def _append_selected_skill(self, item_id, result, seen):
        skill = self.library_tree_items.get(item_id)
        if not skill:
            return
        key = self._skill_archive_key(skill)
        if key in seen:
            return
        seen.add(key)
        result.append(skill)

    def load_library_clipboard_config(self):
        try:
            with open(SKILL_LIBRARY_CLIPBOARD_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            data = {}

        skill_sets = data.get("skill_sets", {})
        if not isinstance(skill_sets, dict):
            skill_sets = {}

        client_format = data.get("client_format", "Codex")
        if client_format not in {"Codex", "Gemini CLI", "Antigravity", "Plain Path"}:
            client_format = "Codex"

        return {
            "client_format": client_format,
            "skill_sets": skill_sets,
            "expanded_categories": data.get("expanded_categories", []),
            "category_state_saved": bool(
                data["category_state_saved"] if "category_state_saved" in data else "expanded_categories" in data
            )
        }

    def load_quick_copy_config(self):
        try:
            with open(QUICK_COPY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            data = {}

        if not data:
            data = {"client_format": self.library_clipboard_config.get("client_format", "Codex")}

        client_format = data.get("client_format", "Codex")
        if client_format not in CLIENT_FORMATS:
            client_format = "Codex"

        skill_sets = data.get("skill_sets", {})
        if not isinstance(skill_sets, dict):
            skill_sets = {}

        manual_references = data.get("manual_references", [])
        if not isinstance(manual_references, list):
            manual_references = []
        manual_references = merge_manual_references([], manual_references)

        manual_references_by_project = data.get("manual_references_by_project", {})
        if not isinstance(manual_references_by_project, dict):
            manual_references_by_project = {}
        
        parsed_references = {}
        for project_key, project_data in manual_references_by_project.items():
            if isinstance(project_data, dict):
                parsed_references[str(project_key)] = {
                    str(client): merge_manual_references([], refs)
                    for client, refs in project_data.items()
                    if isinstance(refs, list)
                }
            elif isinstance(project_data, list):
                # Handle legacy migration during load
                parsed_references[str(project_key)] = {
                    client_format: merge_manual_references([], project_data)
                }
        manual_references_by_project = parsed_references

        essential_skill_keys = data.get("essential_skill_keys", [])
        if not isinstance(essential_skill_keys, list):
            essential_skill_keys = []

        essential_skill_keys_by_project = data.get("essential_skill_keys_by_project", {})
        if not isinstance(essential_skill_keys_by_project, dict):
            essential_skill_keys_by_project = {}
        essential_skill_keys_by_project = {
            str(project_key): sorted({str(key) for key in keys if str(key).strip()})
            for project_key, keys in essential_skill_keys_by_project.items()
            if isinstance(keys, list)
        }

        selected_project_key = str(data.get("selected_project_key", "")).strip()

        selected_skill_keys_by_project = data.get("selected_skill_keys_by_project", {})
        if not isinstance(selected_skill_keys_by_project, dict):
            selected_skill_keys_by_project = {}
        selected_skill_keys_by_project = {
            str(project_key): sorted({str(key) for key in keys if str(key).strip()})
            for project_key, keys in selected_skill_keys_by_project.items()
            if isinstance(keys, list)
        }

        skill_arguments_by_project = data.get("skill_arguments_by_project", {})
        if not isinstance(skill_arguments_by_project, dict):
            skill_arguments_by_project = {}

        return {
            "client_format": client_format,
            "skill_sets": skill_sets,
            "manual_references": manual_references,
            "manual_references_by_project": manual_references_by_project,
            "essential_skill_keys": sorted({str(key) for key in essential_skill_keys if str(key).strip()}),
            "essential_skill_keys_by_project": essential_skill_keys_by_project,
            "selected_project_key": selected_project_key,
            "selected_skill_keys_by_project": selected_skill_keys_by_project,
            "skill_arguments_by_project": skill_arguments_by_project,
        }

    def save_quick_copy_preferences(self):
        client_format = self.quick_copy_config.get("client_format", "Codex")
        if hasattr(self, "quick_copy_client_var"):
            client_format = self.quick_copy_client_var.get()
        if client_format not in CLIENT_FORMATS:
            client_format = "Codex"

        self.quick_copy_config["client_format"] = client_format
        self._remember_quick_copy_manual_references_for_current_project()
        self.quick_copy_config["manual_references"] = merge_manual_references(
            [],
            self.quick_copy_config.get("manual_references", []),
        )
        self.quick_copy_config["manual_references_by_project"] = {
            str(project_key): {
                str(client): merge_manual_references([], refs)
                for client, refs in project_data.items()
            }
            for project_key, project_data in getattr(self, "quick_copy_manual_references_by_project", {}).items()
        }
        self.quick_copy_config["essential_skill_keys"] = sorted(
            self.quick_copy_config.get("essential_skill_keys", [])
        )
        self._remember_quick_copy_essentials_for_current_project()
        self.quick_copy_config["essential_skill_keys_by_project"] = {
            str(project_key): sorted(keys)
            for project_key, keys in getattr(self, "quick_copy_essential_skill_keys_by_project", {}).items()
        }
        self._remember_quick_copy_selection_for_current_project()
        self.quick_copy_config["selected_project_key"] = getattr(self, "quick_copy_selected_project_key", "")
        self.quick_copy_config["selected_skill_keys_by_project"] = {
            str(project_key): sorted(keys)
            for project_key, keys in getattr(self, "quick_copy_selected_skill_keys_by_project", {}).items()
        }
        data = {
            "client_format": client_format,
            "skill_sets": self.quick_copy_config.get("skill_sets", {}),
            "manual_references": self.quick_copy_config.get("manual_references", []),
            "manual_references_by_project": self.quick_copy_config.get("manual_references_by_project", {}),
            "essential_skill_keys": self.quick_copy_config.get("essential_skill_keys", []),
            "essential_skill_keys_by_project": self.quick_copy_config.get("essential_skill_keys_by_project", {}),
            "selected_project_key": self.quick_copy_config.get("selected_project_key", ""),
            "selected_skill_keys_by_project": self.quick_copy_config.get("selected_skill_keys_by_project", {}),
            "skill_arguments_by_project": self.quick_copy_config.get("skill_arguments_by_project", {}),
        }
        tmp_path = f"{QUICK_COPY_FILE}.tmp"
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, QUICK_COPY_FILE)
        except OSError as exc:
            print(f"Error saving Quick Copy config: {exc}")
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except OSError:
                pass

    def save_library_clipboard_preferences(self):
        client_format = self.library_clipboard_config.get("client_format", "Codex")
        if hasattr(self, "library_client_var"):
            client_format = self.library_client_var.get()
        self.library_clipboard_config["client_format"] = client_format
        self.library_clipboard_config["expanded_categories"] = sorted(self.library_expanded_categories)
        self.library_clipboard_config["category_state_saved"] = bool(self.library_category_state_loaded)
        data = {
            "client_format": self.library_clipboard_config.get("client_format", "Codex"),
            "skill_sets": self.library_clipboard_config.get("skill_sets", {}),
            "expanded_categories": self.library_clipboard_config.get("expanded_categories", []),
            "category_state_saved": self.library_clipboard_config.get("category_state_saved", False)
        }
        tmp_path = f"{SKILL_LIBRARY_CLIPBOARD_FILE}.tmp"
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, SKILL_LIBRARY_CLIPBOARD_FILE)
        except OSError as exc:
            print(f"Error saving Library clipboard config: {exc}")
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except OSError:
                pass

    def on_close(self):
        # Save all configurations before closing
        self.save_config()
        
        try:
            if hasattr(self, "library_tree") and self.library_tree.winfo_exists():
                self._capture_library_category_state()
                self.save_library_clipboard_preferences()
        except tk.TclError:
            pass
        self.save_quick_copy_preferences()
        self.destroy()

    def archive_selected_library_item(self):
        selection = self.library_tree.selection()
        if not selection:
            self.show_toast("Archive", "Select a skill or category to archive.", "info")
            return

        item_id = selection[0]
        category = self.library_tree_categories.get(item_id)
        if category:
            if category not in self.library_archive["archived_categories"]:
                self.library_archive["archived_categories"].add(category)
                self.save_library_archive()
            self._apply_skill_library_filters()
            return

        skill = self.library_tree_items.get(item_id)
        if not skill:
            return

        key = self._skill_archive_key(skill)
        if key not in self.library_archive["archived_skills"]:
            self.library_archive["archived_skills"].add(key)
            self.save_library_archive()
        self._apply_skill_library_filters()

    def unarchive_selected_library_item(self):
        selection = self.library_tree.selection()
        if not selection:
            self.show_toast("Unarchive", "Enable Show Archived, then select an archived skill or category.", "info")
            return

        item_id = selection[0]
        category = self.library_tree_categories.get(item_id)
        if category:
            if category in self.library_archive["archived_categories"]:
                self.library_archive["archived_categories"].remove(category)
                self.save_library_archive()
            self._apply_skill_library_filters()
            return

        skill = self.library_tree_items.get(item_id)
        if not skill:
            return

        key = self._skill_archive_key(skill)
        category = skill.get("category", "Uncategorized")
        if key in self.library_archive["archived_skills"]:
            self.library_archive["archived_skills"].remove(key)
            self.save_library_archive()
            self._apply_skill_library_filters()
        elif category in self.library_archive["archived_categories"]:
            self.show_toast("Unarchive", "This skill is hidden by an archived category. Select the category row to unarchive it.", "info")

    def _skill_archive_key(self, skill):
        path = skill.get("local_path") or skill.get("skill_md_path") or skill.get("folder_name") or skill.get("name", "")
        if path:
            return os.path.normcase(os.path.abspath(path))
        return str(skill.get("name", ""))

    def _is_skill_archived(self, skill):
        category = skill.get("category", "Uncategorized")
        if category in self.library_archive.get("archived_categories", set()):
            return True
        return self._skill_archive_key(skill) in self.library_archive.get("archived_skills", set())

    def _archived_skill_count(self):
        return sum(1 for skill in self.library_skills if self._is_skill_archived(skill))

    def load_library_archive(self):
        try:
            with open(SKILL_LIBRARY_ARCHIVE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            data = {}

        return {
            "archived_skills": set(data.get("archived_skills", [])),
            "archived_categories": set(data.get("archived_categories", []))
        }

    def save_library_archive(self):
        data = {
            "archived_skills": sorted(self.library_archive.get("archived_skills", set())),
            "archived_categories": sorted(self.library_archive.get("archived_categories", set()))
        }
        tmp_path = f"{SKILL_LIBRARY_ARCHIVE_FILE}.tmp"
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, SKILL_LIBRARY_ARCHIVE_FILE)
        except OSError as exc:
            print(f"Error saving Library archive: {exc}")
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except OSError:
                pass

    def _show_skill_library_error(self, error):
        self.library_refresh_btn.configure(state="normal")
        self.library_status_label.configure(text="Failed to load Library.")
        self._clear_library_tree()
        self.library_tree.insert("", "end", text=f"Failed to load skills: {error}", values=("",), tags=("category",), open=True)

    def load_local_skills(self):
        # Wait for background data loading to complete
        self._data_ready.wait()
        
        local_skills = []
        source_dirs = self.sources if self.sources else [os.path.expanduser("~/.gemini/skills")]
        
        cached_skills = self.skill_cache.get("skills", {})
        cache_dirty = False
        next_cache = {
            "version": SKILL_LIBRARY_CACHE_VERSION,
            "skills": {}
        }
            
        for base_dir in source_dirs:
            skills_dir = os.path.expanduser(base_dir)
            if not os.path.exists(skills_dir):
                continue
                
            for item in sorted(os.listdir(skills_dir), key=str.lower):
                skill_path = os.path.join(skills_dir, item)
                if os.path.isdir(skill_path):
                    skill_md_path = os.path.join(skill_path, "SKILL.md")
                    if os.path.exists(skill_md_path):
                        stat = os.stat(skill_md_path)
                        cache_key = os.path.normcase(os.path.abspath(skill_md_path))
                        cached_entry = cached_skills.get(cache_key)
                        
                        if (
                            cached_entry
                            and cached_entry.get("mtime_ns") == stat.st_mtime_ns
                            and cached_entry.get("size") == stat.st_size
                        ):
                            skill_data = dict(cached_entry.get("data", {}))
                            from_cache = True
                        else:
                            skill_data = self._parse_skill_md(skill_md_path)
                            cache_dirty = True
                            from_cache = False
                            
                        if not skill_data.get("name"):
                            skill_data["name"] = item
                        skill_data["folder_name"] = item
                        skill_data["local_path"] = skill_path
                        skill_data["skill_md_path"] = skill_md_path
                        skill_data.setdefault("metadata", {})
                        category_refreshed = False
                        if not from_cache or self._skill_category_needs_refresh(skill_data.get("category")):
                            skill_data["category"] = self.categorize_skill(
                                skill_data.get("name", ""),
                                self._skill_classification_text(skill_data)
                            )
                            category_refreshed = True
                            cache_dirty = True
                        if not from_cache or category_refreshed or not skill_data.get("search_text"):
                            skill_data["search_text"] = self._build_skill_search_text(skill_data)
                        local_skills.append(skill_data)
                        
                        cache_data = dict(skill_data)
                        cache_data["raw_content"] = ""
                        next_cache["skills"][cache_key] = {
                            "mtime_ns": stat.st_mtime_ns,
                            "size": stat.st_size,
                            "data": cache_data
                        }
                        
        if cache_dirty or set(next_cache["skills"]) != set(cached_skills):
            self._save_skill_library_cache(next_cache)
        return local_skills
    
    def _load_skill_library_cache(self):
        try:
            with open(SKILL_LIBRARY_CACHE_FILE, "r", encoding="utf-8") as f:
                cache = json.load(f)
            if cache.get("version") == SKILL_LIBRARY_CACHE_VERSION and isinstance(cache.get("skills"), dict):
                return cache
        except (OSError, json.JSONDecodeError):
            pass
        return {"version": SKILL_LIBRARY_CACHE_VERSION, "skills": {}}
    
    def _save_skill_library_cache(self, cache):
        tmp_path = f"{SKILL_LIBRARY_CACHE_FILE}.tmp"
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(cache, f, ensure_ascii=False, indent=2, default=str)
            os.replace(tmp_path, SKILL_LIBRARY_CACHE_FILE)
        except OSError as exc:
            print(f"Error saving Library cache: {exc}")
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except OSError:
                pass
    
    def _build_skill_search_text(self, skill_data):
        parts = [
            skill_data.get("name", ""),
            skill_data.get("description", ""),
            skill_data.get("folder_name", ""),
            skill_data.get("category", "")
        ]
        metadata = skill_data.get("metadata") or {}
        for key in ("source", "risk", "category", "version", "date_added"):
            value = metadata.get(key)
            if value not in (None, ""):
                parts.append(str(value))
        return re.sub(r'\s+', ' ', " ".join(parts)).lower()

    def _skill_classification_text(self, skill_data):
        parts = [skill_data.get("description", "")]
        metadata = skill_data.get("metadata") or {}
        for key in ("category", "source", "risk", "tags", "use_cases"):
            value = metadata.get(key)
            if value not in (None, ""):
                parts.append(str(value))
        return " ".join(parts)

    def _skill_category_needs_refresh(self, category):
        return not str(category or "").strip() or str(category).strip().casefold() == "uncategorized"
    
    def _discover_local_skills(self):
        return self.load_local_skills()

    def _parse_skill_md(self, filepath):
        data = {"name": "", "description": "", "raw_content": "", "metadata": {}}
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                data["raw_content"] = content
                
            match = re.match(r'\A---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|\Z)', content, re.DOTALL)
            if match:
                frontmatter = match.group(1)
                metadata = self._parse_frontmatter(frontmatter)
                data["metadata"] = metadata
                data["name"] = str(metadata.get("name", "") or "").strip()
                data["description"] = self._normalize_description(metadata.get("description", ""))
                
            if not data["description"]:
                data["description"] = self._extract_markdown_description(content)
        except Exception as e:
            print(f"Error parsing {filepath}: {e}")
        return data
    
    def _parse_frontmatter(self, frontmatter):
        if yaml is not None:
            try:
                parsed = yaml.safe_load(frontmatter)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                pass
                
        parsed = {}
        current_key = None
        current_lines = []
        
        def flush_multiline():
            nonlocal current_key, current_lines
            if current_key:
                parsed[current_key] = " ".join(line.strip() for line in current_lines).strip()
                current_key = None
                current_lines = []
        
        for line in frontmatter.splitlines():
            if re.match(r'^\s', line) and current_key:
                current_lines.append(line)
                continue
                
            flush_multiline()
            key_match = re.match(r'^([A-Za-z0-9_-]+):\s*(.*)$', line)
            if not key_match:
                continue
                
            key, value = key_match.groups()
            value = value.strip()
            if value in {">", "|", ">-", "|-"}:
                current_key = key
                current_lines = []
            else:
                parsed[key] = value.strip(' "\'')
                
        flush_multiline()
        return parsed
    
    def _normalize_description(self, value):
        if value is None:
            return ""
        if isinstance(value, list):
            value = " ".join(str(item) for item in value)
        elif not isinstance(value, str):
            value = str(value)
        return re.sub(r'\s+', ' ', value).strip().strip(' "\'')
    
    def _extract_markdown_description(self, content):
        body = re.sub(r'\A---[ \t]*\r?\n.*?\r?\n---[ \t]*(?:\r?\n|\Z)', '', content, count=1, flags=re.DOTALL)
        paragraphs = []
        current = []
        
        for raw_line in body.splitlines():
            line = raw_line.strip()
            if not line:
                if current:
                    paragraphs.append(" ".join(current))
                    current = []
                continue
            if line.startswith("#") or line.startswith("```") or line.startswith("---"):
                continue
            current.append(re.sub(r'[*_`]+', '', line))
            
        if current:
            paragraphs.append(" ".join(current))
            
        return self._normalize_description(paragraphs[0] if paragraphs else "")

    def categorize_skill(self, name, description):
        text = (name + " " + description).lower()
        
        categories = {
            "Core Workflow": ["plan", "planning", "brainstorm", "brainstorming", "constructive work", "kaizen", "essential", "questions", "underspecified", "verification", "completion", "task", "workflow", "conductor", "build", "project guidelines", "sharp edges", "speckit", "updater"],
            "Developer Tools": ["git", "github", "pr", "pull request", "commit", "issue", "dx", "developer experience", "file organizer", "vexor", "semantic file discovery", "cli", "tool", "tools", "comprehensive review"],
            "Debugging": ["debug", "debugging", "error", "stack traces", "bug", "error detective", "logs", "root cause"],
            "Architecture": ["architect", "senior architect", "project architect", "architecture", "architecture diagram", "architecture patterns", "system design", "c4", "adr", "decision record", "domain-driven", "ddd", "cqrs", "event sourcing", "bounded context", "monorepo"],
            "Code Quality": ["technical debt", "legacy", "modernizer", "refactor", "clean code", "code quality"],
            "Security": ["security", "hack", "vulnerability", "pentest", "penetration", "auth", "xss", "threat", "risk", "attack", "red team", "active directory", "kerberos", "forensics", "incident response", "privilege escalation", "secrets", "credentials", "mtls", "zero-trust", "shodan"],
            "Compliance": ["compliance", "audit", "access review", "pci", "policy"],
            "Web Development": ["web", "frontend", "react", "next.js", "tailwind", "css", "ui", "ux", "fullstack", "angular", "vue", "html", "website", "portfolio", "wordpress", "three.js", "threejs", "webgl"],
            "Mobile Development": ["mobile", "ios", "android", "flutter", "expo", "react native", "swift", "swiftui", "swiftpm", "app store", "aso", "kotlin"],
            "Desktop Development": ["macos", "desktop", "electron", "avalonia", "makepad", "robius"],
            "AI": ["ai", "ia", "llm", "rag", "prompt", "model", "claude", "openai", "gemini", "anthropic", "hugging face", "vision model", "computer vision", "yolo", "sam", "notebooklm"],
            "Agents": ["agent", "agents", "subagent", "subagents", "mcp", "crewai", "langchain", "context window", "agentes"],
            "Game Development": ["game", "unity", "godot", "unreal"],
            "Backend Development": ["backend", "rails", "node", "api", "fastapi", "full-stack"],
            "Programming Languages": ["python", "typescript", "javascript", "rust", "go", "golang", "c-pro", " c code", "c++", "c#", "java", "ruby", "php", "elixir", "haskell", "julia", "memory safety", "memory-safe"],
            "Shell Scripting": ["posix", "bash", "powershell", "busybox", "windows", "shell", "jq"],
            "Embedded Systems": ["embedded", "firmware", "arm cortex", "microcontroller"],
            "Localization": ["i18n", "localization", "translation", "locale", "rtl"],
            "Migration": ["migration", "code migration", "framework migration"],
            "Product Management": ["product", "startup", "saas", "micro-saas", "jtbd", "jobs-to-be-done", "customer", "market", "competitive", "brand", "persona", "idea", "darwin", "personal tool"],
            "Business Strategy": ["business", "sales", "cro", "monetization", "pricing", "price", "churn", "retention", "growth"],
            "Psychology": ["psychology", "psychologist", "identity", "trust", "calibrator", "assumption", "auditor", "first-principles", "emotional arc", "loss aversion", "objection", "pitch", "scarcity", "urgency", "sequence"],
            "Careers": ["interview", "job search", "resume", "career"],
            "Marketing": ["marketing", "seo", "ads", "ad creative", "paid ads", "google ads", "meta", "linkedin", "tiktok", "influencer", "lead generation", "leads", "cold email", "copywriting", "headline", "subject line", "campaign", "audience", "brand reputation", "aso", "awareness"],
            "Social Media": ["social", "twitter", "youtube", "publisher", "x/twitter"],
            "DevOps": ["devops", "ci/cd", "ci", "cd", "deploy", "deployment", "on-call", "runbook", "incident", "slack", "tmux"],
            "Cloud Infrastructure": ["docker", "kubernetes", "k8s", "aws", "azure", "gcp", "cloud", "cloudflare", "terraform", "linux", "server", "istio", "service mesh"],
            "Observability": ["observability", "monitor", "monitoring", "prometheus", "slo", "tracing", "jaeger", "tempo"],
            "Build Systems": ["bazel", "nx", "turborepo"],
            "Background Jobs": ["inngest", "background jobs", "queues", "durable execution"],
            "Performance": ["performance", "performance bottlenecks", "performance optimizer", "profiling"],
            "Data": ["data", "vector", "warehouse", "forecast", "analysis", "analyze"],
            "Databases": ["sql", "postgres", "mysql", "database", "dbt"],
            "Analytics": ["analytics", "backtesting", "spreadsheet", "xlsx"],
            "Design": ["design", "canvas", "canva", "art", "figma", "theme", "visual", "hig", "human interface guidelines"],
            "Content": ["content", "writing", "blog", "article", "video", "audio", "gif", "favicon", "unsplash", "remotion", "portfolio", "rsvp", "speed reader"],
            "Diagrams": ["mermaid", "diagram"],
            "Documentation": ["documentation", "docs", "readme", "wiki", "onboarding", "obsidian", "markdown", "latex", "paper", "docx", "pptx", "office", "document"],
            "Knowledge Management": ["summarizer", "explain", "socratic", "bullet", "knowledge", "context", "context save", "context restore", "diary", "logger"],
            "Communications": ["communication", "communication mode", "internal comms", "communications", "brief", "terse", "caveman", "status reports"],
            "Logistics": ["logistics", "freight", "carrier", "returns", "reverse logistics"],
            "Inventory": ["inventory", "demand planning", "warehouse"],
            "Procurement": ["procurement", "purchase", "energy procurement"],
            "Manufacturing": ["production scheduling", "manufacturing"],
            "ERP": ["odoo", "erp", "timesheet"],
            "Quality Control": ["quality control", "non-conformance"],
            "Billing": ["billing", "invoice"],
            "Payments": ["payment", "paypal", "stripe", "tax"],
            "Finance": ["finance", "financial", "trading", "investment", "buffett"],
            "Web3": ["blockchain", "web3", "defi", "nft", "smart contract", "bitcoin", "lightning", "wallet"],
            "Legal": ["legal", "law", "contract", "compliant", "jurid", "direito", "advogado", "criminal", "trabalhista", "tributario", "consumidor", "imobiliario", "civil", "leilao", "leilões", "edital", "nulidades", "cpc", "lei"],
            "Human Resources": ["employment", "hr", "payroll"],
            "Health": ["health", "medical", "clinical", "hospital", "emergency", "medical card", "goal analyzer", "健康", "医疗", "急救"],
            "Fitness": ["fitness", "nutrition", "weightloss", "营养"],
            "Sleep": ["sleep", "睡眠"],
            "Mental Health": ["mental health", "心理"],
            "Sexual Health": ["sexual health"],
            "Oral Health": ["oral health", "口腔"],
            "Occupational Health": ["occupational health"],
            "Rehabilitation": ["rehabilitation", "康复"],
            "Travel Health": ["travel health"],
            "Traditional Medicine": ["tcm", "体质"],
            "Testing": ["test", "testing", "qa", "e2e", "playwright", "cypress", "jest", "tdd", "validation", "acceptance", "verify"],
            "Linting": ["shellcheck", "linting", "lint"]
        }
        
        best_category = "Uncategorized"
        max_matches = 0
        
        for category, keywords in categories.items():
            matches = sum(1 for kw in keywords if self._keyword_matches(text, kw))
            if matches > max_matches:
                max_matches = matches
                best_category = category
                
        return best_category
    
    def _keyword_matches(self, text, keyword):
        normalized_text = re.sub(r'[-_]+', ' ', text)
        normalized_keyword = re.sub(r'[-_]+', ' ', keyword)
        if re.search(r'[+#./\s-]', keyword):
            return keyword in text or normalized_keyword in normalized_text
        return (
            re.search(rf'\b{re.escape(keyword)}\b', text) is not None
            or re.search(rf'\b{re.escape(normalized_keyword)}\b', normalized_text) is not None
        )
    
    def _categorize_skill(self, name, description):
        return self.categorize_skill(name, description)

    def add_skill_to_updater_from_library(self, skill_data):
        local_path = skill_data.get("local_path") or ""
        data = {
            "name": skill_data.get("name"),
            "source_type": "git",
            "repository_url": detect_git_remote(local_path),
            "local_path": local_path,
            "package_name": "",
            "install_args": "",
            "update_command": "",
            "verify_command": "",
            "current_version_command": "",
            "latest_version_command": ""
        }
        
        def on_save(edited_data):
            self.skills.append(normalize_skill_source_config(edited_data))
            self.save_config()
            self.refresh_skill_ui()
            self.show_toast("Source added", f"Added '{edited_data['name']}' to updater.", "success")
            
        SkillEditDialog(self, "Add Skill Source", skill_data=data, callback=on_save)

    def _on_configure(self, event):
        # Only track geometry if it's the main window and state is 'normal'
        if event.widget == self and self.state() == "normal":
            self._normal_geometry = self.geometry()


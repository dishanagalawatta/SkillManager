"""Modular UI components for the Skill Manager Liquid Glass redesign."""

import customtkinter as ctk
from .styles import ctk_color, TEXT_MAIN, TEXT_MUTED


class GlassPill(ctk.CTkFrame):
    """A floating frosted glass panel (pill) for logical UI sections."""

    def __init__(
        self,
        master,
        strong: bool = False,
        corner_radius: int = 18,
        border_width: int = 1,
        **kwargs
    ):
        token_name = "glass_bg_strong" if strong else "glass_bg"
        
        # Use the standard glass style from StyleManager if possible, 
        # but here we implement it directly for component autonomy.
        super().__init__(
            master,
            fg_color=ctk_color(token_name),
            border_color=ctk_color("glass_border"),
            border_width=border_width,
            corner_radius=corner_radius,
            **kwargs
        )


class SkillInspectorOverlay(ctk.CTkFrame):
    """A non-modal overlay for displaying skill details and metadata."""

    def __init__(self, master, on_close=None, **kwargs):
        super().__init__(
            master,
            fg_color=ctk_color("glass_bg_strong"),
            border_color=ctk_color("glass_border"),
            border_width=1,
            corner_radius=20,
            **kwargs
        )
        self.on_close = on_close
        self._setup_ui()

    def _setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Header with Close button
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, padx=15, pady=(15, 10), sticky="ew")
        header.grid_columnconfigure(0, weight=1)

        self.title_label = ctk.CTkLabel(
            header, 
            text="Skill Details", 
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w"
        )
        self.title_label.grid(row=0, column=0, sticky="w")

        close_btn = ctk.CTkButton(
            header,
            text="\u2715",
            width=28,
            height=28,
            fg_color="transparent",
            text_color=TEXT_MUTED,
            hover_color=ctk_color("glass_control_hover"),
            command=self.close
        )
        close_btn.grid(row=0, column=1, sticky="e")

        # Content Area
        self.scroll_canvas = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_canvas.grid(row=1, column=0, padx=5, pady=(0, 5), sticky="nsew")
        self.scroll_canvas.grid_columnconfigure(0, weight=1)

        # Placeholder for dynamic content
        self.content_frame = ctk.CTkFrame(self.scroll_canvas, fg_color="transparent")
        self.content_frame.pack(fill="both", expand=True, padx=10)

        # Footer / Action Controls
        self.footer = ctk.CTkFrame(self, fg_color="transparent")
        self.footer.grid(row=2, column=0, padx=20, pady=(5, 20), sticky="ew")
        self.footer.grid_columnconfigure(0, weight=1)

        # Argument Frame (Quick Copy only)
        self.arg_frame = ctk.CTkFrame(self.footer, fg_color="transparent")
        self.arg_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        self.arg_frame.grid_columnconfigure(1, weight=1)
        
        self.arg_label = ctk.CTkLabel(
            self.arg_frame, 
            text="Argument:", 
            text_color=TEXT_MUTED, 
            font=ctk.CTkFont(size=11, weight="bold")
        )
        self.arg_label.grid(row=0, column=0, padx=(0, 8), sticky="w")
        
        self.argument_var = ctk.StringVar()
        self.argument_entry = ctk.CTkEntry(
            self.arg_frame, 
            textvariable=self.argument_var, 
            height=28, 
            corner_radius=10,
            placeholder_text="e.g. ultra"
        )
        self.argument_entry.grid(row=0, column=1, sticky="ew")

        # Category Row
        self.category_var = ctk.StringVar(value="Uncategorized")
        self.category_menu = ctk.CTkOptionMenu(
            self.footer, 
            variable=self.category_var, 
            width=160, 
            corner_radius=12,
            fg_color=ctk_color("glass_control"),
            button_color=ctk_color("glass_control"),
            button_hover_color=ctk_color("glass_control_hover")
        )
        self.category_menu.grid(row=1, column=0, sticky="ew", padx=(0, 8))
        
        self.apply_category_btn = ctk.CTkButton(
            self.footer, 
            text="Apply", 
            width=70, 
            corner_radius=12
        )
        self.apply_category_btn.grid(row=1, column=1, sticky="e")

        # Context Action Button (Essentials / Archive)
        self.action_btn = ctk.CTkButton(
            self.footer, 
            text="Action", 
            height=38, 
            corner_radius=12,
            fg_color=ctk_color("glass_control"),
            hover_color=ctk_color("glass_control_hover"),
            text_color=TEXT_MAIN
        )
        self.action_btn.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(12, 0))

    def set_content(self, title: str, metadata: dict, content: str, prefix: str = "library"):
        """Updates the overlay content and controls."""
        self.title_label.configure(text=title)
        
        # Configure Controls based on prefix
        if prefix == "quick_copy":
            self.arg_frame.grid()
        else:
            self.arg_frame.grid_remove()

        # Clear existing content
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        # Metadata Section
        if metadata:
            meta_pill = GlassPill(self.content_frame, strong=True, corner_radius=12)
            meta_pill.pack(fill="x", pady=(0, 12))
            
            for key, value in metadata.items():
                label = ctk.CTkLabel(
                    meta_pill, 
                    text=f"{key}: {value}", 
                    text_color=TEXT_MUTED,
                    font=ctk.CTkFont(size=12),
                    anchor="w"
                )
                label.pack(fill="x", padx=12, pady=2)

        # Main Content
        content_box = ctk.CTkTextbox(
            self.content_frame, 
            fg_color="transparent",
            text_color=TEXT_MAIN,
            font=ctk.CTkFont(family="Consolas", size=12),
            wrap="word"
        )
        content_box.pack(fill="both", expand=True)
        content_box.insert("1.0", content)
        content_box.configure(state="disabled")

    def close(self):
        """Hides or destroys the overlay."""
        if self.on_close:
            self.on_close()
        self.place_forget()

    def show(self, x_rel: float = 0.5, y_rel: float = 0.1, width_rel: float = 0.45, height_rel: float = 0.8):
        """Places the overlay on the screen."""
        self.place(relx=x_rel, rely=y_rel, relwidth=width_rel, relheight=height_rel)
        self.lift()

class SidebarFrame(ctk.CTkFrame):
    """A high-opacity frosted glass sidebar for main navigation."""
    def __init__(self, master, on_navigate, **kwargs):
        super().__init__(
            master, 
            fg_color=ctk_color("glass_bg_strong"),
            border_color=ctk_color("glass_border"),
            border_width=0, # Border only on the right usually
            corner_radius=0,
            width=240,
            **kwargs
        )
        self.on_navigate = on_navigate
        self._setup_ui()

    def _setup_ui(self):
        self.grid_propagate(False)
        self.grid_columnconfigure(0, weight=1)
        
        # Spacer for top padding
        ctk.CTkLabel(self, text="", height=20).pack()

        # Logo/Title
        self.logo_label = ctk.CTkLabel(
            self, 
            text="SKILL MANAGER", 
            font=ctk.CTkFont(family="Inter", size=15, weight="bold"),
            text_color=ctk_color("accent"),
            padx=20,
            pady=10,
            anchor="w"
        )
        self.logo_label.pack(fill="x", padx=10, pady=(0, 20))

        self.nav_buttons = {}
        nav_items = [
            ("Quick Copy", "\u2398"),
            ("Library", "\U0001F4DA"),
            ("Updates", "\u21bb"),
            ("Settings", "\u2699")
        ]

        for name, icon in nav_items:
            btn = ctk.CTkButton(
                self,
                text=f"  {icon}   {name}",
                font=ctk.CTkFont(size=14),
                anchor="w",
                height=42,
                fg_color="transparent",
                text_color=TEXT_MAIN,
                hover_color=ctk_color("glass_control_hover"),
                corner_radius=10,
                command=lambda n=name: self.on_navigate(n)
            )
            btn.pack(fill="x", padx=12, pady=3)
            self.nav_buttons[name] = btn

    def set_active(self, name):
        for btn_name, btn in self.nav_buttons.items():
            if btn_name == name:
                btn.configure(fg_color=ctk_color("accent"), text_color="#FFFFFF")
            else:
                btn.configure(fg_color="transparent", text_color=TEXT_MAIN)

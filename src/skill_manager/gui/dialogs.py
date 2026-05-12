import tkinter as tk
from tkinter import filedialog
import customtkinter as ctk
from typing import Optional, Dict, Callable

class SkillEditDialog(ctk.CTkToplevel):
    def __init__(self, parent, title: str, skill_data: Optional[Dict] = None, callback: Optional[Callable] = None):
        super().__init__(parent)
        self.title(title)
        self.geometry("720x610")
        self.minsize(600, 520)
        self.callback = callback
        self.source_type_var = tk.StringVar(value=(skill_data or {}).get("source_type", "auto"))
        self.show_advanced_var = tk.BooleanVar(value=bool(self._has_custom_commands(skill_data or {})))
        
        # Make it modal
        self.transient(parent)
        self.grab_set()

        self.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self, text="Name:").grid(row=0, column=0, padx=10, pady=(20,10), sticky="e")
        self.name_entry = ctk.CTkEntry(self)
        self.name_entry.grid(row=0, column=1, columnspan=2, padx=10, pady=(20,10), sticky="ew")

        ctk.CTkLabel(self, text="Type:").grid(row=1, column=0, padx=10, pady=10, sticky="e")
        self.source_type_menu = ctk.CTkOptionMenu(
            self,
            variable=self.source_type_var,
            values=["auto", "git", "npm", "custom"],
            command=lambda _value: self._toggle_advanced_fields(),
        )
        self.source_type_menu.grid(row=1, column=1, columnspan=2, padx=10, pady=10, sticky="ew")

        ctk.CTkLabel(self, text="Repository URL:").grid(row=2, column=0, padx=10, pady=10, sticky="e")
        self.repository_url_entry = ctk.CTkEntry(self)
        self.repository_url_entry.grid(row=2, column=1, columnspan=2, padx=10, pady=10, sticky="ew")

        ctk.CTkLabel(self, text="Local Path:").grid(row=3, column=0, padx=10, pady=10, sticky="e")
        self.local_path_entry = ctk.CTkEntry(self)
        self.local_path_entry.grid(row=3, column=1, padx=(10, 6), pady=10, sticky="ew")
        ctk.CTkButton(self, text="Browse", width=90, command=self._browse_local_path).grid(row=3, column=2, padx=(0, 10), pady=10, sticky="ew")

        ctk.CTkLabel(self, text="NPM Package:").grid(row=4, column=0, padx=10, pady=10, sticky="e")
        self.package_name_entry = ctk.CTkEntry(self)
        self.package_name_entry.grid(row=4, column=1, columnspan=2, padx=10, pady=10, sticky="ew")

        ctk.CTkLabel(self, text="Install Args:").grid(row=5, column=0, padx=10, pady=10, sticky="e")
        self.install_args_entry = ctk.CTkEntry(self)
        self.install_args_entry.grid(row=5, column=1, columnspan=2, padx=10, pady=10, sticky="ew")

        self.advanced_toggle = ctk.CTkCheckBox(
            self,
            text="Advanced commands",
            variable=self.show_advanced_var,
            command=self._toggle_advanced_fields,
        )
        self.advanced_toggle.grid(row=6, column=1, columnspan=2, padx=10, pady=(8, 2), sticky="w")

        self.advanced_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.advanced_frame.grid(row=7, column=0, columnspan=3, padx=0, pady=0, sticky="ew")
        self.advanced_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self.advanced_frame, text="Update Command:").grid(row=0, column=0, padx=10, pady=8, sticky="e")
        self.update_cmd_entry = ctk.CTkEntry(self.advanced_frame)
        self.update_cmd_entry.grid(row=0, column=1, padx=10, pady=8, sticky="ew")

        ctk.CTkLabel(self.advanced_frame, text="Verify Command:").grid(row=1, column=0, padx=10, pady=8, sticky="e")
        self.verify_cmd_entry = ctk.CTkEntry(self.advanced_frame)
        self.verify_cmd_entry.grid(row=1, column=1, padx=10, pady=8, sticky="ew")

        ctk.CTkLabel(self.advanced_frame, text="Current Version Command:").grid(row=2, column=0, padx=10, pady=8, sticky="e")
        self.current_ver_cmd_entry = ctk.CTkEntry(self.advanced_frame)
        self.current_ver_cmd_entry.grid(row=2, column=1, padx=10, pady=8, sticky="ew")

        ctk.CTkLabel(self.advanced_frame, text="Latest Version Command:").grid(row=3, column=0, padx=10, pady=8, sticky="e")
        self.latest_ver_cmd_entry = ctk.CTkEntry(self.advanced_frame)
        self.latest_ver_cmd_entry.grid(row=3, column=1, padx=10, pady=8, sticky="ew")

        if skill_data:
            self.name_entry.insert(0, skill_data.get("name", ""))
            self.repository_url_entry.insert(0, skill_data.get("repository_url", ""))
            self.local_path_entry.insert(0, skill_data.get("local_path", ""))
            self.package_name_entry.insert(0, skill_data.get("package_name", ""))
            self.install_args_entry.insert(0, skill_data.get("install_args", ""))
            self.update_cmd_entry.insert(0, skill_data.get("update_command", ""))
            self.verify_cmd_entry.insert(0, skill_data.get("verify_command", ""))
            self.current_ver_cmd_entry.insert(0, skill_data.get("current_version_command", ""))
            self.latest_ver_cmd_entry.insert(0, skill_data.get("latest_version_command", ""))

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=8, column=0, columnspan=3, pady=20)
        
        ctk.CTkButton(btn_frame, text="Save", command=self.save).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="Cancel", command=self.destroy).pack(side="left", padx=10)
        self._toggle_advanced_fields()

    def save(self):
        data = {
            "name": self.name_entry.get(),
            "source_type": self.source_type_var.get(),
            "repository_url": self.repository_url_entry.get(),
            "local_path": self.local_path_entry.get(),
            "package_name": self.package_name_entry.get(),
            "install_args": self.install_args_entry.get(),
            "update_command": self.update_cmd_entry.get(),
            "verify_command": self.verify_cmd_entry.get(),
            "current_version_command": self.current_ver_cmd_entry.get(),
            "latest_version_command": self.latest_ver_cmd_entry.get()
        }
        if self.callback:
            self.callback(data)
        self.destroy()

    def _browse_local_path(self):
        directory = filedialog.askdirectory(title="Select Local Source Folder")
        if directory:
            self.local_path_entry.delete(0, "end")
            self.local_path_entry.insert(0, directory)

    def _toggle_advanced_fields(self):
        show = self.show_advanced_var.get() or self.source_type_var.get() == "custom"
        if show:
            self.advanced_frame.grid()
        else:
            self.advanced_frame.grid_remove()

    def _has_custom_commands(self, data):
        if data.get("source_type") == "custom":
            return True
        return any(data.get(key) for key in (
            "verify_command",
            "current_version_command",
        ))

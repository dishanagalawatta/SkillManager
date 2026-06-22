import json
import os
import shutil
from pathlib import Path
from typing import Any

APP_NAME = "SkillManager"
DATA_DIR_ENV = "SKILL_MANAGER_DATA_DIR"

# File Filenames
CONFIG_FILENAME = "config.json"
SKILL_LIBRARY_CACHE_FILENAME = "skill_library_index.json"
SKILL_LIBRARY_ARCHIVE_FILENAME = "skill_library_archive.json"
SKILL_LIBRARY_STARRED_FILENAME = "skill_library_starred.json"
SKILL_LIBRARY_CLIPBOARD_FILENAME = "skill_library_clipboard.json"
QUICK_COPY_FILENAME = "quick_copy.json"
PROJECT_SKILL_OWNERSHIP_FILENAME = "project_skill_ownership.json"
PACKAGE_SKILL_INVENTORY_FILENAME = "package_skill_inventory.json"
SKILLS_LOCK_FILENAME = "skills-lock.json"
TEMP_COPIES_FILENAME = "temp_copies.json"
LEGACY_PROJECT_SKILL_CLIPBOARD_FILENAME = "project_skill_clipboard.json"
DATA_FILENAMES = (
    CONFIG_FILENAME,
    SKILL_LIBRARY_CACHE_FILENAME,
    SKILL_LIBRARY_ARCHIVE_FILENAME,
    SKILL_LIBRARY_STARRED_FILENAME,
    SKILL_LIBRARY_CLIPBOARD_FILENAME,
    QUICK_COPY_FILENAME,
    PROJECT_SKILL_OWNERSHIP_FILENAME,
    PACKAGE_SKILL_INVENTORY_FILENAME,
    SKILLS_LOCK_FILENAME,
    TEMP_COPIES_FILENAME,
)


def get_app_data_dir() -> Path:
    """Returns the platform-specific directory for application data."""
    override = os.environ.get(DATA_DIR_ENV)
    if override:
        return Path(override).expanduser()

    if os.name == "nt":
        base_dir = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        app_dir = (
            Path(base_dir) / APP_NAME if base_dir else Path.home() / "AppData" / "Local" / APP_NAME
        )
    elif xdg_data_home := os.environ.get("XDG_DATA_HOME"):
        app_dir = Path(xdg_data_home) / APP_NAME
    else:
        app_dir = Path.home() / ".local" / "share" / APP_NAME

    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir


def migrate_legacy_data_files(data_dir: Path = None, legacy_dir: Path = None) -> None:
    """Copies old root-level JSON data into the app-data folder when missing."""
    for filename in DATA_FILENAMES:
        resolve_data_file(filename, data_dir, legacy_dir)


def resolve_data_file(filename: str, data_dir: Path = None, legacy_dir: Path = None) -> Path:
    """Returns the app-data path, falling back to a legacy root file if migration is blocked."""
    target_dir = data_dir or get_app_data_dir()
    target_dir.mkdir(parents=True, exist_ok=True)

    if (
        os.environ.get("SKILL_MANAGER_TESTING") == "1"
        and not legacy_dir
        and os.environ.get("SKILL_MANAGER_ALLOW_MIGRATION") != "1"
    ):
        # In testing mode, don't fallback to CWD unless explicitly asked or allowed
        return target_dir / filename

    source_dir = legacy_dir or Path.cwd()
    target_path = target_dir / filename
    legacy_path = source_dir / filename
    fallback_paths = [source_dir / "data" / filename]
    if filename == QUICK_COPY_FILENAME:
        fallback_paths.append(target_dir / LEGACY_PROJECT_SKILL_CLIPBOARD_FILENAME)
        fallback_paths.append(source_dir / LEGACY_PROJECT_SKILL_CLIPBOARD_FILENAME)
        fallback_paths.append(source_dir / "data" / LEGACY_PROJECT_SKILL_CLIPBOARD_FILENAME)

    if target_path.exists():
        return target_path

    for fallback_path in fallback_paths:
        if fallback_path.is_file():
            try:
                shutil.copy2(fallback_path, target_path)
                return target_path
            except OSError:
                return fallback_path

    if legacy_path.is_file():
        try:
            shutil.copy2(legacy_path, target_path)
            return target_path
        except OSError:
            return legacy_path

    return target_path


# Exported Full Paths for the App
DATA_DIR = get_app_data_dir()
CONFIG_FILE = resolve_data_file(CONFIG_FILENAME)
SKILL_LIBRARY_CACHE_FILE = resolve_data_file(SKILL_LIBRARY_CACHE_FILENAME)
SKILL_LIBRARY_ARCHIVE_FILE = resolve_data_file(
    SKILL_LIBRARY_ARCHIVE_FILE_NAME := SKILL_LIBRARY_ARCHIVE_FILENAME
)
SKILL_LIBRARY_STARRED_FILE = resolve_data_file(SKILL_LIBRARY_STARRED_FILENAME)
SKILL_LIBRARY_CLIPBOARD_FILE = resolve_data_file(SKILL_LIBRARY_CLIPBOARD_FILENAME)
QUICK_COPY_FILE = resolve_data_file(QUICK_COPY_FILENAME)
PROJECT_SKILL_OWNERSHIP_FILE = resolve_data_file(PROJECT_SKILL_OWNERSHIP_FILENAME)
PACKAGE_SKILL_INVENTORY_FILE = resolve_data_file(PACKAGE_SKILL_INVENTORY_FILENAME)
SKILLS_LOCK_FILE = resolve_data_file(SKILLS_LOCK_FILENAME)
TEMP_COPIES_FILE = resolve_data_file(TEMP_COPIES_FILENAME)
SKILL_LIBRARY_CACHE_VERSION = 8

DEFAULT_SHORTCUTS = {
    "search": "Ctrl+F",
    "copy": "Ctrl+C",
    "archive": "Ctrl+Shift+X",
    "delete": "Delete",
    "refresh": "F5",
    "expand_all": "Ctrl+E",
    "collapse_all": "Ctrl+Shift+E",
    "top_of_list": "Home",
    "clear_selection": "Esc",
    "theme_toggle": "Ctrl+T",
    "quick_copy_view": "Alt+1",
    "library_view": "Alt+2",
    "updates_view": "Alt+3",
    "settings_view": "Alt+4",
}


class ConfigManager:
    def __init__(self, filename: str = CONFIG_FILENAME):
        self.config_path = resolve_data_file(filename)
        self.data: dict[str, Any] = {}
        self.load()

    def load(self) -> dict[str, Any]:
        """Loads configuration. Migrates from root if needed."""
        root_config = Path.cwd() / self.config_path.name

        if not self.config_path.exists() and root_config.is_file():
            try:
                with open(root_config) as f:
                    self.data = json.load(f)
                self.save()  # Migrate to new location
                # Continue loading to handle potential secondary migrations (e.g. targets -> projects)
            except Exception as e:
                print(f"Error migrating config: {e}")

        if self.config_path.exists():
            try:
                with open(self.config_path) as f:
                    self.data = json.load(f)

                # Migrate "targets" to "projects"
                if "targets" in self.data or "target_aliases" in self.data:
                    if "targets" in self.data:
                        self.data["projects"] = self.data.pop("targets")
                    if "target_aliases" in self.data:
                        self.data["project_aliases"] = self.data.pop("target_aliases")
                    self.save()

                # Ensure default shortcuts are present
                if "shortcuts" not in self.data:
                    self.data["shortcuts"] = DEFAULT_SHORTCUTS.copy()
                    self.save()
                else:
                    # Merge defaults for new shortcuts if any added in future versions
                    changed = False
                    for key, val in DEFAULT_SHORTCUTS.items():
                        if key not in self.data["shortcuts"]:
                            self.data["shortcuts"][key] = val
                            changed = True
                    if changed:
                        self.save()

            except Exception as e:
                print(f"Error loading config: {e}")
        else:
            # New config
            self.data["shortcuts"] = DEFAULT_SHORTCUTS.copy()
            self.save()

        return self.data

    def save(self) -> None:
        """Saves current configuration."""
        try:
            with open(self.config_path, "w") as f:
                json.dump(self.data, f, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.data[key] = value
        self.save()

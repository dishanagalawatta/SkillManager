import logging
import os
import shutil
from pathlib import Path
from typing import Any

import orjson
from platformdirs import user_data_dir

from skill_manager.core.schemas import AppConfig

logger = logging.getLogger(__name__)

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
TEMP_SCREENSHOTS_FILENAME = "temp_screenshots.json"
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

    if base_dir := os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA"):
        app_dir = Path(base_dir) / APP_NAME
    else:
        app_dir = Path(user_data_dir(APP_NAME, appauthor=False, roaming=False))

    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir


def migrate_legacy_data_files(data_dir: Path | None = None, legacy_dir: Path | None = None) -> None:
    """Copies old root-level JSON data into the app-data folder when missing."""
    for filename in DATA_FILENAMES:
        resolve_data_file(filename, data_dir, legacy_dir)


def resolve_data_file(
    filename: str, data_dir: Path | None = None, legacy_dir: Path | None = None
) -> Path:
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
TEMP_SCREENSHOTS_FILE = resolve_data_file(TEMP_SCREENSHOTS_FILENAME)
SKILL_LIBRARY_CACHE_VERSION = 8

DEFAULT_SHORTCUTS = {
    # Find & Select
    "search": "Ctrl+F",
    "select_all": "Ctrl+A",
    "clear_selection": "Esc",
    # Clipboard
    "copy": "Ctrl+C",
    # Skill Ops
    "refresh": "F5",
    "archive": "Ctrl+Shift+X",
    "delete": "Delete",
    # Tree View
    "expand_all": "Ctrl+E",
    "collapse_all": "Ctrl+Shift+E",
    "top_of_list": "Home",
    # Navigate
    "quick_copy_view": "Alt+1",
    "library_view": "Alt+2",
    "updates_view": "Alt+3",
    "settings_view": "Alt+4",
    # Tools
    "theme_toggle": "Ctrl+T",
    "screenshot": "Ctrl+Shift+S",
}

DEFAULT_DISABLED_SHORTCUTS: list[str] = []


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
                with open(root_config, "rb") as f:
                    self.data = orjson.loads(f.read())
                self.save()  # Migrate to new location
                # Continue loading to handle potential secondary migrations (e.g. targets -> projects)
            except Exception as e:
                logger.warning("Error migrating config: %s", e)

        if self.config_path.exists():
            try:
                with open(self.config_path, "rb") as f:
                    self.data = orjson.loads(f.read())

                old_data = dict(self.data)
                self.data = AppConfig.from_legacy(self.data).model_dump(by_alias=True)
                if self.data != old_data:
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

                # Ensure disabled_shortcuts list is present
                if "disabled_shortcuts" not in self.data:
                    self.data["disabled_shortcuts"] = DEFAULT_DISABLED_SHORTCUTS.copy()
                    self.save()

            except Exception as e:
                logger.warning("Error loading config: %s", e)
        else:
            # New config
            self.data["shortcuts"] = DEFAULT_SHORTCUTS.copy()
            self.data["disabled_shortcuts"] = DEFAULT_DISABLED_SHORTCUTS.copy()
            self.save()

        return self.data

    def save(self) -> None:
        """Saves current configuration."""
        try:
            content = orjson.dumps(
                self.data, option=orjson.OPT_INDENT_2 | orjson.OPT_APPEND_NEWLINE
            )
            with open(self.config_path, "wb") as f:
                f.write(content)
        except Exception as e:
            logger.warning("Error saving config: %s", e)

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.data[key] = value
        self.save()

    def set_many(self, updates: dict[str, Any]) -> None:
        """Sets multiple config keys and writes to disk once."""
        self.data.update(updates)
        self.save()

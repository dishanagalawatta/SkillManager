import os
import json
import shutil
import sys
from pathlib import Path
from typing import Any, Dict

APP_NAME = "SkillManager"
DATA_DIR_ENV = "SKILL_MANAGER_DATA_DIR"

# File Filenames
CONFIG_FILENAME = "config.json"
SKILL_LIBRARY_CACHE_FILENAME = "skill_library_index.json"
SKILL_LIBRARY_ARCHIVE_FILENAME = "skill_library_archive.json"
SKILL_LIBRARY_CLIPBOARD_FILENAME = "skill_library_clipboard.json"
QUICK_COPY_FILENAME = "quick_copy.json"
LEGACY_PROJECT_SKILL_CLIPBOARD_FILENAME = "project_skill_clipboard.json"
DATA_FILENAMES = (
    CONFIG_FILENAME,
    SKILL_LIBRARY_CACHE_FILENAME,
    SKILL_LIBRARY_ARCHIVE_FILENAME,
    SKILL_LIBRARY_CLIPBOARD_FILENAME,
    QUICK_COPY_FILENAME,
)

def get_app_data_dir() -> Path:
    """Returns the platform-specific directory for application data."""
    override = os.environ.get(DATA_DIR_ENV)
    if override:
        app_dir = Path(override).expanduser()
    elif sys.platform == 'win32':
        base_dir = Path(os.environ.get('APPDATA', '~')).expanduser()
        app_dir = base_dir / APP_NAME
    elif sys.platform == 'darwin':
        base_dir = Path('~/Library/Application Support').expanduser()
        app_dir = base_dir / APP_NAME
    else:
        base_dir = Path('~/.config').expanduser()
        app_dir = base_dir / APP_NAME

    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir

def migrate_legacy_data_files(data_dir: Path = None, legacy_dir: Path = None) -> None:
    """Copies old root-level JSON data into the app-data folder when missing."""
    for filename in DATA_FILENAMES:
        resolve_data_file(filename, data_dir, legacy_dir)

def resolve_data_file(filename: str, data_dir: Path = None, legacy_dir: Path = None) -> Path:
    """Returns the app-data path, falling back to a legacy root file if migration is blocked."""
    target_dir = data_dir or DATA_DIR
    source_dir = legacy_dir or Path.cwd()
    target_path = target_dir / filename
    legacy_path = source_dir / filename
    fallback_paths = []
    if filename == QUICK_COPY_FILENAME:
        fallback_paths.append(target_dir / LEGACY_PROJECT_SKILL_CLIPBOARD_FILENAME)
        fallback_paths.append(source_dir / LEGACY_PROJECT_SKILL_CLIPBOARD_FILENAME)

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
SKILL_LIBRARY_ARCHIVE_FILE = resolve_data_file(SKILL_LIBRARY_ARCHIVE_FILENAME)
SKILL_LIBRARY_CLIPBOARD_FILE = resolve_data_file(SKILL_LIBRARY_CLIPBOARD_FILENAME)
QUICK_COPY_FILE = resolve_data_file(QUICK_COPY_FILENAME)
SKILL_LIBRARY_CACHE_VERSION = 8

class ConfigManager:
    def __init__(self, filename: str = CONFIG_FILENAME):
        self.config_path = resolve_data_file(filename)
        self.data: Dict[str, Any] = {}
        self.load()

    def load(self) -> Dict[str, Any]:
        """Loads configuration. Migrates from root if needed."""
        root_config = Path.cwd() / self.config_path.name

        if not self.config_path.exists() and root_config.is_file():
            try:
                with open(root_config, 'r') as f:
                    self.data = json.load(f)
                self.save() # Migrate to new location
                return self.data
            except Exception as e:
                print(f"Error migrating config: {e}")

        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    self.data = json.load(f)
            except Exception as e:
                print(f"Error loading config: {e}")
        return self.data

    def save(self) -> None:
        """Saves current configuration."""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.data, f, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.data[key] = value
        self.save()

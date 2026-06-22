import os
import subprocess
import sys
from pathlib import Path


def _patch_subprocess():
    original_popen = subprocess.Popen

    class NoWindowPopen(original_popen):
        def __init__(self, *args, **kwargs):
            if hasattr(subprocess, "CREATE_NO_WINDOW"):
                kwargs["creationflags"] = kwargs.get("creationflags", 0) | subprocess.CREATE_NO_WINDOW
            super().__init__(*args, **kwargs)

    subprocess.Popen = NoWindowPopen


def _disable_qml_disk_cache():
    # Force-disable Qt's on-disk QML compilation cache for the current process.
    # The cache can hold stale .qmlc files that mismatch the current QML source
    # (e.g. after adding/removing components), producing cryptic load errors
    # like "Cannot assign object of type X to list property 'data'".
    # This must run before PySide6 / QtQuick modules are imported.
    os.environ.setdefault("QML_DISABLE_DISK_CACHE", "1")


def _is_dev_mode() -> bool:
    """Detect if running via 'uv run' or in development mode.

    Checks:
    1. SKILL_MANAGER_DEV_MODE env var
    2. sys.frozen (PyInstaller)
    3. src/ directory layout (uv run / editable install)
    """
    if os.environ.get("SKILL_MANAGER_DEV_MODE"):
        return True
    if getattr(sys, "frozen", False):
        return False
    try:
        src_dir = Path(__file__).resolve().parent.parent
        if src_dir.name == "src" and (src_dir.parent / "pyproject.toml").exists():
            return True
    except Exception:
        pass
    return False


# Execute patches before any other imports happen!
_patch_subprocess()
_disable_qml_disk_cache()

import logging  # noqa: E402

from skill_manager.app import main as app_main  # noqa: E402
from skill_manager.core.config import DATA_DIR  # noqa: E402
from skill_manager.core.resources import force_clear_qml_disk_cache  # noqa: E402


def setup_logging():
    log_level = logging.DEBUG if _is_dev_mode() else logging.INFO
    log_file = DATA_DIR / "skill_manager.log"
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(), logging.FileHandler(log_file, encoding="utf-8")],
    )


def main():
    # Force-clear QML cache in dev mode (uv run / editable install)
    if _is_dev_mode():
        force_clear_qml_disk_cache()

    setup_logging()

    # Initialize diagnostic logger
    from skill_manager.core.config import ConfigManager
    from skill_manager.core.diagnostics import get_diagnostic_logger

    diag = get_diagnostic_logger()
    log_level = "DEBUG" if _is_dev_mode() else "INFO"
    diag.initialize(log_level=log_level)

    # Enable only if the user has opted in via Settings > General
    _cfg = ConfigManager()
    diag.set_enabled(_cfg.get("diagnostic_logging", False))
    diag.log_startup()

    app_main()


if __name__ == "__main__":
    main()

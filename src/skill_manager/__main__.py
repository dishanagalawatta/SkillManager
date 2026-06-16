import os
import sys


def _patch_subprocess():
    if sys.platform == "win32":
        import subprocess

        original_popen = subprocess.Popen

        class NoWindowPopen(original_popen):
            def __init__(self, *args, **kwargs):
                # Ensure CREATE_NO_WINDOW is set for all subprocesses
                kwargs["creationflags"] = (
                    kwargs.get("creationflags", 0) | subprocess.CREATE_NO_WINDOW
                )
                super().__init__(*args, **kwargs)

        subprocess.Popen = NoWindowPopen


def _disable_qml_disk_cache():
    # Force-disable Qt's on-disk QML compilation cache for the current process.
    # The cache can hold stale .qmlc files that mismatch the current QML source
    # (e.g. after adding/removing components), producing cryptic load errors
    # like "Cannot assign object of type X to list property 'data'".
    # This must run before PySide6 / QtQuick modules are imported.
    os.environ.setdefault("QML_DISABLE_DISK_CACHE", "1")


# Execute patches before any other imports happen!
_patch_subprocess()
_disable_qml_disk_cache()

import logging  # noqa: E402

from skill_manager.app import main as app_main  # noqa: E402
from skill_manager.core.config import DATA_DIR  # noqa: E402


def setup_logging():
    log_file = DATA_DIR / "skill_manager.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(), logging.FileHandler(log_file, encoding="utf-8")],
    )


def main():
    setup_logging()
    app_main()


if __name__ == "__main__":
    main()

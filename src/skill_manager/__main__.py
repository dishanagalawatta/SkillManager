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


# Execute patch before any other imports happen!
_patch_subprocess()

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

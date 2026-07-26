import os
import subprocess
import sys
from pathlib import Path


def _patch_subprocess():
    if not hasattr(subprocess, "CREATE_NO_WINDOW"):
        return

    try:
        _orig_init = subprocess.Popen.__init__

        def _patched_init(self, *args, **kwargs):  # type: ignore[misc]
            kwargs["creationflags"] = kwargs.get("creationflags", 0) | subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]
            return _orig_init(self, *args, **kwargs)

        subprocess.Popen.__init__ = _patched_init  # type: ignore[method-assign]
    except (TypeError, AttributeError):
        _orig_popen = subprocess.Popen

        class _NoWindowPopen(_orig_popen):  # type: ignore[valid-type]
            def __init__(self, *args, **kwargs):
                kwargs["creationflags"] = (
                    kwargs.get("creationflags", 0) | subprocess.CREATE_NO_WINDOW
                )  # type: ignore[attr-defined]
                super().__init__(*args, **kwargs)

        subprocess.Popen = _NoWindowPopen


def _disable_qml_disk_cache():
    os.environ.setdefault("QML_DISABLE_DISK_CACHE", "1")


def is_dev_mode() -> bool:
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


_patch_subprocess()
_disable_qml_disk_cache()

import logging  # noqa: E402

from skill_manager.app import main as app_main  # noqa: E402
from skill_manager.core.config import DATA_DIR  # noqa: E402
from skill_manager.core.resources import force_clear_qml_disk_cache  # noqa: E402


def setup_logging():
    log_level = logging.DEBUG if is_dev_mode() else logging.INFO
    log_file = DATA_DIR / "skill_manager.log"
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(), logging.FileHandler(log_file, encoding="utf-8")],
    )

    for noisy in ("markdown_it", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def _redirect_qml_log():
    """Redirect stderr (QML console.log goes here) to a log file."""
    log_path = DATA_DIR / "qml_console.log"
    try:
        fh = open(log_path, "w", encoding="utf-8")  # noqa: SIM115 — must keep fh open for sys.stderr replacement
        sys.stderr = fh
    except OSError:
        pass  # best-effort


def main():

    import multiprocessing

    multiprocessing.freeze_support()

    # Force-clear QML cache in dev mode (uv run / editable install)
    if is_dev_mode():
        force_clear_qml_disk_cache()

    setup_logging()
    _redirect_qml_log()

    # Initialize diagnostic logger
    from skill_manager.core.config import ConfigManager
    from skill_manager.core.diagnostics import get_diagnostic_logger

    diag = get_diagnostic_logger()
    log_level = "DEBUG" if is_dev_mode() else "INFO"
    diag.initialize(log_level=log_level)

    # Enable only if the user has opted in via Settings > General
    # Always enable in dev mode for selection_refreshed diagnostics
    _cfg = ConfigManager()
    diag.set_enabled(is_dev_mode() or _cfg.get("diagnostic_logging", False))
    diag.log_startup()

    app_main()


if __name__ == "__main__":
    main()

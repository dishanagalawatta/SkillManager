import contextlib
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
from logging.handlers import RotatingFileHandler  # noqa: E402

from skill_manager.bootstrap import run_gui as app_main  # noqa: E402
from skill_manager.core.config import DATA_DIR  # noqa: E402
from skill_manager.core.resources import force_clear_qml_disk_cache  # noqa: E402

_LOG_MAX_BYTES = 5 * 1024 * 1024  # 5 MB per file, same as diagnostic.log
_LOG_BACKUP_COUNT = 5
_QML_LOG_MAX_BYTES = 5 * 1024 * 1024  # bound qml_console.log to the same size

_VALID_LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
}


def _resolve_log_level() -> int:
    """Honor SKILL_MANAGER_LOG_LEVEL env, fallback to dev-mode default."""
    raw = os.environ.get("SKILL_MANAGER_LOG_LEVEL", "").strip().upper()
    if raw in _VALID_LOG_LEVELS:
        return _VALID_LOG_LEVELS[raw]
    return logging.DEBUG if is_dev_mode() else logging.INFO


def _resolve_diag_log_level() -> str:
    """Honor SKILL_MANAGER_LOG_LEVEL env for diagnostics, fallback to dev-mode default."""
    raw = os.environ.get("SKILL_MANAGER_LOG_LEVEL", "").strip().upper()
    if raw in _VALID_LOG_LEVELS:
        return raw
    return "DEBUG" if is_dev_mode() else "INFO"


def setup_logging():
    log_level = _resolve_log_level()
    log_file = DATA_DIR / "skill_manager.log"
    with contextlib.suppress(OSError):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
    try:
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=_LOG_MAX_BYTES,
            backupCount=_LOG_BACKUP_COUNT,
            encoding="utf-8",
        )
    except OSError:
        file_handler = logging.StreamHandler()
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(), file_handler],
    )

    for noisy in (
        "markdown_it",
        "urllib3",
        "watchdog.observers.inotify_buffer",
        "watchdog.observers.inotify",
        "watchdog.observers",
        "watchdog.events",
    ):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def _enable_qml_binding_removal_warnings():
    """Surface QML binding-break diagnostics (dev/DEBUG only).

    The QML engine drops a property binding on the first imperative
    assignment — the root cause of stale multi-select checkboxes fixed in
    CommandCreateDialog/QuickCopyView. Enabling this category turns future
    occurrences into visible engine warnings instead of silent stale UI.
    Must run before the QML engine loads; process-global and dev-only so
    release logs stay quiet.
    """
    try:
        from PySide6.QtCore import QLoggingCategory

        QLoggingCategory.setFilterRules("qt.qml.binding.removal.info=true")
    except Exception:
        pass  # best-effort: never block startup on diagnostics


def _redirect_qml_log():
    """Redirect stderr (QML console.log goes here) to a log file.

    Appends across restarts (mode "a") so earlier QML output is preserved.
    Truncates once when the file exceeds the size cap to bound disk use.
    """
    log_path = DATA_DIR / "qml_console.log"
    try:
        try:
            oversized = log_path.exists() and log_path.stat().st_size >= _QML_LOG_MAX_BYTES
        except OSError:
            oversized = False
        mode = "w" if oversized else "a"
        fh = open(log_path, mode, encoding="utf-8")  # noqa: SIM115 — must keep fh open for sys.stderr replacement
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
    if logging.getLogger().isEnabledFor(logging.DEBUG):
        _enable_qml_binding_removal_warnings()

    # Initialize diagnostic logger
    from skill_manager.core.config import ConfigManager
    from skill_manager.core.diagnostics import get_diagnostic_logger

    diag = get_diagnostic_logger()
    log_level = _resolve_diag_log_level()
    diag.initialize(log_level=log_level)

    # Enable only if the user has opted in via Settings > General
    # Always enable in dev mode for selection_refreshed diagnostics
    _cfg = ConfigManager()
    diag.set_enabled(is_dev_mode() or _cfg.get("diagnostic_logging", False))
    diag.log_startup()

    app_main()


if __name__ == "__main__":
    main()

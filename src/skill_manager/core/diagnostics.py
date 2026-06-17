"""Structured diagnostic logging for SkillManager.

Industry-standard JSON-line diagnostic log with rotation, thread safety,
and agent-accessible export. Designed for AI agent consumption.

Usage:
    from skill_manager.core.diagnostics import get_diagnostic_logger
    diag = get_diagnostic_logger()
    diag.log_event("INFO", "app_startup", "Application started")
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
import platform
import sys
import threading
import zipfile
from collections import deque
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MAX_RING_BUFFER = 1000
_MAX_ROTATION_FILES = 5
_MAX_ROTATION_BYTES = 5 * 1024 * 1024  # 5 MB per file
_LOG_FILENAME = "diagnostic.log"
_BUNDLE_LOG_FILENAME = "diagnostic_bundle.json"

# Categories for structured event classification
CATEGORY_APP_STARTUP = "app_startup"
CATEGORY_APP_QUIT = "app_quit"
CATEGORY_DIALOG_OPENED = "dialog_opened"
CATEGORY_DIALOG_CLOSED = "dialog_closed"
CATEGORY_MISSING_SKILLS_CHECK = "missing_skills_check"
CATEGORY_MISSING_SKILLS_RESULT = "missing_skills_result"
CATEGORY_STATUS_MESSAGE = "status_message"
CATEGORY_CACHE_CLEARED = "cache_cleared"
CATEGORY_CACHE_DETECTED = "cache_detected"
CATEGORY_COLLECTION_SAVED = "collection_saved"
CATEGORY_COLLECTION_DELETED = "collection_deleted"
CATEGORY_SKILL_COPY = "skill_copy"
CATEGORY_ERROR = "error"
CATEGORY_WARNING = "warning"
CATEGORY_UV_RUN_DETECTED = "uv_run_detected"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _log_dir() -> Path:
    """Return XDG-compliant log directory.

    Windows: %LOCALAPPDATA%/SkillManager/logs/
    Linux/Mac: ~/.local/share/SkillManager/logs/
    """
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA", "")
        if not base:
            base = str(Path.home() / "AppData" / "Local")
    else:
        base = os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share"))
    return Path(base) / "SkillManager" / "logs"


def _current_iso() -> str:
    return datetime.now(UTC).isoformat()


def _platform_info() -> dict[str, str]:
    return {
        "platform": sys.platform,
        "os": platform.system(),
        "os_version": platform.version(),
        "python": platform.python_version(),
    }


def _qt_version() -> str:
    try:
        from PySide6.QtCore import QLibraryInfo

        return QLibraryInfo.version().toString()
    except Exception:
        return "unknown"


def _app_version() -> str:
    try:
        import skill_manager

        return skill_manager.__version__
    except Exception:
        return "unknown"


# ---------------------------------------------------------------------------
# DiagnosticLogger
# ---------------------------------------------------------------------------


class DiagnosticLogger:
    """Thread-safe JSON-line diagnostic logger with ring buffer and rotation."""

    def __init__(self, log_dir: Path | None = None) -> None:
        self._log_dir = log_dir or _log_dir()
        self._log_file = self._log_dir / _LOG_FILENAME
        self._lock = threading.Lock()
        self._ring: deque[dict[str, Any]] = deque(maxlen=_MAX_RING_BUFFER)
        self._initialized = False
        self._log_level = "INFO"
        self._context: dict[str, Any] = {}

    def initialize(
        self,
        log_level: str = "INFO",
        context: dict[str, Any] | None = None,
    ) -> None:
        """Initialize logger: create dirs, set level, populate context."""
        self._log_level = log_level.upper()
        self._context = {
            "app_version": _app_version(),
            "qt_version": _qt_version(),
            "platform": sys.platform,
            "python_version": platform.python_version(),
        }
        if context:
            self._context.update(context)

        try:
            self._log_dir.mkdir(parents=True, exist_ok=True)
            self._initialized = True
        except OSError as exc:
            logger.warning("Could not create diagnostic log directory: %s", exc)
            self._initialized = False

    def _rotate_if_needed(self) -> None:
        """Rotate log file if it exceeds max size."""
        if not self._log_file.exists():
            return
        try:
            if self._log_file.stat().st_size < _MAX_ROTATION_BYTES:
                return
        except OSError:
            return

        # Rotate: diagnostic.log.1 -> diagnostic.log.2 -> ... -> delete oldest
        for i in range(_MAX_ROTATION_FILES - 1, 0, -1):
            src = self._log_file.with_suffix(f".log.{i}")
            dst = self._log_file.with_suffix(f".log.{i + 1}")
            if src.exists():
                if i + 1 >= _MAX_ROTATION_FILES:
                    with contextlib.suppress(OSError):
                        src.unlink()
                else:
                    with contextlib.suppress(OSError):
                        src.rename(dst)
        with contextlib.suppress(OSError):
            rotated = self._log_file.with_suffix(".log.1")
            self._log_file.rename(rotated)

    def log_event(
        self,
        level: str,
        category: str,
        msg: str,
        data: dict[str, Any] | None = None,
    ) -> None:
        """Log a structured diagnostic event.

        Args:
            level: Log level (DEBUG, INFO, WARNING, ERROR).
            category: Event category (use CATEGORY_* constants).
            msg: Human-readable message.
            data: Optional additional structured data.
        """
        if level.upper() == "DEBUG" and self._log_level != "DEBUG":
            return

        event: dict[str, Any] = {
            "ts": _current_iso(),
            "level": level.upper(),
            "category": category,
            "msg": msg,
            "ctx": self._context.copy(),
        }
        if data:
            event["data"] = data

        # Ring buffer (always, even if not initialized)
        with self._lock:
            self._ring.append(event)

        # File output
        if not self._initialized:
            return

        try:
            self._rotate_if_needed()
            line = json.dumps(event, ensure_ascii=False, default=str) + "\n"
            with self._lock, open(self._log_file, "a", encoding="utf-8") as f:
                f.write(line)
        except OSError as exc:
            # Fallback to stderr if file write fails
            logger.warning("Diagnostic log write failed: %s", exc)

    def log_startup(self) -> None:
        """Log application startup with full context."""
        self.log_event(
            "INFO",
            CATEGORY_APP_STARTUP,
            "Application started",
            data={
                "frozen": getattr(sys, "frozen", False),
                "dev_mode": _is_dev_mode(),
                "log_level": self._log_level,
            },
        )

    def get_recent_events(self, count: int = 100) -> list[dict[str, Any]]:
        """Return the most recent diagnostic events from the ring buffer."""
        with self._lock:
            items = list(self._ring)
        return items[-count:]

    def get_log_path(self) -> str:
        """Return the path to the current diagnostic log file."""
        return str(self._log_file)

    def clear_logs(self) -> None:
        """Clear the ring buffer and delete log files."""
        with self._lock:
            self._ring.clear()
        try:
            if self._log_file.exists():
                self._log_file.unlink()
            for i in range(1, _MAX_ROTATION_FILES + 1):
                f = self._log_file.with_suffix(f".log.{i}")
                if f.exists():
                    f.unlink()
        except OSError as exc:
            logger.warning("Failed to clear diagnostic logs: %s", exc)

    def export_bundle(self, output_dir: str | Path | None = None) -> str:
        """Export diagnostic bundle as a zip file.

        Bundle contains:
        - diagnostic.log (current log)
        - diagnostic.log.N (rotated logs)
        - manifest.json (app version, Qt version, OS, Python, recent events)

        Args:
            output_dir: Directory to write the zip to. Defaults to log dir.

        Returns:
            Path to the created zip file, or empty string on failure.
        """
        if output_dir is None:
            output_dir = self._log_dir
        output_path = Path(output_dir)
        try:
            output_path.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            logger.warning("Could not create bundle output dir: %s", exc)
            return ""

        ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        zip_path = output_path / f"diagnostic_bundle_{ts}.zip"

        try:
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                # Write manifest
                manifest = {
                    "app_version": _app_version(),
                    "qt_version": _qt_version(),
                    "platform": sys.platform,
                    "os": platform.system(),
                    "os_version": platform.version(),
                    "python_version": platform.python_version(),
                    "log_level": self._log_level,
                    "recent_events": self.get_recent_events(50),
                    "exported_at": _current_iso(),
                }
                zf.writestr(
                    _BUNDLE_LOG_FILENAME,
                    json.dumps(manifest, indent=2, ensure_ascii=False, default=str),
                )

                # Include log files
                if self._log_file.exists():
                    zf.write(self._log_file, _LOG_FILENAME)
                for i in range(1, _MAX_ROTATION_FILES + 1):
                    f = self._log_file.with_suffix(f".log.{i}")
                    if f.exists():
                        zf.write(f, f.name)

            return str(zip_path)
        except OSError as exc:
            logger.warning("Failed to create diagnostic bundle: %s", exc)
            return ""


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_logger_instance: DiagnosticLogger | None = None
_logger_lock = threading.Lock()


def get_diagnostic_logger() -> DiagnosticLogger:
    """Get or create the module-level DiagnosticLogger singleton."""
    global _logger_instance
    if _logger_instance is None:
        with _logger_lock:
            if _logger_instance is None:
                _logger_instance = DiagnosticLogger()
    return _logger_instance


# ---------------------------------------------------------------------------
# Dev mode detection
# ---------------------------------------------------------------------------


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

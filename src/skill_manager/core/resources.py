import logging
import os
import shutil
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def resource_path(relative_path: str, *, base_path: str | None = None) -> str:
    if base_path is None:
        if hasattr(sys, "_MEIPASS"):
            base_path = sys._MEIPASS
        else:
            # First try relative to the project root (where it lives in the repo)
            # src/skill_manager/core/resources.py -> Project Root is 3 levels up from core
            project_root = Path(__file__).resolve().parent.parent.parent.parent
            if (project_root / relative_path).exists():
                base_path = str(project_root)
            else:
                base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def qml_components_dir(
    *,
    frozen: bool | None = None,
    meipass: str | None = None,
    package_file: str | None = None,
) -> Path:
    if frozen is None:
        frozen = bool(getattr(sys, "frozen", False))
    if meipass is None:
        meipass = getattr(sys, "_MEIPASS", "")
    if package_file is None:
        package_file = __file__

    if frozen:
        base = Path(meipass)
        internal = base / "_internal"
        if internal.exists():
            return internal / "skill_manager" / "SkillManagerComponents"
        return base / "skill_manager" / "SkillManagerComponents"

    return Path(package_file).resolve().parent / "SkillManagerComponents"


_QML_CACHE_VERSION_MARKER = ".qmlcache_version"


def qml_disk_cache_dir() -> Path | None:
    """Return Qt's standard on-disk QML cache directory, if available.

    Returns None when the cache directory has not been created yet (first run).
    """
    if sys.platform != "win32":
        cache_root = Path(os.environ.get("XDG_CACHE_HOME", str(Path.home() / ".cache")))
    else:
        local_app_data = os.environ.get("LOCALAPPDATA")
        if not local_app_data:
            return None
        cache_root = Path(local_app_data)
    return cache_root / "python" / "cache" / "qmlcache"


def invalidate_qml_disk_cache_if_stale(current_version: str) -> bool:
    """Clear Qt's QML disk cache when its version marker is missing or stale.

    Stale `.qmlc` files can survive QML source changes and produce cryptic load
    errors (e.g. "Cannot assign object of type X to list property 'data'"). This
    guard writes a small version marker next to the cache files and clears the
    directory on version mismatch. Returns True when a clear was performed.
    """
    cache_dir = qml_disk_cache_dir()
    if cache_dir is None or not cache_dir.exists():
        return False

    marker = cache_dir / _QML_CACHE_VERSION_MARKER
    existing: str | None = None
    if marker.is_file():
        try:
            existing = marker.read_text(encoding="utf-8").strip() or None
        except OSError as exc:
            logger.warning("Could not read QML cache version marker: %s", exc)

    if existing == current_version:
        return False

    try:
        for entry in cache_dir.iterdir():
            try:
                if entry.is_file() or entry.is_symlink():
                    entry.unlink()
                elif entry.is_dir():
                    shutil.rmtree(entry)
            except OSError as exc:
                logger.warning("Failed to remove stale QML cache entry %s: %s", entry, exc)
        marker.write_text(current_version, encoding="utf-8")
        logger.info(
            "Cleared stale QML disk cache (marker=%s, current=%s) at %s",
            existing,
            current_version,
            cache_dir,
        )
        return True
    except OSError as exc:
        logger.warning("Could not refresh QML cache version marker: %s", exc)
        return False


def force_clear_qml_disk_cache() -> bool:
    """Unconditionally remove the entire QML disk cache directory.

    Used during development (uv run, editable installs) where source QML
    changes frequently and stale .qmlc files cause load errors. Unlike
    ``invalidate_qml_disk_cache_if_stale``, this always clears the
    cache regardless of version markers.

    Returns True when a cache was cleared or confirmed absent.
    """
    cache_dir = qml_disk_cache_dir()
    if cache_dir is None:
        return True
    if not cache_dir.exists():
        return True

    try:
        shutil.rmtree(cache_dir)
        logger.info("Force-cleared QML disk cache at %s", cache_dir)
        return True
    except OSError as exc:
        logger.warning("Could not force-clear QML cache at %s: %s", cache_dir, exc)
        return False


def logo_asset_for_client(fmt: str) -> str:
    fmt_lower = str(fmt or "").lower()
    if "antigravity" in fmt_lower:
        return "clients/antigravity.svg"
    if "gemini" in fmt_lower:
        return "clients/gemini-cli.svg"
    if "codex" in fmt_lower:
        return "clients/codex.svg"
    if "plain" in fmt_lower:
        return "clients/plaintext.svg"
    return "brand/logo.png"

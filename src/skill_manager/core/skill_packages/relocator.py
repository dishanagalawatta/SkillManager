import json
import os
import shutil
from collections.abc import Callable
from pathlib import Path

from .process import _emit


def _cleanup_empty_parents(path: Path, levels: int = 3):
    """Recursively removes empty directories starting from path's parent and going up."""
    try:
        current = path.parent
        for _ in range(levels):
            if current.exists() and current.is_dir():
                if not any(current.iterdir()):
                    current.rmdir()
                    current = current.parent
                else:
                    break
            else:
                current = current.parent
    except OSError:
        pass


def _relocate_path_internal(
    src_path: Path, dest_base: Path, output_callback: Callable[[str], None] | None
) -> bool:
    """Internal helper to move a single directory to dest_base."""
    dest_path = dest_base / src_path.name
    try:
        if dest_path.exists():
            if dest_path.resolve() == src_path.resolve():
                return False
            if dest_path.is_dir():
                _emit(output_callback, f"Cleaning up existing folder at {dest_path}...")
                shutil.rmtree(dest_path)
            else:
                dest_path.unlink()

        dest_path.parent.mkdir(parents=True, exist_ok=True)
        _emit(output_callback, f"Relocating {src_path.name} -> {dest_path}...")
        shutil.move(str(src_path), str(dest_path))

        _cleanup_empty_parents(src_path)
        return True
    except Exception as e:
        _emit(output_callback, f"Relocation failed for {src_path}: {e}")
        return False


def _merge_and_move_lockfile(
    source_lock: Path, target_lock: Path, output_callback: Callable[[str], None] | None
):
    """Moves and carefully merges a skill lockfile."""
    if not source_lock.is_file():
        return

    try:
        if not target_lock.exists():
            target_lock.parent.mkdir(parents=True, exist_ok=True)
            _emit(output_callback, f"Moving lockfile -> {target_lock}...")
            shutil.move(str(source_lock), str(target_lock))
            return

        _emit(output_callback, f"Merging lockfile -> {target_lock}...")
        try:
            with open(target_lock, encoding="utf-8-sig") as f:
                target_data = json.load(f)
        except (json.JSONDecodeError, OSError):
            target_data = {}

        try:
            with open(source_lock, encoding="utf-8-sig") as f:
                source_data = json.load(f)
        except (json.JSONDecodeError, OSError):
            source_data = {}

        if "skills" in source_data and isinstance(source_data["skills"], dict):
            if "skills" not in target_data or not isinstance(target_data["skills"], dict):
                target_data["skills"] = {}
            target_data["skills"].update(source_data["skills"])

        if "version" in source_data and "version" not in target_data:
            target_data["version"] = source_data["version"]

        with open(target_lock, "w", encoding="utf-8") as f:
            json.dump(target_data, f, indent=2)

        source_lock.unlink()

    except Exception as e:
        _emit(output_callback, f"Failed to merge lockfile: {e}")


def relocate_packages(
    source_path: str | os.PathLike,
    target_package_path: str,
    output_callback: Callable[[str], None] | None,
    package_name_prefix: str = "",
) -> list[str] | None:
    """Extracts valid skill folders from source_path and moves them to target_package_path."""
    if not target_package_path:
        _emit(output_callback, "[DEBUG] Relocation skipped: No target package_path configured.")
        return None

    dest_base = Path(os.path.expanduser(target_package_path))
    source_dir = Path(os.path.expanduser(str(source_path))).resolve()

    if not source_dir.is_dir():
        _emit(output_callback, f"[ERROR] Relocation source is not a directory: {source_dir}")
        return None

    skills_dir = source_dir / "skills"
    if not skills_dir.is_dir():
        _emit(
            output_callback,
            f"[WARNING] No 'skills' folder found in {source_dir}. Skipping relocation.",
        )
        return []

    managed_folder_names = set()
    relocated_count = 0

    _emit(output_callback, f"Processing container: {skills_dir.name}")
    try:
        for child in skills_dir.iterdir():
            if child.is_dir() and not child.name.startswith("."):
                # Validate that it is a proper skill folder
                if not (child / "SKILL.md").is_file() and not (child / "config.json").is_file():
                    _emit(output_callback, f"[WARNING] Skipping '{child.name}': No SKILL.md found.")
                    continue

                managed_folder_names.add(child.name)
                if _relocate_path_internal(child, dest_base, output_callback):
                    relocated_count += 1
        _cleanup_empty_parents(skills_dir / "dummy")
    except Exception as e:
        _emit(output_callback, f"Failed to iterate container {skills_dir}: {e}")

    if relocated_count > 0:
        _emit(output_callback, f"Successfully relocated {relocated_count} folders.")

    target_root = dest_base.parent
    if target_root.resolve() == Path.cwd().resolve():
        from skill_manager.core.config import DATA_DIR

        target_root = DATA_DIR

    # Process lockfiles and manifests, namespaced by package_name_prefix to avoid collision
    prefix = f"{package_name_prefix}-" if package_name_prefix else ""
    for lock_name in (
        ".skill-lock.json",
        "skills-lock.json",
        ".antigravity-install-manifest.json",
    ):
        src_lock = source_dir / lock_name
        if src_lock.is_file():
            # Add prefix to target lock name to isolate tracking per repo
            if lock_name.startswith("."):
                target_lock_name = f".{prefix}{lock_name[1:]}"
            else:
                target_lock_name = f"{prefix}{lock_name}"

            tgt_lock = target_root / target_lock_name
            if src_lock.resolve() != tgt_lock.resolve():
                if lock_name.endswith(".json"):
                    _merge_and_move_lockfile(src_lock, tgt_lock, output_callback)
                else:
                    try:
                        if not tgt_lock.exists():
                            tgt_lock.parent.mkdir(parents=True, exist_ok=True)
                            _emit(output_callback, f"Moving manifest -> {tgt_lock}...")
                            shutil.move(str(src_lock), str(tgt_lock))
                    except OSError:
                        pass

    _cleanup_empty_parents(source_dir / "dummy")

    return list(managed_folder_names)

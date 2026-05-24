import json
import os
import re
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

def _relocate_path_internal(src_path: Path, dest_base: Path, output_callback: Callable[[str], None] | None) -> bool:
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

def _merge_and_move_lockfile(source_lock: Path, target_lock: Path, output_callback: Callable[[str], None] | None):
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

def relocate_packages_from_output(
    captured_output: list[str],
    target_package_path: str,
    output_callback: Callable[[str], None] | None,
    *,
    base_path: str | os.PathLike | None = None,
) -> list[str] | None:
    """Parses output log for installed paths and moves those folders to target_package_path."""
    if not target_package_path:
        _emit(output_callback, "[DEBUG] Relocation skipped: No target package_path configured.")
        return None

    dest_base = Path(os.path.expanduser(target_package_path))
    resolve_base = Path(os.path.expanduser(str(base_path))).resolve() if base_path else Path.cwd()
    path_regex = re.compile(
        r"(?:Installed to|to|at|in|at)\s+([a-zA-Z]:[\\/][^…\n\r]+|[a-zA-Z]:[\\/][^…\n\r]+|/[^…\n\r]+|\.[\\/][^…\n\r]+|~[^…\n\r]+)"
    )
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

    _emit(output_callback, f"[DEBUG] Scanning {len(captured_output)} lines for package paths...")
    detected_paths = set()
    for line in captured_output:
        clean_line = ansi_escape.sub("", line)
        match_found = False
        for match in path_regex.finditer(clean_line):
            raw_path = match.group(1).strip()
            try:
                raw_path = raw_path.rstrip("… \t\n\r\v\f│").strip()
                candidate = Path(os.path.expanduser(raw_path))
                if not candidate.is_absolute():
                    candidate = resolve_base / candidate
                expanded = candidate.resolve()
                if expanded.is_dir():
                    detected_paths.add(expanded)
                    _emit(output_callback, f"[DEBUG] Detected path: {expanded}")
                    match_found = True
            except Exception:
                continue

        if not match_found:
            fallback_regex = re.compile(r"([a-zA-Z]:[\\/][^\s│]+[a-zA-Z0-9_.-]+)")
            for match in fallback_regex.finditer(clean_line):
                raw_path = match.group(1).strip()
                try:
                    expanded = Path(os.path.expanduser(raw_path)).resolve()
                    if expanded.is_dir():
                        detected_paths.add(expanded)
                        _emit(output_callback, f"[DEBUG] Fallback detected path: {expanded}")
                except Exception:
                    continue

    if not detected_paths:
        _emit(output_callback, "[DEBUG] No package paths detected in output.")
        return None

    relocated_count = 0
    managed_folder_names = set()

    for src_path in sorted(detected_paths):
        if src_path.name.lower() in ("skills", "agents", ".agents"):
            try:
                for child in src_path.iterdir():
                    if child.is_dir() and not child.name.startswith("."):
                        managed_folder_names.add(child.name)
            except Exception:
                pass
        else:
            managed_folder_names.add(src_path.name)

        try:
            if src_path.resolve() == dest_base.resolve():
                continue
            if str(dest_base.resolve()) in str(src_path.resolve()):
                continue
        except Exception:
            continue

        if src_path.name.lower() in ("skills", "agents", ".agents"):
            _emit(output_callback, f"Processing container: {src_path.name}")
            try:
                for child in src_path.iterdir():
                    if (
                        child.is_dir()
                        and not child.name.startswith(".")
                        and _relocate_path_internal(child, dest_base, output_callback)
                    ):
                        relocated_count += 1
                _cleanup_empty_parents(src_path / "dummy")
            except Exception as e:
                _emit(output_callback, f"Failed to iterate container {src_path}: {e}")
        else:
            if _relocate_path_internal(src_path, dest_base, output_callback):
                relocated_count += 1

    if relocated_count > 0:
        _emit(output_callback, f"Successfully relocated {relocated_count} folders.")

    unique_source_roots = {p.parent.parent for p in detected_paths}
    target_root = dest_base.parent

    if target_root.resolve() == Path.cwd().resolve():
        from skill_manager.core.config import DATA_DIR
        target_root = DATA_DIR

    for src_root in unique_source_roots:
        for lock_name in (".skill-lock.json", "skills-lock.json", ".antigravity-install-manifest.json"):
            src_lock = src_root / lock_name
            if src_lock.is_file():
                tgt_lock = target_root / lock_name
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
        _cleanup_empty_parents(src_root / "skills" / "dummy")

    return list(managed_folder_names)

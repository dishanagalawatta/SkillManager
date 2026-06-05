import json
import os
import re
import shutil
from collections.abc import Callable
from pathlib import Path

from .process import _emit


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
        shutil.copytree(str(src_path), str(dest_path), dirs_exist_ok=True)
        return True
    except Exception as e:
        _emit(output_callback, f"Relocation failed for {src_path}: {e}")
        return False


def _is_safe_relative_to(path: Path, base_path: Path) -> bool:
    try:
        path.resolve().relative_to(base_path.resolve())
        return True
    except ValueError:
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
            shutil.copy2(str(source_lock), str(target_lock))
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
                            shutil.copy2(str(src_lock), str(tgt_lock))
                    except OSError:
                        pass

    return list(managed_folder_names)


def relocate_packages_from_output(
    captured_output: list[str],
    target_package_path: str,
    output_callback: Callable[[str], None] | None,
    base_path: str | os.PathLike | None = None,
    package_name_prefix: str = "",
) -> list[str] | None:
    if not target_package_path:
        _emit(output_callback, "[DEBUG] Relocation skipped: No target package_path configured.")
        return None

    dest_base = Path(os.path.expanduser(target_package_path))
    resolve_base = Path.cwd()
    if base_path:
        resolve_base = Path(os.path.expanduser(str(base_path))).resolve()

    # Match an absolute or relative path that could be an install location
    path_regex = re.compile(r"((?:/|[a-zA-Z]:\\|\~)[^\s│]+)")
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

    _emit(output_callback, f"[DEBUG] Scanning {len(captured_output)} lines for package paths...")
    detected_paths = set()
    for line in captured_output:
        clean_line = ansi_escape.sub("", line)
        match_found = False
        for match in path_regex.finditer(clean_line):
            raw_path = match.group(1).strip()
            try:
                raw_path = re.sub(r"[…\s│]+$", "", raw_path).strip()
                candidate = Path(os.path.expanduser(raw_path))
                if not candidate.is_absolute():
                    candidate = resolve_base / candidate
                expanded = candidate.resolve()
                if expanded.is_dir():
                    if base_path and not _is_safe_relative_to(expanded, resolve_base):
                        _emit(
                            output_callback,
                            f"[WARNING] Security: Ignored path outside of staging directory: {expanded}",
                        )
                        continue
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
                        if base_path and not _is_safe_relative_to(expanded, resolve_base):
                            _emit(
                                output_callback,
                                f"[WARNING] Security: Ignored path outside of staging directory: {expanded}",
                            )
                            continue
                        detected_paths.add(expanded)
                        _emit(output_callback, f"[DEBUG] Fallback detected path: {expanded}")
                except Exception:
                    continue

    if not detected_paths:
        _emit(output_callback, "[DEBUG] No package paths detected in output.")
        return None

    managed_folder_names = set()
    relocated_count = 0

    for src_path in sorted(detected_paths):
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
                    if child.is_dir() and not child.name.startswith("."):
                        # Validate that it is a proper skill folder
                        if not (child / "SKILL.md").is_file() and not (child / "config.json").is_file():
                            # If it's the skills subfolder inside .agents/agents
                            if child.name.lower() == "skills" and src_path.name.lower() in ("agents", ".agents"):
                                # Iterate over the actual skills
                                for inner_child in child.iterdir():
                                    if inner_child.is_dir() and not inner_child.name.startswith("."):
                                        if not (inner_child / "SKILL.md").is_file() and not (inner_child / "config.json").is_file():
                                            _emit(output_callback, f"[WARNING] Skipping '{inner_child.name}': No SKILL.md found.")
                                            continue
                                        managed_folder_names.add(inner_child.name)
                                        if _relocate_path_internal(inner_child, dest_base, output_callback):
                                            relocated_count += 1
                            else:
                                _emit(output_callback, f"[WARNING] Skipping '{child.name}': No SKILL.md found.")
                            continue
                        managed_folder_names.add(child.name)
                        if _relocate_path_internal(child, dest_base, output_callback):
                            relocated_count += 1
            except Exception as e:
                _emit(output_callback, f"Failed to iterate container {src_path}: {e}")
        else:
            if not (src_path / "SKILL.md").is_file() and not (src_path / "config.json").is_file():
                _emit(output_callback, f"[WARNING] Skipping '{src_path.name}': No SKILL.md found.")
            else:
                managed_folder_names.add(src_path.name)
                if _relocate_path_internal(src_path, dest_base, output_callback):
                    relocated_count += 1

    if relocated_count > 0:
        _emit(output_callback, f"Successfully relocated {relocated_count} folders.")

    unique_source_roots = {p.parent.parent for p in detected_paths}
    target_root = dest_base.parent

    if target_root.resolve() == Path.cwd().resolve():
        from skill_manager.core.config import DATA_DIR
        target_root = DATA_DIR

    prefix = f"{package_name_prefix}-" if package_name_prefix else ""
    for src_root in unique_source_roots:
        for lock_name in (
            ".skill-lock.json",
            "skills-lock.json",
            ".antigravity-install-manifest.json",
        ):
            src_lock = src_root / lock_name
            if src_lock.is_file():
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
                                shutil.copy2(str(src_lock), str(tgt_lock))
                        except OSError:
                            pass

    return list(managed_folder_names)

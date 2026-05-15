import json
import os
import re
import shlex
import shutil
import subprocess
from datetime import datetime
from pathlib import Path


def normalize_skill_source_config(data):
    """Return a backward-compatible skill updater/source config."""
    detected = detect_source_config(data)
    source = {
        "name": str(detected.get("name") or "").strip(),
        "source_type": str(detected.get("source_type") or "auto").strip(),
        "repository_url": str(detected.get("repository_url") or "").strip(),
        "local_path": str(detected.get("local_path") or "").strip(),
        "clone_path": str(detected.get("clone_path") or "").strip(),
        "package_name": str(detected.get("package_name") or "").strip(),
        "install_args": str(detected.get("install_args") or "").strip(),
        "update_command": str(detected.get("update_command") or "").strip(),
        "verify_command": str(detected.get("verify_command") or "").strip(),
        "current_version_command": str(detected.get("current_version_command") or "").strip(),
        "latest_version_command": str(detected.get("latest_version_command") or "").strip(),
    }

    for key in ("current_version", "latest_version", "last_updated"):
        if data.get(key):
            source[key] = data.get(key)

    if not source["name"]:
        source["name"] = _fallback_source_name(source)

    return source


def detect_source_config(data):
    source = dict(data or {})
    source_type = str(source.get("source_type") or "auto").strip().lower()
    source["source_type"] = source_type

    update_command = str(source.get("update_command") or "").strip()
    package_name = str(source.get("package_name") or "").strip()
    repository_url = str(source.get("repository_url") or "").strip()
    local_path = str(source.get("local_path") or "").strip()

    if source_type == "auto":
        if package_name:
            source_type = "npm"
        elif update_command:
            source_type = _detect_command_type(update_command)
        source["source_type"] = source_type

    if source_type == "npm":
        _apply_npm_defaults(source)
    elif source_type == "git":
        source["update_command"] = ""
        source.setdefault("latest_version_command", "")
        source.setdefault("current_version_command", "")
    elif source_type == "custom":
        source.setdefault("repository_url", repository_url)
        source.setdefault("local_path", local_path)
    elif update_command:
        source["source_type"] = "custom"

    # Auto-detect verify command for local paths if not provided
    if local_path and not source.get("verify_command"):
        # Expand user path for the generated command to be more portable
        # although our interceptor will handle ~ as well.
        source["verify_command"] = f'test -d {local_path} && echo "Skills installed in {local_path}"'

    return source


def detect_git_remote(local_path):
    if not local_path:
        return ""

    path = Path(os.path.expanduser(local_path))
    if not path.exists():
        return ""

    try:
        result = subprocess.run(
            ["git", "-C", str(path), "config", "--get", "remote.origin.url"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return ""

    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def run_skill_source_update(source, output_callback=None):
    source = normalize_skill_source_config(source)
    local_path = source.get("local_path")
    
    captured_output = []

    def intercept_callback(msg):
        captured_output.append(msg)
        if output_callback:
            output_callback(msg)

    if source.get("source_type") == "npm":
        _run_npm_update(source, intercept_callback)
    elif source.get("update_command"):
        _run_shell_command(source["update_command"], intercept_callback)
    else:
        _run_repository_update(source, intercept_callback)

    # Post-update: Move skills from installation script output if applicable
    if local_path:
        _emit(output_callback, f"[DEBUG] Relocating skills from output to: {local_path}")
        _relocate_skills_from_output(captured_output, local_path, output_callback)

    if source.get("verify_command"):
        _emit(output_callback, f"Verifying {source['name']}...")
        _run_shell_command(source["verify_command"], output_callback)

    current_version = run_version_command(source.get("current_version_command"))
    latest_version = run_version_command(source.get("latest_version_command"))

    if current_version:
        source["current_version"] = current_version
    elif latest_version:
        source["current_version"] = latest_version

    if latest_version:
        source["latest_version"] = latest_version

    source["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return source


def _relocate_path_internal(src_path, dest_base, output_callback):
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
        
        # Cleanup empty parent directories (like .agents/skills)
        _cleanup_empty_parents(src_path)
        return True
    except Exception as e:
        _emit(output_callback, f"Relocation failed for {src_path}: {e}")
        return False


def _relocate_skills_from_output(captured_output, target_local_path, output_callback):
    """Parses output log for installed paths and moves those folders to target_local_path."""
    if not target_local_path:
        _emit(output_callback, "[DEBUG] Relocation skipped: No target local_path configured.")
        return

    dest_base = Path(os.path.expanduser(target_local_path))
    
    # regex to find paths like ~\.agents\skills\caveman or C:\Users\...\.agents\skills\caveman
    # Supports ✓ prefix, handles "Installed to" text, spaces and common path characters.
    # We look for common path starters and capture until end of line or specific delimiters.
    path_regex = re.compile(r'(?:Installed to|to|at|in|at)\s+([a-zA-Z]:[\\/][^…\n\r]+|[a-zA-Z]:[\\/][^…\n\r]+|/[^…\n\r]+|\.\\[^…\n\r]+|~[^…\n\r]+)')
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    
    _emit(output_callback, f"[DEBUG] Scanning {len(captured_output)} lines for installation paths...")
    detected_paths = set()
    for line in captured_output:
        clean_line = ansi_escape.sub('', line)
        # Search for paths after specific keywords to handle spaces correctly
        match_found = False
        for match in path_regex.finditer(clean_line):
            raw_path = match.group(1).strip()
            # Expand ~ and normalize
            try:
                # Remove trailing ellipsis or common terminal artifacts
                raw_path = re.sub(r'[…\s│]+$', '', raw_path).strip()
                expanded = Path(os.path.expanduser(raw_path)).resolve()
                if expanded.is_dir():
                    detected_paths.add(expanded)
                    _emit(output_callback, f"[DEBUG] Detected path: {expanded}")
                    match_found = True
            except Exception:
                continue
        
        if not match_found:
            # Fallback for lines without keywords but containing absolute paths
            fallback_regex = re.compile(r'([a-zA-Z]:[\\/][^\s│]+[a-zA-Z0-9_.-]+)')
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
        _emit(output_callback, "[DEBUG] No installation paths detected in output. Please ensure the tool is installing skills to a visible directory.")
        return

    _emit(output_callback, f"[DEBUG] Total unique paths found: {len(detected_paths)}")
    _emit(output_callback, f"[DEBUG] Relocating to target: {dest_base}")
    relocated_count = 0
    for src_path in sorted(detected_paths):
        # We only want to move folders that are NOT already in the destination
        try:
            if src_path.resolve() == dest_base.resolve():
                continue
            if str(dest_base.resolve()) in str(src_path.resolve()):
                # Already inside destination
                continue
        except Exception:
            continue
            
        # Check if this is a container directory (like 'skills' or 'agents')
        # If it is, we move its contents individually to avoid nested 'skills/skills'
        if src_path.name.lower() in ("skills", "agents", ".agents"):
            _emit(output_callback, f"Processing container: {src_path.name}")
            try:
                for child in src_path.iterdir():
                    if child.is_dir() and not child.name.startswith('.'):
                        if _relocate_path_internal(child, dest_base, output_callback):
                            relocated_count += 1
                # Cleanup the now-empty container
                _cleanup_empty_parents(src_path / "dummy")
            except Exception as e:
                _emit(output_callback, f"Failed to iterate container {src_path}: {e}")
        else:
            if _relocate_path_internal(src_path, dest_base, output_callback):
                relocated_count += 1

    if relocated_count > 0:
        _emit(output_callback, f"Successfully relocated {relocated_count} folders.")
    else:
        _emit(output_callback, "[DEBUG] No folders were moved (maybe already in destination or empty).")

        
        # Handle .skill-lock.json, skills-lock.json and manifest
        # The source lockfile is typically in the parent of the skills folder (e.g. ~/.agent/.skill-lock.json)
        # The target lockfile should be in the parent of the target local_path (e.g. C:/.../.agent/.skill-lock.json)
        unique_source_roots = {p.parent.parent for p in detected_paths}
        target_root = dest_base.parent
        
        # If target_root is project root, use the dedicated data folder to keep root clean
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
                            # fallback for non-json or just move if not exists
                            try:
                                if not tgt_lock.exists():
                                    tgt_lock.parent.mkdir(parents=True, exist_ok=True)
                                    _emit(output_callback, f"Moving manifest -> {tgt_lock}...")
                                    shutil.move(str(src_lock), str(tgt_lock))
                            except OSError:
                                pass
            
            # Clean up the original directories now that lockfiles are removed
            _cleanup_empty_parents(src_root / "skills" / "dummy")


def _merge_and_move_lockfile(source_lock, target_lock, output_callback):
    """Moves and carefully merges a skill lockfile."""
    if not source_lock.is_file():
        return
    
    try:
        if not target_lock.exists():
            target_lock.parent.mkdir(parents=True, exist_ok=True)
            _emit(output_callback, f"Moving lockfile -> {target_lock}...")
            shutil.move(str(source_lock), str(target_lock))
            return
            
        # Target exists, we must merge
        _emit(output_callback, f"Merging lockfile -> {target_lock}...")
        try:
            with open(target_lock, "r", encoding="utf-8-sig") as f:
                target_data = json.load(f)
        except (json.JSONDecodeError, OSError):
            target_data = {}
            
        try:
            with open(source_lock, "r", encoding="utf-8-sig") as f:
                source_data = json.load(f)
        except (json.JSONDecodeError, OSError):
            source_data = {}
            
        # Merge 'skills' dictionary
        if "skills" in source_data and isinstance(source_data["skills"], dict):
            if "skills" not in target_data or not isinstance(target_data["skills"], dict):
                target_data["skills"] = {}
            target_data["skills"].update(source_data["skills"])
            
        # Keep version from source if missing in target
        if "version" in source_data and "version" not in target_data:
            target_data["version"] = source_data["version"]
            
        # Save merged to target
        with open(target_lock, "w", encoding="utf-8") as f:
            json.dump(target_data, f, indent=2)
            
        # Remove source
        source_lock.unlink()
        
    except Exception as e:
        _emit(output_callback, f"Failed to merge lockfile: {e}")


def _cleanup_empty_parents(path, levels=3):
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
                # If current doesn't exist, try its parent (it might have been deleted already)
                current = current.parent
    except OSError:
        pass


def check_skill_source_versions(source):
    source = normalize_skill_source_config(source)
    current_version = run_version_command(source.get("current_version_command"))
    latest_version = run_version_command(source.get("latest_version_command"))

    if current_version:
        source["current_version"] = current_version
    if latest_version:
        source["latest_version"] = latest_version

    return source


def run_version_command(command):
    command = str(command or "").strip()
    if not command:
        return ""

    try:
        if os.name == "nt":
            # On Windows, we need to preserve backslashes in paths.
            # shlex.split in POSIX mode (which is default and best for removing quotes)
            # treats backslashes as escape characters. By doubling them, we ensure
            # they are preserved as single backslashes in the resulting tokens.
            command = command.replace("\\", "\\\\")

        args = shlex.split(command)
        if not args:
            return ""

        # Ensure the executable is resolved from PATH if not an absolute path
        args = _resolve_process_command(args, shell=False)
        result = subprocess.run(args, shell=False, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError, ValueError, IndexError):
        return ""

    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def _run_repository_update(source, output_callback):
    """
    Clones or pulls a git repository.

    Supports two modes:
    - Standard: `local_path` is used for both the git checkout and as the relocation base.
    - Staged: `clone_path` is used for the git checkout; `local_path` is the relocation target.
      After a successful clone/pull, `clone_path` is emitted into output so that
      `_relocate_skills_from_output` can detect it and move skills into `local_path`.
    """
    repository_url = source.get("repository_url")
    local_path = source.get("local_path")
    clone_path = source.get("clone_path") or local_path

    if not repository_url:
        raise ValueError("Configure a repository_url for git sources.")
    if not clone_path:
        raise ValueError("Configure either local_path or clone_path for git sources.")

    path = Path(os.path.expanduser(clone_path))
    if (path / ".git").is_dir():
        _emit(output_callback, f"Pulling {repository_url} in {path}...")
        _run_process(["git", "-C", str(path), "pull", "--ff-only"], output_callback)
    elif path.exists() and any(path.iterdir()):
        raise ValueError(f"Clone path exists but is not an empty git checkout: {path}")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        _emit(output_callback, f"Cloning {repository_url} into {path}...")
        _run_process(["git", "clone", repository_url, str(path)], output_callback)

    # Emit clone_path into output so _relocate_skills_from_output can detect it
    # when clone_path differs from local_path (staged mode).
    if clone_path != local_path:
        _emit(output_callback, f"Installed to {path}")


def _run_npm_update(source, output_callback):
    package_name = source.get("package_name")
    if not package_name:
        raise ValueError("Configure an npm package name.")

    command = ["npx", "--yes", package_name]
    if source.get("install_args"):
        command.extend(_split_args(source["install_args"]))
    _run_process(command, output_callback)


def _run_shell_command(command, output_callback):
    if _intercept_cross_platform_command(command, output_callback):
        return
    _run_process(command, output_callback, shell=True)


def _intercept_cross_platform_command(command, output_callback):
    """
    Interprets simple bash-like commands natively in Python for cross-platform support.
    Currently supports: test -d <path> [&& echo <message>]
    """
    command = str(command or "").strip()
    if not command.startswith("test "):
        return False

    # Handle test -d path && echo "msg" or test -d path
    parts = command.split("&&", 1)
    test_part = parts[0].strip()

    # We only support 'test -d' for now as requested
    if not test_part.startswith("test -d "):
        return False

    path = test_part[len("test -d ") :].strip()
    # Handle quoted paths
    if (path.startswith('"') and path.endswith('"')) or (
        path.startswith("'") and path.endswith("'")
    ):
        path = path[1:-1]

    # Fix common typo where user types ~. instead of ~/.
    if path.startswith("~."):
        path = "~/" + path[1:]

    # Expand ~ and environment variables
    expanded_path = os.path.expandvars(os.path.expanduser(path))

    if not Path(expanded_path).is_dir():
        msg = f"Verification failed: Directory not found: {expanded_path}"
        _emit(output_callback, msg)
        raise RuntimeError(msg)

    if len(parts) > 1:
        echo_part = parts[1].strip()
        if echo_part.startswith("echo "):
            msg = echo_part[len("echo ") :].strip()
            # Remove surrounding quotes from message
            if (msg.startswith('"') and msg.endswith('"')) or (
                msg.startswith("'") and msg.endswith("'")
            ):
                msg = msg[1:-1]
            _emit(output_callback, msg)

    return True


def _run_process(command, output_callback, shell=False):
    command = _resolve_process_command(command, shell)
    process = subprocess.Popen(
        command,
        shell=shell,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )
    last_emit_time = 0
    import time

    if process.stdout is not None:
        for line in process.stdout:
            line_clean = line.strip()
            if line_clean:
                # Always print to terminal for visibility
                print(f"[PROCESS] {line_clean}")
                
                # Throttle progress-like lines to UI (e.g. "Updating files: 45%")
                is_progress = bool(re.search(r'\d+%', line_clean))
                current_time = time.time()
                
                if not is_progress or (current_time - last_emit_time > 0.5):
                    _emit(output_callback, line_clean)
                    if is_progress:
                        last_emit_time = current_time

    process.wait()
    if process.returncode != 0:
        raise subprocess.CalledProcessError(process.returncode, command)


def _resolve_process_command(command, shell=False):
    if shell or not isinstance(command, list) or not command:
        return command

    executable = command[0]
    if os.path.isabs(executable) or os.sep in executable or (os.altsep and os.altsep in executable):
        return command

    resolved = shutil.which(executable)
    if not resolved:
        raise FileNotFoundError(
            f"Executable '{executable}' was not found on PATH while running: {' '.join(command)}"
        )
    return [resolved, *command[1:]]


def _emit(output_callback, message):
    # Print to terminal for debugging and visibility
    if message.startswith("[DEBUG]") or message.startswith("[ERROR]") or "Relocating" in message or "Success" in message:
        print(message)
    if output_callback:
        output_callback(message)


def _fallback_source_name(source):
    package_name = source.get("package_name")
    if package_name:
        return package_name

    repository_url = source.get("repository_url", "").rstrip("/")
    if repository_url:
        return repository_url.rsplit("/", 1)[-1].removesuffix(".git") or "Unnamed Source"

    local_path = source.get("local_path")
    if local_path:
        return Path(local_path).name or "Unnamed Source"

    return "Unnamed Source"


def _apply_npm_defaults(source):
    package_name = str(source.get("package_name") or "").strip()

    if package_name:
        parts = _split_args(package_name)
        if parts and parts[0] == "npx":
            parts.pop(0)
            if parts and parts[0] == "--yes":
                parts.pop(0)
        
        if parts:
            package_name = parts[0]
            extra_args = " ".join(parts[1:])
            source["package_name"] = package_name
            if extra_args:
                existing_args = str(source.get("install_args") or "").strip()
                source["install_args"] = f"{extra_args} {existing_args}".strip()

    update_command = str(source.get("update_command") or "").strip()
    if not package_name and update_command:
        parsed_package, parsed_args = _parse_npx_command(update_command)
        package_name = parsed_package
        source["package_name"] = package_name
        source.setdefault("install_args", parsed_args)

    if not package_name:
        return

    args = str(source.get("install_args") or "").strip()
    source["update_command"] = f"npx --yes {package_name}" + (f" {args}" if args else "")

    source["latest_version_command"] = f"npm show {package_name} version"


def _detect_command_type(command):
    if _parse_npx_command(command)[0]:
        return "npm"
    return "custom"


def _parse_npx_command(command):
    command = command.strip()
    match = re.match(r"^npx\s+(?:--yes\s+)?(?P<package>[^\s]+)(?P<args>.*)$", command)
    if not match:
        return "", ""
    package_name = match.group("package").strip()
    args = match.group("args").strip()
    return package_name, args


def _split_args(value):
    return [part for part in str(value or "").split() if part]

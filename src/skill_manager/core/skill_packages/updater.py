import os
import re
import shlex
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Callable, List

from .process import run_process, _emit
from .config import normalize_skill_package_config
from .versioning import check_skill_package_versions
from .relocator import relocate_packages_from_output

def _run_git_package_update(source: Dict[str, Any], output_callback: Optional[Callable[[str], None]]):
    repository_url = source.get("repository_url")
    package_path = source.get("package_path")
    clone_path = source.get("clone_path") or package_path

    if not repository_url:
        raise ValueError("Configure a repository_url for git sources.")
    if not clone_path:
        raise ValueError("Configure either package_path or clone_path for git sources.")

    path = Path(os.path.expanduser(clone_path))
    auth_url = repository_url

    if (path / ".git").is_dir():
        _emit(output_callback, f"Pulling {repository_url} in {path}...")
        run_process(
            ["git"]
            + (
                [
                    "-c",
                    f"credential.helper=!f() {{ echo username=token; echo password={shlex.quote(source.get('github_token'))}; }}; f",
                ]
                if source.get("github_token")
                else []
            )
            + ["-C", str(path), "pull", "--ff-only"],
            output_callback,
        )
    elif path.exists() and any(path.iterdir()):
        raise ValueError(f"Clone path exists but is not an empty git checkout: {path}")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        _emit(output_callback, f"Cloning {repository_url} into {path}...")
        run_process(
            ["git"]
            + (
                [
                    "-c",
                    f"credential.helper=!f() {{ echo username=token; echo password={shlex.quote(source.get('github_token'))}; }}; f",
                ]
                if source.get("github_token")
                else []
            )
            + ["clone", "--", auth_url, str(path)],
            output_callback,
        )

    if clone_path != package_path:
        _emit(output_callback, f"Installed to {path}")

def _run_npm_update(source: Dict[str, Any], output_callback: Optional[Callable[[str], None]]):
    package_name = source.get("package_name")
    if not package_name:
        raise ValueError("Configure an npm package name.")

    command = ["npx", "--yes", package_name]
    if source.get("package_args"):
        # Local import or copy _split_args
        from .config import _split_args
        command.extend(_split_args(source["package_args"]))
    run_process(command, output_callback)

def _intercept_cross_platform_command(command: str, output_callback: Optional[Callable[[str], None]]) -> bool:
    command = str(command or "").strip()
    if not command.startswith("test "):
        return False

    parts = command.split("&&", 1)
    test_part = parts[0].strip()

    if not test_part.startswith("test -d "):
        return False

    path = test_part[len("test -d ") :].strip()
    if "'" in path or '"' in path:
        try:
            path_tokens = shlex.split(path)
            if path_tokens:
                path = "".join(path_tokens)
        except ValueError:
            if (path.startswith('"') and path.endswith('"')) or (path.startswith("'") and path.endswith("'")):
                path = path[1:-1]

    if path.startswith("~."):
        path = "~/" + path[1:]

    expanded_path = os.path.expandvars(os.path.expanduser(path))

    if not Path(expanded_path).is_dir():
        msg = f"Verification failed: Directory not found: {expanded_path}"
        _emit(output_callback, msg)
        raise RuntimeError(msg)

    if len(parts) > 1:
        echo_part = parts[1].strip()
        if echo_part.startswith("echo "):
            msg = echo_part[len("echo ") :].strip()
            if "'" in msg or '"' in msg:
                try:
                    msg_tokens = shlex.split(msg)
                    if msg_tokens:
                        msg = " ".join(msg_tokens)
                except ValueError:
                    if (msg.startswith('"') and msg.endswith('"')) or (msg.startswith("'") and msg.endswith("'")):
                        msg = msg[1:-1]
            _emit(output_callback, msg)

    return True

def _run_shell_command(command: str, output_callback: Optional[Callable[[str], None]]):
    if _intercept_cross_platform_command(command, output_callback):
        return
    run_process(command, output_callback, shell=True)

def run_skill_package_update(source: Dict[str, Any], output_callback: Optional[Callable[[str], None]] = None) -> Dict[str, Any]:
    source = normalize_skill_package_config(source)
    source.setdefault("current_version", "")
    source.setdefault("latest_version", "")
    source.setdefault("managed_folders", [])
    source.setdefault("removed_folders", [])

    package_path = source.get("package_path")
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
        _run_git_package_update(source, intercept_callback)

    if package_path:
        _emit(output_callback, f"[DEBUG] Relocating skills from output to: {package_path}")
        new_managed = relocate_packages_from_output(captured_output, package_path, output_callback)

        if new_managed is not None:
            old_managed = source.get("managed_folders", [])
            outdated = set(old_managed) - set(new_managed)
            removed = []
            if outdated:
                _emit(output_callback, f"[DEBUG] Cleaning up {len(outdated)} outdated skill folders...")
                dest_base = Path(os.path.expanduser(package_path))
                for folder_name in sorted(outdated):
                    folder_path = dest_base / folder_name
                    if folder_path.is_dir():
                        _emit(output_callback, f"[DEBUG] Deleting outdated skill folder: {folder_name}")
                        try:
                            shutil.rmtree(folder_path)
                            removed.append(folder_name)
                        except Exception as e:
                            _emit(output_callback, f"[ERROR] Failed to delete {folder_name}: {e}")

            source["managed_folders"] = new_managed
            source["removed_folders"] = removed

    if source.get("verify_command"):
        _emit(output_callback, f"Verifying {source['name']}...")
        _run_shell_command(source["verify_command"], output_callback)

    updated_source_info = check_skill_package_versions(source, force_refresh=True)
    source.update(updated_source_info)

    source["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return source

import os
import shlex
import shutil
import tempfile
from collections.abc import Callable
from contextlib import nullcontext
from datetime import datetime
from pathlib import Path
from typing import Any

from git import Repo, cmd

from .config import normalize_skill_package_config
from .process import _emit, run_process
from .relocator import relocate_packages, relocate_packages_from_output
from .versioning import check_skill_package_versions


def _remove_package_folder(path: Path) -> None:
    shutil.rmtree(path)


def _run_git_package_update(source: dict[str, Any], output_callback: Callable[[str], None] | None):
    repository_url = source.get("repository_url")
    package_path = source.get("resolved_package_path") or source.get("package_path")
    clone_path = source.get("clone_path")
    if not clone_path:
        from skill_manager.core.config import DATA_DIR

        from .storage import safe_package_folder_name

        package_name = safe_package_folder_name(source)
        clone_path = str(DATA_DIR / "package_clones" / package_name)
        source["clone_path"] = clone_path

    if not repository_url:
        raise ValueError("Configure a repository_url for git sources.")

    path = Path(os.path.expanduser(clone_path))
    token = source.get("github_token")

    # Use a custom credential helper to provide the token if available
    config_args = ["-c", "protocol.ext.allow=never"]
    if token:
        config_args.extend(
            [
                "-c",
                f"credential.helper=!f() {{ echo username=token; echo password={shlex.quote(token)}; }}; f",
            ]
        )

    if (path / ".git").is_dir():
        _emit(output_callback, f"Pulling {repository_url} in {path}...")
        try:
            repo = Repo(path)
            # We use git.cmd.Git for more control over the pull command with config arguments
            g = repo.git
            # Execute pull with config args
            output = g.execute(["git"] + config_args + ["pull", "--ff-only"])
            if output:
                _emit(output_callback, output)
            _emit(output_callback, f"Successfully pulled '{repository_url}'.")
        except Exception as e:
            _emit(output_callback, f"Git pull failed: {e}")
            raise
    elif path.exists() and any(path.iterdir()):
        raise ValueError(f"Clone path exists but is not an empty git checkout: {path}")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        _emit(output_callback, f"Cloning {repository_url} into {path}...")
        try:
            # Repo.clone_from doesn't easily support arbitrary git -c arguments
            # so we use git.cmd.Git directly
            g = cmd.Git()
            output = g.execute(["git"] + config_args + ["clone", "--", repository_url, str(path)])
            if output:
                _emit(output_callback, output)
            _emit(output_callback, f"Successfully cloned '{repository_url}'.")
        except Exception as e:
            _emit(output_callback, f"Git clone failed: {e}")
            raise

    if clone_path != package_path:
        _emit(output_callback, f"Installed to {path}")


def _run_npx_update(
    source: dict[str, Any],
    output_callback: Callable[[str], None] | None,
    cwd: str | os.PathLike | None = None,
):
    package_name = source.get("package_name")
    if not package_name:
        raise ValueError("Configure an npx package name.")

    command = ["npx", "--yes", "--", package_name]
    if source.get("package_args"):
        from .config import _split_args

        command.extend(_split_args(source["package_args"]))
    run_process(command, output_callback, cwd=cwd)


def _intercept_cross_platform_command(
    command: str, output_callback: Callable[[str], None] | None
) -> bool:
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
            if (path.startswith('"') and path.endswith('"')) or (
                path.startswith("'") and path.endswith("'")
            ):
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
                    if (msg.startswith('"') and msg.endswith('"')) or (
                        msg.startswith("'") and msg.endswith("'")
                    ):
                        msg = msg[1:-1]
            _emit(output_callback, msg)

    return True


def _run_shell_command(
    command: str,
    output_callback: Callable[[str], None] | None,
    cwd: str | os.PathLike | None = None,
):
    if _intercept_cross_platform_command(command, output_callback):
        return
    run_process(command, output_callback, shell=True, cwd=cwd)


def run_skill_package_update(
    source: dict[str, Any], output_callback: Callable[[str], None] | None = None
) -> dict[str, Any]:
    source = normalize_skill_package_config(source)
    source.setdefault("current_version", "")
    source.setdefault("latest_version", "")
    source.setdefault("managed_folders", [])
    source.setdefault("removed_folders", [])

    package_path = source.get("resolved_package_path") or source.get("package_path")
    captured_output = []
    staging_path = None

    def intercept_callback(msg):
        captured_output.append(msg)
        if output_callback:
            output_callback(msg)

    uses_staging = source.get("source_type") == "npx" or bool(source.get("update_command"))
    staging_context = (
        tempfile.TemporaryDirectory(prefix="skillmanager-package-", ignore_cleanup_errors=True)
        if uses_staging
        else nullcontext(None)
    )
    with staging_context as staging_dir:
        staging_path = staging_dir
        if source.get("source_type") == "npx":
            _run_npx_update(source, intercept_callback, cwd=staging_path)
        elif source.get("update_command"):
            _run_shell_command(source["update_command"], intercept_callback, cwd=staging_path)
        else:
            _run_git_package_update(source, intercept_callback)

        if package_path:
            if uses_staging:
                _emit(output_callback, f"[DEBUG] Relocating skills from output to: {package_path}")
                new_managed = relocate_packages_from_output(
                    captured_output,
                    package_path,
                    output_callback,
                    base_path=staging_path,
                    package_name_prefix=source.get("name", ""),
                )
            else:
                _emit(output_callback, f"[DEBUG] Relocating skills from source to: {package_path}")
                clone_path = source.get("clone_path") or package_path
                source_path = Path(os.path.expanduser(clone_path))

                new_managed = relocate_packages(
                    source_path=source_path,
                    target_package_path=package_path,
                    output_callback=output_callback,
                    package_name_prefix=source.get("name", ""),
                )

            if new_managed is not None:
                old_managed = source.get("managed_folders", [])
                outdated = set(old_managed) - set(new_managed)
                removed = []
                if outdated:
                    _emit(
                        output_callback,
                        f"[DEBUG] Cleaning up {len(outdated)} outdated skill folders...",
                    )
                    dest_base = Path(os.path.expanduser(package_path))
                    for folder_name in sorted(outdated):
                        folder_path = dest_base / folder_name
                        if folder_path.is_dir():
                            _emit(
                                output_callback,
                                f"[DEBUG] Deleting outdated skill folder: {folder_name}",
                            )
                            try:
                                _remove_package_folder(folder_path)
                                removed.append(folder_name)
                            except Exception as e:
                                _emit(
                                    output_callback, f"[ERROR] Failed to delete {folder_name}: {e}"
                                )

                source["managed_folders"] = new_managed
                source["removed_folders"] = removed

    if source.get("verify_command"):
        _emit(output_callback, f"Verifying {source['name']}...")
        _run_shell_command(source["verify_command"], output_callback)

    updated_source_info = check_skill_package_versions(source, force_refresh=True)
    source.update(updated_source_info)

    source["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return source

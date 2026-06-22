import os
import shlex
import subprocess
from pathlib import Path
from typing import Any

from .config import normalize_skill_package_config


def detect_git_remote(package_path: str) -> str:
    if not package_path:
        return ""

    path = Path(os.path.expanduser(package_path))
    if not path.exists():
        return ""

    try:
        result = subprocess.run(
            [
                "git",
                "-c",
                "protocol.ext.allow=never",
                "-C",
                str(path),
                "config",
                "--get",
                "remote.origin.url",
            ],
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


def run_version_command(command: str) -> str:
    command = str(command or "").strip()
    if not command:
        return ""

    try:
        command_list = shlex.split(command)
        result = subprocess.run(
            command_list, shell=False, capture_output=True, text=True, timeout=30
        )
    except (OSError, subprocess.SubprocessError, ValueError):
        return ""

    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def get_git_tag(path_or_url: str, is_remote: bool = False, token: str = None) -> str:
    """Fetches the latest semantic tag or fallback to commit hash."""
    try:
        if is_remote:
            auth_url = path_or_url
            # Fetch tags from remote
            result = subprocess.run(
                ["git", "-c", "protocol.ext.allow=never"]
                + (
                    [
                        "-c",
                        f"credential.helper=!f() {{ echo username=token; echo password={shlex.quote(token)}; }}; f",
                    ]
                    if token
                    else []
                )
                + ["ls-remote", "--tags", "--sort=-v:refname", "--", auth_url],
                capture_output=True,
                text=True,
                timeout=15,
            )
            if result.returncode == 0 and result.stdout:
                lines = result.stdout.strip().split("\n")
                for line in lines:
                    if "^{}" in line:
                        continue
                    ref = line.split("\t")[-1]
                    tag = ref.replace("refs/tags/", "")
                    if tag:
                        return tag

            # Fallback to latest commit hash on main/master
            result = subprocess.run(
                ["git", "-c", "protocol.ext.allow=never"]
                + (
                    [
                        "-c",
                        f"credential.helper=!f() {{ echo username=token; echo password={shlex.quote(token)}; }}; f",
                    ]
                    if token
                    else []
                )
                + ["ls-remote", "--", auth_url, "HEAD"],
                capture_output=True,
                text=True,
                timeout=15,
            )
            if result.returncode == 0 and result.stdout:
                return result.stdout.split("\t")[0][:7]
        else:
            path = Path(path_or_url)
            if not (path / ".git").is_dir():
                return ""

            result = subprocess.run(
                [
                    "git",
                    "-c",
                    "protocol.ext.allow=never",
                    "-C",
                    str(path),
                    "describe",
                    "--tags",
                    "--abbrev=0",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0 and result.stdout:
                return result.stdout.strip()

            result = subprocess.run(
                [
                    "git",
                    "-c",
                    "protocol.ext.allow=never",
                    "-C",
                    str(path),
                    "rev-parse",
                    "--short",
                    "HEAD",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0 and result.stdout:
                return result.stdout.strip()
    except Exception:
        pass
    return ""


def check_skill_package_versions(
    source: dict[str, Any], force_refresh: bool = False
) -> dict[str, Any]:
    source = normalize_skill_package_config(source)

    current_version = source.get("current_version", "")
    latest_version = source.get("latest_version", "")

    def clean_v(v):
        if v and v.startswith("v"):
            return v[1:]
        return v

    if source.get("current_version_command"):
        detected_current = run_version_command(source.get("current_version_command"))
        if detected_current:
            current_version = clean_v(detected_current)

    if source.get("latest_version_command"):
        detected_latest = run_version_command(source.get("latest_version_command"))
        if detected_latest:
            latest_version = clean_v(detected_latest)

    repo_url = source.get("repository_url")
    token = source.get("github_token")
    if repo_url and ("github.com" in repo_url or "gitlab.com" in repo_url):
        git_latest = get_git_tag(repo_url, is_remote=True, token=token)
        if git_latest:
            latest_version = clean_v(git_latest)

    if source.get("source_type") == "git":
        clone_path = source.get("clone_path") or source.get("package_path")
        if clone_path:
            path = Path(os.path.expanduser(clone_path))
            if (path / ".git").is_dir():
                detected_local = get_git_tag(str(path), is_remote=False)
                if detected_local:
                    current_version = clean_v(detected_local)

        if (not latest_version or force_refresh) and repo_url:
            git_latest = get_git_tag(repo_url, is_remote=True, token=token)
            if git_latest:
                latest_version = clean_v(git_latest)

    if source.get("source_type") == "npm":
        if not latest_version or force_refresh:
            package_name = source.get("package_name")
            if package_name:
                detected_latest = run_version_command(f"npm view -- {package_name} version")
                if detected_latest:
                    latest_version = clean_v(detected_latest)

        if force_refresh and not current_version and latest_version:
            current_version = latest_version

    if current_version:
        source["current_version"] = clean_v(current_version)
    if latest_version:
        source["latest_version"] = clean_v(latest_version)

    return source

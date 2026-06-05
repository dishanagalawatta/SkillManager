import asyncio
import logging
import os
import shlex
import subprocess
from pathlib import Path
from typing import Any

from git import Repo, cmd
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from .config import normalize_skill_package_config

logger = logging.getLogger(__name__)


def detect_git_remote(package_path: str) -> str:
    if not package_path:
        return ""

    path = Path(os.path.expanduser(package_path))
    if not path.exists() or not (path / ".git").is_dir():
        return ""

    try:
        repo = Repo(path)
        return repo.remotes.origin.url
    except (Exception, AttributeError):
        return ""


@retry(
    retry=retry_if_exception_type(subprocess.SubprocessError),
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=0.5, max=5),
    reraise=False,
)
def run_version_command(command: str) -> str:
    command = str(command or "").strip()
    if not command:
        return ""

    try:
        command_list = shlex.split(command)
        import shutil

        executable = shutil.which(command_list[0])
        if executable:
            command_list[0] = executable

        kwargs = {"shell": False, "capture_output": True, "text": True, "timeout": 30}
        if os.name == "nt":
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

        result = subprocess.run(command_list, **kwargs)
    except (OSError, subprocess.SubprocessError, ValueError) as e:
        logger.warning("Version command failed: %s - %s", command, e)
        return ""

    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def get_git_tag(path_or_url: str, is_remote: bool = False, token: str = None) -> str:
    """Fetches the latest semantic tag or fallback to commit hash using GitPython."""
    try:
        if is_remote:
            g = cmd.Git()
            env = {}
            if token:
                # Use a custom credential helper to provide the token
                env["GIT_TERMINAL_PROMPT"] = "0"
                # GitPython doesn't have a direct way to set -c for ls-remote easily in cmd.Git()
                # but we can use the environment or specialized git config if needed.
                # For ls-remote, passing config via -c is reliable.
                config_args = [
                    "-c",
                    "protocol.ext.allow=never",
                    "-c",
                    f"credential.helper=!f() {{ echo username=token; echo password={shlex.quote(token)}; }}; f",
                ]
            else:
                config_args = ["-c", "protocol.ext.allow=never"]

            # Fetch tags
            try:
                # Use raw git command via GitPython to have full control over arguments
                output = g.execute(
                    ["git"]
                    + config_args
                    + ["ls-remote", "--tags", "--sort=-v:refname", "--", path_or_url]
                )
                if output:
                    lines = output.strip().split("\n")
                    for line in lines:
                        if "^{}" in line:
                            continue
                        ref = line.split("\t")[-1]
                        tag = ref.replace("refs/tags/", "")
                        if tag:
                            return tag
            except Exception as e:
                logger.debug("Remote tag fetch failed, trying HEAD: %s", e)

            # Fallback to HEAD hash
            try:
                output = g.execute(["git"] + config_args + ["ls-remote", "--", path_or_url, "HEAD"])
                if output:
                    return output.split("\t")[0][:7]
            except Exception as e:
                logger.warning("Remote HEAD fetch failed: %s", e)
        else:
            path = Path(path_or_url)
            if not (path / ".git").is_dir():
                return ""

            repo = Repo(path)
            # Try to get the latest tag locally
            tags = sorted(repo.tags, key=lambda t: t.commit.committed_datetime, reverse=True)
            if tags:
                return tags[0].name

            # Fallback to short commit hash
            return repo.head.commit.hexsha[:7]
    except Exception as e:
        logger.warning("Git tag fetch failed for %s: %s", path_or_url, e)

    return ""


async def check_skill_package_versions_async(
    source: dict[str, Any], force_refresh: bool = False
) -> dict[str, Any]:
    """Async version of check_skill_package_versions for non-blocking UI."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None, lambda: check_skill_package_versions(source, force_refresh)
    )


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

    if source.get("source_type") == "npm" and (not latest_version or force_refresh):
        package_name = source.get("package_name")
        if package_name:
            detected_latest = run_version_command(f"npm view -- {package_name} version")
            if detected_latest:
                latest_version = clean_v(detected_latest)

    # After a successful update (indicated by force_refresh=True),
    # we should assume current_version is now latest_version
    # for packages that don't have a reliable local version detection mechanism.
    if (
        force_refresh
        and latest_version
        and source.get("source_type") != "git"
        and not source.get("current_version_command")
    ):
        current_version = latest_version

    if current_version:
        source["current_version"] = clean_v(current_version)
    if latest_version:
        source["latest_version"] = clean_v(latest_version)

    return source

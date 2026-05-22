import hashlib
import os
import re
import shlex
from pathlib import Path
from typing import Any


def _stable_package_id(source: dict[str, Any]) -> str:
    identity = (
        source.get("repository_url")
        or source.get("package_name")
        or source.get("package_path")
        or source.get("name")
        or "unnamed-package"
    )
    digest = hashlib.sha1(str(identity).strip().lower().encode("utf-8")).hexdigest()[:12]
    return f"pkg_{digest}"

def _fallback_package_name(source: dict[str, Any]) -> str:
    package_name = source.get("package_name")
    if package_name:
        return package_name

    repository_url = source.get("repository_url", "").rstrip("/")
    if repository_url:
        return repository_url.rsplit("/", 1)[-1].removesuffix(".git") or "Unnamed Package"

    package_path = source.get("package_path")
    if package_path:
        return Path(package_path).name or "Unnamed Package"

    return "Unnamed Package"

def _split_args(value: Any) -> list[str]:
    return [part for part in str(value or "").split() if part]

def _parse_npx_command(command: str) -> tuple[str, str]:
    command = command.strip()
    match = re.match(r"^npx\s+(?:--yes\s+)?(?P<package>[^\s]+)(?P<args>.*)$", command)
    if not match:
        return "", ""
    package_name = match.group("package").strip()
    args = match.group("args").strip()
    return package_name, args

def _detect_command_type(command: str) -> str:
    if _parse_npx_command(command)[0]:
        return "npm"
    return "custom"

def _apply_npm_defaults(source: dict[str, Any]):
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
                existing_args = str(source.get("package_args") or "").strip()
                source["package_args"] = f"{extra_args} {existing_args}".strip()

    update_command = str(source.get("update_command") or "").strip()
    if not package_name and update_command:
        parsed_package, parsed_args = _parse_npx_command(update_command)
        package_name = parsed_package
        source["package_name"] = package_name
        source.setdefault("package_args", parsed_args)

    if not package_name:
        return

    args = str(source.get("package_args") or "").strip()
    source["update_command"] = f"npx --yes {package_name}" + (f" {args}" if args else "")
    source["latest_version_command"] = f"npm show {package_name} version"

def detect_package_config(data: dict[str, Any]) -> dict[str, Any]:
    source = dict(data or {})
    source_type = str(source.get("source_type") or "auto").strip().lower()
    source["source_type"] = source_type

    update_command = str(source.get("update_command") or "").strip()
    package_name = str(source.get("package_name") or "").strip()
    repository_url = str(source.get("repository_url") or "").strip()
    package_path = str(source.get("package_path") or source.get("local_path") or "").strip()

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
        source.setdefault("package_path", package_path)
    elif update_command:
        source["source_type"] = "custom"

    if (
        source.get("source_type") == "custom"
        and update_command
        and not source.get("current_version_command")
    ):
        source["current_version_command"] = update_command

    if package_path and not source.get("verify_command"):
        expanded = os.path.expanduser(package_path)
        quoted_path = shlex.quote(expanded)
        source["verify_command"] = (
            f'test -d {quoted_path} && echo "Skills installed in "{quoted_path}'
        )

    return source

def normalize_skill_package_config(data: dict[str, Any]) -> dict[str, Any]:
    detected = detect_package_config(data)
    pkg_path = str(detected.get("package_path") or detected.get("local_path") or "").strip()
    pkg_args = str(detected.get("package_args") or detected.get("install_args") or "").strip()

    source = {
        "package_id": str(detected.get("package_id") or "").strip(),
        "name": str(detected.get("name") or "").strip(),
        "source_type": str(detected.get("source_type") or "auto").strip(),
        "repository_url": str(detected.get("repository_url") or "").strip(),
        "github_token": str(detected.get("github_token") or "").strip(),
        "package_path": pkg_path,
        "clone_path": str(detected.get("clone_path") or "").strip(),
        "package_name": str(detected.get("package_name") or "").strip(),
        "package_args": pkg_args,
        "update_command": str(detected.get("update_command") or "").strip(),
        "verify_command": str(detected.get("verify_command") or "").strip(),
        "current_version_command": str(detected.get("current_version_command") or "").strip(),
        "latest_version_command": str(detected.get("latest_version_command") or "").strip(),
    }

    source["local_path"] = source["package_path"]
    source["install_args"] = source["package_args"]

    for key in ("current_version", "latest_version", "last_updated", "managed_folders"):
        if data and hasattr(data, "get") and data.get(key):
            source[key] = data.get(key)

    if not source["name"]:
        source["name"] = _fallback_package_name(source)
    if not source["package_id"]:
        source["package_id"] = _stable_package_id(source)

    return source

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


def split_args(value: Any) -> list[str]:
    return [part for part in str(value or "").split() if part]


def parse_npx_command(command: str) -> tuple[str, str]:
    command = command.strip()
    match = re.match(r"^npx\s+(?:--yes\s+)?(?:--\s+)?(?P<package>[^\s]+)(?P<args>.*)$", command)
    if not match:
        return "", ""
    package_name = match.group("package").strip()
    args = match.group("args").strip()
    return package_name, args


def detect_command_type(command: str) -> str:
    if parse_npx_command(command)[0]:
        return "npx"
    return "custom"


def humanize_slug(slug: str) -> str:
    """Converts a slug like 'agentic-awesome-skills' or 'find_skills' into 'Agentic Awesome Skills'."""
    slug = str(slug or "").strip().lstrip("@")
    if not slug:
        return ""
    words = re.split(r"[-_\s/]+", slug)
    cleaned = [w.capitalize() for w in words if w]
    return " ".join(cleaned)


KNOWN_SKILL_REPO_ALIASES: dict[str, str] = {
    "vercel-labs/find-skills": "vercel-labs/skills",
}


def _sanitize_package_shorthand(text: str) -> str:
    for alias, canonical in KNOWN_SKILL_REPO_ALIASES.items():
        if alias in text:
            text = text.replace(alias, canonical)
    return text


def infer_package_metadata(raw_input: str) -> dict[str, str]:
    """Infers source_type, display_name, package_name, repository_url, and update_command from user input."""
    raw = str(raw_input or "").strip()
    if not raw:
        return {
            "source_type": "npx",
            "display_name": "",
            "package_name": "",
            "repository_url": "",
            "update_command": "",
        }

    # 1. Unwrap 'git clone ...'
    git_clone_match = re.match(r"^git\s+clone\s+(?:--?[^\s]+\s+)*(?P<target>[^\s]+)", raw)
    if git_clone_match:
        target = git_clone_match.group("target").strip()
        clean_url = target.rstrip("/")
        repo_slug = clean_url.rsplit("/", 1)[-1].removesuffix(".git")
        if ":" in repo_slug:
            repo_slug = repo_slug.rsplit(":", 1)[-1]
        return {
            "source_type": "git",
            "display_name": humanize_slug(repo_slug),
            "package_name": "",
            "repository_url": _sanitize_package_shorthand(target),
            "update_command": "",
        }

    # 2. Unwrap 'npx skills add <target>', 'skills add <target>', etc.
    skills_cli_match = re.match(
        r"^(?:npx\s+)?skills\s+(?:add|install|find|get)\s+(?P<rest>.+)$",
        raw,
    )
    if skills_cli_match:
        rest = skills_cli_match.group("rest").strip()
        parts = split_args(rest)
        target = ""
        skill_name = ""
        flags = []
        i = 0
        while i < len(parts):
            p = parts[i]
            if p in ("--skill", "-s") and i + 1 < len(parts):
                skill_name = parts[i + 1]
                flags.extend([p, parts[i + 1]])
                i += 2
            elif p.startswith("-"):
                flags.append(p)
                i += 1
            elif not target:
                target = p
                i += 1
            else:
                flags.append(p)
                i += 1

        if not target and parts:
            target = parts[0]

        git_starters = ("http://", "https://", "git@", "git://", "ssh://")
        if any(target.startswith(p) for p in git_starters) or target.endswith(".git"):
            clean_url = target.rstrip("/")
            repo_slug = clean_url.rsplit("/", 1)[-1].removesuffix(".git")
            if ":" in repo_slug:
                repo_slug = repo_slug.rsplit(":", 1)[-1]
            return {
                "source_type": "git",
                "display_name": humanize_slug(skill_name or repo_slug),
                "package_name": "",
                "repository_url": _sanitize_package_shorthand(target),
                "update_command": "",
            }

        display_slug = skill_name
        if not display_slug:
            if (target.startswith("@") and "/" in target) or "/" in target:
                _, name = target.split("/", 1)
                display_slug = name
            else:
                display_slug = target

        canonical_target = _sanitize_package_shorthand(target)

        if "-y" not in flags and "--yes" not in flags:
            flags.append("-y")
        if not skill_name and "--all" not in flags:
            flags.append("--all")

        args_str = f"add {canonical_target} " + " ".join(flags)
        return {
            "source_type": "npx",
            "display_name": humanize_slug(display_slug),
            "package_name": "skills",
            "package_args": args_str.strip(),
            "repository_url": f"https://github.com/{canonical_target}"
            if ("/" in canonical_target and not canonical_target.startswith("@"))
            else "",
            "update_command": f"npx --yes -- skills {args_str.strip()}",
        }

    # 3. Unwrap 'npm install / add / i' / 'pnpm add' / 'yarn add' / 'bun add'
    pkg_mgr_match = re.match(
        r"^(?:npm|pnpm|yarn|bun)\s+(?:i|install|add)\s+(?:--?[^\s]+\s+)*(?P<target>[^\s]+)",
        raw,
    )
    if pkg_mgr_match:
        target = pkg_mgr_match.group("target").strip()
        if (target.startswith("@") and "/" in target) or "/" in target:
            _, name = target.split("/", 1)
            display_name = humanize_slug(name)
        else:
            display_name = humanize_slug(target)
        canonical_target = _sanitize_package_shorthand(target)
        return {
            "source_type": "npx",
            "display_name": display_name,
            "package_name": canonical_target,
            "repository_url": f"https://github.com/{canonical_target}"
            if ("/" in canonical_target and not canonical_target.startswith("@"))
            else "",
            "update_command": f"npx --yes -- {canonical_target}",
        }

    # 4. Check for custom shell script / command
    custom_starters = ("bash ", "sh ", "./", "python ", "python3 ", "node ", "make ", "pwsh ")
    if raw.startswith(custom_starters) or raw.endswith((".sh", ".py", ".bash")):
        parts = raw.split()
        script_part = (
            parts[1]
            if (
                raw.startswith(("bash ", "sh ", "python ", "python3 ", "node ", "pwsh "))
                and len(parts) > 1
            )
            else parts[0]
        )
        base_name = Path(script_part).stem
        return {
            "source_type": "custom",
            "display_name": humanize_slug(base_name) or "Custom Script",
            "package_name": "",
            "repository_url": "",
            "update_command": raw,
        }

    # 5. Check for Git repository URL
    git_starters = ("http://", "https://", "git@", "git://", "ssh://")
    if (
        any(raw.startswith(prefix) for prefix in git_starters)
        or raw.endswith(".git")
        or "github.com/" in raw
        or "gitlab.com/" in raw
        or "bitbucket.org/" in raw
    ):
        clean_url = raw.rstrip("/")
        repo_slug = clean_url.rsplit("/", 1)[-1].removesuffix(".git")
        if ":" in repo_slug:
            repo_slug = repo_slug.rsplit(":", 1)[-1]
        return {
            "source_type": "git",
            "display_name": humanize_slug(repo_slug),
            "package_name": "",
            "repository_url": _sanitize_package_shorthand(raw),
            "update_command": "",
        }

    # 6. Check for general NPX command or package name
    if raw.startswith("npx "):
        parsed_pkg, parsed_args = parse_npx_command(raw)
        if parsed_pkg:
            if parsed_pkg in ("degit", "gitpick") and parsed_args:
                arg_parts = parsed_args.split()
                if arg_parts:
                    target = arg_parts[0]
                    repo_slug = target.rsplit("/", 1)[-1]
                    canonical_target = _sanitize_package_shorthand(target)
                    return {
                        "source_type": "git"
                        if ("github.com" in target or "http" in target)
                        else "npx",
                        "display_name": humanize_slug(repo_slug),
                        "package_name": canonical_target,
                        "repository_url": f"https://github.com/{canonical_target}"
                        if "/" in canonical_target and not canonical_target.startswith("@")
                        else "",
                        "update_command": raw,
                    }
            raw = parsed_pkg

    if (raw.startswith("@") and "/" in raw) or "/" in raw:
        _, name = raw.split("/", 1)
        display_name = humanize_slug(name)
    else:
        display_name = humanize_slug(raw)

    canonical_raw = _sanitize_package_shorthand(raw)
    return {
        "source_type": "npx",
        "display_name": display_name,
        "package_name": canonical_raw,
        "repository_url": f"https://github.com/{canonical_raw}"
        if ("/" in canonical_raw and not canonical_raw.startswith("@"))
        else "",
        "update_command": f"npx --yes -- {canonical_raw}",
    }


def _apply_npx_defaults(source: dict[str, Any]):
    for field in ("package_name", "package_args", "update_command", "repository_url"):
        if source.get(field):
            source[field] = _sanitize_package_shorthand(str(source[field]))

    package_name = str(source.get("package_name") or "").strip()

    if package_name:
        parts = split_args(package_name)
        if parts and parts[0] == "npx":
            parts.pop(0)
            if parts and parts[0] == "--yes":
                parts.pop(0)
            if parts and parts[0] == "--":
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
        parsed_package, parsed_args = parse_npx_command(update_command)
        package_name = parsed_package
        source["package_name"] = package_name
        source.setdefault("package_args", parsed_args)

    args = str(source.get("package_args") or "").strip()
    if (
        package_name == "skills"
        and args.startswith("add ")
        and "-y" not in args
        and "--yes" not in args
    ):
        args = f"{args} -y"
        source["package_args"] = args
    source["update_command"] = f"npx --yes -- {package_name}" + (f" {args}" if args else "")
    if "/" in package_name and not package_name.startswith("@"):
        if not source.get("repository_url"):
            source["repository_url"] = f"https://github.com/{package_name}"
        source.setdefault("latest_version_command", "")
    else:
        source["latest_version_command"] = f"npm view {package_name} version"


def _apply_git_defaults(source: dict[str, Any]):
    if source.get("repository_url"):
        source["repository_url"] = _sanitize_package_shorthand(str(source["repository_url"]))
    repo_url = str(source.get("repository_url") or "").strip()
    if repo_url and "://" not in repo_url and not repo_url.startswith("git@"):
        parts = repo_url.split("/")
        if len(parts) == 2 and not parts[0].startswith("@"):
            repo_url = f"https://github.com/{parts[0]}/{parts[1]}"
            if not repo_url.endswith(".git"):
                repo_url += ".git"
            source["repository_url"] = repo_url

    source["update_command"] = ""
    source.setdefault("latest_version_command", "")
    source.setdefault("current_version_command", "")


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
            source_type = "npx"
        elif update_command:
            source_type = detect_command_type(update_command)
        source["source_type"] = source_type

    if source_type == "npx":
        _apply_npx_defaults(source)
    elif source_type == "git":
        _apply_git_defaults(source)
    elif source_type == "custom":
        source.setdefault("repository_url", repository_url)
        source.setdefault("package_path", package_path)
    elif update_command:
        source["source_type"] = "custom"

    # Avoid setting current_version_command to update_command as it will cause re-installation on version check

    verify_target_path = str(source.get("resolved_package_path") or package_path)
    if verify_target_path and not source.get("verify_command"):
        expanded = os.path.expanduser(verify_target_path)
        quoted_path = shlex.quote(expanded)
        source["verify_command"] = (
            f'test -d {quoted_path} && echo "Skills installed in "{quoted_path}'
        )

    return source


def normalize_skill_package_config(data: dict[str, Any]) -> dict[str, Any]:
    from skill_manager.core.copier import repair_malformed_path

    detected = detect_package_config(data)
    configured_pkg_path = repair_malformed_path(
        str(
            detected.get("configured_package_path")
            or detected.get("package_path")
            or detected.get("local_path")
            or ""
        ).strip()
    )
    resolved_pkg_path = repair_malformed_path(
        str(detected.get("resolved_package_path") or detected.get("package_path") or "").strip()
    )
    pkg_args = str(detected.get("package_args") or detected.get("install_args") or "").strip()
    clone_path = repair_malformed_path(str(detected.get("clone_path") or "").strip())

    target_path = resolved_pkg_path or configured_pkg_path
    if target_path:
        expanded = os.path.expanduser(target_path)
        quoted_path = shlex.quote(expanded)
        verify_cmd = f'test -d {quoted_path} && echo "Skills installed in "{quoted_path}'
    else:
        verify_cmd = str(detected.get("verify_command") or "").strip()
        if verify_cmd:
            verify_cmd = re.sub(r"\bhome/", "/home/", verify_cmd)

    source = {
        "package_id": str(detected.get("package_id") or "").strip(),
        "name": str(detected.get("name") or "").strip(),
        "source_type": str(detected.get("source_type") or "auto").strip(),
        "repository_url": str(detected.get("repository_url") or "").strip(),
        "github_token": str(detected.get("github_token") or "").strip(),
        "configured_package_path": configured_pkg_path,
        "resolved_package_path": resolved_pkg_path,
        "package_path": resolved_pkg_path or configured_pkg_path,
        "clone_path": clone_path,
        "package_name": str(detected.get("package_name") or "").strip(),
        "package_args": pkg_args,
        "update_command": str(detected.get("update_command") or "").strip(),
        "verify_command": verify_cmd,
        "current_version_command": str(detected.get("current_version_command") or "").strip(),
        "latest_version_command": str(detected.get("latest_version_command") or "").strip(),
    }

    source["local_path"] = source["package_path"]
    source["install_args"] = source["package_args"]

    for key in (
        "current_version",
        "latest_version",
        "last_updated",
        "managed_folders",
        "storage_mode",
    ):
        if data and hasattr(data, "get") and data.get(key):
            source[key] = data.get(key)  # type: ignore[index]

    if not source["name"]:
        source["name"] = _fallback_package_name(source)
    if not source["package_id"]:
        source["package_id"] = _stable_package_id(source)

    return source

import asyncio
import json
import logging
import os
import re
import shlex
import subprocess
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from git import Repo, cmd

from .config import normalize_skill_package_config

logger = logging.getLogger(__name__)

# Bare short/long hex commit ids produced by the get_git_tag HEAD fallback.
# These are content pointers, not comparable releases, and must never
# overwrite a real (semver-like) latest_version for npm-identity packages.
_COMMIT_HASH_RE = re.compile(r"\A[0-9a-f]{7,40}\Z")

# Hard ceiling for a single remote probe.  Every network probe in this module
# is bounded: a git remote that never answers used to block the scan thread
# forever, which left ``_is_loading`` stuck and disabled update scanning for
# the rest of the session.
DEFAULT_GIT_TIMEOUT = 10.0

# ssh must never try to prompt either (BatchMode makes it fail fast).
_SSH_BATCH_COMMAND = "ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new -o ConnectTimeout=10"

_NO_VERSION_REASON = "remote did not report a version (network, auth, or timeout)"

# ``check_status`` values recorded on every package record.  The UI keys off
# these to tell "up to date" apart from "we never found out".
CHECK_STATUS_OK = "ok"
CHECK_STATUS_FAILED = "failed"
CHECK_STATUS_NEVER_CHECKED = "never_checked"


@dataclass(frozen=True)
class VersionProbe:
    """Outcome of a single remote version probe.

    ``ok`` separates "the remote answered" from "the remote could not be
    reached".  ``get_git_tag`` collapses both into ``""``, which is why a
    failed probe used to look exactly like "no newer version" and packages
    silently stopped offering updates.
    """

    version: str = ""
    ok: bool = False
    reason: str = ""

    def __bool__(self) -> bool:
        return bool(self.version)


def _looks_like_commit_hash(value: str) -> bool:
    """True when value is a bare hex commit id rather than a release version."""
    return bool(_COMMIT_HASH_RE.fullmatch(str(value or "").strip().lower()))


def _utc_now_iso() -> str:
    """Timestamp recorded on every version check (UTC, second precision)."""
    return datetime.now(UTC).isoformat(timespec="seconds")


def _git_probe_env() -> dict[str, str]:
    """Environment that makes git fail instead of waiting for credentials.

    These probes run on the scan worker thread.  A remote that wants
    credentials (private repo, renamed owner, auth-gated host) otherwise
    blocks on stdin with no timeout, and the calling thread never returns.
    """
    env = dict(os.environ)
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GCM_INTERACTIVE"] = "never"
    if os.name != "nt":
        # ``echo`` exits immediately without printing, so git aborts instead
        # of prompting.  Skipped on Windows, where it is not a real binary.
        env["GIT_ASKPASS"] = "echo"
    env.setdefault("GIT_SSH_COMMAND", _SSH_BATCH_COMMAND)
    return env


def _decode_git_output(output: Any) -> str:
    """Normalise a GitPython ``execute`` result to text."""
    return output.decode() if isinstance(output, bytes) else str(output or "")


def _probe_reason(error: BaseException, timeout: float) -> str:
    """Human-readable reason for a failed probe (shown in the Updates view)."""
    text = str(error).lower()
    if "timed out" in text or "timeout" in text or "killed" in text:
        return f"timed out after {timeout:.0f}s"
    return "remote unreachable (network, auth, or timeout)"


def _normalize_remote_url(path_or_url: str) -> str:
    """Expand ``owner/repo`` shorthand to a clone URL; pass anything else through."""
    if path_or_url and "://" not in path_or_url and not path_or_url.startswith("git@"):
        parts = path_or_url.strip().split("/")
        if len(parts) == 2 and not parts[0].startswith("@"):
            url = f"https://github.com/{parts[0]}/{parts[1]}"
            if not url.endswith(".git"):
                url += ".git"
            return url
    return path_or_url


def looks_like_git_remote(value: str) -> bool:
    """True when ``value`` can plausibly be probed with ``git ls-remote``.

    Deliberately host-agnostic: the old rule only probed github.com and
    gitlab.com, so packages hosted anywhere else could never be detected as
    outdated.
    """
    text = str(value or "").strip()
    if not text:
        return False
    if "://" in text or text.startswith("git@"):
        return True
    parts = text.split("/")
    return len(parts) == 2 and bool(parts[0]) and bool(parts[1])


def probe_git_remote_version(
    url: str, token: str | None = None, timeout: float = DEFAULT_GIT_TIMEOUT
) -> VersionProbe:
    """Newest tag (falling back to the short HEAD hash) for a git remote.

    Always bounded: interactive prompting is disabled and the child process
    is killed after ``timeout`` seconds, so an unreachable or
    credential-gated remote can never wedge the calling thread.
    """
    if not url:
        return VersionProbe(reason="no repository url")

    url = _normalize_remote_url(url)
    config_args = ["-c", "protocol.ext.allow=never"]
    if token:
        config_args += [
            "-c",
            f"credential.helper=!f() {{ echo username=token; echo password={shlex.quote(token)}; }}; f",
        ]

    env = _git_probe_env()
    reason = ""

    try:
        git_cmd = cmd.Git()
    except Exception as e:  # pragma: no cover - git binary missing / not runnable
        logger.warning("Git unavailable for %s: %s", url, e)
        return VersionProbe(reason=_probe_reason(e, timeout))

    # 1. Tags, newest semantic version first.
    try:
        output = git_cmd.execute(  # type: ignore[reportCallIssue]
            ["git"] + config_args + ["ls-remote", "--tags", "--sort=-v:refname", "--", url],
            env=env,
            kill_after_timeout=timeout,
        )
        for line in _decode_git_output(output).strip().split("\n"):
            if "^{}" in line:
                continue
            tag = line.split("\t")[-1].replace("refs/tags/", "")
            if tag:
                return VersionProbe(version=tag, ok=True)
    except Exception as e:
        # GitCommandError from kill_after_timeout lands here; so does a
        # non-zero exit for an unknown host.
        reason = _probe_reason(e, timeout)
        logger.debug("Remote tag fetch failed, trying HEAD: %s", e)

    # 2. HEAD hash fallback for untagged repositories.
    try:
        output = git_cmd.execute(  # type: ignore[reportCallIssue]
            ["git"] + config_args + ["ls-remote", "--", url, "HEAD"],
            env=env,
            kill_after_timeout=timeout,
        )
        text = _decode_git_output(output)
        if text.strip():
            return VersionProbe(version=text.split("\t")[0][:7], ok=True)
    except Exception as e:
        reason = _probe_reason(e, timeout)
        logger.warning("Remote HEAD fetch failed: %s", e)

    return VersionProbe(reason=reason or _NO_VERSION_REASON)


class RemoteProbeCache:
    """Memoises remote probes for the lifetime of one scan.

    A single version check used to probe the same remote twice — once in the
    generic reconciliation and again in the git/npx branch — so an N package
    library cost ~2N network round-trips per scan.  One entry per
    ``(url, token)`` halves that, and guarantees both call sites reach the
    same "could not check" verdict for a given package.
    """

    def __init__(self, timeout: float = DEFAULT_GIT_TIMEOUT) -> None:
        self.timeout = timeout
        self._probes: dict[tuple[str, str], VersionProbe] = {}

    @property
    def attempted(self) -> bool:
        """True when at least one remote probe has been performed."""
        return bool(self._probes)

    def probe(self, url: str, token: str | None = None) -> VersionProbe:
        """Probe ``url`` once, reusing the result for later identical calls."""
        key = (str(url or ""), str(token or ""))
        cached = self._probes.get(key)
        if cached is None:
            value = get_git_tag(url, is_remote=True, token=token)
            cached = VersionProbe(
                version=value,
                ok=bool(value),
                reason="" if value else _NO_VERSION_REASON,
            )
            self._probes[key] = cached
        return cached

    def git_tag(self, url: str, token: str | None = None) -> str:
        """Convenience accessor for callers that only need the tag string."""
        return self.probe(url, token).version

    def failure_reason(self) -> str:
        """First recorded probe failure, or ``""`` when everything answered."""
        for probe in self._probes.values():
            if not probe.ok and probe.reason:
                return probe.reason
        return ""


def detect_git_remote(package_path: str | None) -> str:
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


def fetch_npm_registry_version(package_name: str, timeout: float = 3.0) -> str:
    """Fetches the latest version directly from registry.npmjs.org with a fast HTTP request."""
    package_name = str(package_name or "").strip()
    if not package_name or ("/" in package_name and not package_name.startswith("@")):
        return ""

    encoded_name = urllib.parse.quote(package_name, safe="@")
    url = f"https://registry.npmjs.org/{encoded_name}/latest"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "SkillManager/1.0", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            if response.status == 200:
                data = json.loads(response.read().decode("utf-8"))
                return str(data.get("version") or "").strip()
    except Exception as e:
        logger.debug("NPM registry lookup failed for %s: %s", package_name, e)
    return ""


def run_version_command(command: str, timeout: float = 5.0) -> str:
    """Executes a version detection command with a short timeout to prevent UI blocking."""
    command = str(command or "").strip()
    if not command:
        return ""

    try:
        command_list = shlex.split(command)
        import shutil

        executable = shutil.which(command_list[0])
        if executable:
            command_list[0] = executable

        kwargs = {"shell": False, "capture_output": True, "text": True, "timeout": timeout}
        if hasattr(subprocess, "CREATE_NO_WINDOW"):
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

        result = subprocess.run(command_list, **kwargs)
    except (OSError, subprocess.SubprocessError, ValueError) as e:
        logger.warning("Version command failed: %s - %s", command, e)
        return ""

    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def get_git_tag(
    path_or_url: str,
    is_remote: bool = False,
    token: str | None = None,
    timeout: float = DEFAULT_GIT_TIMEOUT,
) -> str:
    """Latest tag (or short HEAD hash) for a git remote or a local clone.

    Returns ``""`` when the repository has no tags and no readable HEAD *or*
    when the remote could not be reached.  Callers that must tell those apart
    use :func:`probe_git_remote_version`, which returns a :class:`VersionProbe`
    carrying the outcome and a failure reason.
    """
    if is_remote:
        return probe_git_remote_version(path_or_url, token=token, timeout=timeout).version

    try:
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
    source: dict[str, Any], force_refresh: bool = False, sync_current_to_latest: bool = False
) -> dict[str, Any]:
    """Async version of check_skill_package_versions for non-blocking UI."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None,
        lambda: check_skill_package_versions(source, force_refresh, sync_current_to_latest),
    )


def _sync_current_to_latest_if_applicable(
    current_version: str,
    latest_version: str,
    source: dict[str, Any],
) -> str:
    """Snap current_version to latest_version when detection is unreliable.

    When ``current_version`` is empty and ``latest_version`` is available,
    snap to latest.  This covers git sources whose local clone path was
    not detected (e.g. user entered the install path instead of the
    clone path) and non-git sources without a reliable local version
    detection mechanism.  The snap is skipped when a
    ``current_version_command`` is set, giving the user explicit control.
    """
    if latest_version and not current_version and not source.get("current_version_command"):
        return latest_version
    return current_version


def normalize_version(value: Any) -> str:
    """Normalize a version string for comparison.

    Strips whitespace and a single leading ``v``/``V`` (``v1.2.3`` == ``1.2.3``).
    Returns ``""`` for empty/None input.  Matches the QML ``isLatest``
    logic (strict equality after normalization) so Python auto-update
    decisions stay consistent with the UpdatesView Update buttons.
    """
    if value is None:
        return ""
    text = str(value).strip()
    if len(text) > 1 and text[0] in ("v", "V"):
        text = text[1:].strip()
    return text


def is_package_outdated(package: dict[str, Any] | Any) -> bool:
    """True when a package record has a known newer version available.

    Conservative by design (no false auto-update loops):
    - both ``current_version`` and ``latest_version`` must be non-empty
    - the ``"latest"`` sentinel (detection fallback) never counts as outdated
    - comparison is normalized string inequality (matches QML ``isLatest``)

    Accepts dicts or objects with ``current_version``/``latest_version`` attrs.
    """
    if isinstance(package, dict):
        current = package.get("current_version", "")
        latest = package.get("latest_version", "")
    else:
        current = getattr(package, "current_version", "")
        latest = getattr(package, "latest_version", "")
    current_n = normalize_version(current)
    latest_n = normalize_version(latest)
    if not current_n or not latest_n:
        return False
    if current_n.casefold() == "latest" or latest_n.casefold() == "latest":
        return False
    return current_n != latest_n


def get_outdated_packages(packages: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """Return the subset of package records with a newer version available."""
    if not packages:
        return []
    return [p for p in packages if is_package_outdated(p)]


def count_outdated_packages(packages: list[dict[str, Any]] | None) -> int:
    """Count packages with a newer version available (0 for None/empty)."""
    return len(get_outdated_packages(packages))


def get_unchecked_packages(packages: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """Return package records whose last version check failed.

    These are the packages the UI must *not* present as "up to date": we did
    not learn their latest version, so "0 updates" is unproven for them.
    """
    if not packages:
        return []
    return [
        p for p in packages if isinstance(p, dict) and p.get("check_status") == CHECK_STATUS_FAILED
    ]


def count_unchecked_packages(packages: list[dict[str, Any]] | None) -> int:
    """Count packages whose version could not be checked."""
    return len(get_unchecked_packages(packages))


def check_skill_package_versions(
    source: dict[str, Any],
    force_refresh: bool = False,
    sync_current_to_latest: bool = False,
    promote_current_to_latest: bool = False,
    remote_cache: RemoteProbeCache | None = None,
) -> dict[str, Any]:
    """Reconcile current_version/latest_version for a skill package record.

    Scan (default) only refreshes an empty latest_version. ``force_refresh``
    re-probes latest. ``sync_current_to_latest`` snaps current to latest on
    add/edit when no local detection exists. ``promote_current_to_latest``
    is the post-update transition: after a *successful* update of an
    npx/custom package (which has no local current detection), the stored
    current is stale by construction, so it is promoted to latest.

    The outcome of the check is recorded on the record so the UI can tell
    "up to date" apart from "we could not reach the remote":

    ``check_status``      ``ok`` | ``failed`` | ``never_checked``
    ``check_error``       human-readable reason when the status is ``failed``
    ``last_checked_at``   UTC ISO timestamp of this check

    ``remote_cache`` is shared across one scan so a remote is probed once
    per ``(url, token)`` instead of once per call site.
    """
    source = normalize_skill_package_config(source)

    cache = remote_cache if remote_cache is not None else RemoteProbeCache()

    current_version = source.get("current_version", "")
    latest_version = source.get("latest_version", "")

    def clean_v(v):
        if v and v.startswith("v"):
            return v[1:]
        return v

    if source.get("current_version_command"):
        detected_current = run_version_command(
            source.get("current_version_command")  # type: ignore[arg-type]
        )
        if detected_current:
            current_version = clean_v(detected_current)

    if source.get("latest_version_command"):
        detected_latest = run_version_command(
            source.get("latest_version_command")  # type: ignore[arg-type]
        )
        if detected_latest:
            latest_version = clean_v(detected_latest)

    repo_url = str(source.get("repository_url") or "").strip()
    token = source.get("github_token")
    if repo_url and looks_like_git_remote(repo_url):
        # Host-agnostic on purpose: the previous github.com/gitlab.com check
        # skipped every other host, so packages hosted anywhere else could
        # never be detected as outdated.
        git_latest = cache.git_tag(repo_url, token)
        hash_would_clobber = (
            source.get("source_type") in ("npx", "custom")
            and _looks_like_commit_hash(git_latest)
            and bool(latest_version)
        )
        if git_latest and not hash_would_clobber:
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
            # Deduped by the cache: the generic probe above already asked the
            # same remote, so this is a dictionary hit rather than a second
            # network round-trip (previously ~2N probes per scan).
            git_latest = cache.git_tag(repo_url, token)
            if git_latest:
                latest_version = clean_v(git_latest)

    if source.get("source_type") == "npx" and (not latest_version or force_refresh):
        package_name = str(source.get("package_name") or "").strip()
        repo_url = str(source.get("repository_url") or "").strip()

        probed_git = ""
        if repo_url and "github.com" in repo_url:
            git_url = repo_url if repo_url.endswith(".git") else f"{repo_url}.git"
            probed_git = cache.git_tag(git_url, token)
        elif package_name and "/" in package_name and not package_name.startswith("@"):
            git_url = f"https://github.com/{package_name}.git"
            probed_git = cache.git_tag(git_url, token)

        if not latest_version:
            registry_version = fetch_npm_registry_version(package_name, timeout=3.0)
            if registry_version:
                latest_version = clean_v(registry_version)

        if not latest_version:
            import shutil

            if package_name and shutil.which("npm"):
                detected_latest = run_version_command(
                    f"npm view -- {package_name} version", timeout=3.0
                )
                if detected_latest:
                    latest_version = clean_v(detected_latest)

        if not latest_version and probed_git:
            if _looks_like_commit_hash(probed_git):
                latest_version = probed_git.strip()
            else:
                latest_version = clean_v(probed_git)

    # After a successful update (force_refresh) or on initial add
    # (sync_current_to_latest), snap current_version to latest_version
    # for packages without a reliable local version detection mechanism.
    if force_refresh or sync_current_to_latest:
        current_version = _sync_current_to_latest_if_applicable(
            current_version, latest_version, source
        )

    # Post-update reconciliation for sources with no local current detection.
    # npx/custom packages never observe their installed version, so without
    # this the stored current stays stale forever and the UI keeps offering
    # the same update after every successful run.
    if (
        promote_current_to_latest
        and latest_version
        and not source.get("current_version_command")
        and source.get("source_type") in ("npx", "custom")
    ):
        current_version = latest_version

    failure = cache.failure_reason()
    if failure:
        source["check_status"] = CHECK_STATUS_FAILED
        source["check_error"] = failure
    elif latest_version or current_version:
        source["check_status"] = CHECK_STATUS_OK
        source["check_error"] = ""
    else:
        source["check_status"] = CHECK_STATUS_NEVER_CHECKED
        source["check_error"] = ""
    source["last_checked_at"] = _utc_now_iso()

    if current_version:
        source["current_version"] = clean_v(current_version)
    if latest_version:
        source["latest_version"] = clean_v(latest_version)

    return source

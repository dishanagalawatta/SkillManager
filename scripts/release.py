#!/usr/bin/env bash
# ==============================================================================
# Release & Version Synchronization Pipeline for SkillManager
# Usage:
#   uv run python scripts/release.py patch
#   uv run python scripts/release.py minor
#   uv run python scripts/release.py major
#   uv run python scripts/release.py dev
#   uv run python scripts/release.py 1.9.1
#   uv run python scripts/release.py 2.2.4-dev.1
#   uv run python scripts/release.py patch --dry-run
#   uv run python scripts/release.py tag          (after the release PR merges)
# ==============================================================================
"""Release and version synchronization tool for SkillManager."""

import argparse
import datetime
import os
import re
import subprocess
import sys
import tomllib

from packaging.version import InvalidVersion, Version


def get_project_root() -> str:
    """Return the absolute path to the repository root."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_current_version(project_root: str) -> str:
    """Read the current project.version from pyproject.toml."""
    pyproject_path = os.path.join(project_root, "pyproject.toml")
    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)
    return data["project"]["version"]


def parse_version(version_str: str) -> tuple[int, int, int, int | None]:
    """Parse 'X.Y.Z' or 'X.Y.Z-dev.N' into (major, minor, patch, dev).

    dev is None for stable versions, else the pre-release counter.
    """
    clean_ver = version_str.lstrip("v").strip()
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)(?:-dev\.(\d+))?$", clean_ver)
    if not match:
        raise ValueError(
            f"Invalid version format: '{version_str}'. "
            "Expected 'MAJOR.MINOR.PATCH' or 'MAJOR.MINOR.PATCH-dev.N'."
        )
    dev = int(match.group(4)) if match.group(4) is not None else None
    return int(match.group(1)), int(match.group(2)), int(match.group(3)), dev


def calculate_next_version(current_ver: str, bump_type_or_ver: str) -> str:
    """Calculate the next version given a bump type or explicit version.

    'dev' sequencing:
      - stable X.Y.Z      -> X.Y.(Z+1)-dev.1  (first pre-release of next patch)
      - dev X.Y.Z-dev.N   -> X.Y.Z-dev.(N+1)  (increment pre-release counter)
      - 'patch' on a dev  -> X.Y.Z            (promote pre-release to stable)
      - 'minor'/'major' on a dev -> drop the pre-release suffix
    """
    bump_lower = bump_type_or_ver.lower().strip()
    if bump_lower in ("patch", "minor", "major", "dev"):
        major, minor, patch, dev = parse_version(current_ver)
        if bump_lower == "dev":
            if dev is None:
                return f"{major}.{minor}.{patch + 1}-dev.1"
            return f"{major}.{minor}.{patch}-dev.{dev + 1}"
        if bump_lower == "patch":
            if dev is not None:
                return f"{major}.{minor}.{patch}"
            return f"{major}.{minor}.{patch + 1}"
        if bump_lower == "minor":
            return f"{major}.{minor + 1}.0"
        return f"{major + 1}.0.0"

    parse_version(bump_type_or_ver)
    return bump_type_or_ver.lstrip("v").strip()


def sync_pyproject(project_root: str, new_ver: str, dry_run: bool = False) -> None:
    """Update version in pyproject.toml."""
    path = os.path.join(project_root, "pyproject.toml")
    with open(path, encoding="utf-8") as f:
        content = f.read()

    new_content = re.sub(
        r'(version\s*=\s*")[^"]+(")',
        rf"\g<1>{new_ver}\g<2>",
        content,
        count=1,
    )
    if not dry_run:
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_content)
    print(f'  [OK] pyproject.toml -> version = "{new_ver}"')


def sync_init_py(project_root: str, new_ver: str, dry_run: bool = False) -> None:
    """Update __version__ in src/skill_manager/__init__.py."""
    path = os.path.join(project_root, "src", "skill_manager", "__init__.py")
    with open(path, encoding="utf-8") as f:
        content = f.read()

    new_content = re.sub(
        r'(__version__\s*=\s*")[^"]+(")',
        rf"\g<1>{new_ver}\g<2>",
        content,
        count=1,
    )
    if not dry_run:
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_content)
    print(f'  [OK] src/skill_manager/__init__.py -> __version__ = "{new_ver}"')


def sync_installer_iss(project_root: str, new_ver: str, dry_run: bool = False) -> None:
    """Update MyAppVersion in packaging/windows/installer.iss."""
    path = os.path.join(project_root, "packaging", "windows", "installer.iss")
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        content = f.read()

    new_content = re.sub(
        r'(#define\s+MyAppVersion\s+")[^"]+(")',
        rf"\g<1>{new_ver}\g<2>",
        content,
        count=1,
    )
    if not dry_run:
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_content)
    print(f'  [OK] packaging/windows/installer.iss -> MyAppVersion = "{new_ver}"')


def sync_metainfo_xml(project_root: str, new_ver: str, dry_run: bool = False) -> None:
    """Add new release node in packaging/linux/org.dishanagalawatta.SkillManager.metainfo.xml."""
    path = os.path.join(
        project_root,
        "packaging",
        "linux",
        "org.dishanagalawatta.SkillManager.metainfo.xml",
    )
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        content = f.read()

    today = datetime.date.today().isoformat()
    if f'<release version="{new_ver}"' not in content:
        release_block = f"""  <releases>
    <release version="{new_ver}" date="{today}">
      <url type="details">https://github.com/dishanagalawatta/SkillManager/releases</url>
    </release>"""
        new_content = re.sub(r"  <releases>", release_block, content, count=1)
        if not dry_run:
            with open(path, "w", encoding="utf-8") as f:
                f.write(new_content)
    print(
        f"  [OK] packaging/linux/org.dishanagalawatta.SkillManager.metainfo.xml -> added v{new_ver}"
    )


def sync_readme(project_root: str, new_ver: str, dry_run: bool = False) -> None:
    """Update version badge in README.md."""
    path = os.path.join(project_root, "README.md")
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        content = f.read()

    new_content = re.sub(
        r"(badge/version-)[^-\s]+(-orange\.svg)",
        rf"\g<1>{new_ver}\g<2>",
        content,
        count=1,
    )
    if not dry_run:
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_content)
    print(f"  [OK] README.md -> badge version-{new_ver}")


def sync_uvlock(project_root: str, new_ver: str, dry_run: bool = False) -> None:
    """Regenerate uv.lock so its skill-manager entry matches pyproject.toml.

    uv.lock is not part of the release metadata sync list and drifts whenever
    pyproject.toml is bumped (the release commit changes the version in
    pyproject.toml but not in the lockfile). CI's `uv sync` then rewrites
    uv.lock, which trips check_git_status on the next release run. Running
    `uv lock` after the pyproject bump keeps the lockfile in sync so release
    commits stay clean and self-contained.
    """
    uv_lock_path = os.path.join(project_root, "uv.lock")
    if not os.path.exists(uv_lock_path):
        print("  [SKIP] uv.lock not found; skipping lockfile sync.")
        return
    if dry_run:
        print(f"  [OK] uv.lock -> would regenerate lockfile for version {new_ver}")
        return

    res = subprocess.run(["uv", "lock"], cwd=project_root, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"  [ERROR] uv lock failed: {res.stderr.strip()}")
        sys.exit(1)

    with open(uv_lock_path, encoding="utf-8") as f:
        content = f.read()
    match = re.search(r'name = "skill-manager"\nversion = "([^"]+)"', content)
    actual_ver = match.group(1) if match else None
    try:
        converged = bool(actual_ver) and Version(actual_ver) == Version(new_ver)
    except InvalidVersion:
        converged = False
    if not converged:
        print(
            f"  [ERROR] uv.lock skill-manager version is {actual_ver or 'unknown'}, "
            f"expected {new_ver}. Lockfile sync did not converge."
        )
        sys.exit(1)
    print(f"  [OK] uv.lock -> skill-manager version {new_ver}")


def update_changelog(
    project_root: str, new_ver: str, release_notes: str | None = None, dry_run: bool = False
) -> None:
    """Prepend release section to CHANGELOG.md if not present."""
    path = os.path.join(project_root, "CHANGELOG.md")
    if not os.path.exists(path):
        return

    with open(path, encoding="utf-8") as f:
        content = f.read()

    header_pattern = f"## [{new_ver}]"
    if header_pattern in content:
        print(f"  [OK] CHANGELOG.md already has section for v{new_ver}")
        return

    today = datetime.date.today().isoformat()
    notes = release_notes or "### Changes\n- Release version bump."
    new_entry = f"## [{new_ver}] - {today}\n\n{notes}\n\n"

    # Insert below '# Changelog' header
    if "# Changelog" in content:
        new_content = content.replace("# Changelog\n\n", f"# Changelog\n\n{new_entry}", 1)
    else:
        new_content = f"# Changelog\n\n{new_entry}{content}"

    if not dry_run:
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_content)
    print(f"  [OK] CHANGELOG.md -> added release section for [{new_ver}] - {today}")


def check_git_status(project_root: str) -> None:
    """Ensure working tree is clean before releasing."""
    res = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=True,
    )
    if res.stdout.strip():
        print(
            "ERROR: Git working directory is not clean. Please commit or stash changes before releasing."
        )
        print("Untracked/modified files:")
        print(res.stdout)
        sys.exit(1)


def run_preflight_checks(project_root: str, skip_tests: bool, skip_lint: bool) -> None:
    """Run linter and tests before bumping version."""
    if not skip_lint:
        print("Running pre-flight lint check (ruff)...")
        subprocess.run(
            ["uv", "run", "ruff", "check", "src", "tests"],
            cwd=project_root,
            check=True,
        )
        print("  [OK] Linting passed.")

    if not skip_tests:
        print("Running pre-flight test suite (pytest)...")
        subprocess.run(
            ["uv", "run", "pytest", "-n", "auto"],
            cwd=project_root,
            check=True,
        )
        print("  [OK] All tests passed.")


def _current_branch(project_root: str) -> str:
    """Return the name of the checked-out branch."""
    res = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=True,
    )
    return res.stdout.strip()


def prepare_release_pr(
    project_root: str,
    next_version: str,
    custom_msg: str | None = None,
    push: bool = True,
    dry_run: bool = False,
) -> None:
    """Commit the version sync on a release branch and open a pull request.

    ``main`` is protected, so the bump cannot be pushed directly: it lands
    through a pull request. The tag is created afterwards, once merged, by
    :func:`tag_current_version`.
    """
    branch = f"release/v{next_version}"
    tag_name = f"v{next_version}"
    # No [skip ci]: the release PR must run CI, otherwise the required "CI Gate"
    # status check never reports and the pull request can never merge.
    commit_msg = custom_msg or f"chore(release): bump version to {tag_name}"

    if dry_run:
        print(f"\n[DRY RUN] Would create branch: '{branch}'")
        print(f"[DRY RUN] Would commit synchronized files with message: '{commit_msg}'")
        if push:
            print(f"[DRY RUN] Would push '{branch}' and open a pull request into main")
            print("[DRY RUN] After the merge: uv run python scripts/release.py tag")
        return

    if _current_branch(project_root) != "main":
        print("ERROR: Release branches are cut from 'main'. Switch to main first.")
        sys.exit(1)

    print(f"\nCreating release branch: {branch}...")
    subprocess.run(["git", "checkout", "-b", branch], cwd=project_root, check=True)

    print("Staging synchronized files in git...")
    subprocess.run(
        [
            "git",
            "add",
            "pyproject.toml",
            "uv.lock",
            "src/skill_manager/__init__.py",
            "packaging/",
            "README.md",
            "CHANGELOG.md",
        ],
        cwd=project_root,
        check=True,
    )

    subprocess.run(["git", "commit", "-m", commit_msg], cwd=project_root, check=True)
    print(f"  [OK] Created commit: {commit_msg}")

    if not push:
        print("\nSkipped git push (--no-push). To open the release PR manually:")
        print(f"  git push -u origin {branch}")
        print(f"  gh pr create --base main --head {branch} --title '{commit_msg}'")
        return

    print(f"\nPushing {branch} to origin...")
    subprocess.run(["git", "push", "-u", "origin", branch], cwd=project_root, check=True)
    print("  [OK] Branch pushed.")
    subprocess.run(["git", "checkout", "main"], cwd=project_root, check=True)

    print("\nOpening release pull request...")
    pr = subprocess.run(
        [
            "gh",
            "pr",
            "create",
            "--base",
            "main",
            "--head",
            branch,
            "--title",
            commit_msg,
            "--body",
            (
                "Version bump prepared by `scripts/release.py`.\n\n"
                "Merge once `CI Gate` is green, then tag the merge commit:\n\n"
                "```\nuv run python scripts/release.py tag\n```"
            ),
        ],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if pr.returncode == 0:
        print(f"  [OK] Pull request opened: {pr.stdout.strip()}")
    else:
        print("  [WARN] Could not open the pull request (gh missing or unauthenticated).")
        print(f"  Open it manually: compare/main...{branch}?expand=1")
    print("\nNext: merge the PR, then run:\n  uv run python scripts/release.py tag")


def tag_current_version(
    project_root: str,
    custom_msg: str | None = None,
    push: bool = True,
    dry_run: bool = False,
) -> None:
    """Tag the already-merged release version and push the tag.

    Push the tag *after* the release PR merges: the tag is what triggers
    ``release-build.yml``.
    """
    version = get_current_version(project_root)
    tag_name = f"v{version}"
    message = custom_msg or f"Release {tag_name}"

    existing = subprocess.run(
        ["git", "tag", "--list", tag_name],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=True,
    )
    if existing.stdout.strip():
        print(f"ERROR: Tag {tag_name} already exists.")
        sys.exit(1)

    if dry_run:
        print(f"[DRY RUN] Would create annotated tag: '{tag_name}'")
        if push:
            print(f"[DRY RUN] Would push tag {tag_name} (triggers release-build.yml)")
        return

    branch = _current_branch(project_root)
    if branch != "main":
        print(f"ERROR: Tag on 'main', not '{branch}' — the release PR must merge first.")
        sys.exit(1)
    check_git_status(project_root)

    print(f"Creating annotated tag: {tag_name}...")
    subprocess.run(["git", "tag", "-a", tag_name, "-m", message], cwd=project_root, check=True)
    print(f"  [OK] Created tag: {tag_name}")

    if push:
        print(f"\nPushing tag {tag_name} to origin...")
        subprocess.run(["git", "push", "origin", tag_name], cwd=project_root, check=True)
        print(f"\nGitHub Actions release workflow will now build and publish release {tag_name}!")
    else:
        print("\nSkipped git push (--no-push). To push manually:")
        print(f"  git push origin {tag_name}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Release & Version Synchronization Tool for SkillManager."
    )
    parser.add_argument(
        "target",
        help="Bump type ('patch', 'minor', 'major', 'dev'), explicit version (e.g. '1.9.1' or '2.2.4-dev.1'), or 'tag' to tag the merged version. Required: releases are bumped deliberately, never inferred.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate the release process without modifying files or git",
    )
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Skip running pytest suite",
    )
    parser.add_argument(
        "--skip-lint",
        action="store_true",
        help="Skip running ruff linter",
    )
    parser.add_argument(
        "--no-push",
        action="store_true",
        help="Do not push git commit and tags to remote",
    )
    parser.add_argument(
        "-m",
        "--message",
        help="Custom commit and release message",
    )

    args = parser.parse_args()
    project_root = get_project_root()

    if args.target.lower() == "tag":
        tag_current_version(
            project_root,
            args.message,
            push=not args.no_push,
            dry_run=args.dry_run,
        )
        return

    current_ver = get_current_version(project_root)

    next_ver = calculate_next_version(current_ver, args.target)

    print("==================================================")
    print("  SkillManager Release & Version Synchronization  ")
    print("==================================================")
    print(f"Current version: v{current_ver}")
    print(f"Target version:  v{next_ver}")
    print(f"Dry run:         {args.dry_run}")
    print("--------------------------------------------------")

    if not args.dry_run:
        check_git_status(project_root)
        run_preflight_checks(project_root, args.skip_tests, args.skip_lint)

    print("\nSynchronizing version across files...")
    sync_pyproject(project_root, next_ver, args.dry_run)
    sync_uvlock(project_root, next_ver, args.dry_run)
    sync_init_py(project_root, next_ver, args.dry_run)
    sync_installer_iss(project_root, next_ver, args.dry_run)
    sync_metainfo_xml(project_root, next_ver, args.dry_run)
    sync_readme(project_root, next_ver, args.dry_run)
    update_changelog(project_root, next_ver, dry_run=args.dry_run)

    prepare_release_pr(
        project_root,
        next_ver,
        args.message,
        push=not args.no_push,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()

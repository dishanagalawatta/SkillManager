"""
Purpose: Calculates the correct arguments for python-semantic-release to achieve the
desired version bump according to SemVer pre-release rules.
Usage: python scripts/version_bump_calculator.py <current_version> <commit_message>
"""

import re
import sys


def main():
    if len(sys.argv) < 3:
        print("Usage: python version_bump_calculator.py <version> <commit_message>")
        sys.exit(1)

    version = sys.argv[1]
    commit_msg = sys.argv[2]

    # Find explicit command in commit message
    match = re.search(r"\[(dev|patch|minor|major|preminor|premajor)\]", commit_msg)
    if not match:
        print("")
        sys.exit(0)
    else:
        cmd = match.group(1)

    # Parse current version using regex
    # e.g. 1.2.3 or 1.2.4-dev.2 or v1.2.3
    v_match = re.match(r"^v?(\d+)\.(\d+)\.(\d+)(?:-dev\.(\d+))?$", version)
    if not v_match:
        sys.stderr.write(f"ERROR: Invalid version format {version}\n")
        sys.exit(1)

    major, minor, patch, dev = v_match.groups()
    is_dev = dev is not None

    # Handle Edge Case B: Cross-grade logic
    # If we are working towards a minor/major release (patch == "0") and command is patch, fail.
    if is_dev and patch == "0" and cmd == "patch":
        sys.stderr.write(
            f"ERROR: Cross-grade detected. Cannot graduate minor/major prerelease {version} via 'bump patch'.\n"
        )
        sys.exit(1)

    # Map commands to python-semantic-release flags
    if cmd == "dev":
        if is_dev:
            # Continuing dev cycle
            args = "--prerelease --prerelease-token dev"
        else:
            # Starting new dev cycle targeting patch
            args = "--patch --as-prerelease --prerelease-token dev"
    elif cmd == "patch":
        args = "--patch"
    elif cmd == "minor":
        args = "--minor"
    elif cmd == "major":
        args = "--major"
    elif cmd == "preminor":
        args = "--minor --as-prerelease --prerelease-token dev"
    elif cmd == "premajor":
        args = "--major --as-prerelease --prerelease-token dev"
    else:
        args = ""

    print(args)


if __name__ == "__main__":
    main()

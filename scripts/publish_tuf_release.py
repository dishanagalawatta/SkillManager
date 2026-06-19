"""
Script to automate tufup repository creation and release publishing.
This script handles:
1. Initializing TUF repository if not exists.
2. Adding a new release bundle (e.g. from PyInstaller).
3. Generating patches.
4. Signing and updating metadata.

Usage:
    python scripts/publish_tuf_release.py --version 1.0.1 --bundle dist/SkillManager

    # CI mode: reads keys from environment variables (TUF_KEY_ROOT, TUF_KEY_SNAPSHOT, etc.)
    python scripts/publish_tuf_release.py --version 1.0.1 --bundle dist/SkillManager --ci
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path

from tufup.repo import Repository

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

REPO_DIR = Path("tuf_repo")
KEYS_DIR = Path("tuf_keys")

KEY_NAMES = ["root", "snapshot", "targets", "timestamp"]


def write_keys_from_env(target_dir: Path) -> None:
    """Write TUF signing keys from environment variables to files."""
    target_dir.mkdir(parents=True, exist_ok=True)

    for key_name in KEY_NAMES:
        env_var = f"TUF_KEY_{key_name.upper()}"
        key_content = os.environ.get(env_var)

        if not key_content:
            logger.error(f"Environment variable {env_var} is not set")
            sys.exit(1)

        key_path = target_dir / key_name
        try:
            parsed = json.loads(key_content)
            key_path.write_text(json.dumps(parsed, indent=2), encoding="utf-8")
        except json.JSONDecodeError:
            key_path.write_text(key_content, encoding="utf-8")

        logger.info(f"Wrote {key_name} key from {env_var}")


def main():
    parser = argparse.ArgumentParser(description="Publish a SkillManager update via tufup.")
    parser.add_argument("--version", required=True, help="New version string (e.g. 1.0.1)")
    parser.add_argument(
        "--bundle", required=True, help="Path to the app bundle directory (e.g. dist/SkillManager)"
    )
    parser.add_argument(
        "--init",
        action="store_true",
        help="Initialize the repository and keys if they don't exist.",
    )
    parser.add_argument(
        "--ci",
        action="store_true",
        help="CI mode: read signing keys from environment variables.",
    )

    args = parser.parse_args()
    version = args.version
    bundle_path = Path(args.bundle)

    if not bundle_path.exists():
        logger.error(f"Bundle path does not exist: {bundle_path}")
        sys.exit(1)

    # Ensure repo directory exists
    REPO_DIR.mkdir(exist_ok=True)

    # Handle keys: CI reads from env vars, local reads from tuf_keys/
    if args.ci:
        logger.info("CI mode: reading TUF keys from environment variables")
        write_keys_from_env(KEYS_DIR)
    else:
        KEYS_DIR.mkdir(exist_ok=True)

    # Initialize Repository object
    repo = Repository(
        repo_dir=str(REPO_DIR),
        keys_dir=str(KEYS_DIR),
        app_name="SkillManager",
    )

    # Auto-initialize if repo has no metadata (first run in CI)
    metadata_dir = REPO_DIR / "metadata"
    needs_init = args.init or not metadata_dir.exists() or not any(metadata_dir.iterdir())
    if needs_init:
        logger.info("Initializing TUF repository and keys...")
        repo.initialize()
        logger.warning(f"KEYS GENERATED IN {KEYS_DIR}. KEEP THEM SECRET AND BACKED UP!")

    # Create the release
    logger.info(f"Adding release {version} from {bundle_path}...")

    try:
        repo.add_bundle(new_version=version, new_bundle_dir=str(bundle_path))
        logger.info("Release bundle added successfully.")
    except Exception as e:
        logger.error(f"Failed to add bundle: {e}")
        sys.exit(1)

    # Publish (Update metadata)
    logger.info("Updating TUF metadata and signing...")
    try:
        repo.publish_changes(private_key_dirs=[str(KEYS_DIR)])
        logger.info("Repository published successfully.")
    except Exception as e:
        logger.error(f"Failed to publish: {e}")
        sys.exit(1)

    logger.info("-" * 40)
    logger.info(f"Done! Release {version} is ready in {REPO_DIR}")
    logger.info("To deploy to GitHub Pages:")
    logger.info(
        f"1. Push the contents of {REPO_DIR}/metadata and {REPO_DIR}/targets to the 'gh-pages' branch."
    )
    logger.info("-" * 40)


if __name__ == "__main__":
    main()

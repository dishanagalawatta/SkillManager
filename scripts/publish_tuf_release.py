"""
Script to automate tufup repository creation and release publishing.
This script handles:
1. Initializing TUF repository if not exists.
2. Adding a new release bundle (e.g. from PyInstaller).
3. Generating patches.
4. Signing and updating metadata.

Usage:
    python scripts/publish_tuf_release.py --version 1.0.1 --bundle dist/SkillManager
"""

import argparse
import logging
import sys
from pathlib import Path

from tufup.repo import Repository

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

REPO_DIR = Path("tuf_repo")
KEYS_DIR = Path("tuf_keys")  # IMPORTANT: Keep these safe and DO NOT commit them!


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

    args = parser.parse_args()
    version = args.version
    bundle_path = Path(args.bundle)

    if not bundle_path.exists():
        logger.error(f"Bundle path does not exist: {bundle_path}")
        sys.exit(1)

    # Ensure repo and keys directories exist
    REPO_DIR.mkdir(exist_ok=True)
    KEYS_DIR.mkdir(exist_ok=True)

    # Initialize Repository object
    # In a real environment, you would load your private keys here securely
    repo = Repository(
        repo_dir=str(REPO_DIR),
        keys_dir=str(KEYS_DIR),
        app_name="SkillManager",
    )

    if args.init:
        logger.info("Initializing TUF repository and keys...")
        repo.initialize()
        logger.warning(f"KEYS GENERATED IN {KEYS_DIR}. KEEP THEM SECRET AND BACKED UP!")

    # Create the release
    # tufup expects a compressed archive of the app bundle
    logger.info(f"Adding release {version} from {bundle_path}...")

    # tufup handles archiving and patching automatically when we call add_bundle
    # It will create a .tar.gz in the targets directory
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

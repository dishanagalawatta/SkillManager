import argparse
import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)


def update_projects(project_paths, source_paths, progress_callback=None):
    """
    Iterates through subfolders in each project path.
    For each subfolder, it checks the source paths in the order they were provided.
    The first source path containing a matching subfolder is considered the highest priority.
    It copies the contents of that prioritized source subfolder to the project subfolder,
    overwriting existing files.
    """

    projects = []
    for tp in project_paths:
        p = Path(tp).resolve()
        if p.is_dir():
            projects.append(p)
        else:
            logger.warning(
                "Warning: Project path '%s' is not a directory or does not exist. Skipping.", tp
            )

    sources = []
    for sp in source_paths:
        p = Path(sp).resolve()
        if p.is_dir():
            sources.append(p)
        else:
            logger.warning(
                "Warning: Source path '%s' is not a directory or does not exist. Skipping.", sp
            )

    if not projects:
        logger.error("Error: No valid project directories provided.")
        return None

    if not sources:
        logger.error("Error: No valid source directories provided.")
        return None

    # Count total folders to process
    total_folders = 0
    project_items = []
    for project_dir in projects:
        items = [item for item in project_dir.iterdir() if item.is_dir()]
        project_items.append((project_dir, items))
        total_folders += len(items)

    logger.info("Starting update process...")
    logger.info("Projects:")
    for t in projects:
        logger.info("  - %s", t)
    logger.info("\nSources (in order of priority):")
    for s in sources:
        logger.info("  - %s", s)
    logger.info("-" * 40)

    updated_count = 0
    skipped_count = 0
    processed_count = 0

    # Iterate through each project directory
    for project_dir, items in project_items:
        logger.info("\nProcessing project directory: '%s'", project_dir.name)

        for item in items:
            folder_name = item.name

            # Find the highest priority source that contains this folder
            selected_source_subfolder = None
            selected_source_dir = None

            for source_dir in sources:
                potential_source = source_dir / folder_name
                if potential_source.is_dir():
                    selected_source_subfolder = potential_source
                    selected_source_dir = source_dir
                    break  # Stop at the first (highest priority) match

            if selected_source_subfolder:
                msg = f"Updating '{folder_name}'..."
                logger.info("[*] %s (using source: '%s')", msg, selected_source_dir.name)
                if progress_callback:
                    progress_callback(processed_count, total_folders, msg)
                try:
                    # dirs_exist_ok=True allows merging into existing directories (Python 3.8+)
                    shutil.copytree(selected_source_subfolder, item, dirs_exist_ok=True)
                    logger.info("    Successfully updated '%s'.", folder_name)
                    updated_count += 1
                except Exception as e:
                    logger.error("    [!] Error updating '%s': %s", folder_name, e)
            else:
                msg = f"Skipping '{folder_name}'"
                logger.info("[-] %s - no matching folder found in any source directory.", msg)
                if progress_callback:
                    progress_callback(processed_count, total_folders, msg)
                skipped_count += 1

            processed_count += 1

    if progress_callback:
        progress_callback(total_folders, total_folders, "Update process complete.")

    logger.info("\n" + "=" * 40)
    logger.info("Update process complete.")
    logger.info("Total projects updated: %d", updated_count)
    logger.info("Total projects skipped: %d", skipped_count)
    return updated_count, skipped_count


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Update subfolders in multiple project directories from multiple prioritized source directories."
    )
    parser.add_argument(
        "--projects",
        nargs="+",
        required=True,
        help="One or more project directories containing subfolders to be updated.",
    )
    parser.add_argument(
        "--sources",
        nargs="+",
        required=True,
        help="One or more source directories containing updates. The order specifies priority (first = highest).",
    )

    args = parser.parse_args()

    update_projects(args.projects, args.sources)

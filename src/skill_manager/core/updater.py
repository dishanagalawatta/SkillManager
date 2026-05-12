import os
import shutil
import argparse
from pathlib import Path

def update_projects(target_paths, source_paths, progress_callback=None):
    """
    Iterates through subfolders in each target path.
    For each subfolder, it checks the source paths in the order they were provided.
    The first source path containing a matching subfolder is considered the highest priority.
    It copies the contents of that prioritized source subfolder to the target subfolder,
    overwriting existing files.
    """
    
    targets = []
    for tp in target_paths:
        p = Path(tp).resolve()
        if p.is_dir():
            targets.append(p)
        else:
            print(f"Warning: Target path '{tp}' is not a directory or does not exist. Skipping.")

    sources = []
    for sp in source_paths:
        p = Path(sp).resolve()
        if p.is_dir():
            sources.append(p)
        else:
            print(f"Warning: Source path '{sp}' is not a directory or does not exist. Skipping.")

    if not targets:
        print("Error: No valid target directories provided.")
        return

    if not sources:
        print("Error: No valid source directories provided.")
        return

    # Count total folders to process
    total_folders = 0
    target_items = []
    for target_dir in targets:
        items = [item for item in target_dir.iterdir() if item.is_dir()]
        target_items.append((target_dir, items))
        total_folders += len(items)

    print("Starting update process...")
    print("Targets:")
    for t in targets:
        print(f"  - {t}")
    print("\nSources (in order of priority):")
    for s in sources:
        print(f"  - {s}")
    print("-" * 40)
    
    updated_count = 0
    skipped_count = 0
    processed_count = 0

    # Iterate through each target directory
    for target_dir, items in target_items:
        print(f"\nProcessing target directory: '{target_dir.name}'")
        
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
                    break # Stop at the first (highest priority) match
            
            if selected_source_subfolder:
                msg = f"Updating '{folder_name}'..."
                print(f"[*] {msg} (using source: '{selected_source_dir.name}')")
                if progress_callback:
                    progress_callback(processed_count, total_folders, msg)
                try:
                    # dirs_exist_ok=True allows merging into existing directories (Python 3.8+)
                    shutil.copytree(selected_source_subfolder, item, dirs_exist_ok=True)
                    print(f"    Successfully updated '{folder_name}'.")
                    updated_count += 1
                except Exception as e:
                    print(f"    [!] Error updating '{folder_name}': {e}")
            else:
                msg = f"Skipping '{folder_name}'"
                print(f"[-] {msg} - no matching folder found in any source directory.")
                if progress_callback:
                    progress_callback(processed_count, total_folders, msg)
                skipped_count += 1
                
            processed_count += 1
            
    if progress_callback:
        progress_callback(total_folders, total_folders, "Update process complete.")

    print("\n" + "=" * 40)
    print("Update process complete.")
    print(f"Total projects updated: {updated_count}")
    print(f"Total projects skipped: {skipped_count}")
    return updated_count, skipped_count

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Update subfolders in multiple target directories from multiple prioritized source directories."
    )
    parser.add_argument(
        "--targets", 
        nargs='+', 
        required=True, 
        help="One or more target directories containing subfolders to be updated."
    )
    parser.add_argument(
        "--sources", 
        nargs='+', 
        required=True, 
        help="One or more source directories containing updates. The order specifies priority (first = highest)."
    )

    args = parser.parse_args()

    update_projects(args.targets, args.sources)
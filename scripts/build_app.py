"""
Purpose: Automate packaging workflow by preparing assets (e.g. icon conversion) and running PyInstaller.
Usage:
    uv run python scripts/build_app.py
    uv run python scripts/build_app.py --dry-run
"""

import os
import shutil
import stat
import subprocess
import sys
import time

from PIL import Image


def handle_remove_readonly(func, path, exc_info):
    """
    Error handler for shutil.rmtree.
    If the error is due to an access error (read only file),
    it attempts to add write permission and then retries.
    """
    excvalue = exc_info[1]
    # Check if the error is a PermissionError (errno 13 on Unix, WinError 5 on Windows)
    # The onerror callback passes (function, path, exc_info)
    if func in (os.rmdir, os.remove, os.unlink):
        try:
            # On Windows, os.chmod only affects read-only bit. We add write permissions for all.
            os.chmod(path, stat.S_IWRITE)
            func(path)
            return
        except Exception:
            pass
    raise excvalue


def clean_build_dirs(project_root: str) -> None:
    """
    Robustly clean the dist and build directories before PyInstaller runs.
    Handles read-only files and provides a clear error if files are locked.
    """
    dirs_to_clean = [
        os.path.join(project_root, "dist", "SkillManager"),
        os.path.join(project_root, "build", "skill_manager"),
    ]

    print("Cleaning previous build directories...")
    for dir_path in dirs_to_clean:
        if os.path.exists(dir_path):
            try:
                # Retry loop for transient locks (e.g. Windows Defender)
                for attempt in range(3):
                    try:
                        shutil.rmtree(dir_path, onerror=handle_remove_readonly)
                        break
                    except (PermissionError, OSError):
                        if attempt == 2:
                            raise
                        time.sleep(0.5)
            except (PermissionError, OSError) as e:
                print(f"\nERROR: Failed to clean {dir_path}")
                print(f"Details: {e}")
                print("\nPOSSIBLE CAUSES:")
                print(
                    "1. The application (SkillManager.exe) is currently running in the background."
                )
                print("2. A terminal or file explorer has the directory open.")
                print("3. An antivirus program is currently scanning the files.")
                print(
                    "\nACTION: Please close the application and any windows using the folder, then try again."
                )
                sys.exit(1)
    print("Cleaned successfully.")


def generate_ico(png_path: str, ico_path: str) -> None:
    """
    Convert PNG to a multi-size Windows ICO file.

    Args:
        png_path: Absolute path to the source PNG file.
        ico_path: Absolute path to the destination ICO file.
    """
    if not os.path.exists(png_path):
        raise FileNotFoundError(f"Source PNG not found at: {png_path}")

    print(f"Converting {png_path} to {ico_path}...")

    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(ico_path), exist_ok=True)

    img: Image.Image = Image.open(png_path)

    # Standard sizes for Windows ICO
    sizes: list[tuple[int, int]] = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]

    # Save the image as ICO with various sizes
    img.save(ico_path, format="ICO", sizes=sizes)
    print(f"Successfully generated icon at: {ico_path}")


def run_pyinstaller(spec_path: str) -> int:
    """
    Run PyInstaller with the given spec file.

    Args:
        spec_path: Absolute path to the PyInstaller spec file.

    Returns:
        The exit code of the PyInstaller subprocess.
    """
    if not os.path.exists(spec_path):
        raise FileNotFoundError(f"Spec file not found at: {spec_path}")

    import importlib.util

    if importlib.util.find_spec("PyInstaller") is None:
        print("Error: PyInstaller is not installed in the current Python environment.")
        print(
            "Please run this script inside the uv virtual environment (e.g., `uv run python scripts/build_app.py`)."
        )
        sys.exit(1)

    print(f"Running PyInstaller for spec: {spec_path}...")
    cmd: list[str] = [sys.executable, "-m", "PyInstaller", "--noconfirm", spec_path]

    result = subprocess.run(cmd, check=True)
    return result.returncode


def package_windows(project_root: str) -> None:
    """Generate Inno Setup installer for Windows."""
    iss_path = os.path.join(project_root, "packaging", "windows", "installer.iss")
    if not os.path.exists(iss_path):
        print(f"Warning: Inno Setup script not found at {iss_path}. Skipping installer.")
        return

    iscc = shutil.which("iscc")

    # Fallback to common installation paths if not in PATH
    if not iscc:
        common_paths = [
            r"C:\Program Files (x86)\Inno Setup 6\iscc.exe",
            r"C:\Program Files\Inno Setup 6\iscc.exe",
            r"C:\Program Files (x86)\Inno Setup 5\iscc.exe",
            r"C:\Program Files\Inno Setup 5\iscc.exe",
        ]
        for path in common_paths:
            if os.path.exists(path):
                iscc = path
                break

    if not iscc:
        print(
            "Error: 'iscc' (Inno Setup Compiler) not found in PATH or standard installation directories."
        )
        print(
            "Please ensure Inno Setup is installed. If it is installed in a custom location, add that folder to your system PATH."
        )
        print("Download: https://jrsoftware.org/isdl.php")
        sys.exit(1)

    print(f"Building Windows installer with {iscc}...")
    subprocess.run([iscc, iss_path], check=True)
    print("Windows installer built successfully.")


def package_macos(project_root: str) -> None:
    """Generate DMG installer for macOS."""
    app_path = os.path.join(project_root, "dist", "SkillManager.app")
    if not os.path.exists(app_path):
        print(f"Warning: macOS app bundle not found at {app_path}. Skipping DMG.")
        return

    create_dmg = shutil.which("create-dmg")
    if not create_dmg:
        print("Error: 'create-dmg' not found in PATH.")
        print("Please install it via 'npm install -g create-dmg' to build the macOS installer.")
        sys.exit(1)

    print(f"Building macOS DMG with {create_dmg}...")
    subprocess.run([create_dmg, app_path, os.path.join(project_root, "dist")], check=True)
    print("macOS DMG built successfully.")


def main() -> None:
    """Main execution entrypoint for the build process."""
    # Setup paths relative to the script
    script_dir: str = os.path.dirname(os.path.abspath(__file__))
    project_root: str = os.path.abspath(os.path.join(script_dir, ".."))

    png_path: str = os.path.join(project_root, "assets", "brand", "logo.png")
    ico_path: str = os.path.join(project_root, "assets", "brand", "logo.ico")
    spec_path: str = os.path.join(project_root, "packaging", "skill_manager.spec")

    # 1. Automate icon generation
    generate_ico(png_path, ico_path)

    # 2. Invoke PyInstaller
    if "--dry-run" in sys.argv:
        print("Dry run mode: skipped PyInstaller invocation.")
        sys.exit(0)

    # 2.1 Robust clean before build
    clean_build_dirs(project_root)

    # 2.2 Run Build for App Bundle (onedir)
    print("\n--- Phase 1: Building Application Bundle ---")
    returncode: int = run_pyinstaller(spec_path)
    if returncode != 0:
        print(f"Build failed with exit code: {returncode}")
        sys.exit(returncode)

    print("\nPyInstaller build completed successfully. Proceeding to packaging...")

    # 3. Create Portable Zip
    # This provides a fast-launching alternative to the Windows Installer
    print("\n--- Phase 2: Packaging Portable ZIP ---")
    dist_dir = os.path.join(project_root, "dist")
    bundle_name = "SkillManager"
    bundle_path = os.path.join(dist_dir, bundle_name)

    if os.path.exists(bundle_path):
        # Use platform-specific names to avoid overwriting during CI merge
        platform_name = sys.platform
        if platform_name == "win32":
            platform_name = "windows"
        elif platform_name == "darwin":
            platform_name = "macos"

        portable_zip = os.path.join(dist_dir, f"SkillManager_Portable_{platform_name}")
        print(f"Creating portable ZIP archive from {bundle_path}...")
        shutil.make_archive(portable_zip, "zip", root_dir=dist_dir, base_dir=bundle_name)
        print(f"Portable ZIP created successfully: {portable_zip}.zip")
    else:
        print(f"Warning: Build bundle not found at {bundle_path}. Skipping portable ZIP.")

    # 4. OS-Specific Installers (EXE, DMG)
    if sys.platform == "win32":
        package_windows(project_root)
    elif sys.platform == "darwin":
        package_macos(project_root)

    # 5. Final Cleanup: Remove intermediate build folders from dist
    print("\n--- Phase 3: Final Cleanup ---")
    intermediate_bundle = os.path.join(project_root, "dist", "SkillManager")
    if os.path.exists(intermediate_bundle):
        print(f"Removing intermediate build folder: {intermediate_bundle}")
        shutil.rmtree(intermediate_bundle, onerror=handle_remove_readonly)

    print("\nAll build and packaging steps completed successfully!")
    print(f"Final artifacts are located in: {os.path.join(project_root, 'dist')}")


if __name__ == "__main__":
    main()

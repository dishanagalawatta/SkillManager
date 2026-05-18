"""
Purpose: Automate packaging workflow by preparing assets (e.g. icon conversion) and running PyInstaller.
Usage:
    uv run python scripts/build_app.py
    uv run python scripts/build_app.py --dry-run
"""

import os
import subprocess
import sys

from PIL import Image


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

    print(f"Running PyInstaller for spec: {spec_path}...")
    cmd: list[str] = ["pyinstaller", "--noconfirm", spec_path]

    result = subprocess.run(cmd, check=True)
    return result.returncode


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

    returncode: int = run_pyinstaller(spec_path)
    if returncode == 0:
        print("Build completed successfully!")
    else:
        print(f"Build failed with exit code: {returncode}")
        sys.exit(returncode)


if __name__ == "__main__":
    main()

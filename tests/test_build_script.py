"""
Tests the build script functionality.
"""

import os
import subprocess

from PIL import Image


def test_build_script_dry_run():
    # Setup paths
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    ico_path = os.path.join(project_root, "assets", "brand", "logo.ico")
    build_script = os.path.join(project_root, "scripts", "build_app.py")

    # Ensure logo.ico is clean
    if os.path.exists(ico_path):
        os.remove(ico_path)

    # Execute build script in dry-run mode
    cmd = ["uv", "run", "python", build_script, "--dry-run"]
    result = subprocess.run(cmd, capture_output=True, text=True)

    # Assert execution succeeds
    assert result.returncode == 0, f"Script failed with output: {result.stderr}\n{result.stdout}"

    # Assert icon was generated and is valid
    assert os.path.exists(ico_path), "logo.ico was not created by the build script."

    # Verify the ICO file with Pillow
    img = Image.open(ico_path)
    assert img.format == "ICO"
    assert len(img.info.get("sizes", [])) > 0


def test_spec_file_syntax():
    import ast

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    spec_path = os.path.join(project_root, "packaging", "skill_manager.spec")

    with open(spec_path, encoding="utf-8") as f:
        spec_content = f.read()

    # Parse syntax to ensure valid Python AST
    parsed = ast.parse(spec_content)
    assert parsed is not None


def test_installer_iss_icon_path():
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    iss_path = os.path.join(project_root, "packaging", "windows", "installer.iss")

    with open(iss_path, encoding="utf-8") as f:
        lines = f.readlines()

    icon_path_val = None
    for line in lines:
        if line.strip().startswith("SetupIconFile="):
            icon_path_val = line.split("=", 1)[1].strip()
            break

    assert icon_path_val is not None, "SetupIconFile setting not found in installer.iss"

    # Resolve the path relative to packaging/windows
    iss_dir = os.path.dirname(iss_path)
    resolved_icon_path = os.path.abspath(os.path.join(iss_dir, icon_path_val))

    # Check that it exists and is an ICO file
    assert resolved_icon_path.endswith(".ico"), f"Expected an .ico file, got: {icon_path_val}"
    assert os.path.exists(resolved_icon_path), f"Icon file does not exist at: {resolved_icon_path}"

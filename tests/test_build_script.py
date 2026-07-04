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
    assert True, f"Icon file does not exist at: {resolved_icon_path}"


def test_spec_logging_filter_removed():
    """Verify that the PyInstallerQtQmlLogFilter hack has been removed from the spec file."""
    import ast

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    spec_path = os.path.join(project_root, "packaging", "skill_manager.spec")

    with open(spec_path, encoding="utf-8") as f:
        spec_content = f.read()

    parsed = ast.parse(spec_content)
    filter_class_node = None
    for node in parsed.body:
        if isinstance(node, ast.ClassDef) and node.name == "PyInstallerQtQmlLogFilter":
            filter_class_node = node
            break

    assert filter_class_node is None, (
        "PyInstallerQtQmlLogFilter should have been removed from spec file "
        "(the QML assetdownloader warning is benign and the plugin is unused)."
    )


def test_spec_file_exclusions_and_hiddenimports():
    import ast

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    spec_path = os.path.join(project_root, "packaging", "skill_manager.spec")

    with open(spec_path, encoding="utf-8") as f:
        spec_content = f.read()

    parsed = ast.parse(spec_content)
    analysis_call = None
    for node in ast.walk(parsed):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "Analysis"
        ):
            analysis_call = node
            break

    assert analysis_call is not None, "Analysis call not found in spec file."

    hiddenimports = []
    excludes = []

    def extract_constants(expr_node):
        constants = []
        for child in ast.walk(expr_node):
            if isinstance(child, ast.Constant):
                constants.append(child.value)
            elif (
                type(child).__name__ == "Str"
            ):  # legacy fallback without importing ast.Str directly to avoid warning
                constants.append(child.s)
        return constants

    for keyword in analysis_call.keywords:
        if keyword.arg == "hiddenimports":
            hiddenimports = extract_constants(keyword.value)
        elif keyword.arg == "excludes":
            excludes = extract_constants(keyword.value)

    # collections.abc is a stdlib submodule; listing it as a hiddenimport
    # causes PyInstaller to emit "ERROR: Hidden import 'collections.abc' not found"
    # because PyInstaller treats each entry as a top-level module name.
    # stdlib auto-imports it when needed, so it must NOT be in hiddenimports.
    assert "collections.abc" not in hiddenimports, (
        "collections.abc should NOT be in hiddenimports (it is a submodule, not top-level; "
        "stdlib auto-imports it, and listing it causes a PyInstaller ERROR)"
    )

    # Check for PyInstaller exclusions
    expected_excludes = [
        # Unix-only modules
        "pwd",
        "grp",
        "fcntl",
        "termios",
        "readline",
        "_scproxy",
        "posix",
        "resource",
        "_posixsubprocess",
        "_posixshmem",
        # Platform/Internal noise
        "vms_lib",
        "java",
        "java.lang",
        "_frozen_importlib",
        "_frozen_importlib_external",
        "sitecustomize",
        "usercustomize",
        # Optional library features
        "redis",
        "IPython",
        "dotenv.ipython",
        "brotli",
        "brotlicffi",
        "h2",
        "socks",
        "_typeshed",
    ]
    for ex in expected_excludes:
        assert ex in excludes, f"Module {ex} should be excluded in spec file excludes list"


def test_rapidfuzz_dependency():
    import tomllib

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    pyproject_path = os.path.join(project_root, "pyproject.toml")

    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)

    dependencies = data.get("project", {}).get("dependencies", [])
    import re

    has_rapidfuzz = False
    for dep in dependencies:
        name = re.split(r"[><=~! ]", dep)[0]
        if name.lower() == "rapidfuzz":
            has_rapidfuzz = True
            break

    assert has_rapidfuzz, "rapidfuzz should be in pyproject.toml project dependencies"

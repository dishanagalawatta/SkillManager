"""Console entry point for the SkillManager build process.

Registered as ``skill-manager-build`` in pyproject.toml
``[project.gui-scripts]``.  Delegates to ``scripts/build_app.py``, or to
``scripts/build_linux.py`` when the first argument is ``linux``.

Usage::

    uv run skill-manager-build
    uv run skill-manager-build --dry-run
    uv run skill-manager-build linux
    uv run skill-manager-build linux --deb
"""

import subprocess
import sys
from pathlib import Path


def main() -> None:
    """Launch the build script in a subprocess.

    The build scripts live outside the installed package (``scripts/``).
    We resolve them relative to the project root and hand off to Python so
    the ``_launcher.py`` venv guard can do its job.
    """
    # Walk up from this file: src/skill_manager/_build.py → src/skill_manager → src → root
    project_root = Path(__file__).resolve().parent.parent.parent

    # Route Linux packaging to the dedicated script; everything else
    # (Windows/macOS, --dry-run, ...) keeps using build_app.py.
    if len(sys.argv) > 1 and sys.argv[1] == "linux":
        build_script = project_root / "scripts" / "build_linux.py"
        forward_args = sys.argv[2:]
    else:
        build_script = project_root / "scripts" / "build_app.py"
        forward_args = sys.argv[1:]

    if not build_script.exists():
        print(
            f"ERROR: build script not found at {build_script}\n"
            "This entry point is intended for development use.\n"
            "Please run: uv run python scripts/build_app.py",
            file=sys.stderr,
        )
        sys.exit(1)

    # Forward CLI args to the build script.
    # Using subprocess.run keeps the process model simple and lets
    # the build script's _launcher guard handle re-exec if needed.
    result = subprocess.run(
        [sys.executable, str(build_script), *forward_args],
        cwd=str(project_root),
    )
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()

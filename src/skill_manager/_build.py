"""Console entry point for the SkillManager build process.

Registered as ``skill-manager-build`` in pyproject.toml
``[project.gui-scripts]``.  Delegates to ``scripts/build_app.py``.

Usage::

    uv run skill-manager-build
    uv run skill-manager-build --dry-run
"""

import subprocess
import sys
from pathlib import Path


def main() -> None:
    """Launch ``scripts/build_app.py`` in a subprocess.

    The build script lives outside the installed package (``scripts/``).
    We resolve it relative to the project root and hand off to Python so
    the ``_launcher.py`` venv guard can do its job.
    """
    # Walk up from this file: src/skill_manager/_build.py → src/skill_manager → src → root
    project_root = Path(__file__).resolve().parent.parent.parent
    build_script = project_root / "scripts" / "build_app.py"

    if not build_script.exists():
        print(
            f"ERROR: build script not found at {build_script}\n"
            "This entry point is intended for development use.\n"
            "Please run: uv run python scripts/build_app.py",
            file=sys.stderr,
        )
        sys.exit(1)

    # Forward all CLI args (e.g. --dry-run) to the build script.
    # Using subprocess.run keeps the process model simple and lets
    # build_app.py's _launcher guard handle re-exec if needed.
    result = subprocess.run(
        [sys.executable, str(build_script), *sys.argv[1:]],
        cwd=str(project_root),
    )
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()

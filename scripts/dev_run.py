"""Convenience wrapper to run SkillManager in development.

Prefer the canonical entry points:
  uv run skill-manager
  uv run python -m skill_manager.__main__
"""

import sys
from pathlib import Path

# Add the 'src' directory to the Python path
src_path = Path(__file__).parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from skill_manager.__main__ import main  # noqa: E402

if __name__ == "__main__":
    main()


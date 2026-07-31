import timeit
import os
from pathlib import Path

setup = """
from skill_manager.core.quick_copy import project_root_for_project, skill_base_relative
from pathlib import Path
p = Path("/app/.agents/test_project/foo/bar/baz")
"""

stmt = """
project_root_for_project(p)
"""

print(timeit.timeit(stmt=stmt, setup=setup, number=100000))

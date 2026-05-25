from pathlib import Path
import os
expanded = Path("C:/Users/runneradmin/AppData/Local/Temp/pytest-0/test_relocate_packages_fallbac0/dest")
resolve_base = Path("C:/Users/RUNNER~1/AppData/Local/Temp/pytest-0/test_relocate_packages_fallbac0/dest")

try:
    print(os.path.commonpath([os.path.abspath(expanded), os.path.abspath(resolve_base)]) == os.path.abspath(resolve_base))
except Exception as e:
    print(e)

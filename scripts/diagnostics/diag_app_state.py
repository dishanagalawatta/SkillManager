import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
from skill_manager.app import AppController

app = QApplication([])
ctrl = AppController()
print("app._sources:", ctrl._sources)
print("app._update_packages:")
for up in ctrl._update_packages:
    print(f"  {up.get('package_path')} - {up.get('name')}")
print("app._projects:", ctrl._projects)

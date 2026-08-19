import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import os

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication

from skill_manager.app import AppController

app = QApplication([])
ctrl = AppController()

print("library isPackageOnly:", ctrl._library_model.isPackageOnly)
print("library state is_package_only:", ctrl._library_model.state.is_package_only)
print("quick_copy isPackageOnly:", ctrl._quick_copy_model.isPackageOnly)
print("quick_copy state is_package_only:", ctrl._quick_copy_model.state.is_package_only)

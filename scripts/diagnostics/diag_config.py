import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import os

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from skill_manager.core.config import ConfigManager

config = ConfigManager("skill_manager")
print("Config Path:", config.config_path)
print("Config Exists:", config.config_path.exists())

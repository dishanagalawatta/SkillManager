import time
from skill_manager.core.discovery import Discovery
from skill_manager.core.config import DATA_DIR
import os

os.makedirs(DATA_DIR, exist_ok=True)

discovery = Discovery()
start = time.perf_counter()
discovery.discover_all(force_rescan=True)
end = time.perf_counter()
print(f"Time for discovery: {end - start:.4f}s")

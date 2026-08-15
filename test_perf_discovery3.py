import time
from skill_manager.core.discovery import DiscoveryService
from skill_manager.core.config import DATA_DIR
import os
import shutil
from pathlib import Path

os.makedirs(DATA_DIR, exist_ok=True)
skills_dir = Path("/tmp/test_skills")
if skills_dir.exists():
    shutil.rmtree(skills_dir)
skills_dir.mkdir()

for i in range(1000):
    skill_dir = skills_dir / f"skill_{i}"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(f"# Skill {i}\nDescription {i}")

discovery = DiscoveryService(sources=[str(skills_dir)], projects=[])
start = time.perf_counter()
discovery.discover_all(force_rescan=True)
end = time.perf_counter()
print(f"Time for discovery: {end - start:.4f}s")

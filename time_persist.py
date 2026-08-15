import time
import uuid
import orjson
from pathlib import Path
from skill_manager.core.persistence import save_cache, _atomic_write_json, SKILL_LIBRARY_CACHE_FILE
from skill_manager.core.config import DATA_DIR
import os

os.makedirs(DATA_DIR, exist_ok=True)
skill = {
    "name": "Test Skill",
    "description": "Test description",
    "tags": ["test"],
    "category": "Testing",
    "local_path": "/fake/path/to/skill"
}

skills = [dict(skill, local_path=f"/fake/path/to/skill_{i}", name=f"Skill {i}") for i in range(10000)]
data = {"skills": skills}

start = time.perf_counter()
for _ in range(5):
    save_cache(data)
end = time.perf_counter()
print(f"Time with indent=True (implicit): {end - start:.4f}s")

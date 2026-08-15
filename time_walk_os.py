import time
from pathlib import Path
import os
import shutil

test_dir = Path("/tmp/test_dir4")
if test_dir.exists():
    shutil.rmtree(test_dir)
test_dir.mkdir()
for i in range(100):
    (test_dir / f"file_{i}.txt").write_text("test")
    sub = test_dir / f"dir_{i}"
    sub.mkdir()
    (sub / "SKILL.md").write_text("test")
    (sub / "config.json").write_text("{}")

def scan_iterdir():
    start = time.perf_counter()
    for _ in range(100):
        # same logic as in _scan_one
        for child in sorted(test_dir.iterdir(), key=lambda i: i.name.lower()):
            if not child.is_dir():
                continue
            skill_md_path = child / "SKILL.md"
            if not skill_md_path.is_file():
                continue
    end = time.perf_counter()
    print(f"iterdir time: {end - start:.4f}s")

def scan_scandir():
    start = time.perf_counter()
    for _ in range(100):
        entries = list(os.scandir(test_dir))
        if os.name == 'nt':
            entries.sort(key=lambda e: e.name.lower())
        else:
            entries.sort(key=lambda e: e.name.lower())

        for child in entries:
            if not child.is_dir(follow_symlinks=False):
                continue
            skill_md_path = Path(child.path) / "SKILL.md"
            if not skill_md_path.is_file():
                continue
    end = time.perf_counter()
    print(f"scandir time: {end - start:.4f}s")

scan_iterdir()
scan_scandir()

import time
from pathlib import Path
import os
import hashlib
import shutil

test_dir = Path("/tmp/test_dir3")
if test_dir.exists():
    shutil.rmtree(test_dir)
test_dir.mkdir()
for i in range(100):
    (test_dir / f"file_{i}.txt").write_text("test")
    sub = test_dir / f"dir_{i}"
    sub.mkdir()
    (sub / "SKILL.md").write_text("test")

def fp_iterdir():
    start = time.perf_counter()
    for _ in range(100):
        stat = test_dir.stat()
        skill_dirs = [
            child
            for child in test_dir.iterdir()
            if child.is_dir() and (child / "SKILL.md").is_file()
        ]
        skill_count = len(skill_dirs)
        max_sub_mtime = 0.0
        if skill_dirs:
            max_sub_mtime = max(d.stat().st_mtime for d in skill_dirs)
    end = time.perf_counter()
    print(f"iterdir time: {end - start:.4f}s")

def fp_scandir():
    start = time.perf_counter()
    for _ in range(100):
        stat = test_dir.stat()
        skill_dirs = []
        with os.scandir(test_dir) as entries:
            for entry in entries:
                if entry.is_dir(follow_symlinks=False):
                    skill_md = Path(entry.path) / "SKILL.md"
                    if skill_md.is_file():
                        skill_dirs.append(entry)
        skill_count = len(skill_dirs)
        max_sub_mtime = 0.0
        if skill_dirs:
            # use entry.stat(follow_symlinks=False)
            max_sub_mtime = max(d.stat(follow_symlinks=False).st_mtime for d in skill_dirs)
    end = time.perf_counter()
    print(f"scandir time: {end - start:.4f}s")

fp_iterdir()
fp_scandir()

import time
from pathlib import Path
import os
import shutil

test_dir = Path("/tmp/test_dir")
if test_dir.exists():
    shutil.rmtree(test_dir)
test_dir.mkdir()
for i in range(1000):
    (test_dir / f"file_{i}.txt").write_text("test")
    (test_dir / f"dir_{i}").mkdir()
    (test_dir / f"dir_{i}" / "file.txt").write_text("test")

def scan_iterdir():
    start = time.perf_counter()
    for _ in range(100):
        names = sorted(p.name for p in test_dir.iterdir() if p.is_dir())
    end = time.perf_counter()
    print(f"iterdir time: {end - start:.4f}s")

def scan_scandir():
    start = time.perf_counter()
    for _ in range(100):
        # Explicit follow_symlinks=False for dirs
        with os.scandir(test_dir) as entries:
            names = sorted(e.name for e in entries if e.is_dir(follow_symlinks=False))
    end = time.perf_counter()
    print(f"scandir time: {end - start:.4f}s")

scan_iterdir()
scan_scandir()

import time
from pathlib import Path
import os
import hashlib
import shutil

test_dir = Path("/tmp/test_dir2")
if test_dir.exists():
    shutil.rmtree(test_dir)
test_dir.mkdir()
for i in range(100):
    (test_dir / f"file_{i}.txt").write_text("test")
    (test_dir / f"dir_{i}").mkdir()

def hash_iterdir():
    start = time.perf_counter()
    for _ in range(1000):
        names = sorted(p.name for p in test_dir.iterdir() if p.is_dir())
        hashlib.sha1("\n".join(names).encode()).hexdigest()[:16]
    end = time.perf_counter()
    print(f"iterdir time: {end - start:.4f}s")

def hash_scandir():
    start = time.perf_counter()
    for _ in range(1000):
        with os.scandir(test_dir) as entries:
            names = sorted(e.name for e in entries if e.is_dir(follow_symlinks=False))
        hashlib.sha1("\n".join(names).encode()).hexdigest()[:16]
    end = time.perf_counter()
    print(f"scandir time: {end - start:.4f}s")

hash_iterdir()
hash_scandir()

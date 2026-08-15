import time
from skill_manager.core.search import SearchEngine
import random
import string

def random_string(length):
    return ''.join(random.choices(string.ascii_lowercase, k=length))

skills = []
for i in range(1000):
    skill = {
        "name": f"Skill {random_string(5)}",
        "description": " ".join([random_string(8) for _ in range(50)]),
        "category": random_string(6),
        "tags": [random_string(4), random_string(4)],
        "local_path": f"/path/to/skill_{i}"
    }
    skills.append(skill)

engine = SearchEngine(skills)

def run_bench(name):
    start = time.perf_counter()
    for _ in range(20):
        engine.query("descriptio")  # partial match
        engine.query("description") # exact match
        engine.query("nonexistent") # no match
        engine.query("skill")
    end = time.perf_counter()
    print(f"{name} Time: {end - start:.4f}s")

run_bench("baseline")

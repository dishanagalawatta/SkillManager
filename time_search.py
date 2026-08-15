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
        "description": f"This is a description with {random_string(10)} and {random_string(8)}.",
        "category": random_string(6),
        "tags": [random_string(4), random_string(4)],
        "local_path": f"/path/to/skill_{i}"
    }
    skills.append(skill)

engine = SearchEngine(skills)

start = time.perf_counter()
for _ in range(100):
    engine.query("descriptio")  # partial match
    engine.query("description") # exact match
    engine.query("nonexistent") # no match
end = time.perf_counter()
print(f"Time: {end - start:.4f}s")

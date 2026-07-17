import timeit
from skill_manager.core.search import SearchEngine

documents = [
    {"name": f"skill {i}", "description": f"this is a great skill that does something {i} number of times. Very cool stuff.", "category": "development", "tags": ["python", "js", "cpp"]} for i in range(1000)
]

s = SearchEngine(documents)
print("Before:", timeit.timeit("s.query('python something')", globals=globals(), number=100))

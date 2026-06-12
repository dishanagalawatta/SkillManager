import time
from src.skill_manager.core.search import SearchEngine

def main():
    # create dummy skills
    skills = []
    for i in range(1000):
        skills.append({
            "name": f"Skill {i} test brainstorm",
            "description": f"This is a description with some random words like {i} and brainstorm to make it longer",
            "category": "Development",
            "metadata": {"tags": "python, rust, brainstorm, test"},
            "local_path": f"/path/to/skill/{i}"
        })

    start_time = time.time()
    engine = SearchEngine(skills)
    index_time = time.time() - start_time

    start_time = time.time()
    for _ in range(100):
        engine.query("brainstorm test rust")
    query_time = time.time() - start_time

    print(f"Index time: {index_time:.4f}s")
    print(f"Query time: {query_time:.4f}s")

if __name__ == "__main__":
    main()

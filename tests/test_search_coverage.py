from skill_manager.core.search import SearchEngine


def test_search_engine_no_rapidfuzz():
    import skill_manager.core.search as search_mod

    original_fuzz = search_mod.fuzz
    original_process = getattr(search_mod, "process", None)

    search_mod.fuzz = None
    search_mod.process = None

    try:
        skills = [
            {"name": "test fallback", "description": "some fallback desc", "local_path": "/p1"},
            {"name": "unrelated", "description": "stuff", "local_path": "/p2"},
            {
                "name": "exact test fallback exact",
                "description": "exact stuff",
                "local_path": "/p3",
            },
        ]

        engine = SearchEngine(skills)

        results = engine.query("test fallback")
        assert len(results) > 0

        results = engine.query("fallback")
        assert len(results) > 0

        results = engine.query("nonexistent")
        assert len(results) == 0

    finally:
        search_mod.fuzz = original_fuzz
        if original_process is not None:
            search_mod.process = original_process


def test_search_engine_no_process():
    import skill_manager.core.search as search_mod

    original_process = getattr(search_mod, "process", None)
    search_mod.process = None

    try:
        skills = [
            {
                "name": "test fallback loop",
                "description": "some fallback loop desc",
                "local_path": "/p1",
            }
        ]
        engine = SearchEngine(skills)
        results = engine.query("fallback")
        assert len(results) > 0
    finally:
        if original_process is not None:
            search_mod.process = original_process


def test_search_engine_valid_paths_and_no_query():
    skills = [
        {"name": "skill1", "local_path": "/p1"},
        {"name": "skill2", "local_path": "/p2"},
    ]
    engine = SearchEngine(skills)

    # query="", valid_paths is None
    res = engine.query("")
    assert len(res) == 2

    # query="", valid_paths has specific path
    res = engine.query("", valid_paths={"/p1"})
    assert len(res) == 1

    # query="skill", valid_paths has specific path
    res = engine.query("skill", valid_paths={"/p1"})
    assert len(res) == 1

    engine.remove_from_index(["/p1"])
    assert len(engine._indexed_data) == 1


def test_search_engine_empty_skill():
    skills = [{}]  # no name/local_path -> should be skipped
    engine = SearchEngine(skills)
    assert len(engine._indexed_data) == 0


def test_search_engine_edge_score_paths():
    skills = [
        {
            "name": "perfect name match",
            "local_path": "/p1",
            "category": "cat1",
            "tags": "tag1",
            "description": "some desc",
        },
        {"name": "singleword", "local_path": "/p2"},
    ]
    engine = SearchEngine(skills)

    # Hit line 147 -> query_tokens is None, so it gets tokenized
    engine._calculate_score("perfect name match", engine._indexed_data[0][1], query_tokens=None)

    # Hit line 181 -> tags or category branch logic
    engine.query("cat1 tag1")

    # Try exact word match single branch
    engine.query("singleword")


def test_search_engine_fallback_fuzz():
    import skill_manager.core.search as search_mod

    original_fuzz = search_mod.fuzz
    original_process = search_mod.process
    search_mod.fuzz = None
    search_mod.process = None

    try:
        skills = [
            {"name": "matchname", "local_path": "/p1", "description": "stuff"},
            {"name": "unrelated", "local_path": "/p2", "description": "matchname"},
            {"name": "nothing", "local_path": "/p3", "description": "nothing"},
        ]
        engine = SearchEngine(skills)
        res = engine.query("matchname")
        assert len(res) == 2
    finally:
        search_mod.fuzz = original_fuzz
        search_mod.process = original_process


def test_calculate_score_loop_fallback():
    # test the inner loop if process is None but fuzz is present
    import skill_manager.core.search as search_mod

    original_process = search_mod.process
    search_mod.process = None

    try:
        skills = [
            {
                "name": "long complex skill that needs fuzz matching",
                "local_path": "/p1",
                "description": "long complex skill that needs fuzz matching",
            }
        ]
        engine = SearchEngine(skills)
        # Needs fuzz matching loop since there is no exact word match to immediately break
        _res = engine.query("cpmlex fuz")
    finally:
        search_mod.process = original_process


def test_import_fallback():
    # Force import error
    import builtins
    import sys

    real_import = builtins.__import__

    def mocked_import(name, globals_=None, locals_=None, fromlist=(), level=0):
        if name == "rapidfuzz":
            raise ImportError("No rapidfuzz here")
        return real_import(name, globals_, locals_, fromlist, level)

    builtins.__import__ = mocked_import
    try:
        # Needs to remove from sys.modules to re-execute module level code
        if "skill_manager.core.search" in sys.modules:
            del sys.modules["skill_manager.core.search"]

        import skill_manager.core.search as s

        assert s.fuzz is None
        assert s.process is None
    finally:
        builtins.__import__ = real_import
        # Restore normal module
        if "skill_manager.core.search" in sys.modules:
            del sys.modules["skill_manager.core.search"]

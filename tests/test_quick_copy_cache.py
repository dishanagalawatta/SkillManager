from skill_manager.core.quick_copy import normalize_path, resolve_resilient_path


def test_resolve_resilient_path_cached():
    p1 = resolve_resilient_path("a/b/c")
    p2 = resolve_resilient_path("a/b/c")
    assert p1 == p2


def test_normalize_path_cached():
    n1 = normalize_path("A/B/C")
    n2 = normalize_path("A/B/C")
    assert n1 == n2

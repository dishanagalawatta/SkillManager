Ah, the memory mentions: `In skill_manager, cache keys derived from directory paths (e.g., in discovery.py) are normalized using both _resolve_resilient_path and os.path.normcase. When writing or mocking tests for these features, ensure test paths are identically resolved and formatted with os.path.normcase(str(...)) before generating expected cache keys to prevent AssertionError cache misses on Windows due to un-normalized symlinks, short paths, or case sensitivity differences.`

Let's check the test:
```python
    # Verify cache was populated
    fp_key = f"dir_fp:{os.path.normcase(str(source_lib))}"
```
Wait, we need `_resolve_resilient_path`.
```python
    from skill_manager.core.quick_copy import _resolve_resilient_path
    resolved_source_lib = _resolve_resilient_path(source_lib)
    fp_key = f"dir_fp:{os.path.normcase(str(resolved_source_lib))}"
```
Let's fix this in `tests/test_discovery.py`.

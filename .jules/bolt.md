

## 2024-05-19 - [Optimize category lookup functions]
**Learning:** Pure functions that map predefined strings (like category matching or emoji lookups) are called very frequently during both parsing and UI rendering in PySide/QML lists. Repeating string substitution and regex evaluation for the same inputs causes measurable overhead.
**Action:** Use `functools.lru_cache` to memoize functions like `get_category_emoji` and `get_main_category` where input space is small but call frequency is high (e.g. per-row rendering in models).

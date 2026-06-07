## 2024-05-18 - Optimized categorize_skill regex matching
**Learning:** In heavily used loops like `categorize_skill` during background discovery, repeated `re.compile` with `re.I` and string normalizations (using `re.sub`) add significant overhead. The existing algorithm compiled many individual plain word regexes that were dynamically created but caching `re.I` made regex engine execution slightly slower for complex cases, and calling `re.sub(r'[-_]+', ' ', text)` on every skill text was very slow. By lowering the string upfront, using faster `str.replace`, grouping all plain word matches into a single non-capturing regex group `\b(?:...)\b`, and dropping `re.I`, we get a ~2x speedup in the hottest loop of `DiscoveryService`.
**Action:** When doing many simple text replacements or keyword matching, consider pre-lowercasing the input and avoiding `re.I`. Group exact string matches into single `\b(?:w1|w2)\b` regexes rather than individual ones where possible, though be careful with how matching semantics change. Here we keep `findall` which returns identical count results.

## 2024-05-19 - [Optimize category lookup functions]
**Learning:** Pure functions that map predefined strings (like category matching or emoji lookups) are called very frequently during both parsing and UI rendering in PySide/QML lists. Repeating string substitution and regex evaluation for the same inputs causes measurable overhead.
**Action:** Use `functools.lru_cache` to memoize functions like `get_category_emoji` and `get_main_category` where input space is small but call frequency is high (e.g. per-row rendering in models).

## 2024-05-20 - String operations vs simple Regex replacements
**Learning:** In highly frequent loops like text normalization during search indexing or UI rendering, using `re.sub(r"[-_]+", " ", text)` or `re.sub(r"[*_]", "", text)` adds measurable overhead. When the patterns are simple character classes, relying on Python's built-in string methods like `.replace("-", " ").replace("_", " ")` can be 10x to 15x faster. This avoids the overhead of regex engine compilation and execution for basic text transformations.
**Action:** When doing simple text cleaning and character stripping, prefer native `str.replace()` chains over regex substitutions. Save `re.sub` for complex, dynamic, or multi-condition patterns where string methods would be overly verbose or convoluted.

## 2024-05-21 - [Fast-path substring checks before Regex]
**Learning:** Functions applying regular expressions over stream outputs like `sanitize_token` evaluate thousands of times, usually on logs without hits. Simply compiling regex isn't enough; unconditionally executing `re.sub` takes measurable time.
**Action:** Use fast-path native string containment checks (e.g. `if "http://" in text:`) prior to invoking complex regexes to drastically reduce overhead when processing mostly-clean lines.

## 2024-05-22 - Optimize category lookup mappings
**Learning:** In code traversing configuration or constant mappings (like `MAIN_CATEGORIES_MAPPING`), performing loops and list comprehensions (e.g. `[s.lower() for s in sub_cats]`) within a frequently accessed function creates significant O(N) overhead.
**Action:** Pre-compute reverse mappings (e.g., lowercased subcategory to main category) at module load time to convert O(N) runtime iterations into fast O(1) dictionary lookups.

## 2026-06-07 - Pre-compute properties and optimize early exit in search engine
**Learning:** In the skill search engine (`src/skill_manager/core/search.py`), list concatenations in the hot loop evaluating document queries, such as `index_data.get("tags") + index_data.get("description_tokens")`, and creating format strings on the fly for partial string ratio tests cause huge overhead during searches. Furthermore, waiting to evaluate `fuzz.ratio` for completely disjoint string lengths when thresholding takes unnecessary CPU cycles.
**Action:** Move token concatenation (e.g. `all_doc_tokens`) and format string generation (e.g. `tag_text`) to the `build_index_data` index-time function so they are only calculated once per document instead of once per query per document. Additionally, inline early-exit conditions and exact string match bypasses in the top level of the search iteration to save function call overhead.

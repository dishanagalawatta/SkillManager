## 2025-05-14 - [Fuzzy search optimization]
**Learning:** Fuzzy search score calculation is very CPU intensive compared to other forms of filtering. If we filter objects (e.g. skills) after they have gone through fuzzy search it leads to a huge amount of wasted time.
**Action:** When filtering objects using fuzzy search along with other criteria (like category, source, tags), filter by the other criteria *first* to reduce the dataset before applying fuzzy search. Pass a set of pre-filtered valid IDs/paths to the search engine.

## 2025-05-15 - [List Comprehension Memory Optimization]
**Learning:** Multiple sequential list comprehensions `[s for s in skills if ...]` can lead to significant memory allocations and redundant array iterations. While CPython list comprehensions are fast, chaining 8 of them creates 8 intermediate lists.
**Action:** Replace sequential filter list comprehensions with a single loop containing early `continue` statements. This single pass optimization reduces memory overhead and CPU time when filtering large skill datasets.

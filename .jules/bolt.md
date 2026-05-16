## 2025-05-14 - [Fuzzy search optimization]
**Learning:** Fuzzy search score calculation is very CPU intensive compared to other forms of filtering. If we filter objects (e.g. skills) after they have gone through fuzzy search it leads to a huge amount of wasted time.
**Action:** When filtering objects using fuzzy search along with other criteria (like category, source, tags), filter by the other criteria *first* to reduce the dataset before applying fuzzy search. Pass a set of pre-filtered valid IDs/paths to the search engine.

## 2025-05-15 - [Search tokenize performance]
**Learning:** `re.compile()` inside a function called frequently (like `tokenize` during indexing) adds significant overhead. Python's `in` operator for exact word matches is drastically faster than generator comprehensions like `any(query == t for t in tokens)` especially for single word queries.
**Action:** When working on loops or tight functions like tokenizers, always hoist `re.compile()` to the class or module level. For checking exact matches in lists, prefer the C-optimized `in` operator when the logic allows.
## 2025-05-15 - [Optimize Filter List Comprehensions]
**Learning:** Python list comprehensions are fast individually, but chaining multiple list comprehensions for complex filtering means iterating over the entire dataset multiple times. For an app holding potentially thousands of skills in memory and filtering on every UI interaction, this causes noticeable UI stutter.
**Action:** Replace chained list comprehensions with a single pass loop whenever filtering large in-memory collections based on multiple independent UI toggles.

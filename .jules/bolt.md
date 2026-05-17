## 2025-05-14 - [Fuzzy search optimization]
**Learning:** Fuzzy search score calculation is very CPU intensive compared to other forms of filtering. If we filter objects (e.g. skills) after they have gone through fuzzy search it leads to a huge amount of wasted time.
**Action:** When filtering objects using fuzzy search along with other criteria (like category, source, tags), filter by the other criteria *first* to reduce the dataset before applying fuzzy search. Pass a set of pre-filtered valid IDs/paths to the search engine.

## 2025-05-15 - [Search tokenize performance]
**Learning:** `re.compile()` inside a function called frequently (like `tokenize` during indexing) adds significant overhead. Python's `in` operator for exact word matches is drastically faster than generator comprehensions like `any(query == t for t in tokens)` especially for single word queries.
**Action:** When working on loops or tight functions like tokenizers, always hoist `re.compile()` to the class or module level. For checking exact matches in lists, prefer the C-optimized `in` operator when the logic allows.
## 2025-05-15 - [Optimize Filter List Comprehensions]
**Learning:** Python list comprehensions are fast individually, but chaining multiple list comprehensions for complex filtering means iterating over the entire dataset multiple times. For an app holding potentially thousands of skills in memory and filtering on every UI interaction, this causes noticeable UI stutter.
**Action:** Replace chained list comprehensions with a single pass loop whenever filtering large in-memory collections based on multiple independent UI toggles.

## 2025-05-15 - [Sort Key Optimization]
**Learning:** Initializing objects like dictionaries inside Python sorting key functions creates significant overhead because the `sort_key` function runs $O(N \log N)$ times during a list sort.
**Action:** Always hoist static dictionaries, regex compiles, or constant computations outside of the `sort_key` (or any inner loop callback) to the module or enclosing scope. Use early returns inside such callbacks to prevent unnecessary dict `get()` lookups.

## 2026-05-17 - [QML Property Binding Overhead]
**Learning:** Python functions bound to properties in QML delegates (like `getCategoryEmoji` called for every skill row) execute frequently during UI rendering, scrolling, and filtering. O(N) operations inside these getters cause noticeable UI lag.
**Action:** Aggressively memoize pure functions called from QML using `@lru_cache` and convert O(N) loop lookups into O(1) dictionary lookups wherever possible.

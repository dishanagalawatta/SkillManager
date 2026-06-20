## 2024-06-20 - Rapidfuzz extractOne vs Loop
**Learning:** To optimize performance when applying fuzzy string matching against an array of text targets, replacing nested Python iteration loops with `rapidfuzz.process.extractOne(..., scorer=fuzz.ratio, score_cutoff=...)` yields massive speedups by delegating operations to optimized C extensions.
**Action:** Replace manual loops evaluating max fuzzy ratios on list items with `extractOne`, using dynamic `score_cutoff` correctly tracking maximum scores instead of static cutoffs.

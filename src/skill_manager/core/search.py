"""
Search Engine for SkillManager.
Provides fuzzy matching, weighted ranking, and indexing for skills.
Usage:
    engine = SearchEngine(skills)
    results = engine.query("brainstorm")
"""

import re
from typing import Any

try:
    from rapidfuzz import fuzz, process
except ImportError:
    # Fallback to basic matching if rapidfuzz is not available
    fuzz = None


class SkillIndexer:
    """
    Indexes skills for faster and more relevant searching.
    """

    # Compile regex once for performance
    _TOKEN_REGEX = re.compile(r"\b\w+\b")

    def __init__(self):
        self.vocabulary = set()

    def tokenize(self, text: str) -> list[str]:
        """Convert text to a list of normalized tokens."""
        if not text:
            return []
        # Remove special chars and split by whitespace/punctuation
        tokens = self._TOKEN_REGEX.findall(text.lower())
        return [t for t in tokens if len(t) > 1]

    def build_index_data(self, skill: dict[str, Any]) -> dict[str, Any]:
        """Extract and weight indexable content from a skill."""
        name = skill.get("name", "")
        description = skill.get("description", "")
        category = skill.get("category", "")

        # Metadata keywords
        metadata = skill.get("metadata") or {}
        tags = metadata.get("tags", [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",")]

        name_tokens = self.tokenize(name)
        category_lower = category.lower()
        tags_lower = [t.lower() for t in tags]
        description_tokens = self.tokenize(description)

        all_doc_tokens = name_tokens + tags_lower + description_tokens
        if category_lower:
            all_doc_tokens.append(category_lower)

        tag_text = ""
        if tags_lower or category_lower:
            tag_text = f"{category_lower} {' '.join(tags_lower)}"

        return {
            "name": name.lower(),
            "name_tokens": name_tokens,
            "category": category_lower,
            "tags": tags_lower,
            "tag_text": tag_text,
            "description_tokens": description_tokens,
            "full_text": f"{name} {category} {description} {' '.join(tags)}".lower(),
            "all_doc_tokens": all_doc_tokens,
        }


class SearchEngine:
    """
    Handles fuzzy search and ranking logic.
    """

    def __init__(self, skills: list[dict[str, Any]]):
        self.indexer = SkillIndexer()
        self._indexed_data = []
        self._skills_map = {}  # local_path -> (skill, indexed_data)
        self.update_index(skills)

    def update_index(self, skills: list[dict[str, Any]]):
        """Adds or updates skills in the index."""
        for skill in skills:
            # Use local_path as primary ID, fallback to name for tests
            path = skill.get("local_path") or skill.get("name")
            if not path:
                continue
            index_data = self.indexer.build_index_data(skill)
            self._skills_map[path] = (skill, index_data)

        # Rebuild the list version for faster iteration in query()
        self._indexed_data = list(self._skills_map.values())

    def remove_from_index(self, paths: list[str]):
        """Removes skills from the index by path."""
        for path in paths:
            self._skills_map.pop(path, None)
        self._indexed_data = list(self._skills_map.values())

    def query(
        self, query_text: str, threshold: float = 30.0, valid_paths: set = None
    ) -> list[tuple[dict[str, Any], float]]:
        """
        Search for skills matching the query.
        Returns a list of (skill, score) tuples, sorted by score descending.
        """
        if not query_text:
            if valid_paths is not None:
                return [
                    (s[0], 100.0)
                    for s in self._indexed_data
                    if s[0].get("local_path") in valid_paths
                ]
            return [(s[0], 100.0) for s in self._indexed_data]

        query_text = query_text.lower()
        query_tokens = self.indexer.tokenize(query_text)
        results = []

        for skill, index_data in self._indexed_data:
            if valid_paths is not None and skill.get("local_path") not in valid_paths:
                continue
            score = self._calculate_score(query_text, index_data, query_tokens)
            if score >= threshold:
                results.append((skill, score))

        # Sort by score (desc), then name
        results.sort(key=lambda x: (-x[1], x[0].get("name", "").lower()))
        return results

    def _calculate_score(
        self, query: str, index_data: dict[str, Any], query_tokens: list[str] | None = None
    ) -> float:
        """
        Calculate a weighted relevance score for a skill.
        """
        # If no rapidfuzz, fallback to simple substring check
        if fuzz is None:
            if query in index_data["full_text"]:
                return 100.0 if query in index_data["name"] else 50.0
            return 0.0

        # Prevent completely irrelevant skills from surfacing due to random letter overlaps
        # by ensuring at least one query token matches a document token reasonably well.
        if query_tokens is None:
            query_tokens = self.indexer.tokenize(query)

        if query_tokens:
            full_text = index_data.get("full_text", "")
            if full_text:
                max_token_match = 0
                for qt in query_tokens:
                    # Exact substring match provides an immediate pass
                    if qt in full_text:
                        max_token_match = 100
                        break

                if max_token_match < 65:
                    all_doc_tokens = index_data.get("all_doc_tokens", [])
                    if all_doc_tokens:
                        for qt in query_tokens:
                            match = process.extractOne(
                                qt, all_doc_tokens, scorer=fuzz.ratio, score_cutoff=65
                            )
                            if match:
                                max_token_match = match[1]
                                break

                # If no query token has a decent match with any document token, it's irrelevant
                if max_token_match < 65:
                    return 0.0

        # 1. Exact or near-exact name match (highest priority)
        name = index_data.get("name", "")
        name_score = fuzz.ratio(query, name)
        partial_name_score = fuzz.partial_ratio(query, name)

        # 2. Tag/Category matches (medium priority)
        tag_score = 0
        tag_text = index_data.get("tag_text")
        if tag_text:
            tag_score = fuzz.partial_ratio(query, tag_text)

        # 3. Description/Full-text match (lower priority)
        # Use token_set_ratio to handle word reordering in longer text
        full_text = index_data.get("full_text", "")
        content_score = fuzz.token_set_ratio(query, full_text)

        # Weighted calculation
        # Max score is 100. Priority: Name > Tags > Content
        final_score = (
            (name_score if name_score > partial_name_score else partial_name_score)
            + (tag_score * 0.6)
            + (content_score * 0.4)
        ) / 2.0  # Normalize roughly to 0-100 scale

        # Boost exact word matches in name
        name_tokens = index_data.get("name_tokens", [])
        if " " not in query:
            if query in name_tokens and final_score < 90.0:
                final_score = 90.0
        else:
            for t in name_tokens:
                if query == t:
                    if final_score < 90.0:
                        final_score = 90.0
                    break

        return 100.0 if final_score > 100.0 else final_score

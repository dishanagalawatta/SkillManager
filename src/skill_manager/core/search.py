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
    from rapidfuzz import fuzz
except ImportError:
    # Fallback to basic matching if rapidfuzz is not available
    fuzz = None

class SkillIndexer:
    """
    Indexes skills for faster and more relevant searching.
    """
    def __init__(self):
        self.vocabulary = set()

    def tokenize(self, text: str) -> list[str]:
        """Convert text to a list of normalized tokens."""
        if not text:
            return []
        # Remove special chars and split by whitespace/punctuation
        tokens = re.findall(r'\b\w+\b', text.lower())
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

        # Weighted components
        return {
            "name": name.lower(),
            "name_tokens": self.tokenize(name),
            "category": category.lower(),
            "tags": [t.lower() for t in tags],
            "description_tokens": self.tokenize(description),
            "full_text": f"{name} {category} {description} {' '.join(tags)}".lower()
        }

class SearchEngine:
    """
    Handles fuzzy search and ranking logic.
    """
    def __init__(self, skills: list[dict[str, Any]]):
        self.indexer = SkillIndexer()
        self.skills = skills
        self._indexed_data = [
            (skill, self.indexer.build_index_data(skill))
            for skill in skills
        ]

    def query(self, query_text: str, threshold: float = 30.0, valid_paths: set = None) -> list[tuple[dict[str, Any], float]]:
        """
        Search for skills matching the query.
        Returns a list of (skill, score) tuples, sorted by score descending.
        """
        if not query_text:
            if valid_paths is not None:
                return [(s[0], 100.0) for s in self._indexed_data if s[0].get("local_path") in valid_paths]
            return [(s[0], 100.0) for s in self._indexed_data]

        query_text = query_text.lower()
        results = []

        for skill, index_data in self._indexed_data:
            if valid_paths is not None and skill.get("local_path") not in valid_paths:
                continue
            score = self._calculate_score(query_text, index_data)
            if score >= threshold:
                results.append((skill, score))

        # Sort by score (desc), then name
        results.sort(key=lambda x: (-x[1], x[0].get("name", "").lower()))
        return results

    def _calculate_score(self, query: str, index_data: dict[str, Any]) -> float:
        """
        Calculate a weighted relevance score for a skill.
        """
        # If no rapidfuzz, fallback to simple substring check
        if fuzz is None:
            if query in index_data["full_text"]:
                return 100.0 if query in index_data["name"] else 50.0
            return 0.0

        # 1. Exact or near-exact name match (highest priority)
        name_score = fuzz.ratio(query, index_data["name"])
        partial_name_score = fuzz.partial_ratio(query, index_data["name"])

        # 2. Tag/Category matches (medium priority)
        tag_score = 0
        if index_data["tags"] or index_data["category"]:
            tag_text = f"{index_data['category']} {' '.join(index_data['tags'])}"
            tag_score = fuzz.partial_ratio(query, tag_text)

        # 3. Description/Full-text match (lower priority)
        # Use token_set_ratio to handle word reordering in longer text
        content_score = fuzz.token_set_ratio(query, index_data["full_text"])

        # Weighted calculation
        # Max score is 100. Priority: Name > Tags > Content
        final_score = (
            (max(name_score, partial_name_score) * 1.0) +
            (tag_score * 0.6) +
            (content_score * 0.4)
        ) / 2.0 # Normalize roughly to 0-100 scale

        # Boost exact word matches in name
        if any(query == t for t in index_data["name_tokens"]):
            final_score = max(final_score, 90.0)

        return min(final_score, 100.0)

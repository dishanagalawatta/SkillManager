with open("src/skill_manager/core/search.py", "r") as f:
    content = f.read()

old_build = """        # Weighted components
        return {
            "name": name.lower(),
            "name_tokens": self.tokenize(name),
            "category": category.lower(),
            "tags": [t.lower() for t in tags],
            "description_tokens": self.tokenize(description),
            "full_text": f"{name} {category} {description} {' '.join(tags)}".lower(),
        }"""

new_build = """        # Pre-compute tokens to avoid O(N) list concatenation during search
        name_tokens = self.tokenize(name)
        description_tokens = self.tokenize(description)
        tags_lower = [t.lower() for t in tags]
        category_lower = category.lower()

        all_doc_tokens = name_tokens + tags_lower + description_tokens
        if category_lower:
            all_doc_tokens.append(category_lower)

        tag_text = f"{category_lower} {' '.join(tags_lower)}".strip()

        # Weighted components
        return {
            "name": name.lower(),
            "name_tokens": name_tokens,
            "category": category_lower,
            "tags": tags_lower,
            "tag_text": tag_text,
            "description_tokens": description_tokens,
            "all_doc_tokens": all_doc_tokens,
            "full_text": f"{name} {category} {description} {' '.join(tags)}".lower(),
        }"""
content = content.replace(old_build, new_build)

old_query = """        query_text = query_text.lower()
        results = []

        for skill, index_data in self._indexed_data:
            if valid_paths is not None and skill.get("local_path") not in valid_paths:
                continue
            score = self._calculate_score(query_text, index_data)
            if score >= threshold:
                results.append((skill, score))"""

new_query = """        query_text = query_text.lower()
        query_tokens = self.indexer.tokenize(query_text)
        results = []

        has_fuzz = fuzz is not None

        for skill, index_data in self._indexed_data:
            if valid_paths is not None and skill.get("local_path") not in valid_paths:
                continue

            full_text = index_data["full_text"]

            # Fast substring pass - if query is exactly in full_text, it's highly relevant
            if query_text in full_text:
                score = self._calculate_score(query_text, index_data)
                if score >= threshold:
                    results.append((skill, score))
                continue

            # Early relevance check
            if query_tokens and has_fuzz:
                max_token_match = 0
                all_doc_tokens = index_data.get("all_doc_tokens") or []

                # Check for fast substring matches first before fuzzing
                for qt in query_tokens:
                    if qt in full_text:
                        max_token_match = 100
                        break

                if max_token_match < 70:
                    for qt in query_tokens:
                        for dt in all_doc_tokens:
                            score = fuzz.ratio(qt, dt)
                            if score > max_token_match:
                                max_token_match = score
                            if max_token_match > 70:
                                break
                        if max_token_match > 70:
                            break

                if max_token_match < 65:
                    continue  # Score will be 0

            score = self._calculate_score(query_text, index_data)
            if score >= threshold:
                results.append((skill, score))"""
content = content.replace(old_query, new_query)

old_calc_1 = """        # Prevent completely irrelevant skills from surfacing due to random letter overlaps
        # by ensuring at least one query token matches a document token reasonably well.
        query_tokens = self.indexer.tokenize(query)
        if query_tokens:
            all_doc_tokens = (
                index_data.get("name_tokens", [])
                + index_data.get("tags", [])
                + index_data.get("description_tokens", [])
            )
            # Also include category as a token if present
            if index_data.get("category"):
                all_doc_tokens.append(index_data["category"])

            if all_doc_tokens:
                max_token_match = 0
                for qt in query_tokens:
                    # Exact substring match provides an immediate pass
                    if qt in index_data["full_text"]:
                        max_token_match = 100
                        break

                    for dt in all_doc_tokens:
                        score = fuzz.ratio(qt, dt)
                        if score > max_token_match:
                            max_token_match = score
                        if max_token_match > 70:
                            break
                    if max_token_match > 70:
                        break

                # If no query token has a decent match with any document token, it's irrelevant
                if max_token_match < 65:
                    return 0.0"""
content = content.replace(old_calc_1, "")

old_calc_2 = """        # 2. Tag/Category matches (medium priority)
        tag_score = 0
        if index_data["tags"] or index_data["category"]:
            tag_text = f"{index_data['category']} {' '.join(index_data['tags'])}"
            tag_score = fuzz.partial_ratio(query, tag_text)"""

new_calc_2 = """        # 2. Tag/Category matches (medium priority)
        tag_score = 0
        if index_data.get("tag_text"):
            tag_score = fuzz.partial_ratio(query, index_data["tag_text"])
        elif index_data["tags"] or index_data["category"]:
            tag_text = f"{index_data['category']} {' '.join(index_data['tags'])}"
            tag_score = fuzz.partial_ratio(query, tag_text)"""

content = content.replace(old_calc_2, new_calc_2)

with open("src/skill_manager/core/search.py", "w") as f:
    f.write(content)

from .entities import FilterState, Skill

MAIN_CATEGORY_ORDER = {
    "⚙️ System & Workflow": "1_⚙️ System & Workflow",
    "💻 Core Engineering & Technology": "2_💻 Core Engineering & Technology",
    "💼 Business & Operations": "3_💼 Business & Operations",
    "🧪 Quality & Data": "4_🧪 Quality & Data",
    "📚 Content & Knowledge": "5_📚 Content & Knowledge",
    "🎨 Specialized & Lifestyle": "6_🎨 Specialized & Lifestyle",
}


class FilterEngine:
    """Pure logic engine for filtering, sorting, and processing skill lists."""

    @staticmethod
    def get_main_category(skill: Skill) -> str:
        if skill.is_starred or skill.is_bundle or skill.is_command:
            return "Special"
        return skill.main_category or "⚙️ System & Workflow"

    @staticmethod
    def get_sub_category(skill: Skill) -> str:
        if skill.is_command:
            return skill.category or "Custom Commands"
        if skill.is_starred:
            return skill.category or "General"
        if skill.is_bundle:
            return "Collections"
        return skill.category or "General"

    @staticmethod
    def get_section(skill: Skill) -> str:
        return f"{FilterEngine.get_main_category(skill)}|{FilterEngine.get_sub_category(skill)}"

    @staticmethod
    def sort_key(skill: Skill) -> tuple[str, str]:
        if skill.is_command or skill.is_starred:
            return (f"0_Special|{skill.category or 'General'}", skill.name.lower())
        if skill.is_bundle:
            return ("0_Special|Collections", skill.name.lower())

        main_cat = skill.main_category or "⚙️ System & Workflow"
        sub_cat = skill.category or "General"
        name = skill.name.lower()
        order_prefix = MAIN_CATEGORY_ORDER.get(main_cat, f"99_{main_cat}")
        return (f"{order_prefix}|{sub_cat}", name)

    def filter_skills(self, all_skills: list[Skill], state: FilterState) -> list[Skill]:
        """Filters the raw skill list based on the provided FilterState."""
        filtered = []
        client_filter_lower = (
            state.client_filter.lower()
            if (state.client_filter and state.filter_by_client)
            else None
        )

        for skill in all_skills:
            if not state.show_archived and skill.is_archived:
                continue
            if state.collection_filter and not skill.is_bundle:
                continue
            if state.category_filter and skill.category != state.category_filter:
                continue

            if (
                state.project_filter
                and state.is_package_only is not True
                and skill.project_label != state.project_filter
            ):
                continue

            if not state.show_commands and skill.is_command:
                continue
            if not state.show_starred and skill.is_starred:
                continue

            if state.is_package_only is True and not skill.is_package:
                continue
            if state.is_package_only is False and skill.is_package:
                continue

            if client_filter_lower and skill.client and skill.client.lower() != client_filter_lower:
                continue

            filtered.append(skill)
        return filtered

    def prepare_rows(self, skills: list[Skill]) -> list[Skill]:
        """Enriches skill objects with UI-specific metadata like sections and group boundaries."""
        previous_section = None
        for skill in skills:
            main_cat = self.get_main_category(skill)
            sub_cat = self.get_sub_category(skill)
            section = f"{main_cat}|{sub_cat}"

            skill._main_category_name = main_cat
            skill._sub_category_name = sub_cat
            skill._section_name = section
            skill._is_first_in_subcategory = section != previous_section
            previous_section = section
        return skills

    def build_visible_rows(
        self, skills: list[Skill], collapsed_categories: set[str]
    ) -> list[Skill]:
        """Computes the subset of skills that should be visible based on expansion/collapse state."""
        visible = []
        seen_main = set()
        seen_section = set()

        for skill in skills:
            main_cat = skill._main_category_name or self.get_main_category(skill)
            section = skill._section_name or self.get_section(skill)

            if main_cat in collapsed_categories:
                if main_cat not in seen_main:
                    visible.append(skill)
                    seen_main.add(main_cat)
                continue

            seen_main.add(main_cat)
            if section in collapsed_categories:
                if section not in seen_section:
                    visible.append(skill)
                    seen_section.add(section)
                continue

            visible.append(skill)
            seen_section.add(section)
        return visible

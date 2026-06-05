from dataclasses import dataclass, field
from typing import Any

from skill_manager.core.schemas import SkillRecord


@dataclass
class Skill:
    """Represents a single skill or command entity."""

    name: str = ""
    category: str = "General"
    description: str = ""
    local_path: str = ""
    project_label: str = ""
    project_path: str = ""
    project_root: str = ""
    skill_md_path: str = ""
    is_starred: bool = False
    is_archived: bool = False
    is_bundle: bool = False
    is_command: bool = False
    is_package: bool = False
    raw_content: str = ""
    body_content: str = ""
    risk: str = "Unknown"
    source: str = "Unknown"
    date: str = "Unknown"
    client: str = ""
    main_category: str = "⚙️ System & Workflow"

    # Internal UI/Sorting flags
    _section_name: str | None = None
    _main_category_name: str | None = None
    _sub_category_name: str | None = None
    _is_first_in_subcategory: bool = False

    def get(self, key: str, default: Any = None) -> Any:
        """Compatibility method for dictionary-like access."""
        return getattr(self, key, default)

    def __getitem__(self, key: str) -> Any:
        """Compatibility method for dictionary-like access."""
        if hasattr(self, key):
            return getattr(self, key)
        raise KeyError(key)

    def __setitem__(self, key: str, value: Any):
        """Compatibility method for dictionary-like access."""
        if hasattr(self, key):
            setattr(self, key, value)
        else:
            raise KeyError(key)

    def __contains__(self, key: str) -> bool:
        """Compatibility method for dictionary-like access."""
        return hasattr(self, key)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Skill":
        """Factory method to create a Skill from a raw dictionary."""
        record = SkillRecord.model_validate(data)
        data = record.model_dump()
        # Handle some legacy key mappings
        is_package = data.get("is_package", data.get("is_source", False))

        return cls(
            name=str(data.get("name", "")),
            category=data.get("category", "General"),
            description=data.get("description", ""),
            local_path=data.get("local_path", ""),
            project_label=data.get("project_label", ""),
            project_path=data.get("project_path", ""),
            project_root=data.get("project_root", ""),
            skill_md_path=data.get("skill_md_path", ""),
            is_starred=data.get("is_starred", False),
            is_archived=data.get("is_archived", False),
            is_bundle=data.get("is_bundle", False),
            is_command=data.get("is_command", False),
            is_package=is_package,
            raw_content=data.get("raw_content", ""),
            body_content=data.get("body_content", ""),
            risk=data.get("risk", "Unknown"),
            source=data.get("source", "Unknown"),
            date=data.get("date", "Unknown"),
            client=data.get("client", ""),
            main_category=data.get("main_category", "⚙️ System & Workflow"),
        )


@dataclass
class FilterState:
    """Represents the current filtering and view state."""

    filter_text: str = ""
    show_archived: bool = False
    category_filter: str = ""
    collection_filter: bool = False
    project_filter: str = ""
    client_filter: str = ""
    filter_by_client: bool = True
    show_commands: bool = True
    show_starred: bool = True
    is_package_only: bool | None = None  # None = All, True = Packages, False = Projects
    collapsed_categories: set[str] = field(default_factory=set)

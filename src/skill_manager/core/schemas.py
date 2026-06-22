from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_MAIN_CATEGORY = "⚙️ System & Workflow"


class SkillMetadata(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str = ""
    description: str | list[Any] = ""
    category: str = ""
    type: str = ""
    risk: str = "Unknown"
    source: str = "Unknown"
    date: str = "Unknown"
    date_added: str = "Unknown"
    starred: bool = False
    essential: bool = False
    tags: list[str] | str = Field(default_factory=list)

    @field_validator("tags", mode="before")
    @classmethod
    def _coerce_tags(cls, value: Any) -> list[str] | str:
        if value is None:
            return []
        return value


class SkillRecord(BaseModel):
    model_config = ConfigDict(extra="allow")

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
    main_category: str = DEFAULT_MAIN_CATEGORY
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("name", "category", "description", "local_path", mode="before")
    @classmethod
    def _coerce_string_fields(cls, value: Any) -> str:
        if value is None:
            return ""
        return str(value)


class ShortcutConfig(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    search: str = "Ctrl+F"
    copy_: str = Field(default="Ctrl+C", alias="copy")
    archive: str = "Ctrl+Shift+X"
    delete: str = "Delete"
    refresh: str = "F5"
    expand_all: str = "Ctrl+E"
    collapse_all: str = "Ctrl+Shift+E"
    top_of_list: str = "Home"
    clear_selection: str = "Esc"
    theme_toggle: str = "Ctrl+T"
    quick_copy_view: str = "Alt+1"
    library_view: str = "Alt+2"
    updates_view: str = "Alt+3"
    settings_view: str = "Alt+4"


class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(extra="allow", env_prefix="SKILL_MANAGER_")

    sources: list[str] = Field(default_factory=list)
    projects: list[str] = Field(default_factory=list)
    project_aliases: dict[str, str] = Field(default_factory=dict)
    shortcuts: dict[str, str] = Field(default_factory=dict)
    scroll_speed_multiplier: float = 1.0
    show_menu_icons: bool = True
    compact_menu: bool = False
    auto_check_updates: bool = True
    auto_download_updates: bool = False
    update_check_interval_hours: int = 24
    skill_package_auto_update: bool = True
    skill_package_auto_update_mode: str = "prompt"

    @field_validator("project_aliases", "shortcuts", mode="before")
    @classmethod
    def _dict_or_empty(cls, value: Any) -> dict[str, Any]:
        return value if isinstance(value, dict) else {}

    @classmethod
    def from_legacy(cls, data: dict[str, Any]) -> AppConfig:
        migrated = dict(data or {})
        if "targets" in migrated and "projects" not in migrated:
            migrated["projects"] = migrated.pop("targets")
        else:
            migrated.pop("targets", None)
        if "target_aliases" in migrated and "project_aliases" not in migrated:
            migrated["project_aliases"] = migrated.pop("target_aliases")
        else:
            migrated.pop("target_aliases", None)
        return cls(**migrated)


class PackageConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str = ""
    path: str = ""
    update_command: str | list[str] = ""
    enabled: bool = True


class CacheState(BaseModel):
    model_config = ConfigDict(extra="allow")

    skills: list[SkillRecord] = Field(default_factory=list)
    projects: list[dict[str, Any]] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    project_labels: list[str] = Field(default_factory=list)
    status: str = ""

    @field_validator("skills", mode="before")
    @classmethod
    def _validate_skills(cls, value: Any) -> list[Any]:
        if not isinstance(value, list):
            return []
        validated = []
        for item in value:
            if isinstance(item, dict):
                validated.append(SkillRecord.model_validate(item))
            elif isinstance(item, SkillRecord):
                validated.append(item)
        return validated

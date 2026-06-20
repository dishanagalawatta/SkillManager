from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_MAIN_CATEGORY = "⚙️ System & Workflow"


class SkillMetadata(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str = ""
    description: str = ""
    category: str = ""
    type: str = ""
    risk: str = "Unknown"
    source: str = "Unknown"
    date: str = "Unknown"
    date_added: str = "Unknown"
    starred: bool = False
    essential: bool = False
    tags: list[str] = Field(default_factory=list)

    @field_validator("tags", mode="before")
    @classmethod
    def _coerce_tags(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [tag.strip() for tag in value.split(",") if tag.strip()]
        if isinstance(value, list):
            return [str(v) for v in value if v]
        return []

    @field_validator("description", mode="before")
    @classmethod
    def _coerce_description(cls, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, list):
            return "\n".join(str(v) for v in value)
        return str(value)


class SkillRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str = Field(..., min_length=1)
    local_path: str = Field(..., min_length=1)
    category: str = "General"
    description: str = ""
    project_label: str = ""
    project_path: str = ""
    project_root: str = ""
    skill_md_path: str = ""
    is_starred: bool = False
    is_archived: bool = False
    is_bundle: bool = False
    is_command: bool = False
    is_package: bool = False
    is_screenshot: bool = False
    raw_content: str = ""
    body_content: str = ""
    risk: str = "Unknown"
    source: str = "Unknown"
    date: str = "Unknown"
    client: str = ""
    main_category: str = DEFAULT_MAIN_CATEGORY
    metadata: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)

    @field_validator("name", "category", "local_path", mode="before")
    @classmethod
    def _coerce_string_fields(cls, value: Any) -> str:
        if value is None:
            return ""
        return str(value).strip()

    @field_validator("description", mode="before")
    @classmethod
    def _coerce_description(cls, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, list):
            return "\n".join(str(v) for v in value)
        return str(value)

    @field_validator("tags", mode="before")
    @classmethod
    def _coerce_tags(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [tag.strip() for tag in value.split(",") if tag.strip()]
        if isinstance(value, list):
            return [str(v) for v in value if v]
        return []


class ShortcutConfig(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

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


class CollectionConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    paths: list[str] = Field(default_factory=list)
    projects: list[str] = Field(default_factory=list)
    shortcut: str = ""
    shortcut_enabled: bool = True


class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(extra="allow", env_prefix="SKILL_MANAGER_")

    sources: list[str] = Field(default_factory=list)
    projects: list[str] = Field(default_factory=list)
    project_aliases: dict[str, str] = Field(default_factory=dict)
    shortcuts: dict[str, str] = Field(default_factory=dict)
    scroll_speed_multiplier: float = Field(default=1.0, ge=0.1, le=10.0)
    skill_package_auto_update_mode: str = "prompt"
    auto_minimize_on_screenshot: bool = False
    auto_minimize_on_quick_copy: bool = False
    temporary_screenshots: bool = False
    diagnostic_logging: bool = False
    top_bar_clients: list[str] = Field(
        default_factory=lambda: ["Plain Text", "Gemini CLI", "Antigravity", "Codex"]
    )

    @field_validator("project_aliases", "shortcuts", mode="before")
    @classmethod
    def _dict_or_empty(cls, value: Any) -> dict[str, Any]:
        return value if isinstance(value, dict) else {}

    @field_validator("skill_package_auto_update_mode")
    @classmethod
    def _validate_update_mode(cls, value: str) -> str:
        allowed = {"off", "prompt", "silent"}
        if value not in allowed:
            return "prompt"
        return value

    @field_validator("scroll_speed_multiplier", mode="before")
    @classmethod
    def _coerce_float(cls, value: Any) -> float:
        try:
            return float(value)
        except (ValueError, TypeError):
            return 1.0

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
    model_config = ConfigDict(extra="ignore")

    id: str = ""
    path: str = ""
    update_command: str | list[str] = ""
    enabled: bool = True


class UpdatePackageRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str = ""
    source_type: str = "npx"  # git, npx, local, custom
    package_name: str = ""
    package_id: str = ""
    package_path: str = ""
    resolved_package_path: str = ""
    local_path: str = ""
    last_updated: str = "Never"
    is_updating: bool = False
    just_finished: bool = False
    current_version: str = ""
    latest_version: str = ""
    storage_mode: str = "individual"  # individual, grouped
    managed_folders: list[str] = Field(default_factory=list)
    removed_folders: list[str] = Field(default_factory=list)
    updated_folders: list[str] = Field(default_factory=list)
    removals_verified: bool = False

    @field_validator("name", mode="before")
    @classmethod
    def _coerce_name(cls, value: Any) -> str:
        return str(value or "").strip()


class Redaction(BaseModel):
    model_config = ConfigDict(extra="ignore")
    x: int = Field(..., ge=0)
    y: int = Field(..., ge=0)
    width: int = Field(..., gt=0)
    height: int = Field(..., gt=0)


class AnnotationPoint(BaseModel):
    model_config = ConfigDict(extra="ignore")
    x: float
    y: float


class BaseAnnotation(BaseModel):
    model_config = ConfigDict(extra="ignore")
    color: str = "#FF0000"
    strokeWidth: int = 3


class RectAnnotation(BaseAnnotation):
    type: Literal["rect"] = "rect"
    x: float
    y: float
    width: float
    height: float


class ArrowAnnotation(BaseAnnotation):
    type: Literal["arrow"] = "arrow"
    x1: float
    y1: float
    x2: float
    y2: float


class FilledRectAnnotation(BaseAnnotation):
    type: Literal["filledRect", "redact"] = "filledRect"
    x: float
    y: float
    width: float
    height: float
    color: str = "#000000"


# Backward compatibility alias
RedactAnnotation = FilledRectAnnotation


class FreehandAnnotation(BaseAnnotation):
    type: Literal["freehand"] = "freehand"
    points: list[AnnotationPoint] = Field(..., min_length=2)


class EllipseAnnotation(BaseAnnotation):
    type: Literal["ellipse"] = "ellipse"
    x: float
    y: float
    width: float
    height: float


class FilledEllipseAnnotation(BaseAnnotation):
    type: Literal["filledEllipse"] = "filledEllipse"
    x: float
    y: float
    width: float
    height: float
    color: str = "#000000"


class TextAnnotation(BaseAnnotation):
    type: Literal["text"] = "text"
    x: float
    y: float
    text: str = Field(..., min_length=1)
    fontSize: int = 16
    fontFamily: str = "Segoe UI"


class HighlightAnnotation(BaseAnnotation):
    type: Literal["highlight"] = "highlight"
    x: float
    y: float
    width: float
    height: float
    color: str = "#FFFF00"


# Discriminated union for validation.
#
# The ``type`` field is the discriminator — it lives on each
# annotation subclass as a ``Literal[...]`` (e.g. ``"rect"``,
# ``"arrow"``) and is intentionally *not* declared on the
# ``BaseAnnotation`` base class. This keeps each subclass' ``type``
# field independent (no mutable-class-attribute override), so pyright
# no longer rejects the discriminator narrowing with
# ``reportIncompatibleVariableOverride``. ``Field(discriminator=...)``
# tells Pydantic to validate by inspecting the discriminator value
# first, avoiding a left-to-right trial of every union member.
Annotation = Annotated[
    RectAnnotation
    | ArrowAnnotation
    | FilledRectAnnotation
    | FreehandAnnotation
    | TextAnnotation
    | HighlightAnnotation
    | EllipseAnnotation
    | FilledEllipseAnnotation,
    Field(discriminator="type"),
]


class AppUpdateState(BaseModel):
    model_config = ConfigDict(extra="ignore")
    is_checking: bool = False
    update_available: bool = False
    has_checked: bool = False
    current_version: str = ""
    latest_version: str = ""
    error: str | None = None


class ScreenshotParams(BaseModel):
    model_config = ConfigDict(extra="ignore")
    crop_x: int = Field(..., ge=0)
    crop_y: int = Field(..., ge=0)
    crop_width: int = Field(..., gt=0)
    crop_height: int = Field(..., gt=0)
    redactions: list[Redaction] = Field(default_factory=list)


class UIStateRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")
    window_width: int = Field(default=1300, ge=1050)
    window_height: int = Field(default=650, ge=650)
    window_x: int = 100
    window_y: int = 100
    dark_mode: bool = False
    current_view: str = "Library"
    startup_view: str = "Library"
    remember_filters: bool = True
    reduced_motion: bool = False
    compact_list_rows: bool = False
    inspector_width: int = Field(default=0, ge=0)


class CacheState(BaseModel):
    model_config = ConfigDict(extra="ignore")

    skills: list[SkillRecord] = Field(default_factory=list)
    projects: list[dict[str, Any]] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    project_labels: list[str] = Field(default_factory=list)
    status: str = ""

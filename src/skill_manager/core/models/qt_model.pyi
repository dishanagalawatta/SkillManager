from typing import Any, ClassVar

from PySide6.QtCore import (
    QAbstractListModel,
    QByteArray,
    QModelIndex,
    QPersistentModelIndex,
    Qt,
    Signal,
    Slot,
)

from skill_manager.core.models.entities import FilterState, Skill
from skill_manager.core.models.filter_engine import FilterEngine
from skill_manager.core.search import SearchEngine

class SkillModel(QAbstractListModel):
    """
    Qt List Model for skills, delegating logic to FilterEngine.

    Type stub override for PySide6 6.11.0: the runtime ``@Property`` /
    ``@propname.setter`` pattern produces a ``Property`` instance as a
    class attribute, which the PySide6 stub types as opaque (no
    settable surface). This file re-declares the writable properties
    as plain instance attributes so callers can assign to them
    (``model.showArchived = True``) without triggering false-positive
    ``reportAttributeAccessIssue`` errors. Runtime behavior is
    unchanged — the actual ``@Property`` descriptors in ``qt_model.py``
    still fire.
    """

    # Role constants
    NameRole: ClassVar[int]
    CategoryRole: ClassVar[int]
    DescriptionRole: ClassVar[int]
    PathRole: ClassVar[int]
    ProjectRole: ClassVar[int]
    IsStarredRole: ClassVar[int]
    IsSelectedRole: ClassVar[int]
    SearchTextRole: ClassVar[int]
    IsArchivedRole: ClassVar[int]
    IsCollectionRole: ClassVar[int]
    SectionRole: ClassVar[int]
    RawContentRole: ClassVar[int]
    BodyContentRole: ClassVar[int]
    RiskRole: ClassVar[int]
    SourceRole: ClassVar[int]
    DateRole: ClassVar[int]
    IsCollapsedRole: ClassVar[int]
    IsCommandRole: ClassVar[int]
    ClientRole: ClassVar[int]
    MainCategoryNameRole: ClassVar[int]
    IsFirstInSubcategoryRole: ClassVar[int]
    IsMainCollapsedRole: ClassVar[int]
    IsSubCollapsedRole: ClassVar[int]
    SubCategoryNameRole: ClassVar[int]
    IsPackageRole: ClassVar[int]
    IsScreenshotRole: ClassVar[int]

    # Signals
    filterChanged: ClassVar[Signal]
    showArchivedChanged: ClassVar[Signal]
    categoryFilterChanged: ClassVar[Signal]
    collectionFilterChanged: ClassVar[Signal]
    projectFilterChanged: ClassVar[Signal]
    selectionStateChanged: ClassVar[Signal]
    collapsedCategoriesChanged: ClassVar[Signal]
    showCommandsChanged: ClassVar[Signal]
    showStarredChanged: ClassVar[Signal]
    isPackageOnlyChanged: ClassVar[Signal]
    clientFilterChanged: ClassVar[Signal]
    filterByClientChanged: ClassVar[Signal]
    totalSelectableCountChanged: ClassVar[Signal]

    # Writable properties (have @propname.setter in qt_model.py)
    filterText: str
    showArchived: bool
    categoryFilter: str
    collectionFilter: bool
    projectFilter: str
    clientFilter: str
    filterByClient: bool
    showCommands: bool
    showStarred: bool
    isPackageOnly: Qt.CheckState

    # Read-only properties (no setter in qt_model.py)
    selectedCount: int
    visibleSelectableCount: int
    visibleSelectedCount: int
    totalSelectableCount: int
    collapsedCategories: list[str]
    isAllExpanded: bool

    # Internal state accessed by tests / internal helpers
    _all_skills: list[Skill]
    _all_filtered_skills: list[Skill]
    _filtered_skills: list[Skill]
    _config: Any
    _search_engine: SearchEngine | None
    _selected_ids: dict[str, None]
    _engine: FilterEngine
    _state: FilterState
    _suppress_layout: bool
    _batch_apply_needed: bool
    _selections_by_project: dict[str, list[str]]
    _collapse_save_timer: Any
    _project_selections_save_timer: Any
    _cached_selected_count: int
    _cached_visible_selectable: int
    _cached_visible_selected: int
    _cached_total_selectable: int

    def __init__(self, parent: Any = ..., config: Any = ...) -> None: ...
    def rowCount(self, parent: QModelIndex | QPersistentModelIndex = ...) -> int: ...
    def data(self, index: QModelIndex | QPersistentModelIndex, role: int = ...) -> Any: ...
    def roleNames(self) -> dict[int, QByteArray]: ...

    # Slots & public methods
    @Slot(int)
    def toggleSelection(self, row: int) -> None: ...
    @Slot()
    def clearSelection(self) -> None: ...
    @Slot()
    def selectAll(self) -> None: ...
    @Slot(result=list)
    def getSelectedPaths(self) -> list[str]: ...
    @Slot(result=list)
    def getFilteredSelectedPaths(self) -> list[str]: ...
    @Slot(list)
    def selectByPaths(self, paths: list[str]) -> None: ...
    def removeSkillsByPath(self, paths: list[str]) -> None: ...
    def updateSkillProperty(self, path: str, key: str, value: Any) -> bool: ...
    def _apply_filter(self, reset: bool = ...) -> None: ...
    def _begin_batch(self) -> None: ...
    def _end_batch(self) -> None: ...
    def _execute_filter_logic(self) -> list[Skill]: ...
    def _is_main_collapsed(self, skill: Skill) -> bool: ...
    def _is_sub_collapsed(self, skill: Skill) -> bool: ...
    def _emit_selection_data_changed(self) -> None: ...
    def _update_selection_counts(self) -> None: ...
    @Slot(int, result=dict)
    def get_skill_at(self, row: int) -> dict[str, Any]: ...
    @Slot(list)
    def setSkills(self, skills: list[dict[str, Any]]) -> None: ...
    @Slot(list)
    def addOrUpdateSkills(self, new_skills: list[dict[str, Any]]) -> None: ...
    @Slot(int, bool)
    def setSelected(self, row: int, selected: bool) -> None: ...
    @Slot()
    def toggleAll(self) -> None: ...
    @Slot(str)
    def toggleCategory(self, name: str) -> None: ...
    @Slot()
    def expandAll(self) -> None: ...
    @Slot()
    def collapseAll(self) -> None: ...
    def _rebuild_visible_rows(self) -> None: ...
    @Slot(str, result=bool)
    def isCategoryCollapsed(self, name: str) -> bool: ...
    def _save_collapsed(self) -> None: ...
    def _do_save_collapsed(self) -> None: ...
    def _save_project_selections(self) -> None: ...
    def _do_save_project_selections(self) -> None: ...
    def _save_filters(self) -> None: ...

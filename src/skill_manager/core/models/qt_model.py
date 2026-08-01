import logging
import os
from typing import Any

from PySide6.QtCore import (
    Property,
    QAbstractListModel,
    QByteArray,
    QModelIndex,
    QPersistentModelIndex,
    Qt,
    QTimer,
)

from skill_manager.core.models.collapse import CollapseMixin
from skill_manager.core.models.entities import FilterState, Skill
from skill_manager.core.models.filter_engine import FilterEngine
from skill_manager.core.models.incubation import IncubationMixin
from skill_manager.core.models.ingest import IngestMixin
from skill_manager.core.models.pipeline import PipelineMixin
from skill_manager.core.models.roles import (
    BodyContentRole,
    CategoryRole,
    ClientRole,
    DateRole,
    DescriptionRole,
    EmojiRole,
    IsArchivedRole,
    IsCollapsedRole,
    IsCollectionRole,
    IsCommandRole,
    IsFirstInSubcategoryRole,
    IsMainCollapsedRole,
    IsPackageRole,
    IsScreenshotRole,
    IsSelectedRole,
    IsStarredRole,
    IsSubCollapsedRole,
    MainCategoryNameRole,
    NameRole,
    PathRole,
    ProjectRole,
    RawContentRole,
    RiskRole,
    RolesMixin,
    SearchTextRole,
    SectionRole,
    SourceRole,
    SubCategoryNameRole,
)
from skill_manager.core.models.selection import SelectionMixin

# Signal aliases for the ``@Property(notify=...)`` decorators on the
# facade's filter properties. The declarations themselves live on
# ``RolesMixin`` (imported above) and are inherited by ``SkillModel``;
# these module-level names only give the class body something to
# reference at definition time.
filterChanged = RolesMixin.filterChanged  # noqa: N816
showArchivedChanged = RolesMixin.showArchivedChanged  # noqa: N816
categoryFilterChanged = RolesMixin.categoryFilterChanged  # noqa: N816
collectionFilterChanged = RolesMixin.collectionFilterChanged  # noqa: N816
projectFilterChanged = RolesMixin.projectFilterChanged  # noqa: N816
clientFilterChanged = RolesMixin.clientFilterChanged  # noqa: N816
filterByClientChanged = RolesMixin.filterByClientChanged  # noqa: N816
showCommandsChanged = RolesMixin.showCommandsChanged  # noqa: N816
showStarredChanged = RolesMixin.showStarredChanged  # noqa: N816
isPackageOnlyChanged = RolesMixin.isPackageOnlyChanged  # noqa: N816

logger = logging.getLogger(__name__)


class SkillModel(
    RolesMixin,
    SelectionMixin,
    PipelineMixin,
    IncubationMixin,
    CollapseMixin,
    IngestMixin,
    QAbstractListModel,
):
    """
    Qt List Model for skills, delegating logic to FilterEngine.

    Facade class: role constants and signals live in ``RolesMixin``,
    selection in ``SelectionMixin``, the filter pipeline in
    ``PipelineMixin``, incubation coordination in ``IncubationMixin``,
    collapse/expansion in ``CollapseMixin``, and ingestion in
    ``IngestMixin`` — composed before ``QAbstractListModel`` so the Qt
    metaobject registers their slots/properties/signals on this class.
    """

    def __init__(self, parent=None, config=None):
        super().__init__(parent)
        self._all_skills: list[Skill] = []
        self._all_filtered_skills: list[Skill] = []
        self._filtered_skills: list[Skill] = []
        self._config = config
        self._search_engine = None
        self._selected_ids: dict[str, None] = {}
        self._engine = FilterEngine()
        self.state = FilterState()
        self._suppress_layout = False
        self._batch_apply_needed = False
        self._selections_by_project: dict[str, list[str]] = {}
        self._project_selections_save_timer = None
        self._collapse_save_timer = None
        self._cached_selected_count = 0
        self._cached_visible_selectable = 0
        self._cached_visible_selected = 0
        self._cached_total_selectable = 0

        # Incubation coordination: when the model is being mutated while
        # QML delegates are still being instantiated, deferring the
        # layout-changing signals avoids the "Object destroyed during
        # incubation" runtime warning. See onIncubationReady() and
        # _force_end_incubation() for the protocol details.
        self._pending_signals: list[Any] = []
        self._replay_deferred = False
        self._incubating = False
        self._reset_pending = False
        self._prepared_generation: int = -1
        self._incubation_timer = QTimer(self)
        self._incubation_timer.setSingleShot(True)
        self._incubation_timer.setInterval(5000)  # 5s safety window
        self._incubation_timer.timeout.connect(self._force_end_incubation)

        self._filter_debounce_timer = QTimer(self)
        self._filter_debounce_timer.setSingleShot(True)
        self._filter_debounce_timer.setInterval(50)  # 50ms search debounce
        self._filter_debounce_timer.timeout.connect(self._apply_filter)

        if self._config:
            self.state.collapsed_categories = set(self._config.get("collapsed_categories", []))
            self.state.show_archived = self._config.get("show_archived", False)
            self.state.category_filter = self._config.get("category_filter", "")
            self.state.collection_filter = self._config.get("collection_filter", False)
            self.state.project_filter = self._config.get("project_filter", "")
            self.state.client_filter = self._config.get("client_format", "")
            self.state.show_commands = self._config.get("show_commands", True)
            self.state.show_starred = self._config.get("show_starred", True)
            self.state.is_package_only = self._config.get(
                "is_package_only", self._config.get("is_source_only", None)
            )
            raw = self._config.get("project_selections", {})
            if raw:
                self._selections_by_project = {k: list(v) for k, v in raw.items()}
            initial_project = self.state.project_filter
            if initial_project and initial_project in self._selections_by_project:
                self._selected_ids = dict.fromkeys(self._selections_by_project[initial_project])

    def rowCount(self, parent: QModelIndex | QPersistentModelIndex = QModelIndex()) -> int:  # noqa: ARG002
        return len(self._filtered_skills)

    def data(
        self,
        index: QModelIndex | QPersistentModelIndex,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if not index.isValid() or index.row() >= len(self._filtered_skills):
            return None

        skill = self._filtered_skills[index.row()]
        path = skill.local_path

        if role == self.NameRole:
            return skill.name
        if role == self.CategoryRole:
            return skill.category
        if role == self.DescriptionRole:
            return skill.description
        if role == self.PathRole:
            return path
        if role == self.ProjectRole:
            return skill.project_label
        if role == self.IsStarredRole:
            return skill.is_starred
        if role == self.IsSelectedRole:
            return path in self._selected_ids
        if role == self.IsArchivedRole:
            return skill.is_archived
        if role == self.IsCollectionRole:
            return skill.is_bundle
        if role == self.SectionRole:
            return skill.section_name or self._engine.get_section(skill)
        if role == self.MainCategoryNameRole:
            return skill.main_category_name or self._engine.get_main_category(skill)
        if role == self.RawContentRole:
            return skill.raw_content
        if role == self.BodyContentRole:
            return skill.body_content
        if role == self.RiskRole:
            return skill.risk
        if role == self.SourceRole:
            return skill.source
        if role == self.DateRole:
            return skill.date
        if role == self.IsCollapsedRole:
            return self._is_main_collapsed(skill) or self._is_sub_collapsed(skill)
        if role == self.IsCommandRole:
            return skill.is_command
        if role == self.ClientRole:
            return skill.client
        if role == self.IsFirstInSubcategoryRole:
            return skill.is_first_in_subcategory
        if role == self.IsMainCollapsedRole:
            return self._is_main_collapsed(skill)
        if role == self.IsSubCollapsedRole:
            return self._is_sub_collapsed(skill)
        if role == self.SubCategoryNameRole:
            return skill.sub_category_name or self._engine.get_sub_category(skill)
        if role == self.IsPackageRole:
            return skill.is_package
        if role == self.IsScreenshotRole:
            return skill.is_screenshot
        if role == self.EmojiRole:
            if not skill.is_command:
                return None
            if self._config is None:
                return "⚡"
            return self._config.get_command_emoji(skill.local_path)

        return None

    def roleNames(self) -> dict[int, QByteArray]:
        return {
            NameRole: QByteArray(b"name"),
            CategoryRole: QByteArray(b"category"),
            DescriptionRole: QByteArray(b"description"),
            PathRole: QByteArray(b"path"),
            ProjectRole: QByteArray(b"project"),
            IsStarredRole: QByteArray(b"isStarred"),
            IsSelectedRole: QByteArray(b"isSelected"),
            SearchTextRole: QByteArray(b"searchText"),
            IsArchivedRole: QByteArray(b"isArchived"),
            IsCollectionRole: QByteArray(b"isCollection"),
            SectionRole: QByteArray(b"sectionName"),
            RawContentRole: QByteArray(b"rawContent"),
            BodyContentRole: QByteArray(b"bodyContent"),
            RiskRole: QByteArray(b"risk"),
            SourceRole: QByteArray(b"source"),
            MainCategoryNameRole: QByteArray(b"mainCategoryName"),
            DateRole: QByteArray(b"date"),
            IsCollapsedRole: QByteArray(b"isCollapsed"),
            IsCommandRole: QByteArray(b"isCommand"),
            ClientRole: QByteArray(b"client"),
            IsFirstInSubcategoryRole: QByteArray(b"isFirstInSubcategory"),
            IsMainCollapsedRole: QByteArray(b"isMainCollapsed"),
            IsSubCollapsedRole: QByteArray(b"isSubCollapsed"),
            SubCategoryNameRole: QByteArray(b"subCategoryName"),
            IsPackageRole: QByteArray(b"isPackage"),
            IsScreenshotRole: QByteArray(b"isScreenshot"),
            EmojiRole: QByteArray(b"emoji"),
        }

    # Properties
    @Property(str, notify=filterChanged)
    def filterText(self):  # type: ignore[reportRedeclaration]
        return self.state.filter_text

    @filterText.setter  # type: ignore[func-attr]
    def filterText(self, value):
        if self.state.filter_text != value:
            self.state.filter_text = value
            self.filterChanged.emit()
            if os.environ.get("SKILL_MANAGER_TESTING") == "1":
                self._apply_filter()
            else:
                self._filter_debounce_timer.start()

    @Property(bool, notify=showArchivedChanged)
    def showArchived(self):  # type: ignore[reportRedeclaration]
        return self.state.show_archived

    @showArchived.setter  # type: ignore[func-attr]
    def showArchived(self, value):
        if self.state.show_archived != value:
            self.state.show_archived = value
            self._apply_filter()
            self._save_filters()
            self.showArchivedChanged.emit()

    @Property(str, notify=categoryFilterChanged)
    def categoryFilter(self):  # type: ignore[reportRedeclaration]
        return self.state.category_filter

    @categoryFilter.setter  # type: ignore[func-attr]
    def categoryFilter(self, value):
        if self.state.category_filter != value:
            self.state.category_filter = value
            self._apply_filter()
            self._save_filters()
            self.categoryFilterChanged.emit()

    @Property(bool, notify=collectionFilterChanged)
    def collectionFilter(self):  # type: ignore[reportRedeclaration]
        return self.state.collection_filter

    @collectionFilter.setter  # type: ignore[func-attr]
    def collectionFilter(self, value):
        if self.state.collection_filter != value:
            self.state.collection_filter = value
            self._apply_filter()
            self._save_filters()
            self.collectionFilterChanged.emit()

    @Property(str, notify=projectFilterChanged)
    def projectFilter(self):  # type: ignore[reportRedeclaration]
        return self.state.project_filter

    @projectFilter.setter  # type: ignore[func-attr]
    def projectFilter(self, value):
        if self.state.project_filter != value:
            old_project = self.state.project_filter
            self._swap_project_selection(old_project, value)
            self.state.project_filter = value
            self._apply_filter()
            self._save_filters()
            self._save_project_selections()
            self.projectFilterChanged.emit()

    @Property(str, notify=clientFilterChanged)
    def clientFilter(self):  # type: ignore[reportRedeclaration]
        return self.state.client_filter

    @clientFilter.setter  # type: ignore[func-attr]
    def clientFilter(self, value):
        if self.state.client_filter != value:
            self.state.client_filter = value

            if self.state.filter_by_client:
                self._apply_filter()
            self._save_filters()
            self.clientFilterChanged.emit()

    @Property(bool, notify=filterByClientChanged)
    def filterByClient(self):  # type: ignore[reportRedeclaration]
        return self.state.filter_by_client

    @filterByClient.setter  # type: ignore[func-attr]
    def filterByClient(self, value):
        if self.state.filter_by_client != value:
            self.state.filter_by_client = value
            self._apply_filter()
            self.filterByClientChanged.emit()

    @Property(bool, notify=showCommandsChanged)
    def showCommands(self):  # type: ignore[reportRedeclaration]
        return self.state.show_commands

    @showCommands.setter  # type: ignore[func-attr]
    def showCommands(self, value):
        if self.state.show_commands != value:
            self.state.show_commands = value
            self._apply_filter()
            self._save_filters()
            self.showCommandsChanged.emit()

    @Property(bool, notify=showStarredChanged)
    def showStarred(self):  # type: ignore[reportRedeclaration]
        return self.state.show_starred

    @showStarred.setter  # type: ignore[func-attr]
    def showStarred(self, value):
        if self.state.show_starred != value:
            self.state.show_starred = value
            self._apply_filter()
            self._save_filters()
            self.showStarredChanged.emit()

    @Property(Qt.CheckState, notify=isPackageOnlyChanged)
    def isPackageOnly(self):  # type: ignore[reportRedeclaration]
        if self.state.is_package_only is None:
            return Qt.CheckState.PartiallyChecked
        return Qt.CheckState.Checked if self.state.is_package_only else Qt.CheckState.Unchecked

    @isPackageOnly.setter  # type: ignore[func-attr]
    def isPackageOnly(self, value):
        new_val = None
        if value == Qt.CheckState.Checked or value is True:
            new_val = True
        elif value == Qt.CheckState.Unchecked or value is False:
            new_val = False
        if self.state.is_package_only != new_val:
            self.state.is_package_only = new_val
            self._apply_filter()
            self._save_filters()
            self.isPackageOnlyChanged.emit()

    def _save_filters(self):
        if not self._config:
            return
        self._config.set_many(
            {
                "show_archived": self.state.show_archived,
                "category_filter": self.state.category_filter,
                "collection_filter": self.state.collection_filter,
                "project_filter": self.state.project_filter,
                "client_format": self.state.client_filter,
                "show_commands": self.state.show_commands,
                "show_starred": self.state.show_starred,
                "is_package_only": self.state.is_package_only,
                "is_source_only": self.state.is_package_only,
            }
        )

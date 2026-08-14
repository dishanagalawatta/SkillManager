"""Role constants, ``_ALL_ROLES``, and signal declarations for the SkillModel facade.

The composed ``SkillModel`` inherits every class attribute in
:class:`RolesMixin` via the MRO, so they are re-exported on the facade
class exactly as before the Phase 4 split. PySide6 registers the
``Signal()`` declarations in the facade's Qt metaobject when the
composed class is created (verified empirically in the Phase 4 gate
probe); mixins that need a signal in a ``@Property(notify=...)``
decorator import the corresponding module-level alias from this module.
"""

from PySide6.QtCore import Qt, Signal


class RolesMixin:
    """Qt roles and signals shared by every model subsystem."""

    aboutToMutateStructure = Signal()
    structureMutated = Signal()

    NameRole = Qt.ItemDataRole.UserRole + 1
    CategoryRole = Qt.ItemDataRole.UserRole + 2
    DescriptionRole = Qt.ItemDataRole.UserRole + 3
    PathRole = Qt.ItemDataRole.UserRole + 4
    ProjectRole = Qt.ItemDataRole.UserRole + 5
    IsStarredRole = Qt.ItemDataRole.UserRole + 6
    IsSelectedRole = Qt.ItemDataRole.UserRole + 7
    SearchTextRole = Qt.ItemDataRole.UserRole + 8
    IsArchivedRole = Qt.ItemDataRole.UserRole + 9
    IsCollectionRole = Qt.ItemDataRole.UserRole + 10
    SectionRole = Qt.ItemDataRole.UserRole + 11
    RawContentRole = Qt.ItemDataRole.UserRole + 12
    BodyContentRole = Qt.ItemDataRole.UserRole + 13
    RiskRole = Qt.ItemDataRole.UserRole + 14
    SourceRole = Qt.ItemDataRole.UserRole + 15
    DateRole = Qt.ItemDataRole.UserRole + 16
    IsCollapsedRole = Qt.ItemDataRole.UserRole + 17
    IsCommandRole = Qt.ItemDataRole.UserRole + 18
    ClientRole = Qt.ItemDataRole.UserRole + 19
    MainCategoryNameRole = Qt.ItemDataRole.UserRole + 20
    IsFirstInSubcategoryRole = Qt.ItemDataRole.UserRole + 21
    IsMainCollapsedRole = Qt.ItemDataRole.UserRole + 22
    IsSubCollapsedRole = Qt.ItemDataRole.UserRole + 23
    SubCategoryNameRole = Qt.ItemDataRole.UserRole + 24
    IsPackageRole = Qt.ItemDataRole.UserRole + 25
    IsSnapRole = Qt.ItemDataRole.UserRole + 26
    EmojiRole = Qt.ItemDataRole.UserRole + 27

    _ALL_ROLES = [
        NameRole,
        CategoryRole,
        DescriptionRole,
        PathRole,
        ProjectRole,
        IsStarredRole,
        IsSelectedRole,
        SearchTextRole,
        IsArchivedRole,
        IsCollectionRole,
        SectionRole,
        RawContentRole,
        BodyContentRole,
        RiskRole,
        SourceRole,
        DateRole,
        IsCollapsedRole,
        IsCommandRole,
        ClientRole,
        MainCategoryNameRole,
        IsFirstInSubcategoryRole,
        IsMainCollapsedRole,
        IsSubCollapsedRole,
        SubCategoryNameRole,
        IsPackageRole,
        IsSnapRole,
        EmojiRole,
    ]

    filterChanged = Signal()
    showArchivedChanged = Signal()
    categoryFilterChanged = Signal()
    collectionFilterChanged = Signal()
    projectFilterChanged = Signal()
    selectionStateChanged = Signal()
    collapsedCategoriesChanged = Signal()
    showCommandsChanged = Signal()
    showStarredChanged = Signal()
    isPackageOnlyChanged = Signal()
    clientFilterChanged = Signal()
    filterByClientChanged = Signal()
    totalSelectableCountChanged = Signal()
    incubatingChanged = Signal()


NameRole = RolesMixin.NameRole
CategoryRole = RolesMixin.CategoryRole
DescriptionRole = RolesMixin.DescriptionRole
PathRole = RolesMixin.PathRole
ProjectRole = RolesMixin.ProjectRole
IsStarredRole = RolesMixin.IsStarredRole
IsSelectedRole = RolesMixin.IsSelectedRole
SearchTextRole = RolesMixin.SearchTextRole
IsArchivedRole = RolesMixin.IsArchivedRole
IsCollectionRole = RolesMixin.IsCollectionRole
SectionRole = RolesMixin.SectionRole
RawContentRole = RolesMixin.RawContentRole
BodyContentRole = RolesMixin.BodyContentRole
RiskRole = RolesMixin.RiskRole
SourceRole = RolesMixin.SourceRole
DateRole = RolesMixin.DateRole
IsCollapsedRole = RolesMixin.IsCollapsedRole
IsCommandRole = RolesMixin.IsCommandRole
ClientRole = RolesMixin.ClientRole
MainCategoryNameRole = RolesMixin.MainCategoryNameRole
IsFirstInSubcategoryRole = RolesMixin.IsFirstInSubcategoryRole
IsMainCollapsedRole = RolesMixin.IsMainCollapsedRole
IsSubCollapsedRole = RolesMixin.IsSubCollapsedRole
SubCategoryNameRole = RolesMixin.SubCategoryNameRole
IsPackageRole = RolesMixin.IsPackageRole
IsSnapRole = RolesMixin.IsSnapRole
EmojiRole = RolesMixin.EmojiRole
_ALL_ROLES = list(RolesMixin._ALL_ROLES)

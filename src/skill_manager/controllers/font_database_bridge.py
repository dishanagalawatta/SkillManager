"""
Purpose: QObject bridge that exposes QFontDatabase data to QML.
Provides font families, styles, sizes, and properties for the custom font picker.
"""

from PySide6.QtCore import Property, QObject, Signal, Slot
from PySide6.QtGui import QFont, QFontDatabase


class FontDatabaseBridge(QObject):
    """Exposes QFontDatabase static methods to QML as properties and slots."""

    familiesChanged = Signal()
    selectedFamilyChanged = Signal()
    selectedStyleChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._families: list[str] = []
        self._selected_family: str = ""
        self._selected_style: str = ""
        self._styles: list[str] = []
        self._sizes: list[int] = []
        self._refresh_families()

    # ------------------------------------------------------------------ #
    # Properties
    # ------------------------------------------------------------------ #

    @Property(list, notify=familiesChanged)
    def families(self) -> list[str]:
        """Sorted list of all available font families."""
        return self._families

    @Property(str, notify=selectedFamilyChanged)
    def selectedFamily(self) -> str:
        return self._selected_family

    @Property(list, notify=selectedFamilyChanged)
    def styles(self) -> list[str]:
        """Styles for the currently selected family (empty until selected)."""
        return self._styles

    @Property(list, notify=selectedStyleChanged)
    def sizes(self) -> list[int]:
        """Available sizes for the current family + style combo."""
        return self._sizes

    @Property(list, constant=True)
    def standardSizes(self) -> list[int]:
        """Standard font sizes (independent of family)."""
        return QFontDatabase.standardSizes()

    # ------------------------------------------------------------------ #
    # Slots (callable from QML)
    # ------------------------------------------------------------------ #

    @Slot(str, result=list)
    def getStyles(self, family: str) -> list[str]:
        """Return available styles for a given font family."""
        if not family:
            return []
        return QFontDatabase.styles(family)

    @Slot(str, str, result=list)
    def getSizes(self, family: str, style: str) -> list[int]:
        """Return smooth sizes; fall back to pointSizes; fall back to standard."""
        if not family or not style:
            return QFontDatabase.standardSizes()
        sizes = QFontDatabase.smoothSizes(family, style)
        if not sizes:
            sizes = QFontDatabase.pointSizes(family, style)
        if not sizes:
            sizes = QFontDatabase.standardSizes()
        return sizes

    @Slot(str, str, int, result=QFont)
    def font(self, family: str, style: str, point_size: int) -> QFont:
        """Construct a QFont from family, style, and point size."""
        return QFontDatabase.font(family, style, point_size)

    @Slot(str, str, result=int)
    def weight(self, family: str, style: str) -> int:
        """Return the numeric weight for a family/style combination."""
        if not family or not style:
            return QFont.Normal
        return QFontDatabase.weight(family, style)

    @Slot(str, str, result=bool)
    def isBold(self, family: str, style: str) -> bool:
        """Check if a family/style combination is bold."""
        if not family or not style:
            return False
        return QFontDatabase.bold(family, style)

    @Slot(str, str, result=bool)
    def isItalic(self, family: str, style: str) -> bool:
        """Check if a family/style combination is italic."""
        if not family or not style:
            return False
        return QFontDatabase.italic(family, style)

    @Slot(str, str, result=bool)
    def isFixedPitch(self, family: str, style: str) -> bool:
        """Check if a family/style combination is monospaced."""
        if not family or not style:
            return False
        return QFontDatabase.isFixedPitch(family, style)

    @Slot(str, result=bool)
    def hasFamily(self, family: str) -> bool:
        """Check if a font family exists on the system."""
        return QFontDatabase.hasFamily(family)

    @Slot(str)
    def setSelectedFamily(self, family: str):
        """Update selected family and refresh derived styles/sizes."""
        if self._selected_family != family:
            self._selected_family = family
            self._styles = QFontDatabase.styles(family) if family else []
            if self._styles:
                self._selected_style = self._styles[0]
                self._sizes = self._get_sizes_for(family, self._selected_style)
            else:
                self._selected_style = ""
                self._sizes = QFontDatabase.standardSizes()
            self.selectedFamilyChanged.emit()

    @Slot(str)
    def setSelectedStyle(self, style: str):
        """Update selected style and refresh sizes."""
        if self._selected_style != style:
            self._selected_style = style
            self._sizes = self._get_sizes_for(self._selected_family, style)
            self.selectedStyleChanged.emit()

    @Slot()
    def refreshFamilies(self):
        """Re-scan system fonts (e.g. after loading app fonts)."""
        self._refresh_families()

    # ------------------------------------------------------------------ #
    # Private helpers
    # ------------------------------------------------------------------ #

    def _refresh_families(self):
        self._families = sorted(QFontDatabase.families())
        self.familiesChanged.emit()

    def _get_sizes_for(self, family: str, style: str) -> list[int]:
        if not family or not style:
            return QFontDatabase.standardSizes()
        sizes = QFontDatabase.smoothSizes(family, style)
        if not sizes:
            sizes = QFontDatabase.pointSizes(family, style)
        if not sizes:
            sizes = QFontDatabase.standardSizes()
        return sizes

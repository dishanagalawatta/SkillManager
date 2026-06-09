from PySide6.QtGui import QPixmap
from PySide6.QtQuick import QQuickImageProvider


class ScreenshotImageProvider(QQuickImageProvider):
    """Provides the captured screenshot to QML via image://screenshot/current."""

    def __init__(self):
        super().__init__(QQuickImageProvider.Pixmap)
        self._pixmap = QPixmap()

    def set_pixmap(self, pixmap: QPixmap):
        self._pixmap = pixmap

    def requestPixmap(self, _id: str, _size, _requested_size) -> QPixmap:  # noqa: N802
        if self._pixmap.isNull():
            # Return a transparent 1x1 pixel if no pixmap is set
            dummy = QPixmap(1, 1)
            dummy.fill("transparent")
            return dummy
        return self._pixmap

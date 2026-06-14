import logging
import threading

from PySide6.QtGui import QPixmap
from PySide6.QtQuick import QQuickImageProvider

logger = logging.getLogger(__name__)


class ScreenshotImageProvider(QQuickImageProvider):
    """Provides the captured screenshot to QML via image://screenshot/current."""

    def __init__(self):
        super().__init__(QQuickImageProvider.Pixmap)
        self._pixmap = QPixmap()
        self._lock = threading.Lock()

    def set_pixmap(self, pixmap: QPixmap):
        with self._lock:
            self._pixmap = pixmap
        logger.info(
            "Image provider pixmap set: %dx%d, isNull=%s",
            pixmap.width(),
            pixmap.height(),
            pixmap.isNull(),
        )

    def requestPixmap(self, _id: str, _size, _requested_size) -> QPixmap:  # noqa: N802
        with self._lock:
            if self._pixmap.isNull():
                logger.warning("Image provider: pixmap is null, returning 1x1 transparent")
                dummy = QPixmap(1, 1)
                dummy.fill("transparent")
                return dummy
            logger.info(
                "Image provider: returning pixmap %dx%d (id=%s)",
                self._pixmap.width(),
                self._pixmap.height(),
                _id,
            )
            return self._pixmap

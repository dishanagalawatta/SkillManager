import logging

from PySide6.QtCore import QRect
from PySide6.QtGui import QColor, QPainter, QPixmap

from skill_manager.core.schemas import Redaction

logger = logging.getLogger(__name__)


class ImageProcessor:
    """Handles pure image manipulation logic (cropping and redacting)."""

    @staticmethod
    def crop_and_redact(pixmap: QPixmap, crop_rect: QRect, redactions: list[Redaction]) -> QPixmap:
        """
        Creates a cropped copy of the pixmap and applies redactions.
        Coordinates in `redactions` are expected to be relative to the `crop_rect`.
        """
        if pixmap.isNull():
            raise ValueError("Cannot process a null QPixmap.")

        if crop_rect.isEmpty():
            raise ValueError("Crop rectangle cannot be empty.")

        # 1. Create a cropped copy
        final_image = pixmap.copy(crop_rect)

        # 2. Draw redactions
        if redactions:
            painter = QPainter(final_image)
            # Use strict black for redactions
            painter.setBrush(QColor("black"))
            painter.setPen(QColor("black"))

            for r in redactions:
                rect = QRect(r.x, r.y, r.width, r.height)
                painter.drawRect(rect)

            painter.end()

        return final_image

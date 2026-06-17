"""
Purpose: Backend for image inspection and annotation saving.
Refactored to use Pydantic for validation and AnnotationEngine for drawing.
"""

import logging
from pathlib import Path

from pydantic import TypeAdapter
from PySide6.QtCore import QUrl, Signal, Slot
from PySide6.QtGui import QPainter, QPixmap

from skill_manager.controllers.base import BaseController
from skill_manager.core.annotations import AnnotationEngine
from skill_manager.core.schemas import Annotation

logger = logging.getLogger(__name__)


class ImageInspectorController(BaseController):
    """Backend for image inspection and annotation saving."""

    imageSaved = Signal(str)
    imageLoadError = Signal(str)

    @Slot(str, list, result=bool)
    def saveAnnotations(self, image_path: str, raw_annotations: list) -> bool:
        """Load image, validate and apply annotations, save back to disk."""
        if not image_path:
            logger.error("No image path provided for annotation save.")
            return False

        # Parse URL back to local file path
        local_path = image_path
        if image_path.startswith("file://"):
            local_path = QUrl(image_path).toLocalFile()

        path = Path(local_path)
        if not path.exists():
            logger.error("Image path does not exist: %s", local_path)
            self.imageLoadError.emit(f"File not found: {local_path}")
            return False

        # 1. Validate Annotations
        try:
            adapter = TypeAdapter(list[Annotation])
            validated_anns = adapter.validate_python(raw_annotations)
        except Exception as e:
            logger.error("Annotation validation failed: %s", e)
            self.imageLoadError.emit(f"Invalid annotation data: {e}")
            return False

        # 2. Load Pixmap
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            logger.error("Failed to load image from: %s", image_path)
            self.imageLoadError.emit(f"Failed to load image: {image_path}")
            return False

        # 3. Apply Drawing
        painter = QPainter(pixmap)
        try:
            AnnotationEngine.draw_annotations(painter, validated_anns)
        finally:
            painter.end()

        # 4. Save
        if pixmap.save(str(path)):
            logger.info("Annotated image saved to: %s", image_path)
            self.imageSaved.emit(str(path))
            return True

        logger.error("Failed to save annotated image to: %s", image_path)
        self.imageLoadError.emit(f"Failed to save: {image_path}")
        return False

    @Slot(str, result=bool)
    def openExternally(self, image_path: str) -> bool:
        """Open image with system default viewer."""
        if not image_path:
            return False

        local_path = image_path
        if image_path.startswith("file://"):
            local_path = QUrl(image_path).toLocalFile()

        path = Path(local_path)
        if not path.exists():
            return False

        from PySide6.QtGui import QDesktopServices

        return QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

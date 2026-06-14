import logging
import math

from PySide6.QtCore import QPointF, QRectF, Qt, QUrl, Signal, Slot
from PySide6.QtGui import (
    QColor,
    QFont,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QPolygonF,
)

from skill_manager.controllers.base import BaseController

logger = logging.getLogger(__name__)


class ImageInspectorController(BaseController):
    """Backend for image inspection and annotation saving."""

    imageSaved = Signal(str)
    imageLoadError = Signal(str)

    @Slot(str, list, result=bool)
    def saveAnnotations(self, image_path: str, annotations: list) -> bool:
        """Load image, apply annotations with QPainter, save back to disk."""
        if not image_path:
            logger.error("No image path provided for annotation save.")
            return False

        pixmap = QPixmap(image_path)
        if pixmap.isNull():
            logger.error("Failed to load image from: %s", image_path)
            self.imageLoadError.emit(f"Failed to load image: {image_path}")
            return False

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        for ann in annotations:
            self._drawAnnotation(pixmap, painter, ann)

        painter.end()

        if pixmap.save(image_path):
            logger.info("Annotated image saved to: %s", image_path)
            self.imageSaved.emit(image_path)
            return True

        logger.error("Failed to save annotated image to: %s", image_path)
        self.imageLoadError.emit(f"Failed to save: {image_path}")
        return False

    def _drawAnnotation(self, _pixmap: QPixmap, painter: QPainter, ann: dict):
        """Draw a single annotation onto the painter."""
        ann_type = ann.get("type", "")
        color = QColor(ann.get("color", "#FF0000"))
        stroke_width = ann.get("strokeWidth", 3)

        if ann_type == "rect":
            self._drawRect(painter, ann, color, stroke_width)
        elif ann_type == "arrow":
            self._drawArrow(painter, ann, color, stroke_width)
        elif ann_type == "redact":
            self._drawRedact(painter, ann)
        elif ann_type == "freehand":
            self._drawFreehand(painter, ann, color, stroke_width)
        elif ann_type == "text":
            self._drawText(painter, ann, color)
        elif ann_type == "highlight":
            self._drawHighlight(painter, ann, color)

    def _drawRect(self, painter: QPainter, ann: dict, color: QColor, stroke_width: int):
        pen = QPen(color, stroke_width)
        painter.setPen(pen)
        painter.setBrush(QColor(0, 0, 0, 0))
        rect = QRectF(ann["x"], ann["y"], ann["width"], ann["height"])
        painter.drawRect(rect)

    def _drawArrow(self, painter: QPainter, ann: dict, color: QColor, stroke_width: int):
        pen = QPen(color, stroke_width)
        painter.setPen(pen)
        painter.setBrush(color)

        p1 = QPointF(ann["x1"], ann["y1"])
        p2 = QPointF(ann["x2"], ann["y2"])

        painter.drawLine(p1, p2)

        # Calculate arrowhead
        angle = math.atan2(p2.y() - p1.y(), p2.x() - p1.x())
        arrow_length = 12 + stroke_width * 2
        arrow_angle = math.pi / 6

        head1 = QPointF(
            p2.x() - arrow_length * math.cos(angle - arrow_angle),
            p2.y() - arrow_length * math.sin(angle - arrow_angle),
        )
        head2 = QPointF(
            p2.x() - arrow_length * math.cos(angle + arrow_angle),
            p2.y() - arrow_length * math.sin(angle + arrow_angle),
        )

        arrowhead = QPolygonF([p2, head1, head2])
        painter.drawPolygon(arrowhead)

    def _drawRedact(self, painter: QPainter, ann: dict):
        color = QColor(ann.get("color", "#000000"))
        painter.setPen(QColor(0, 0, 0, 0))
        painter.setBrush(color)
        rect = QRectF(ann["x"], ann["y"], ann["width"], ann["height"])
        painter.drawRect(rect)

    def _drawFreehand(self, painter: QPainter, ann: dict, color: QColor, stroke_width: int):
        points = ann.get("points", [])
        if len(points) < 2:
            return

        pen = QPen(color, stroke_width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(QColor(0, 0, 0, 0))

        path = QPainterPath()
        first = points[0]
        path.moveTo(first["x"], first["y"])

        for pt in points[1:]:
            path.lineTo(pt["x"], pt["y"])

        painter.drawPath(path)

    def _drawText(self, painter: QPainter, ann: dict, color: QColor):
        font_size = ann.get("fontSize", 16)
        text = ann.get("text", "")
        if not text:
            return

        font = QFont("Segoe UI", font_size)
        font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(font)
        painter.setPen(color)

        # Draw text with a subtle shadow for readability
        pos = QPointF(ann["x"], ann["y"])
        shadow_color = QColor(0, 0, 0, 120)
        painter.setPen(shadow_color)
        painter.drawText(pos + QPointF(1, 1), text)
        painter.setPen(color)
        painter.drawText(pos, text)

    def _drawHighlight(self, painter: QPainter, ann: dict, color: QColor):
        highlight_color = QColor(color.red(), color.green(), color.blue(), 80)
        painter.setPen(QColor(0, 0, 0, 0))
        painter.setBrush(highlight_color)
        rect = QRectF(ann["x"], ann["y"], ann["width"], ann["height"])
        painter.drawRect(rect)

    @Slot(str, result=bool)
    def openExternally(self, image_path: str) -> bool:
        """Open image with system default viewer."""
        if not image_path:
            return False
        from PySide6.QtGui import QDesktopServices

        return QDesktopServices.openUrl(QUrl.fromLocalFile(image_path))

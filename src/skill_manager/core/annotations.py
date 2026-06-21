"""
Purpose: Pure logic for drawing annotations onto QPainter.
Decoupled from controllers to facilitate unit testing.
"""

import logging
import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QPainter,
    QPainterPath,
    QPen,
    QPolygonF,
)

from skill_manager.core.schemas import (
    Annotation,
    ArrowAnnotation,
    EllipseAnnotation,
    FilledEllipseAnnotation,
    FilledRectAnnotation,
    FreehandAnnotation,
    HighlightAnnotation,
    RectAnnotation,
    TextAnnotation,
)

logger = logging.getLogger(__name__)


class AnnotationEngine:
    """Handles the rendering of validated annotation models onto a QPainter."""

    @staticmethod
    def draw_annotations(painter: QPainter, annotations: list[Annotation]):
        """Draws a list of validated annotations."""
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        for ann in annotations:
            if isinstance(ann, RectAnnotation):
                AnnotationEngine._draw_rect(painter, ann)
            elif isinstance(ann, ArrowAnnotation):
                AnnotationEngine._draw_arrow(painter, ann)
            elif isinstance(ann, FilledRectAnnotation):
                AnnotationEngine.draw_filled_rect(painter, ann)
            elif isinstance(ann, FreehandAnnotation):
                AnnotationEngine.draw_freehand(painter, ann)
            elif isinstance(ann, TextAnnotation):
                AnnotationEngine.draw_text(painter, ann)
            elif isinstance(ann, HighlightAnnotation):
                AnnotationEngine._draw_highlight(painter, ann)
            elif isinstance(ann, EllipseAnnotation):
                AnnotationEngine.draw_ellipse(painter, ann)
            elif isinstance(ann, FilledEllipseAnnotation):
                AnnotationEngine.draw_filled_ellipse(painter, ann)

    @staticmethod
    def _draw_rect(painter: QPainter, ann: RectAnnotation):
        color = QColor(ann.color)
        pen = QPen(color, ann.strokeWidth)
        painter.setPen(pen)
        painter.setBrush(QColor(0, 0, 0, 0))
        rect = QRectF(ann.x, ann.y, ann.width, ann.height)
        painter.drawRect(rect)

    @staticmethod
    def _draw_arrow(painter: QPainter, ann: ArrowAnnotation):
        color = QColor(ann.color)
        pen = QPen(color, ann.strokeWidth)
        painter.setPen(pen)
        painter.setBrush(color)

        p1 = QPointF(ann.x1, ann.y1)
        p2 = QPointF(ann.x2, ann.y2)

        # Calculate arrowhead
        angle = math.atan2(p2.y() - p1.y(), p2.x() - p1.x())
        arrow_length = 12 + ann.strokeWidth * 2
        arrow_angle = math.pi / 6

        shorten = arrow_length * 0.8
        line_p2 = QPointF(
            p2.x() - shorten * math.cos(angle),
            p2.y() - shorten * math.sin(angle),
        )
        painter.drawLine(p1, line_p2)

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

    @staticmethod
    def draw_filled_rect(painter: QPainter, ann: FilledRectAnnotation):
        color = QColor(ann.color)
        painter.setPen(QColor(0, 0, 0, 0))
        painter.setBrush(color)
        rect = QRectF(ann.x, ann.y, ann.width, ann.height)
        painter.drawRect(rect)

    @staticmethod
    def draw_freehand(painter: QPainter, ann: FreehandAnnotation):
        if not ann.points:
            return

        color = QColor(ann.color)
        pen = QPen(color, ann.strokeWidth)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(QColor(0, 0, 0, 0))

        path = QPainterPath()
        first = ann.points[0]
        path.moveTo(first.x, first.y)

        for pt in ann.points[1:]:
            path.lineTo(pt.x, pt.y)

        painter.drawPath(path)

    @staticmethod
    def draw_text(painter: QPainter, ann: TextAnnotation):
        color = QColor(ann.color)
        font = QFont(ann.fontFamily, ann.fontSize)
        font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(font)

        # Draw text with a subtle shadow for readability
        pos = QPointF(ann.x, ann.y)
        shadow_color = QColor(0, 0, 0, 120)
        painter.setPen(shadow_color)
        painter.drawText(pos + QPointF(1, 1), ann.text)
        painter.setPen(color)
        painter.drawText(pos, ann.text)

    @staticmethod
    def _draw_highlight(painter: QPainter, ann: HighlightAnnotation):
        highlight_base = QColor(ann.color)
        highlight_color = QColor(
            highlight_base.red(), highlight_base.green(), highlight_base.blue(), 80
        )
        painter.setPen(QColor(0, 0, 0, 0))
        painter.setBrush(highlight_color)
        rect = QRectF(ann.x, ann.y, ann.width, ann.height)
        painter.drawRect(rect)

    @staticmethod
    def draw_ellipse(painter: QPainter, ann: EllipseAnnotation):
        color = QColor(ann.color)
        pen = QPen(color, ann.strokeWidth)
        painter.setPen(pen)
        painter.setBrush(QColor(0, 0, 0, 0))
        rect = QRectF(ann.x, ann.y, ann.width, ann.height)
        painter.drawEllipse(rect)

    @staticmethod
    def draw_filled_ellipse(painter: QPainter, ann: FilledEllipseAnnotation):
        color = QColor(ann.color)
        painter.setPen(QColor(0, 0, 0, 0))
        painter.setBrush(color)
        rect = QRectF(ann.x, ann.y, ann.width, ann.height)
        painter.drawEllipse(rect)

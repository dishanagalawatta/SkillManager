from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtGui import QColor, QPainter, QPixmap

from skill_manager.controllers.image_inspector_controller import ImageInspectorController
from skill_manager.core.annotations import AnnotationEngine
from skill_manager.core.schemas import (
    AnnotationPoint,
    ArrowAnnotation,
    EllipseAnnotation,
    FilledEllipseAnnotation,
    FilledRectAnnotation,
    FreehandAnnotation,
    HighlightAnnotation,
    RectAnnotation,
    TextAnnotation,
)


@pytest.fixture
def mock_app():
    app = MagicMock()
    app._config = MagicMock()
    return app


@pytest.fixture
def controller(mock_app):
    return ImageInspectorController(mock_app)


class TestAnnotationEngine:
    def test_draw_all_types(self):
        pixmap = QPixmap(100, 100)
        painter = QPainter(pixmap)

        annotations = [
            RectAnnotation(x=0, y=0, width=10, height=10),
            ArrowAnnotation(x1=0, y1=0, x2=10, y2=10),
            FilledRectAnnotation(x=20, y=20, width=5, height=5),
            FreehandAnnotation(points=[AnnotationPoint(x=0, y=0), AnnotationPoint(x=5, y=5)]),
            TextAnnotation(x=40, y=40, text="Test"),
            HighlightAnnotation(x=50, y=50, width=20, height=10),
            EllipseAnnotation(x=10, y=10, width=30, height=20),
            FilledEllipseAnnotation(x=60, y=60, width=25, height=15),
        ]

        # Should not crash
        AnnotationEngine.draw_annotations(painter, annotations)
        painter.end()

    def test_draw_ellipse(self):
        pixmap = QPixmap(100, 100)
        painter = QPainter(pixmap)
        ann = EllipseAnnotation(x=10, y=10, width=30, height=20)
        AnnotationEngine.draw_ellipse(painter, ann)
        painter.end()

    def test_draw_filled_ellipse(self):
        pixmap = QPixmap(100, 100)
        painter = QPainter(pixmap)
        ann = FilledEllipseAnnotation(x=10, y=10, width=30, height=20)
        AnnotationEngine.draw_filled_ellipse(painter, ann)
        painter.end()

    def test_draw_text_with_font_family(self):
        pixmap = QPixmap(100, 100)
        painter = QPainter(pixmap)
        ann = TextAnnotation(x=10, y=10, text="Test", fontFamily="Arial")
        AnnotationEngine.draw_text(painter, ann)
        painter.end()

    def test_draw_filled_rect(self):
        pixmap = QPixmap(100, 100)
        painter = QPainter(pixmap)
        ann = FilledRectAnnotation(x=10, y=10, width=30, height=20)
        AnnotationEngine.draw_filled_rect(painter, ann)
        painter.end()

    def test_freehand_empty_points(self):
        # Validation normally prevents this, but let's test the engine safety
        pixmap = QPixmap(10, 10)
        painter = QPainter(pixmap)
        # Using a mock for the model since Pydantic min_length=2 prevents direct instantiation of invalid state
        mock_ann = MagicMock(spec=FreehandAnnotation)
        mock_ann.points = []

        AnnotationEngine.draw_freehand(painter, mock_ann)
        painter.end()


class TestImageInspectorControllerSDET:
    def test_save_annotations_success(self, controller, tmp_path):
        img_path = tmp_path / "test.png"
        pix = QPixmap(100, 100)
        pix.fill(QColor("white"))
        pix.save(str(img_path))

        anns = [{"type": "rect", "x": 10, "y": 10, "width": 20, "height": 20}]

        success_emitted = []
        controller.imageSaved.connect(success_emitted.append)

        result = controller.saveAnnotations(str(img_path), anns)

        assert result is True
        assert len(success_emitted) == 1
        assert success_emitted[0] == str(img_path)

    def test_save_annotations_invalid_data(self, controller, tmp_path):
        img_path = tmp_path / "test_invalid.png"
        img_path.touch()

        # Invalid: missing required fields for rect
        anns = [{"type": "rect", "x": 10}]

        error_emitted = []
        controller.imageLoadError.connect(error_emitted.append)

        result = controller.saveAnnotations(str(img_path), anns)

        assert result is False
        assert len(error_emitted) == 1
        assert "Invalid annotation data" in error_emitted[0]

    def test_save_annotations_file_not_found(self, controller):
        result = controller.saveAnnotations("nonexistent.png", [])
        assert result is False

    def test_open_externally_nonexistent(self, controller):
        assert controller.openExternally("no.png") is False

    @patch("PySide6.QtGui.QDesktopServices.openUrl")
    def test_open_externally_success(self, mock_open, controller, tmp_path):
        f = tmp_path / "test.png"
        f.touch()
        result = controller.openExternally(str(f))
        assert result is not None  # QDesktopServices returns bool
        mock_open.assert_called_once()

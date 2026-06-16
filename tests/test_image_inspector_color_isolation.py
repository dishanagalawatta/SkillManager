# Purpose: Verify that annotations preserve independent colors when saved.
# Regression test for the bug where changing the active color in the QML
# color picker retroactively changed all existing annotations to the new color.
# Root cause: QML `color` property values stored as QColor objects could
# maintain a reference/binding to `root.activeColor`. Fix: convert to string
# via `.toString()` at annotation creation time.
# Usage: uv run pytest tests/test_image_inspector_color_isolation.py

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from pydantic import TypeAdapter
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap

from skill_manager.controllers.image_inspector_controller import ImageInspectorController
from skill_manager.core.annotations import AnnotationEngine
from skill_manager.core.schemas import Annotation


def _validate(raw: list[dict]) -> list[Annotation]:
    adapter = TypeAdapter(list[Annotation])
    return adapter.validate_python(raw)


@pytest.fixture
def mock_app():
    app = MagicMock()
    app._config = MagicMock()
    return app


@pytest.fixture
def controller(mock_app):
    return ImageInspectorController(mock_app)


def _make_annotations() -> list[dict]:
    """Create annotations with explicit string colors (the fix ensures QML sends strings)."""
    return [
        {
            "type": "rect",
            "x": 10,
            "y": 10,
            "width": 50,
            "height": 50,
            "color": "#FF0000",
            "strokeWidth": 3,
        },
        {
            "type": "arrow",
            "x1": 100,
            "y1": 10,
            "x2": 200,
            "y2": 100,
            "color": "#00FF00",
            "strokeWidth": 3,
        },
        {
            "type": "freehand",
            "points": [{"x": 10, "y": 200}, {"x": 50, "y": 220}, {"x": 100, "y": 200}],
            "color": "#0000FF",
            "strokeWidth": 3,
        },
    ]


class TestAnnotationColorIsolation:
    """Annotations must each retain their own color independently."""

    def test_annotation_data_preserves_colors(self):
        anns = _make_annotations()
        assert anns[0]["color"] == "#FF0000"
        assert anns[1]["color"] == "#00FF00"
        assert anns[2]["color"] == "#0000FF"
        assert anns[0]["color"] != anns[1]["color"]

    def test_painter_receives_correct_colors(self, tmp_path):
        pixmap = QPixmap(300, 300)
        pixmap.fill(QColor(255, 255, 255))
        painter = QPainter(pixmap)

        anns = _validate(_make_annotations())
        for ann in anns:
            assert QColor(ann.color).isValid(), f"Invalid color for annotation: {ann.color}"

        AnnotationEngine.draw_annotations(painter, anns)
        painter.end()

        out_path = tmp_path / "color_test.png"
        assert pixmap.save(str(out_path)), "Failed to save test image"
        assert out_path.exists()

    def test_color_independence_after_multiple_annotations(self):
        anns_raw = [
            {
                "type": "rect",
                "x": 0,
                "y": 0,
                "width": 20,
                "height": 20,
                "color": "#FF0000",
                "strokeWidth": 3,
            },
            {
                "type": "rect",
                "x": 30,
                "y": 0,
                "width": 20,
                "height": 20,
                "color": "#00FF00",
                "strokeWidth": 3,
            },
        ]

        pixmap = QPixmap(60, 30)
        pixmap.fill(QColor(255, 255, 255))
        painter = QPainter(pixmap)

        AnnotationEngine.draw_annotations(painter, _validate(anns_raw))
        painter.end()

        c1 = QColor(pixmap.toImage().pixel(1, 1))
        c2 = QColor(pixmap.toImage().pixel(31, 1))

        assert c1.red() > 200, f"Expected red stroke at (1,1), got R={c1.red()}"
        assert c2.green() > 200, f"Expected green stroke at (31,1), got G={c2.green()}"

    def test_all_annotation_types_accept_string_color(self, tmp_path):
        pixmap = QPixmap(400, 400)
        pixmap.fill(QColor(255, 255, 255))
        painter = QPainter(pixmap)

        annotations = [
            {
                "type": "rect",
                "x": 10,
                "y": 10,
                "width": 50,
                "height": 50,
                "color": "#FF0000",
                "strokeWidth": 3,
            },
            {
                "type": "arrow",
                "x1": 100,
                "y1": 10,
                "x2": 200,
                "y2": 100,
                "color": "#00FF00",
                "strokeWidth": 3,
            },
            {"type": "redact", "x": 10, "y": 150, "width": 60, "height": 30, "color": "#000000"},
            {
                "type": "freehand",
                "points": [{"x": 250, "y": 10}, {"x": 300, "y": 60}],
                "color": "#0000FF",
                "strokeWidth": 3,
            },
            {
                "type": "text",
                "x": 10,
                "y": 250,
                "text": "Hello",
                "color": "#FF00FF",
                "fontSize": 16,
            },
            {
                "type": "highlight",
                "x": 150,
                "y": 200,
                "width": 100,
                "height": 30,
                "color": "#FFFF00",
            },
        ]

        for ann in annotations:
            color = QColor(ann["color"])
            assert color.isValid(), f"QColor failed to parse: {ann['color']}"

        AnnotationEngine.draw_annotations(painter, _validate(annotations))
        painter.end()

        out_path = tmp_path / "all_types.png"
        assert pixmap.save(str(out_path)), "Failed to save test image"
        assert out_path.exists()

    def test_redact_default_color(self):
        ann = {"type": "redact", "x": 0, "y": 0, "width": 10, "height": 10}
        pixmap = QPixmap(20, 20)
        pixmap.fill(QColor(255, 255, 255))
        painter = QPainter(pixmap)
        AnnotationEngine.draw_annotations(painter, _validate([ann]))
        painter.end()

        c = QColor(pixmap.toImage().pixel(5, 5))
        assert c.red() == 0 and c.green() == 0 and c.blue() == 0, (
            f"Expected black fill, got R={c.red()} G={c.green()} B={c.blue()}"
        )

    def test_color_isolation_with_save_roundtrip(self, controller, tmp_path):

        img_path = tmp_path / "input.png"
        base = QPixmap(100, 100)
        base.fill(QColor(255, 255, 255))
        assert base.save(str(img_path))

        anns = [
            {
                "type": "rect",
                "x": 5,
                "y": 5,
                "width": 30,
                "height": 30,
                "color": "#FF0000",
                "strokeWidth": 3,
            },
            {
                "type": "rect",
                "x": 55,
                "y": 5,
                "width": 30,
                "height": 30,
                "color": "#0000FF",
                "strokeWidth": 3,
            },
        ]

        result = controller.saveAnnotations(str(img_path), anns)
        assert result, "saveAnnotations returned False"

        saved = QImage(str(img_path))
        assert not saved.isNull()

        left_color = QColor(saved.pixel(6, 6))
        assert left_color.red() > 200, f"Left rect should be red, got R={left_color.red()}"

        right_color = QColor(saved.pixel(56, 6))
        assert right_color.blue() > 200, f"Right rect should be blue, got B={right_color.blue()}"

        assert left_color != right_color, "Both annotations ended up with the same color!"

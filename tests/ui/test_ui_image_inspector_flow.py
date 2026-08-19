import pytest
from PySide6.QtGui import QColor, QPixmap


@pytest.mark.usefixtures("setup_qml_style")
class TestUIImageInspectorFlow:
    def test_save_annotations_ui_signal_propagation(
        self, qml_engine, app_controller, qtbot, tmp_path
    ):
        """Verify that calling saveAnnotations emits the imageSaved signal and updates disk."""

        # 1. Create a dummy image
        img_path = tmp_path / "ui_test.png"
        pix = QPixmap(200, 200)
        pix.fill(QColor("blue"))
        pix.save(str(img_path))

        inspector = app_controller.image_inspector

        # 2. Setup signal spy
        with qtbot.waitSignal(inspector.imageSaved, timeout=2000) as blocker:
            # 3. Trigger save via controller slot
            # Simulating what QML would send
            annotations = [
                {"type": "rect", "x": 10, "y": 10, "width": 50, "height": 50, "color": "#FF0000"},
                {"type": "text", "x": 100, "y": 100, "text": "UI Test", "color": "#FFFFFF"},
            ]
            success = inspector.saveAnnotations(str(img_path), annotations)
            assert success is True

        # 4. Verify signal arguments
        assert blocker.args[0] == str(img_path)

        # 5. Verify file modified (just check it still exists and was saved)
        assert img_path.exists()
        new_pix = QPixmap(str(img_path))
        assert not new_pix.isNull()

    def test_load_error_propagation(self, qml_engine, app_controller, qtbot):
        """Verify that errors (like missing files) propagate to the UI signal."""
        inspector = app_controller.image_inspector

        with qtbot.waitSignal(inspector.imageLoadError, timeout=2000) as blocker:
            success = inspector.saveAnnotations("nonexistent_ui_test.png", [])
            assert success is False

        assert "File not found" in blocker.args[0]

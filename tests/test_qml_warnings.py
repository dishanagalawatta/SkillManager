from unittest.mock import patch

from skill_manager.app import _handle_qml_warning, logger


class DummyMsg:
    def __init__(self, msg):
        self.msg = msg
    def toString(self):  # noqa: N802
        return self.msg

def test_qml_warning_handler_filters_incubation():
    """
    Test that the QML warning handler properly filters the benign
    'Object or context destroyed during incubation' warnings.
    """
    with patch.object(logger, "debug") as mock_debug, patch.object(logger, "warning") as mock_warning:
        # Test benign warning
        _handle_qml_warning(DummyMsg("file:///.../QuickCopyView.qml: Object or context destroyed during incubation"))
        mock_debug.assert_called_with("QML Warning (suppressed): file:///.../QuickCopyView.qml: Object or context destroyed during incubation")
        mock_warning.assert_not_called()

        mock_debug.reset_mock()
        mock_warning.reset_mock()

        # Test real warning
        _handle_qml_warning(DummyMsg("file:///.../View.qml: TypeError: Cannot read property"))
        mock_warning.assert_called_with("QML Warning: file:///.../View.qml: TypeError: Cannot read property")
        mock_debug.assert_not_called()


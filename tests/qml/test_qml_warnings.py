from unittest.mock import patch

from skill_manager.app import _handle_qml_warning, logger


class DummyMsg:
    def __init__(self, msg):
        self.msg = msg

    def toString(self):  # noqa: N802
        return self.msg


def test_qml_warning_handler_logs_all_warnings():
    """
    All QML warnings — including 'Object or context destroyed during
    incubation' — must be logged at WARNING level.  We do not suppress
    any warnings; regressions must surface visibly so they can be fixed
    at the source.
    """
    with patch.object(logger, "warning") as mock_warning:
        # Incubation warning — must be logged, not suppressed
        _handle_qml_warning(
            DummyMsg("file:///.../QuickCopyView.qml: Object or context destroyed during incubation")
        )
        mock_warning.assert_called_with(
            "QML Warning: file:///.../QuickCopyView.qml: Object or context destroyed during incubation"
        )

        mock_warning.reset_mock()

        # Real warning — also logged
        _handle_qml_warning(DummyMsg("file:///.../View.qml: TypeError: Cannot read property"))
        mock_warning.assert_called_with(
            "QML Warning: file:///.../View.qml: TypeError: Cannot read property"
        )

        mock_warning.reset_mock()

        # Font warning — also logged
        _handle_qml_warning(DummyMsg("QFontDatabase: Cannot find font directory /some/path"))
        mock_warning.assert_called_with(
            "QML Warning: QFontDatabase: Cannot find font directory /some/path"
        )

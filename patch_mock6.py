import sys
from pathlib import Path

tests_app = Path("tests/test_app_dark_mode_native.py")
content = tests_app.read_text()
content = content.replace('import ctypes', 'import ctypes\nimport sys\nfrom unittest.mock import patch, MagicMock')
content = content.replace('with patch("ctypes.windll.dwmapi.DwmSetWindowAttribute")', 'if not hasattr(ctypes, "windll"): ctypes.windll = MagicMock()\n        with patch("ctypes.windll.dwmapi.DwmSetWindowAttribute", create=True)')
tests_app.write_text(content)

tests_cov = Path("tests/test_coverage_boost.py")
content = tests_cov.read_text()
content = content.replace('    def test_win32_get_window_placement(self):', '    def test_win32_get_window_placement(self):\n        import ctypes\n        if not hasattr(ctypes, "windll"): ctypes.windll = MagicMock()')
content = content.replace('patch(\n                "skill_manager.utils.win32.ctypes.windll.user32.GetWindowPlacement",', 'patch(\n                "skill_manager.utils.win32.ctypes.windll.user32.GetWindowPlacement", create=True,')
tests_cov.write_text(content)

tests_win = Path("tests/test_win32_utils.py")
content = tests_win.read_text()
content = content.replace('    window = MagicMock()', '    window = MagicMock()\n    import ctypes\n    if not hasattr(ctypes, "windll"): ctypes.windll = MagicMock()')
tests_win.write_text(content)

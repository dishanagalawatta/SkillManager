# -*- mode: python ; coding: utf-8 -*-

import os
import sys
import logging
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Intercept and rewrite PyInstaller's malformed QtQml logging messages to prevent crash
class PyInstallerQtQmlLogFilter(logging.Filter):
    def filter(self, record):
        if record.msg == "%s: QML plugin binary %r does not exist!":
            if isinstance(record.args, tuple) and len(record.args) == 1:
                record.args = (record.args[0], "unknown")
            elif not isinstance(record.args, tuple):
                record.args = (record.args, "unknown")
        return True

# Register the filter on the root logger, PyInstaller logger, and their handlers
qt_qml_filter = PyInstallerQtQmlLogFilter()
logging.getLogger().addFilter(qt_qml_filter)
logging.getLogger('PyInstaller').addFilter(qt_qml_filter)

for handler in logging.getLogger().handlers:
    handler.addFilter(qt_qml_filter)
for handler in logging.getLogger('PyInstaller').handlers:
    handler.addFilter(qt_qml_filter)

block_cipher = None

# Base path relative to this spec file (using PyInstaller's injected SPECPATH)
base_path = os.path.abspath(os.path.join(SPECPATH, '..'))

# Assets to include
# Format: (source_path, target_subdir)
added_files = [
    (os.path.join(base_path, 'assets'), 'assets'),
    (os.path.join(base_path, 'src', 'skill_manager', 'SkillManagerComponents'), 'skill_manager/SkillManagerComponents'),
]

# Collect any additional data files if needed
# added_files += collect_data_files('some_library')

a = Analysis(
    [os.path.join(base_path, 'src', 'skill_manager', '__main__.py')],
    pathex=[os.path.join(base_path, 'src')],
    binaries=[],
    datas=added_files,
    hiddenimports=[
        'PySide6.QtQuick',
        'PySide6.QtQml',
        'PySide6.QtNetwork',
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'yaml',
        'pywinstyles',
        'posthog',
        'dotenv',
        'httpx',
        'pydantic',
        'pydantic_settings',
        'watchdog',
        'platformdirs',
        'frontmatter',
        'markdown_it',
        'collections.abc',
        'orjson',
        'diskcache',
        'sentry_sdk',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Unix-only modules
        'pwd', 'grp', 'fcntl', 'termios', 'readline', '_scproxy', 'posix', 'resource', '_posixsubprocess', '_posixshmem',
        # Platform/Internal noise
        'vms_lib', 'java', 'java.lang', '_frozen_importlib', '_frozen_importlib_external', 'sitecustomize', 'usercustomize',
        # Optional library features
        'redis', 'IPython', 'dotenv.ipython', 'brotli', 'brotlicffi', 'h2', 'socks', '_typeshed',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='SkillManager',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Set to True for debugging
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(base_path, 'assets', 'brand', 'logo.ico'), # Using generated multi-size .ico icon
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='SkillManager',
)

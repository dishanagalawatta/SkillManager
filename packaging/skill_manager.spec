# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

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
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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

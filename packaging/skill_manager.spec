import os
import sys

block_cipher = None

# Base path relative to this spec file (using PyInstaller's injected SPECPATH)
base_path = os.path.abspath(os.path.join(SPECPATH, ".."))

# Assets to include
# Format: (source_path, target_subdir)
added_files = [
    (os.path.join(base_path, "assets"), "assets"),
    (
        os.path.join(base_path, "src", "skill_manager", "SkillManagerComponents"),
        "skill_manager/SkillManagerComponents",
    ),
]

# Collect any additional data files if needed
from PyInstaller.utils.hooks import collect_all

# Collect metadata and submodules for dynamic packages
apscheduler_datas, apscheduler_binaries, apscheduler_hiddenimports = collect_all('apscheduler')
tzlocal_datas, tzlocal_binaries, tzlocal_hiddenimports = collect_all('tzlocal')
pynput_datas, pynput_binaries, pynput_hiddenimports = collect_all('pynput')
joblib_datas, joblib_binaries, joblib_hiddenimports = collect_all('joblib')
diskcache_datas, diskcache_binaries, diskcache_hiddenimports = collect_all('diskcache')

added_files += apscheduler_datas + tzlocal_datas + pynput_datas + joblib_datas + diskcache_datas
added_binaries = apscheduler_binaries + tzlocal_binaries + pynput_binaries + joblib_binaries + diskcache_binaries
added_hidden = apscheduler_hiddenimports + tzlocal_hiddenimports + pynput_hiddenimports + joblib_hiddenimports + diskcache_hiddenimports + ["git", "psutil", "msgpack"]

# Linux-only excludes: the app never imports WebEngine/Multimedia/Quick3D,
# so dropping them shrinks the Linux bundle (no WebEngine/GStreamer/Quick3D).
# Windows/macOS builds keep the full PySide6 set.
_LINUX_EXCLUDES = [
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineWidgets",
    "PySide6.QtWebEngineQuick",
    "PySide6.QtMultimedia",
    "PySide6.QtMultimediaWidgets",
    "PySide6.QtQuick3D",
    "PySide6.Qt3DCore",
]

# The app's joblib/loky pipeline needs the real POSIX runtime modules on
# Linux (multiprocessing.resource_tracker imports _posixshmem, etc.), so the
# Unix-module names below are only excluded on Windows/macOS, where they are
# pure noise.
_UNIX_ONLY_EXCLUDES = [
    "pwd",
    "grp",
    "fcntl",
    "termios",
    "readline",
    "_scproxy",
    "posix",
    "resource",
    "_posixsubprocess",
    "_posixshmem",
]

a = Analysis(
    [os.path.join(base_path, "src", "skill_manager", "__main__.py")],
    pathex=[os.path.join(base_path, "src")],
    binaries=added_binaries,
    datas=added_files,
    hiddenimports=[
        "PySide6.QtQuick",
        "PySide6.QtQml",
        "PySide6.QtNetwork",
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
        "yaml",
        "pywinstyles",
        "posthog",
        "dotenv",
        "httpx",
        "pydantic",
        "pydantic_settings",
        "watchdog",
        "platformdirs",
        "frontmatter",
        "markdown_it",
        "orjson",
        "sentry_sdk",
    ] + added_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Platform/Internal noise
        "vms_lib",
        "java",
        "java.lang",
        "_frozen_importlib",
        "_frozen_importlib_external",
        "sitecustomize",
        "usercustomize",
        # Optional library features
        "redis",
        "IPython",
        "dotenv.ipython",
        "brotli",
        "brotlicffi",
        "h2",
        "socks",
        "_typeshed",
    ]
    + ([] if sys.platform.startswith("linux") else _UNIX_ONLY_EXCLUDES)
    + (_LINUX_EXCLUDES if sys.platform.startswith("linux") else []),
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
    name="SkillManager",
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
    icon=os.path.join(
        base_path, "assets", "brand", "logo.ico"
    ),  # Using generated multi-size .ico icon
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="SkillManager",
)

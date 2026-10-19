"""Windows version resource for the PyInstaller build.

PyInstaller embeds ProductName/ProductVersion only when it is handed a version
resource file. Windows builds had none, so ``SkillManager.exe`` shipped with
empty file properties and a signing service has no product metadata to verify
against.

The resource is generated from ``pyproject.toml`` at build time rather than
checked in. A checked-in copy would be a second home for the version, and the
release automation already bumps ``pyproject.toml`` and
``skill_manager.__version__`` -- a third file would drift silently.

PyInstaller ``eval``s the generated text, so the constants below are emitted as
a ``VSVersionInfo`` expression rather than serialised as data.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

PRODUCT_NAME = "SkillManager"
ORIGINAL_FILENAME = "SkillManager.exe"
DESCRIPTION = "SkillManager"
COMPANY_NAME = "dishanagalawatta"
LEGAL_COPYRIGHT = "Copyright (c) 2026 Don Dishan Kanchuka Agalawatta"

# Written inside the build tree, which is gitignored.
_GENERATED_NAME = "SkillManager_version.txt"

# Leading major.minor.patch of a PEP 440 version, optionally v-prefixed.
_VERSION_PREFIX = re.compile(r"^(\d+)\.(\d+)\.(\d+)")

# en-US, Unicode.
_LANGUAGE_ID = 1033
_CODEPAGE = 1200


def version_tuple(version: str) -> tuple[int, int, int, int]:
    """Return the four-part numeric version Windows records for a release.

    ``pyproject.toml`` may hold a prerelease such as ``2.13.0-dev.3``. The
    file/prod version tuple is numeric-only, so the prerelease suffix is dropped
    there while the version *strings* keep the full value.
    """
    match = _VERSION_PREFIX.match(version.strip().lstrip("v"))
    if match is None:
        raise ValueError(f"Cannot derive a Windows version tuple from {version!r}")
    major, minor, patch = (int(part) for part in match.groups())
    return major, minor, patch, 0


def resolve_version(root: str | Path) -> str:
    """Read the project version from its single source of truth."""
    pyproject = Path(root) / "pyproject.toml"
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    return data["project"]["version"]


def build_version_file(version: str) -> str:
    """Return the ``VSVersionInfo`` expression PyInstaller evaluates."""
    major, minor, patch, build = version_tuple(version)
    return f"""\
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({major}, {minor}, {patch}, {build}),
    prodvers=({major}, {minor}, {patch}, {build}),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0),
  ),
  kids=[
    StringFileInfo(
      [
        StringTable(
          "040904B0",
          [
            StringStruct("CompanyName", "{COMPANY_NAME}"),
            StringStruct("FileDescription", "{DESCRIPTION}"),
            StringStruct("FileVersion", "{version}"),
            StringStruct("InternalName", "{PRODUCT_NAME}"),
            StringStruct("LegalCopyright", "{LEGAL_COPYRIGHT}"),
            StringStruct("OriginalFilename", "{ORIGINAL_FILENAME}"),
            StringStruct("ProductName", "{PRODUCT_NAME}"),
            StringStruct("ProductVersion", "{version}"),
          ],
        )
      ]
    ),
    VarFileInfo([VarStruct("Translation", [{_LANGUAGE_ID}, {_CODEPAGE}])]),
  ],
)
"""


def write_version_file(root: str | Path, version: str | None = None) -> str:
    """Write the version resource into the build tree and return its path."""
    root = Path(root)
    destination = root / "build" / _GENERATED_NAME
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(build_version_file(version or resolve_version(root)), encoding="utf-8")
    return str(destination)

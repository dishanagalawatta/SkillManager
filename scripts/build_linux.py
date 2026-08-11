"""
Purpose: Build Linux packages (AppImage + .deb) from the PyInstaller onedir output.
Usage:
    uv run python scripts/build_linux.py
    uv run python scripts/build_linux.py --appimage
    uv run python scripts/build_linux.py --deb
    uv run python scripts/build_linux.py --all
    uv run skill-manager-build linux
"""

import os
import shutil
import stat
import subprocess
import sys
import tomllib

# ── Venv guard (re-exec to project venv if not already in it) ─────────────────
# Must run BEFORE any third-party imports so the child process lands on a
# Python where the build tooling exists.
_scripts_dir = os.path.dirname(os.path.abspath(__file__))
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)
from _launcher import ensure_venv  # noqa: E402

ensure_venv()

# ── Safe to import third-party packages below this line ────────────────────────

# AppRun launcher for the AppImage. QML_DISABLE_DISK_CACHE is defense-in-depth
# only; the app registers its QML import path programmatically in frozen mode
# (core/resources.py::qml_components_dir + bootstrap.py::_load_qml_engine), so
# QML2_IMPORT_PATH must NOT be set here.
APPRUN_SCRIPT = """#!/bin/bash
HERE="$(dirname "$(readlink -f "$0")")"
export QML_DISABLE_DISK_CACHE=1
export PATH="$HERE/usr/bin:$PATH"
exec "$HERE/usr/bin/skill-manager" "$@"
"""


def handle_remove_readonly(func, path, exc_info):
    """
    Error handler for shutil.rmtree.
    If the error is due to an access error (read only file),
    it attempts to add write permission and then retries.
    """
    excvalue = exc_info[1]
    # Check if the error is a PermissionError (errno 13 on Unix, WinError 5 on Windows)
    # The onerror callback passes (function, path, exc_info)
    if func in (os.rmdir, os.remove, os.unlink):
        try:
            # On Windows, os.chmod only affects read-only bit. We add write permissions for all.
            os.chmod(path, stat.S_IWRITE)
            func(path)
            return
        except Exception:
            pass
    raise excvalue


def get_version(project_root: str) -> str:
    """Read ``project.version`` from pyproject.toml (stdlib tomllib)."""
    pyproject_path = os.path.join(project_root, "pyproject.toml")
    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)
    return data["project"]["version"]


def check_onedir(project_root: str) -> str:
    """
    Verify the PyInstaller onedir output exists and return its path.

    Expected layout: ``dist/SkillManager/SkillManager`` (binary) plus
    ``dist/SkillManager/_internal/`` (bundled dependencies).
    """
    onedir = os.path.join(project_root, "dist", "SkillManager")
    binary = os.path.join(onedir, "SkillManager")
    internal = os.path.join(onedir, "_internal")
    if not (os.path.isfile(binary) and os.path.isdir(internal)):
        print(f"ERROR: PyInstaller onedir output not found at {onedir}")
        print(
            "Run PyInstaller first: "
            "uv run python -m PyInstaller --noconfirm packaging/skill_manager.spec"
        )
        sys.exit(1)
    return onedir


def stage_share_files(project_root: str, usr_prefix: str) -> None:
    """
    Copy the desktop entry, metainfo and hicolor icons under ``usr_prefix``.

    Shared by both the AppImage AppDir and the .deb package root.
    """
    share = os.path.join(usr_prefix, "share")
    applications = os.path.join(share, "applications")
    metainfo = os.path.join(share, "metainfo")
    icon_svg = os.path.join(share, "icons", "hicolor", "scalable", "apps")
    icon_png = os.path.join(share, "icons", "hicolor", "128x128", "apps")
    for dir_path in (applications, metainfo, icon_svg, icon_png):
        os.makedirs(dir_path, exist_ok=True)

    shutil.copy2(
        os.path.join(project_root, "packaging", "linux", "skill-manager.desktop"),
        os.path.join(applications, "skill-manager.desktop"),
    )
    shutil.copy2(
        os.path.join(
            project_root,
            "packaging",
            "linux",
            "org.dishanagalawatta.SkillManager.metainfo.xml",
        ),
        os.path.join(metainfo, "org.dishanagalawatta.SkillManager.metainfo.xml"),
    )
    shutil.copy2(
        os.path.join(project_root, "assets", "brand", "logo.svg"),
        os.path.join(icon_svg, "skill-manager.svg"),
    )
    shutil.copy2(
        os.path.join(project_root, "assets", "brand", "logo-128.png"),
        os.path.join(icon_png, "skill-manager.png"),
    )


def stage_appdir(project_root: str, onedir: str) -> str:
    """Stage the AppImage AppDir under ``build/linux/AppDir``."""
    appdir = os.path.join(project_root, "build", "linux", "AppDir")
    if os.path.exists(appdir):
        shutil.rmtree(appdir, onerror=handle_remove_readonly)

    usr_bin = os.path.join(appdir, "usr", "bin")
    os.makedirs(usr_bin, exist_ok=True)

    # Rename the PyInstaller binary to the canonical launcher name
    shutil.copy2(os.path.join(onedir, "SkillManager"), os.path.join(usr_bin, "skill-manager"))
    shutil.copytree(os.path.join(onedir, "_internal"), os.path.join(usr_bin, "_internal"))

    # AppImage spec requires a .desktop file and icon at the AppDir root
    # (appimagetool discovers them there, not in usr/share/applications).
    shutil.copy2(
        os.path.join(project_root, "packaging", "linux", "skill-manager.desktop"),
        os.path.join(appdir, "skill-manager.desktop"),
    )
    shutil.copy2(
        os.path.join(project_root, "assets", "brand", "logo-128.png"),
        os.path.join(appdir, "skill-manager.png"),
    )

    stage_share_files(project_root, os.path.join(appdir, "usr"))

    apprun = os.path.join(appdir, "AppRun")
    with open(apprun, "w", encoding="utf-8") as f:
        f.write(APPRUN_SCRIPT)
    os.chmod(apprun, 0o755)
    return appdir


def find_appimagetool() -> str:
    """Locate appimagetool: PATH, then APPIMAGETOOL env var, then /tmp."""
    tool = shutil.which("appimagetool")
    if tool:
        return tool
    env_tool = os.environ.get("APPIMAGETOOL")
    if env_tool and os.path.exists(env_tool):
        return env_tool
    tmp_tool = "/tmp/appimagetool"
    if os.path.exists(tmp_tool):
        return tmp_tool
    print("ERROR: 'appimagetool' not found in PATH, APPIMAGETOOL, or /tmp.")
    print("Download it from: https://github.com/AppImage/appimagetool/releases")
    print("Example:")
    print("  wget https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage -O /tmp/appimagetool")
    print("  chmod +x /tmp/appimagetool")
    sys.exit(1)


def build_appimage(project_root: str, version: str) -> str:
    """Build the AppImage from the staged AppDir."""
    print("\n--- Phase 1: Building AppImage ---")
    onedir = check_onedir(project_root)
    appdir = stage_appdir(project_root, onedir)
    tool = find_appimagetool()

    out_path = os.path.join(project_root, "dist", f"SkillManager-{version}-x86_64.AppImage")
    # ARCH must be passed via the environment, not --arch: the AppImageKit
    # "continuous" appimagetool (as installed in CI) predates --arch and
    # only honors the ARCH env var; newer appimagetool builds accept both.
    env = dict(os.environ)
    env["ARCH"] = "x86_64"
    print(f"Running appimagetool: {tool} AppDir {out_path} (ARCH=x86_64)")
    # chdir to build/linux so the relative "AppDir" path resolves
    subprocess.run(
        [tool, "AppDir", out_path],
        check=True,
        cwd=os.path.dirname(appdir),
        env=env,
    )

    print(f"Removing staging directory: {appdir}")
    shutil.rmtree(appdir, onerror=handle_remove_readonly)
    print(f"AppImage built successfully: {out_path}")
    return out_path


def build_deb(project_root: str, version: str) -> str:
    """Build the .deb package from a staged deb-root."""
    print("\n--- Phase 2: Building .deb ---")
    onedir = check_onedir(project_root)

    deb_root = os.path.join(project_root, "build", "linux", "deb-root")
    pkg_dir = os.path.join(deb_root, f"skill-manager_{version}_amd64")
    if os.path.exists(deb_root):
        shutil.rmtree(deb_root, onerror=handle_remove_readonly)

    # DEBIAN/control
    control_dir = os.path.join(pkg_dir, "DEBIAN")
    os.makedirs(control_dir, exist_ok=True)
    control = f"""Package: skill-manager
Version: {version}
Architecture: amd64
Maintainer: Don Dishan Kanchuka Agalawatta
Depends: libglib2.0-0, libxcb-cursor0, libxkbcommon-x11-0, libxcb-xinerama0, libxcb-icccm4, libxcb-keysyms1, xdg-desktop-portal
Section: utils
Priority: optional
Homepage: https://github.com/dishanagalawatta/SkillManager
Description: A professional tool for managing reusable agent skills across repositories
"""
    with open(os.path.join(control_dir, "control"), "w", encoding="utf-8") as f:
        f.write(control)

    # opt/SkillManager ← full onedir contents
    shutil.copytree(onedir, os.path.join(pkg_dir, "opt", "SkillManager"))

    # usr/bin/skill-manager → symlink into the onedir
    usr_bin = os.path.join(pkg_dir, "usr", "bin")
    os.makedirs(usr_bin, exist_ok=True)
    os.symlink("/opt/SkillManager/SkillManager", os.path.join(usr_bin, "skill-manager"))

    stage_share_files(project_root, os.path.join(pkg_dir, "usr"))

    dpkg_deb = shutil.which("dpkg-deb")
    if not dpkg_deb:
        print("ERROR: 'dpkg-deb' not found in PATH.")
        print("Install it with: sudo apt install dpkg")
        sys.exit(1)

    out_deb = os.path.join(project_root, "dist", f"skill-manager_{version}_amd64.deb")
    print(f"Running dpkg-deb: {dpkg_deb} --build --root-owner-group {pkg_dir} {out_deb}")
    subprocess.run([dpkg_deb, "--build", "--root-owner-group", pkg_dir, out_deb], check=True)

    print(f"Removing staging directory: {deb_root}")
    shutil.rmtree(deb_root, onerror=handle_remove_readonly)
    print(f".deb built successfully: {out_deb}")
    return out_deb


def main() -> None:
    """Main execution entrypoint for the Linux packaging process."""
    script_dir: str = os.path.dirname(os.path.abspath(__file__))
    project_root: str = os.path.abspath(os.path.join(script_dir, ".."))

    # argparse-free CLI parsing: --appimage | --deb | --all (default --all)
    flags = {arg for arg in sys.argv[1:] if arg.startswith("--")}
    if not (flags & {"--appimage", "--deb", "--all"}):
        flags.add("--all")
    want_appimage = "--appimage" in flags or "--all" in flags
    want_deb = "--deb" in flags or "--all" in flags

    version = get_version(project_root)
    print(f"SkillManager version: {version}")

    artifacts: list[str] = []
    if want_appimage:
        artifacts.append(build_appimage(project_root, version))
    if want_deb:
        artifacts.append(build_deb(project_root, version))

    print("\n--- Phase 3: Summary ---")
    for artifact in artifacts:
        size_mib = os.path.getsize(artifact) / (1024 * 1024)
        print(f"{artifact} ({size_mib:.1f} MiB)")
    print("\nAll Linux packaging steps completed successfully!")


if __name__ == "__main__":
    main()

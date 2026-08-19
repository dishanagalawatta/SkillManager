"""Smoke and regression tests for scripts/install.sh (Linux bash installer).

The script is sourced with a BASH_SOURCE guard so functions (ver_compare)
can be unit-tested, and executed with a stubbed dpkg on PATH to exercise
the update decision flow without root or network access.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
INSTALL_SH = REPO_ROOT / "scripts" / "install.sh"

pytestmark = pytest.mark.skipif(
    sys.platform == "win32",
    reason="install.sh is a Linux bash script; CI runs this suite on windows-latest",
)


def bash_script(
    script: str, cwd: Path = REPO_ROOT, env: dict | None = None
) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", "-c", script],
        capture_output=True,
        text=True,
        cwd=cwd,
        env=env,
    )


@pytest.mark.parametrize(
    ("a", "b", "expected"),
    [
        ("2.2.4", "2.2.4", 0),
        ("v2.2.4", "2.2.4", 0),
        ("2.2.1", "2.2.4", -1),
        ("2.2.4", "2.2.1", 1),
        ("2.10.0", "2.9.9", 1),
        ("2.2.5-dev.1", "2.2.4", 1),
        ("2.2.4", "2.2.5-dev.1", -1),
        ("2.2.5-dev.1", "2.2.5-dev.2", -1),
        ("2.2.5-dev.2", "2.2.5-dev.1", 1),
        ("2.2.5-dev.1", "2.2.5", -1),
        ("2.2.5", "2.2.5-dev.1", 1),
    ],
)
def test_ver_compare(a: str, b: str, expected: int) -> None:
    proc = bash_script(f'source "{INSTALL_SH}"; ver_compare "{a}" "{b}"')
    assert proc.returncode == 0, proc.stderr
    assert int(proc.stdout.strip()) == expected


def test_sourcing_does_not_run_entrypoint() -> None:
    proc = bash_script(f'source "{INSTALL_SH}"')
    assert proc.returncode == 0
    assert "[SUCCESS]" not in proc.stdout
    assert proc.stdout.strip() == ""


def test_piped_execution_runs_entrypoint() -> None:
    # Simulates curl -fsSL https://.../install.sh | bash -s -- --help
    with open(INSTALL_SH) as f:
        script_text = f.read()
    proc = subprocess.run(
        ["bash", "-s", "--", "--help"],
        input=script_text,
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    assert proc.returncode == 0, proc.stderr
    assert "SkillManager Linux Setup & Package Manager" in proc.stdout
    assert "Usage:" in proc.stdout


def make_stub_dpkg(bindir: Path, version: str) -> None:
    bindir.mkdir(parents=True, exist_ok=True)
    dpkg = bindir / "dpkg"
    dpkg.write_text(
        "#!/usr/bin/env bash\n"
        'if [ "$1" = "-s" ] && [ "$2" = "skill-manager" ]; then\n'
        '  echo "Package: skill-manager"\n'
        '  echo "Status: install ok installed"\n'
        f'  echo "Version: {version}"\n'
        "  exit 0\n"
        "fi\n"
        "exit 1\n"
    )
    dpkg.chmod(0o755)
    uname = bindir / "uname"
    uname.write_text("#!/usr/bin/env bash\necho x86_64\n")
    uname.chmod(0o755)


def run_update(tmp_path: Path, installed: str, target: str) -> subprocess.CompletedProcess:
    bindir = tmp_path / "bin"
    make_stub_dpkg(bindir, installed)
    env = dict(os.environ)
    env["PATH"] = f"{bindir}:{env['PATH']}"
    return subprocess.run(
        ["bash", str(INSTALL_SH), "--update", "--dry-run", "--version", target],
        capture_output=True,
        text=True,
        env=env,
        cwd=REPO_ROOT,
    )


def test_update_upgrade_path(tmp_path: Path) -> None:
    proc = run_update(tmp_path, installed="2.2.1", target="2.2.4")
    assert proc.returncode == 0, proc.stderr
    assert "Upgrade available: v2.2.1 -> v2.2.4" in proc.stdout
    assert "[DRY RUN] Would download and install SkillManager v2.2.4" in proc.stdout


def test_update_up_to_date(tmp_path: Path) -> None:
    proc = run_update(tmp_path, installed="2.2.4", target="2.2.4")
    assert proc.returncode == 0, proc.stderr
    assert "already up to date (v2.2.4)" in proc.stdout


def test_update_downgrade_from_dev_pre_release(tmp_path: Path) -> None:
    proc = run_update(tmp_path, installed="2.2.5-dev.1", target="2.2.4")
    assert proc.returncode == 0, proc.stderr
    assert "Downgrade available: v2.2.5-dev.1 -> v2.2.4" in proc.stdout
    assert "Target version:    v2.2.4" in proc.stdout
    assert "[DRY RUN] Would download and install SkillManager v2.2.4" in proc.stdout


def test_update_downgrade_target_older_than_installed(tmp_path: Path) -> None:
    proc = run_update(tmp_path, installed="2.2.4", target="2.2.1")
    assert proc.returncode == 0, proc.stderr
    assert "Downgrade available: v2.2.4 -> v2.2.1" in proc.stdout

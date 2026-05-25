"""
Purpose: Tests for the version bump calculator to ensure Semantic Versioning
pre-release state machine rules are correctly implemented.
Usage: Run via pytest `uv run pytest tests/test_version_bump_calculator.py`
"""

import subprocess
import sys
from pathlib import Path


# Helper to run the script
def run_calculator(version, commit_msg):
    script_path = Path(__file__).parent.parent / "scripts" / "version_bump_calculator.py"
    return subprocess.run(
        [sys.executable, str(script_path), version, commit_msg],
        capture_output=True,
        text=True
    )

def test_stable_to_dev():
    # 1.2.3 -> bump dev -> --patch --as-prerelease --prerelease-token dev
    res = run_calculator("1.2.3", "feat: new thing [bump dev]")
    assert res.returncode == 0
    assert res.stdout.strip() == "--patch --as-prerelease --prerelease-token dev"

def test_stable_to_patch():
    # 1.2.3 -> bump patch -> --patch
    res = run_calculator("1.2.3", "fix: bug [bump patch]")
    assert res.returncode == 0
    assert res.stdout.strip() == "--patch"

def test_stable_to_minor():
    res = run_calculator("1.2.3", "feat: feature [bump minor]")
    assert res.returncode == 0
    assert res.stdout.strip() == "--minor"

def test_stable_to_major():
    res = run_calculator("1.2.3", "feat!: breaking [bump major]")
    assert res.returncode == 0
    assert res.stdout.strip() == "--major"

def test_dev_to_dev():
    # 1.2.4-dev.2 -> bump dev -> --prerelease --prerelease-token dev
    res = run_calculator("1.2.4-dev.2", "feat: work [bump dev]")
    assert res.returncode == 0
    assert res.stdout.strip() == "--prerelease --prerelease-token dev"

def test_dev_to_patch_graduation():
    # 1.2.4-dev.2 -> bump patch -> --patch
    res = run_calculator("1.2.4-dev.2", "fix: finalize [bump patch]")
    assert res.returncode == 0
    assert res.stdout.strip() == "--patch"

def test_dev_to_minor():
    res = run_calculator("1.2.4-dev.2", "feat: switch to minor [bump minor]")
    assert res.returncode == 0
    assert res.stdout.strip() == "--minor"

def test_scope_creep_preminor():
    # 1.2.4-dev.2 -> bump preminor -> --minor --as-prerelease --prerelease-token dev
    res = run_calculator("1.2.4-dev.2", "feat: big [bump preminor]")
    assert res.returncode == 0
    assert res.stdout.strip() == "--minor --as-prerelease --prerelease-token dev"

def test_cross_grade_error():
    # 1.3.0-dev.2 -> bump patch -> ERROR
    res = run_calculator("1.3.0-dev.2", "fix: cross grade [bump patch]")
    assert res.returncode != 0
    assert "Cross-grade detected" in res.stderr

def test_cross_grade_major_error():
    # 2.0.0-dev.1 -> bump patch -> ERROR
    res = run_calculator("2.0.0-dev.1", "fix: cross grade [bump patch]")
    assert res.returncode != 0
    assert "Cross-grade detected" in res.stderr

def test_fallback_tags():
    # Legacy tags support
    res = run_calculator("1.2.3", "fix: test [patch]")
    assert res.returncode == 0
    assert res.stdout.strip() == "--patch"

def test_no_tag():
    res = run_calculator("1.2.3", "fix: nothing")
    assert res.returncode == 0
    assert res.stdout.strip() == ""

"""Lightweight tests for the MCP bridge functions that need no Qt/AppController.

These exercise the parts of ``skill_manager.mcp.bridge`` that are safe to run
headless: the async job buffer (``run_async_job`` / ``get_job``) and the
filesystem grep (``static_analyze``). They never call ``get_app_controller()``,
so no Qt application is constructed.
"""

from __future__ import annotations

import time
from typing import Any

import pytest

from skill_manager.mcp import bridge


def test_run_async_job_returns_id_and_buffers() -> None:
    """run_async_job returns a job_id and records a running buffer immediately."""
    job_id = bridge.run_async_job(lambda: 42)

    assert isinstance(job_id, str) and job_id
    job = bridge.get_job(job_id)
    assert job is not None
    assert job["job_id"] == job_id
    assert job["status"] in {"running", "done", "error"}


def test_run_async_job_captures_result() -> None:
    """A completed job buffer carries the return value and done status."""
    job_id = bridge.run_async_job(lambda: {"ok": True})

    # Poll briefly; the fallback daemon thread should finish quickly.
    job: dict[str, Any] | None = None
    for _ in range(50):
        job = bridge.get_job(job_id)
        if job is not None and job["status"] == "done":
            break
        time.sleep(0.02)

    assert job is not None
    assert job["status"] == "done"
    assert job["result"] == {"ok": True}
    assert job["error"] is None


def test_run_async_job_captures_exception() -> None:
    """A failing job records the error and an error status."""
    job_id = bridge.run_async_job(lambda: (_ for _ in ()).throw(RuntimeError("kaboom")))

    job = None
    for _ in range(50):
        job = bridge.get_job(job_id)
        if job is not None and job["status"] == "error":
            break
        time.sleep(0.02)

    assert job is not None
    assert job["status"] == "error"
    assert "kaboom" in (job["error"] or "")


def test_get_job_unknown_returns_none() -> None:
    """get_job returns None for an id that was never dispatched."""
    assert bridge.get_job("does-not-exist") is None


def test_static_analyze_finds_pattern(tmp_path: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    """static_analyze greps a directory tree and returns file/line/text matches."""
    monkeypatch.setattr(bridge, "_REPO_ROOT", tmp_path)
    (tmp_path / "a.py").write_text("x = 1\nSECRET_TOKEN = 'abc'\ny = 2\n", encoding="utf-8")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.py").write_text("print('hello')\nSECRET_TOKEN = 9\n", encoding="utf-8")

    matches = bridge.static_analyze(pattern="SECRET_TOKEN", path=".")

    assert len(matches) == 2
    files = {m["file"] for m in matches}
    assert any("a.py" in f for f in files)
    assert any("b.py" in f for f in files)
    assert all(m["text"] for m in matches)


def test_static_analyze_invalid_pattern(tmp_path: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    """An invalid regex yields a structured error entry, not a crash."""
    monkeypatch.setattr(bridge, "_REPO_ROOT", tmp_path)

    matches = bridge.static_analyze(pattern="([", path=".")

    assert len(matches) == 1
    assert "error" in matches[0]
    assert "invalid_pattern" in matches[0]["error"]


def test_static_analyze_missing_path(tmp_path: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    """A non-existent search root yields an empty match list."""
    monkeypatch.setattr(bridge, "_REPO_ROOT", tmp_path)

    matches = bridge.static_analyze(pattern="x", path="no-such-dir-xyz")

    assert matches == []

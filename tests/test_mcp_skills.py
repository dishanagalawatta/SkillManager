"""Unit tests for the new SkillManager MCP skill management tools.

Exercises handlers in ``skill_manager.mcp.tools.skills`` and ``skill_manager.mcp.tools.write``.
"""

from __future__ import annotations

from typing import Any

import anyio
import pytest

from skill_manager.mcp.tools import skills as skills_mod, write as write_mod


def _run(coro: Any) -> Any:
    return anyio.run(lambda: coro)


# ---------------------------------------------------------------------------
# skills.py handlers
# ---------------------------------------------------------------------------
def test_handle_get_skill_missing_arg() -> None:
    """sm_get_skill with empty skill_id returns error."""
    result = _run(skills_mod._handle_get_skill({}))
    assert result.ok is False
    assert "skill_id" in (result.error or "")


def test_handle_get_skill_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """sm_get_skill returns skill detail on match."""
    fake_skill = {"found": True, "skill": {"name": "test-skill", "local_path": "/path"}}
    monkeypatch.setattr(skills_mod, "get_skill", lambda skill_id: fake_skill)

    result = _run(skills_mod._handle_get_skill({"skill_id": "test-skill"}))
    assert result.ok is True
    assert result.data == fake_skill


def test_handle_get_skill_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    """sm_get_skill returns error when not found."""
    monkeypatch.setattr(skills_mod, "get_skill", lambda skill_id: {"found": False})

    result = _run(skills_mod._handle_get_skill({"skill_id": "unknown"}))
    assert result.ok is False
    assert "not found" in (result.error or "")


def test_handle_search_skills_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """sm_search_skills returns matches."""
    fake_results = [{"name": "test-skill", "local_path": "/path"}]
    monkeypatch.setattr(skills_mod, "search_skills", lambda **kwargs: fake_results)

    result = _run(skills_mod._handle_search_skills({"query": "test"}))
    assert result.ok is True
    assert result.data == {"count": 1, "skills": fake_results}


def test_handle_sync_skills_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """sm_sync_skills returns sync summary."""
    fake_sync = {"synced": True, "count": 10, "message": "Synced"}
    monkeypatch.setattr(skills_mod, "sync_skills", lambda force_full_scan: fake_sync)

    result = _run(skills_mod._handle_sync_skills({}))
    assert result.ok is True
    assert result.data == fake_sync


# ---------------------------------------------------------------------------
# write.py new handlers
# ---------------------------------------------------------------------------
def test_create_skill_gated_when_read_only() -> None:
    """sm_create_skill refuses execution when allow_write is False."""
    handlers = write_mod.get_handlers(allow_write=False)
    result = handlers["sm_create_skill"]({"name": "new-skill", "content": "..."})

    assert result.ok is False
    assert "write mode disabled" in (result.error or "")


def test_create_skill_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """sm_create_skill creates skill when allow_write is True."""
    fake_created = {"created": True, "name": "demo", "local_path": "/demo"}
    monkeypatch.setattr(write_mod, "create_skill", lambda **kwargs: fake_created)

    handlers = write_mod.get_handlers(allow_write=True)
    result = handlers["sm_create_skill"]({"name": "demo", "content": "# Demo"})

    assert result.ok is True
    assert result.data == fake_created


def test_update_skill_gated_when_read_only() -> None:
    """sm_update_skill refuses execution when allow_write is False."""
    handlers = write_mod.get_handlers(allow_write=False)
    result = handlers["sm_update_skill"]({"skill_id": "demo", "content": "..."})

    assert result.ok is False
    assert "write mode disabled" in (result.error or "")


def test_update_skill_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """sm_update_skill updates skill when allow_write is True."""
    fake_updated = {"updated": True, "skill_id": "demo", "local_path": "/demo"}
    monkeypatch.setattr(write_mod, "update_skill", lambda **kwargs: fake_updated)

    handlers = write_mod.get_handlers(allow_write=True)
    result = handlers["sm_update_skill"]({"skill_id": "demo", "content": "Updated"})

    assert result.ok is True
    assert result.data == fake_updated


def test_deploy_gated_when_read_only() -> None:
    """sm_deploy refuses execution when allow_write is False."""
    handlers = write_mod.get_handlers(allow_write=False)
    result = handlers["sm_deploy"]({"skill_id": "demo", "target": "proj"})

    assert result.ok is False
    assert "write mode disabled" in (result.error or "")


def test_deploy_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """sm_deploy deploys skill when allow_write is True."""
    fake_deployed = {"deployed": True, "skill_id": "demo", "target": "/proj"}
    monkeypatch.setattr(write_mod, "deploy", lambda skill_id, target: fake_deployed)

    handlers = write_mod.get_handlers(allow_write=True)
    result = handlers["sm_deploy"]({"skill_id": "demo", "target": "proj"})

    assert result.ok is True
    assert result.data == fake_deployed

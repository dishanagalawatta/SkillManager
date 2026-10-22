"""Regression tests for the defects found while auditing the model layer.

* B1 — the main-category sort order used stale emoji, pushing four of the
  six main categories into a fallback bucket.
* B2 — a model role was advertised to QML but never served, so
  ``model.searchText`` was always undefined.
* B3 — the search path evaluated a Pydantic validation for every hit on
  every keystroke, because ``dict.get`` evaluates its default eagerly.
* B4 — the git probe passed GitPython's ``kill_after_timeout``, which
  raises on Windows, so every git package failed to check there.
* B12 — ``_batch_reset_needed`` was only ever assigned inside the batch
  helpers, so ``onIncubationReady`` could read an unset attribute.
"""

import subprocess

import pytest

from skill_manager.core.models import filter_engine as filter_engine_mod
from skill_manager.core.models.entities import Skill
from skill_manager.core.models.pipeline import PipelineMixin
from skill_manager.core.models.roles import RolesMixin
from skill_manager.core.parsing.constants import MAIN_CATEGORIES_MAPPING
from skill_manager.core.skill_packages import versioning

# ── B1: the category order must follow the canonical mapping ─────────────


def test_every_main_category_has_a_sort_prefix():
    """No main category may fall into the "99_" fallback bucket."""
    for name in MAIN_CATEGORIES_MAPPING:
        prefix = filter_engine_mod.MAIN_CATEGORY_ORDER.get(name)
        assert prefix is not None, f"{name!r} has no sort prefix"
        assert not prefix.startswith("99_"), f"{name!r} fell into the fallback bucket"


def test_the_order_matches_the_canonical_mapping():
    """The order is derived, so it cannot drift from the mapping again."""
    expected = [f"{index}_{name}" for index, name in enumerate(MAIN_CATEGORIES_MAPPING, start=1)]
    assert list(filter_engine_mod.MAIN_CATEGORY_ORDER.values()) == expected


def test_sort_key_orders_the_main_categories():
    """Two skills in different main categories sort by the mapped order."""
    first_name = next(iter(MAIN_CATEGORIES_MAPPING))
    second_name = list(MAIN_CATEGORIES_MAPPING)[1]

    first = Skill(name="a", main_category=first_name, category="X")
    second = Skill(name="b", main_category=second_name, category="X")

    assert filter_engine_mod.FilterEngine.sort_key(first) < (
        filter_engine_mod.FilterEngine.sort_key(second)
    )


# ── B2: no role may be advertised without being served ───────────────────


def test_no_dead_search_text_role():
    """The unused searchText role is gone from the model's public surface."""
    assert not hasattr(RolesMixin, "SearchTextRole")
    from skill_manager.core.models.qt_model import SkillModel

    assert "searchText" not in {bytes(name).decode() for name in SkillModel().roleNames().values()}


def test_every_advertised_role_is_served():
    """Every role in ``roleNames()`` must be handled by ``data()``."""
    from skill_manager.core.models.qt_model import SkillModel

    served = set(SkillModel._ALL_ROLES)
    assert served, "the model must advertise roles"
    # The role numbers are contiguous from UserRole+1.
    numbers = sorted(int(r) for r in served)
    assert numbers == list(range(numbers[0], numbers[0] + len(numbers)))


# ── B3: the search path must not validate every hit ─────────────────────


class _FakeSearchEngine:
    def __init__(self, hits):
        self._hits = hits

    def query(self, _text, valid_paths=None):
        return [(hit, 100.0) for hit in self._hits]


def test_search_uses_the_known_skill_instead_of_revalidating(monkeypatch):
    """A hit that is already in the model must not be re-validated.

    ``dict.get(key, default)`` evaluates the default eagerly, so the old
    code ran a full Pydantic validation for every hit on every keystroke —
    and raised on a record the model already held a valid copy of.
    """
    skill = Skill(name="Known", local_path="/known/SKILL.md", category="X")
    invalid_hit = {"local_path": "/known/SKILL.md", "name": ""}

    model = _make_model([skill])
    model._search_engine = _FakeSearchEngine([invalid_hit])
    model.state.filter_text = "known"

    rows = model._execute_filter_logic()

    assert len(rows) == 1
    # The known object is returned — the invalid dict never reaches the
    # validator, so the malformed name cannot raise here.
    assert rows[0] is skill


def _make_model(skills):
    """A minimal object exposing the pipeline mixin's filter logic."""
    from skill_manager.core.models.filter_engine import FilterEngine

    class _Model(PipelineMixin):
        def __init__(self):
            self._all_skills = list(skills)
            self._filtered_skills: list[Skill] = []
            self.state = filter_engine_mod.FilterState()
            self._engine = FilterEngine()
            self._search_engine = None
            self._suppress_layout = False
            self._batch_apply_needed = False
            self._batch_reset_needed = False
            self._incubating = False
            self._pending_signals = []
            self._replay_deferred = False
            self._selected_ids = {}

    return _Model()


# ── B4: the git probe must work on Windows ──────────────────────────────


class _FakeWindowsProc:
    """Stand-in for the Popen handle GitPython returns on Windows."""

    def __init__(self, out: bytes, returncode: int = 0):
        self._out = out
        self.returncode = returncode
        self.killed = False

    def communicate(self, timeout=None):
        return (self._out, b"")

    def kill(self):
        self.killed = True


class _FakeWindowsWrapper:
    def __init__(self, proc):
        self.proc = proc


def _fake_windows_wrapper(out: bytes, returncode: int = 0):
    return _FakeWindowsWrapper(_FakeWindowsProc(out, returncode))


def test_git_probe_never_passes_kill_after_timeout_on_windows(monkeypatch):
    """GitPython raises on ``kill_after_timeout`` under Windows.

    Passing it made every git package fail to check on the app's primary
    platform, so the packages were permanently reported as "could not
    check".
    """
    import git

    recorded: dict = {}

    def fake_execute(self, command, **kwargs):  # noqa: ANN001
        recorded.update(kwargs)
        recorded["command"] = list(command)
        return _fake_windows_wrapper(b"deadbeef\trefs/tags/v1.2.3\n")

    monkeypatch.setattr(git.cmd.Git, "execute", fake_execute)
    monkeypatch.setattr(versioning.os, "name", "nt")

    probe = versioning.probe_git_remote_version("https://github.com/acme/skills.git")

    assert probe.ok is True
    assert probe.version == "v1.2.3"
    assert "kill_after_timeout" not in recorded


def test_git_probe_passes_kill_after_timeout_off_windows(monkeypatch):
    """The POSIX path keeps GitPython's own timeout handling."""
    import git

    recorded: dict = {}

    def fake_execute(self, command, **kwargs):  # noqa: ANN001
        recorded.update(kwargs)
        return "deadbeef\trefs/tags/v2.0.0\n"

    monkeypatch.setattr(git.cmd.Git, "execute", fake_execute)
    monkeypatch.setattr(versioning.os, "name", "posix")

    probe = versioning.probe_git_remote_version("https://github.com/acme/skills.git")

    assert probe.ok is True
    assert recorded.get("kill_after_timeout") is not None


def test_git_probe_windows_path_kills_a_hung_process(monkeypatch):
    """The Windows path enforces the deadline itself."""
    import git

    class _FakeProc:
        returncode = None

        def __init__(self):
            self.killed = False

        def communicate(self, timeout=None):
            raise subprocess.TimeoutExpired(cmd="git", timeout=timeout or 0)

        def kill(self):
            self.killed = True

    proc = _FakeProc()

    class _Wrapper:
        def __init__(self):
            self.proc = proc

    monkeypatch.setattr(git.cmd.Git, "execute", lambda self, command, **kw: _Wrapper())
    monkeypatch.setattr(versioning.os, "name", "nt")

    probe = versioning.probe_git_remote_version("https://github.com/acme/skills.git")

    assert probe.ok is False
    assert "timed out" in probe.reason
    assert proc.killed is True


# ── B12: the batch flag must always exist ───────────────────────────────


def test_batch_reset_needed_is_initialised():
    """``onIncubationReady`` reads the flag, so it must always be set."""
    from skill_manager.core.models.qt_model import SkillModel

    model = SkillModel()
    assert model._batch_reset_needed is False
    assert model._batch_apply_needed is False


@pytest.mark.parametrize("attribute", ["_batch_apply_needed", "_batch_reset_needed"])
def test_batch_flags_exist_on_a_fresh_model(attribute):
    from skill_manager.core.models.qt_model import SkillModel

    assert hasattr(SkillModel(), attribute)

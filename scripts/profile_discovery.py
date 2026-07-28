"""Profiling harness: replicate DiscoveryController._build_prepared_states on real data.

Measures each heavy stage of the discovery->prepared-state pipeline:
  1. discover_all (filesystem scan + parse + cache)
  2. Skill.from_dict_fast xN
  3. FilterEngine.filter_skills x2 + prepare_rows x2 + build_visible_rows x2
  4. SearchEngine build
  5. SkillModel.replacePreparedState (main-thread commit)
Patches analytics to no-op so import doesn't block on network.
"""

import os
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("SKILL_MANAGER_SKIP_INITIAL_LOAD", "1")

# Patch analytics before any submodule imports it.
import skill_manager.core.analytics as _an  # noqa: E402


def _noop(*_args, **_kwargs):  # analytics no-op so import never blocks on network
    return None


for _n in ("capture_event", "capture_exception", "capture"):
    if hasattr(_an, _n):
        setattr(_an, _n, _noop)

from skill_manager.core.config import ConfigManager  # noqa: E402
from skill_manager.core.discovery import DiscoveryService  # noqa: E402
from skill_manager.core.models.entities import FilterState, PreparedModelState, Skill  # noqa: E402
from skill_manager.core.models.filter_engine import FilterEngine  # noqa: E402
from skill_manager.core.models.qt_model import SkillModel  # noqa: E402
from skill_manager.core.search import SearchEngine  # noqa: E402


def _time(label, fn):
    t0 = time.perf_counter()
    r = fn()
    print(f"{label:46s} {(time.perf_counter() - t0) * 1000:8.1f} ms")
    return r


cfg = ConfigManager()
sources = cfg.get("sources", []) or []
projects = cfg.get("projects", []) or []
print(f"sources={len(sources)} projects={len(projects)}")
for s in sources[:3]:
    print("  src:", s, "exists=", os.path.isdir(s))

print("\n=== STAGE 1: discover_all ===")
svc = DiscoveryService(sources=sources, projects=projects)

res = _time(
    "discover_all(force_full_scan=True)",
    lambda: svc.discover_all(cache_callback=None, force_full_scan=True),
)
res_cached = _time(
    "discover_all(use_cache=True)",
    lambda: svc.discover_all(cache_callback=None, force_full_scan=False),
)
records = res_cached.get("skills", [])
print(f"  skills discovered: {len(records)}")

print("\n=== STAGE 2: entity conversion ===")
all_skills = _time(
    f"Skill.from_dict_fast x{len(records)}", lambda: [Skill.from_dict_fast(r) for r in records]
)

print("\n=== STAGE 3: FilterEngine (library + quickcopy) ===")
eng = FilterEngine()
fs = FilterState()
lib_f = _time("filter_skills (library)", lambda: eng.filter_skills(all_skills, fs))
_time("prepare_rows (library)", lambda: eng.prepare_rows(lib_f))
qc_f = _time("filter_skills (quickcopy)", lambda: eng.filter_skills(all_skills, fs))
_time("prepare_rows (quickcopy)", lambda: eng.prepare_rows(qc_f))

print("\n=== STAGE 4: SearchEngine build ===")
idx_skills = [
    {
        "local_path": s.local_path,
        "name": s.name,
        "category": s.category,
        "description": s.description,
        "metadata": {"tags": s.tags},
    }
    for s in all_skills
]
_time("SearchEngine(skills_for_index)", lambda: SearchEngine(idx_skills))

print("\n=== STAGE 5: SkillModel commit ===")
cats = sorted({s.category for s in all_skills if s.category})
mock_se = SearchEngine(idx_skills)
ps = PreparedModelState(
    all_skills=all_skills,
    search_engine=mock_se,
    all_filtered_skills=lib_f,
    visible_rows=lib_f,
    categories=cats,
    status="prof",
    generation=1,
)
model = SkillModel()
_time("replacePreparedState", lambda: model.replacePreparedState(ps))

print("\nDONE")

# Tech Stack

> Locked technology choices for SkillManager. Changing one requires
> a new ADR under [`../ADR_INDEX.md`](../ADR_INDEX.md).

## Runtime

- Python 3.12+
- PySide6 (Qt 6.8+)
- QML declarative UI

## Data & Config

- pydantic, pydantic-settings
- platformdirs
- pathspec
- orjson
- diskcache

## Parsing

- markdown-it-py
- python-frontmatter
- rapidfuzz

## Networking & Filesystem

- httpx, tenacity
- watchdog
- gitpython

## Telemetry

- sentry-sdk
- posthog

## Scheduling

- apscheduler
- pynput

## Tooling

- uv (package manager)
- ruff (lint + format)
- pytest, pytest-xdist, pytest-qt, pytest-cov, pytest-asyncio
- python-semantic-release 10.5.3 (see ADR-0009)
- PyInstaller (build)
- Inno Setup (Windows installer)

## Removed

- tufup — replaced by GitHub Releases API (see ADR-0010).

## Cross-references

- Product: [`conductor/product.md`](product.md)
- ADRs: [`../ADR_INDEX.md`](../ADR_INDEX.md)
- Environment: [`../docs/ENVIRONMENT.md`](../docs/ENVIRONMENT.md)

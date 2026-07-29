# SkillManager Documentation

> Complete documentation hub for SkillManager v1.8.0.
> For the project overview, quickstart, and architecture summary, see the [root README](../README.md).

---

## Getting Started

| Document | Description |
|----------|-------------|
| [INSTALL.md](INSTALL.md) | Installation instructions for all platforms |
| [USER_GUIDE.md](USER_GUIDE.md) | End-user manual: Library, QuickCopy, Settings, Screenshot |
| [ENVIRONMENT.md](ENVIRONMENT.md) | Full environment variable reference |
| [../environments/README.md](../environments/README.md) | Tier-specific env setup (dev / staging / prod) |

---

## Development

| Document | Description |
|----------|-------------|
| [DEVELOPMENT.md](DEVELOPMENT.md) | Developer setup, conventions, and debug workflows |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Contribution guidelines and PR process |
| [API.md](API.md) | QML/Python controller API reference (`@Slot`, `@Signal`, `@Property`) |
| [API/index.md](API/index.md) | API landing page: controller summary + MCP tool inventory |
| [MCP_SERVER.md](MCP_SERVER.md) | MCP server setup, all tool schemas, and client configs |

---

## Architecture

| Document | Description |
|----------|-------------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Full system architecture with data flow diagrams |
| [../DESIGN.md](../DESIGN.md) | Design system, patterns, threading model, QML conventions |
| [../ADR_INDEX.md](../ADR_INDEX.md) | Architecture Decision Records index |
| [adr/](adr/) | Individual ADR files (`ADR-0010` through `ADR-0022`) |
| [RIBBON_COLLAPSE.md](RIBBON_COLLAPSE.md) | GlassPill ribbon collapse specification |

---

## Operations

| Document | Description |
|----------|-------------|
| [CI_CD.md](CI_CD.md) | CI/CD pipeline reference (GitHub Actions) |
| [RELEASING.md](RELEASING.md) | Release checklist, semantic-release workflow, versioning |
| [VERSIONING.md](VERSIONING.md) | Semantic versioning policy and commit keyword conventions |
| [SECURITY.md](SECURITY.md) | Security policy and token handling guidelines |
| [HOUSEKEEPING.md](HOUSEKEEPING.md) | Workspace cleanup rules, targets, and exclusions |
| [../conductor/workflow.md](../conductor/workflow.md) | Conductor track lifecycle and metadata schema |

---

## Features & Reference

| Document | Description |
|----------|-------------|
| [CATEGORIES.md](CATEGORIES.md) | Skill categorization system and taxonomy |
| [PRODUCT_TELEMETRY.md](PRODUCT_TELEMETRY.md) | PostHog/Sentry integration and opt-in mechanics |

---

## Quick Links

- **Run app**: `uv run skill-manager`
- **Run MCP server**: `uv run skill-manager --mcp`
- **Run tests**: `uv run pytest -n auto --dist loadfile`
- **Lint**: `uv run ruff check src tests --fix`
- **All checks**: `python scripts/dev_test.py`
- **Build**: `uv run skill-manager-build`

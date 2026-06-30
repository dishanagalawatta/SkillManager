# Environments Setup Guide

> SkillManager uses a tiered environment configuration system.
> Each tier has specific defaults for Qt/QML, logging, and telemetry.

## Tier Matrix

| Tier | Log Level | Telemetry | QML Cache | Testing | Headless |
|------|-----------|-----------|-----------|---------|----------|
| **Dev** | `DEBUG` | Disabled | Disabled | On | `offscreen` |
| **Staging** | `WARNING` | Enabled (staging tokens) | Disabled | On | `offscreen` |
| **Production** | `ERROR` | Enabled (prod tokens) | Enabled | Off | Native |

## Setup

1. **Choose your tier:**

   ```bash
   # Development (default)
   cp environments/.env.dev.example .env

   # Staging
   cp environments/.env.staging.example .env

   # Production
   cp environments/.env.prod.example .env
   ```

2. **Fill in secrets** (staging/production only):

   | Variable | Where to get it |
   |----------|-----------------|
   | `POSTHOG_PROJECT_TOKEN` | PostHog dashboard → Project Settings → API Key |
   | `POSTHOG_HOST` | PostHog dashboard → Project Settings → Instance |
   | `SENTRY_DSN` | Sentry dashboard → Project Settings → Client Keys |

3. **Validate** (optional):

   ```bash
   python -c "from dotenv import load_dotenv; load_dotenv(); import os; assert os.getenv('POSTHOG_PROJECT_TOKEN'), 'Missing POSTHOG_PROJECT_TOKEN'"
   ```

## Security

- **Never commit `.env`** — it contains live API tokens.
- `.env` is gitignored (`.gitignore`).
- `.env.example` is the canonical reference for all supported variables.
- Rotate tokens immediately if accidentally committed (PostHog: Settings → Revoke).

## Cross-references

- [`.env.example`](../.env.example) — canonical template with all variables
- [`docs/ENVIRONMENT.md`](../docs/ENVIRONMENT.md) — full environment variable reference
- [`docs/PRODUCT_TELEMETRY.md`](../docs/PRODUCT_TELEMETRY.md) — PostHog/Sentry integration details
- [`docs/HOUSEKEEPING.md`](../docs/HOUSEKEEPING.md) — cleanup rules for `.env` and `data/`

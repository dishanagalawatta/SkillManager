# ADR-0043: PR-Gated `main` and Manual, Two-Step Releases

> Status: **Accepted**
> Date: 2026-10-20
> Owner: @DIKKA

## Context

Releases used to be fully automated: a push to `main` ran an `Auto Version &
Release` workflow that detected a bump from commit messages, bumped the version,
tagged, and pushed. That model had accumulated three problems.

**It could not be secured.** The workflow needed to push to `main`, so `main`
could not require pull requests or status checks. Force-pushes and deletion were
blocked, but any push that reached `main` could release.

**There was no free signing path for the bot.** Windows signing moved to the
SignPath Foundation route, which requires a human to approve every signing
request and issues artifacts through its own service. A release pipeline that
fires on every push does not fit a flow with a mandatory manual approval step.

**Version bumps were being inferred.** With `python-semantic-release` remnants
in the tree and commit-parsing code in `scripts/release.py`, the version could
change without anyone deciding it should. The maintainer now wants to pump the
version deliberately.

On 2026-10-19 the repository was deleted and recreated to purge a leaked signing
key from history. That reset also removed every previous pull request ref, which
made it possible to install rules the old repository could never accept.

## Decision

**Releases are manual and two-step.**

1. `uv run python scripts/release.py <bump>` synchronizes the seven version
   locations, commits them on `release/vX.Y.Z`, pushes the branch, and opens a
   pull request.
2. After the pull request merges, `uv run python scripts/release.py tag` creates
   the annotated tag `vX.Y.Z` on `main` and pushes it. The tag push is what
   triggers `release-build.yml`.

The target argument is required. There is no `auto` mode, no commit-message
detection, and no workflow that bumps the version.

**`main` is protected by ruleset `25431580` with no bypass actors:**

| Rule | Effect |
|---|---|
| `deletion` | `main` cannot be deleted |
| `non_fast_forward` | force-pushes are rejected for everyone, including the owner |
| `pull_request` | changes must arrive through a pull request; 0 approvals required |
| `required_status_checks` → `CI Gate` | a pull request cannot merge until lint and both test jobs pass |

Because no actor can bypass, the owner merges their own pull requests instead of
pushing to `main`.

**`ci.yml` runs on every pull request with no `paths-ignore`.** A workflow that
`paths-ignore` skips never reports `CI Gate`, which would leave a docs-only pull
request permanently unmergeable. The `pull_request` trigger also names its
activity types explicitly: a `pull_request:` key whose body is empty or
comment-only is parsed as null and GitHub then silently creates no run at all.

**The release commit does not carry `[skip ci]`.** It did under the push-to-main
model, where skipping CI saved a redundant run. In a pull request that same
marker skips the required check and makes the release PR unmergeable.

## Consequences

**Positive**

- Every change to `main` is linted and tested, including documentation changes.
- Force-pushes and deletion are impossible for everyone, which is stronger than
  the previous "no bypass" setup that still allowed direct pushes.
- Releases are a deliberate act with an explicit version, and each one has a pull
  request that records what changed.
- The manual approval step that SignPath requires now sits naturally in the flow.

**Negative**

- A hotfix costs a branch, a pull request, and roughly five minutes of CI.
- The release takes two commands and a merge instead of one command.
- If GitHub Actions suffers an outage, `main` cannot be updated at all.

**Neutral**

- The owner can relax this by adding a `bypass_actors` entry with
  `bypass_mode: "always"` for the repository-admin role, at the cost of allowing
  direct and force pushes again.

## Alternatives Considered

| Alternative | Why rejected |
|---|---|
| Keep auto-release and give it a PAT that can bypass | A long-lived token with push rights on `main` is the same class of secret that caused the 2026-10-19 purge. It also conflicts with SignPath's manual approval step. |
| Admin bypass so the owner can keep pushing directly | `required_status_checks` gates direct pushes, so bypassing it means `bypass_mode: "always"`, which also re-allows force-pushes and defeats the protection. |
| Classic branch protection instead of a ruleset | It rejects bypass lists on user-owned repositories (*"Only organization repositories can have users and team restrictions"*), and it cannot express required checks without also blocking direct pushes. |
| Transfer the repository to an organization so the Actions integration can be a bypass actor | Solves the bypass problem but changes ownership, billing surface, and the publishing identity for no functional gain the maintainer asked for. |
| Tag the release branch commit before the merge | The tag would not be an ancestor of `main`, so `git describe` on `main` would not see it and the built commit would not be the merged one. |

## References

- [`docs/RELEASING.md`](../RELEASING.md) — release runbook
- [`docs/CI_CD.md`](../CI_CD.md) — pipeline reference and branch protection
- [`docs/VERSIONING.md`](../VERSIONING.md) — versioning rules
- [`AGENTS.md`](../../AGENTS.md) — contributor and agent workflow

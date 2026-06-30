# ADR-0010: Drop TUF (The Update Framework)

> Status: **Accepted**
> Date: 2026-05-15
> Owner: @DIKKA

## Context

SkillManager originally integrated TUF for secure app update verification. TUF provided cryptographic signing and verification of update bundles. However, the overhead of managing TUF keys, repository metadata, and the complexity of the integration outweighed the security benefits for a desktop application distributed via installer.

## Decision

Remove all TUF-related code and artifacts:

- `tuf_keys/` directory
- `tuf_repo/` directory
- `.tufup-repo-config` file
- TUF client initialization in `AppUpdateController`
- TUF bundle validation in `AppUpdateService`

Replaced with simple HTTP(S) update checking with signature verification via `cryptography` library.

## Consequences

### Positive

- Removed ~500 lines of TUF-related code
- Eliminated TUF key management burden
- Simplified update flow (single HTTP check → download → verify → apply)
- Reduced dependency surface (removed `tuf` package)

### Negative

- Lost TUF's advanced security features (rollback protection, delegation)
- Acceptable trade-off for desktop distribution model

### Neutral

- Update mechanism now uses standard HTTPS + signature verification
- `tuf_keys/`, `tuf_repo/`, `.tufup-repo-config` added to `.gitignore`

## Alternatives Considered

### Keep TUF

Maintained the full TUF integration. Rejected due to operational complexity and low risk profile of desktop distribution.

### Use only HTTPS

Rejected — provides no tamper detection after download.

## References

- [TUF Specification](https://theupdateframework.io/specification/)
- [`docs/HOUSEKEEPING.md`](../HOUSEKEEPING.md) — TUF artifacts listed for cleanup

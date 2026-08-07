# os-zapret2-restyle — Current state

Project: `os-zapret2-restyle`
Primary branch: `main`
Published stable release/package: `v0.3.2` / `os-zapret2-restyle-0.3.2_1.pkg`
Latest published testing prerelease: `v0.3.3_5` / `os-zapret2-restyle-0.3.3_5.pkg`
Current source line: `VERSION=0.3.3`
Current corrective package revision: `PLUGIN_REVISION=10`
Target ABI: **FreeBSD:15:amd64 only**

## Historical live boundary

`v0.3.3_5` remains the latest owner-tested package. Revision `_6` corrected its confirmed stage-50/stage-90 defects but was not owner-tested before the third audit reopened the corrective series. Live verification remains paused until Patch 8 designates a later candidate.

## Third audit corrective series

Status: **IN PROGRESS**

Authoritative plan: `docs/audit/AUDIT-2026-08-07-STRATEGY-LAB-THIRD-AUDIT.md`.

## Patch progress

### Patch 1 — documentation and corrective plan

Status: **MERGED AND VERIFIED** — PR #115, main `ed82ddff891ece514fac01895c197ef07d844557`.

### Patch 2 — ordinary stale recovery and timeout chain

Status: **MERGED AND VERIFIED** — PR #116, main `dd95d77e4d75e6751315ff893798cc2ea66a9330`; CI `31151805919`; FreeBSD 15 artifact `8983642442`, package `_7`.

### Patch 3 — circular stale recovery lifecycle ownership

Status: **MERGED AND VERIFIED** — PR #117, main `f0c43de7133f8ba337a5458de0803409949a0096`; CI `31152455413`; FreeBSD 15 artifact `8983891990`, package `_8`.

### Patch 4 — remove load-order overrides and obsolete hooks

Status: **MERGED AND VERIFIED** — PR #118, main `15ed2b057ca94a1a780ecf9da9f304d0e6cd652c`; latest-head CI `31154664416` passed the complete corrective matrix, unique-module-namespace gate, obsolete-surface contract, repository validation, and FreeBSD 15 package build. Artifact `8984745215` contains `os-zapret2-restyle-0.3.3_9.pkg`.

`SL3-003` + `SL3-006` source scope is implemented: load order no longer selects worker behavior, `worker_state_serialization.sh` and transitional skip hooks are removed, canonical state writers retain lock/revision semantics, circular eligibility uses the TLS 1.3 circular subset, and the namespace contract rejects future duplicate functions in jointly loaded worker modules.

Implementation log: `docs/devlog/2026-08-07-v0.3.3_9-module-order.md`.

### Patch 5 — serialize worker state transitions

Status: **SOURCE IMPLEMENTED — PR/CI VERIFICATION PENDING**

Package revision: `_10`.

Implemented scope for `SL3-004`:

- `worker_skip_unfinished()` no longer reads/replaces `status.json` directly;
- skip state now uses the canonical `strategy_lab_state_transform()` lock, atomic replacement, and revision increment;
- cancel, repeated cancel, unfinished-stage skip, finalization, and terminal-state protection are exercised in one race regression;
- cancellation timestamp and boolean must survive concurrent skip/finalization state changes;
- the regression rejects reintroduction of the old private `.worker-skip.*` writer.

Implementation log: `docs/devlog/2026-08-07-v0.3.3_10-state-serialization.md`.

## Remaining approved sequence

6. **Patch 6 — complete RU/EN progress localization.** Close `SL3-007`.
7. **Patch 7 — integrated third-audit regression gate.** Exercise corrected paths together and require the complete corrective matrix, repository CI, and FreeBSD 15 package build.
8. **Patch 8 — source/CI closure and live-test handoff.** Record exact evidence and designate the resulting FreeBSD 15 package for owner-assisted live verification.

Each packaged behavior patch keeps `VERSION=0.3.3`, increments `PLUGIN_REVISION` once, uses one task branch and one Ready PR, passes focused validation plus required CI/package gates, and squash-merges to `main` with the expected head SHA. Documentation/CI-only patches do not increment package metadata.

## Current verification boundary

Live OPNsense matrix: **PAUSED PENDING THIRD-AUDIT SOURCE/CI COMPLETION**.

Scenario 1 resumes only after Patch 8 designates the new corrective candidate; scenarios 2–18 remain blocked until Scenario 1 passes. No source/CI result substitutes for owner-provided live OPNsense evidence.

Authoritative live plan: `docs/verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md`.

## Current GitHub delivery authority

Evidence-first GitHub operations remain authoritative through:

- repository-root `AGENTS.md`;
- `docs/GITHUB_PUBLICATION.md`;
- `docs/decisions/DEC-2026-08-06-evidence-first-github-operations.md`;
- `docs/decisions/DEC-2026-08-05-universal-versioned-github-titles.md`;
- `docs/decisions/DEC-2026-08-05-efficient-github-delivery.md`;
- `docs/GITHUB_WORKFLOW.md`.

The connected GitHub plugin is the mandatory first repository interface. One logical scope uses one task branch and one Ready PR; same-scope repairs stay in that PR; the latest head must pass required checks; merge is squash with the expected head SHA; published history is not rewritten.

## Release gate

Stable release preparation and pkg-repository promotion: **BLOCKED ON THIRD-AUDIT CORRECTIVE SERIES AND LIVE MATRIX**.

Testing prerelease publication for a later live candidate requires separate exact owner authorization.

Current product authority:

- `docs/audit/AUDIT-2026-08-07-STRATEGY-LAB-THIRD-AUDIT.md`;
- `docs/architecture/STRATEGY_LAB_CORRECTIVE_CONTRACT.md`;
- `docs/architecture/STRATEGY_LAB_OBSOLETE_SURFACES.md`;
- `docs/audit/STRATEGY_LAB_HARDENING_CLOSURE.md`;
- `docs/verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md`.

Next action after Patch 5 merge/verification: **Patch 6 — complete RU/EN progress localization**.

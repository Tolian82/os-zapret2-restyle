# os-zapret2-restyle — Current state

Project: `os-zapret2-restyle`
Primary branch: `main`
Published stable release/package: `v0.3.2` / `os-zapret2-restyle-0.3.2_1.pkg`
Latest published testing prerelease: `v0.3.3_5` / `os-zapret2-restyle-0.3.3_5.pkg`
Current source line: `VERSION=0.3.3`
Current corrective package revision: `PLUGIN_REVISION=11`
Target ABI: **FreeBSD:15:amd64 only**

## Historical live boundary

`v0.3.3_5` remains the latest owner-tested package. Revision `_6` corrected its confirmed stage-50/stage-90 defects but was not owner-tested before the third audit reopened the corrective series. Live verification remains paused until Patch 8 designates a later candidate.

## Third audit corrective series

Status: **IN PROGRESS — PRODUCT FIXES COMPLETE, INTEGRATED REGRESSION GATE ACTIVE**

Authoritative plan: `docs/audit/AUDIT-2026-08-07-STRATEGY-LAB-THIRD-AUDIT.md`.

## Patch progress

### Patch 1 — documentation and corrective plan

Status: **MERGED AND VERIFIED** — PR #115, main `ed82ddff891ece514fac01895c197ef07d844557`.

### Patch 2 — ordinary stale recovery and timeout chain

Status: **MERGED AND VERIFIED** — PR #116, main `dd95d77e4d75e6751315ff893798cc2ea66a9330`; CI `31151805919`; FreeBSD 15 artifact `8983642442`, package `_7`.

### Patch 3 — circular stale recovery lifecycle ownership

Status: **MERGED AND VERIFIED** — PR #117, main `f0c43de7133f8ba337a5458de0803409949a0096`; CI `31152455413`; FreeBSD 15 artifact `8983891990`, package `_8`.

### Patch 4 — remove load-order overrides and obsolete hooks

Status: **MERGED AND VERIFIED** — PR #118, main `15ed2b057ca94a1a780ecf9da9f304d0e6cd652c`; latest-head CI `31154664416`; FreeBSD 15 artifact `8984745215`, package `_9`.

`SL3-003` + `SL3-006` source scope is implemented: load order no longer selects worker behavior, `worker_state_serialization.sh` and transitional skip hooks are removed, canonical state writers retain lock/revision semantics, circular eligibility uses the TLS 1.3 circular subset, and the namespace contract rejects future duplicate functions in jointly loaded worker modules.

Implementation log: `docs/devlog/2026-08-07-v0.3.3_9-module-order.md`.

### Patch 5 — serialize worker state transitions

Status: **MERGED AND VERIFIED** — PR #119, main `41ccadd47136375cb58a64e527f2fecff9f1630e`; latest-head CI `31155184080`; FreeBSD 15 artifact `8984931432`, package `_10`.

`SL3-004` source scope is implemented: unfinished-stage skipping uses the canonical state transform, cancellation evidence survives concurrent skip/finalization, every mutation remains revisioned, and terminal state is irreversible under the race regression.

Implementation log: `docs/devlog/2026-08-07-v0.3.3_10-state-serialization.md`.

### Patch 6 — complete RU/EN progress localization

Status: **MERGED AND VERIFIED** — PR #120, main `00107d38f287462a2c0627a04629f6381774d05c`; latest-head CI `31156513189` passed the complete corrective matrix and repository validation. FreeBSD 15 artifact `8985427611` contains package `os-zapret2-restyle-0.3.3_11.pkg`.

`SL3-007` source scope is implemented: backend `cancel_requested` has deliberate RU/EN presentation, circular `stop_requested` remains distinct, and the focused regression derives the actual backend state key and requires both mappings.

Architecture authority: `docs/architecture/STRATEGY_LAB_PROGRESS_LOCALIZATION.md`.

Implementation log: `docs/devlog/2026-08-07-v0.3.3_11-localization.md`.

### Patch 7 — integrated third-audit regression gate

Status: **SOURCE IMPLEMENTED — PR/CI VERIFICATION PENDING**

Package revision remains `_11`; this patch changes CI/test coverage only and introduces no product behavior.

Integration scope:

- one new third-audit integration contract binds the canonical matrix to ordinary stale RUNNING/STOPPED recovery, semantic mismatch failure, circular stale recovery ownership, Extended mixed shortlist versus TLS 1.3 circular subset, cancel/skip/finalize serialization, the 180/190/200 recovery envelope, saved Traffic Strategy immutability, and residue cleanup;
- the canonical corrective matrix continues to execute focused regressions directly once each and retains only its existing explicit e2e delegations, preventing duplicate orchestration;
- the FreeBSD 15 package-CI contract is part of this patch so the integration-only PR still requires a fresh `_11` package build and manifest verification on its exact head.

Implementation log: `docs/devlog/2026-08-07-strategy-lab-third-audit-integration.md`.

## Remaining approved sequence

8. **Patch 8 — source/CI closure and live-test handoff.** Record exact evidence and designate the resulting FreeBSD 15 `_11` package for owner-assisted live verification. Do not claim live PASS.

Packaged behavior patches keep `VERSION=0.3.3`, increment `PLUGIN_REVISION` once, use one task branch and one Ready PR, pass focused validation plus required CI/package gates, and squash-merge to `main` with the expected head SHA. Documentation/CI-only patches do not increment package metadata.

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
- `docs/architecture/STRATEGY_LAB_PROGRESS_LOCALIZATION.md`;
- `docs/audit/STRATEGY_LAB_HARDENING_CLOSURE.md`;
- `docs/verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md`.

Next action after Patch 7 merge/verification: **Patch 8 — source/CI closure and live-test handoff**.

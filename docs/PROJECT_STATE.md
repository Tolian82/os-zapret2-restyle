# os-zapret2-restyle — Current state

Project: `os-zapret2-restyle`
Primary branch: `main`
Published stable release/package: `v0.3.2` / `os-zapret2-restyle-0.3.2_1.pkg`
Latest published testing prerelease: `v0.3.3_5` / `os-zapret2-restyle-0.3.3_5.pkg`
Current source line: `VERSION=0.3.3`
Current corrective package revision: `PLUGIN_REVISION=9`
Target ABI: **FreeBSD:15:amd64 only**

## Historical live boundary

`v0.3.3_5` remains the latest owner-tested package. Revision `_6` corrected its confirmed stage-50/stage-90 defects but was not owner-tested before the third audit reopened the corrective series. Live verification remains paused until Patch 8 designates a later candidate.

## Third audit corrective series

Status: **IN PROGRESS**

Authoritative plan: `docs/audit/AUDIT-2026-08-07-STRATEGY-LAB-THIRD-AUDIT.md`.

Open third-audit findings are `SL3-001` through `SL3-007` as recorded there.

## Patch progress

### Patch 1 — documentation and corrective plan

Status: **MERGED AND VERIFIED**

PR #115 merged as `ed82ddff891ece514fac01895c197ef07d844557`.

### Patch 2 — ordinary stale recovery and timeout chain

Status: **MERGED AND VERIFIED**

PR #116 merged as `dd95d77e4d75e6751315ff893798cc2ea66a9330`. Latest-head CI run `31151805919` passed the complete Strategy Lab corrective matrix, repository validation, and FreeBSD 15 package build. Artifact `8983642442` contains `os-zapret2-restyle-0.3.3_7.pkg`.

Source scope `SL3-001` + `SL3-005` is implemented: stale ordinary restoration is lifecycle-owned and semantic-proof based; contradictory proof becomes `RESTORE_FAILED`; ordinary synchronous control/recovery uses the 180/190/200-second configd/MVC/browser envelope.

Implementation log: `docs/devlog/2026-08-07-v0.3.3_7-stale-recovery.md`.

### Patch 3 — circular stale recovery lifecycle ownership

Status: **MERGED AND VERIFIED**

PR #117 merged as `f0c43de7133f8ba337a5458de0803409949a0096`. Latest-head CI run `31152455413` passed the complete Strategy Lab corrective matrix, repository validation, and FreeBSD 15 package build. Artifact `8983891990` contains `os-zapret2-restyle-0.3.3_8.pkg`.

Source scope `SL3-002` is implemented: stale circular restoration delegates to the lifecycle-owned semantic recovery transaction, contradictory proof is rejected and retry remains blocked, and circular control/recovery uses the same 180/190/200-second outer timeout ordering.

Implementation log: `docs/devlog/2026-08-07-v0.3.3_8-circular-recovery.md`.

### Patch 4 — remove load-order overrides and obsolete hooks

Status: **SOURCE IMPLEMENTED — PR/CI VERIFICATION PENDING**

Package revision: `_9`.

Implemented scope for `SL3-003` + `SL3-006`:

- removed `worker_state_serialization.sh` after migrating its lock/revision behavior into canonical module owners;
- removed the worker source-order dependency on that override module;
- `worker_result.sh` is the sole owner of circular eligibility and uses the TLS 1.3 `circular_items/circular_count` subset rather than the general multi-protocol shortlist count;
- `profile.sh` is the sole owner of unified shortlist construction; the old TLS-only shortlist implementation in `stability.sh` is removed;
- obsolete `strategy_lab_skip_unfinished()` and `strategy_lab_skip_remaining()` control-flow hooks are removed from expansion/stability/extended/QUIC/UDP paths;
- canonical lifecycle, budget, expansion, stability, extended, QUIC, UDP, candidate/family, and result persistence uses `strategy_lab_state_transform()` in the main worker path, preserving the state lock and revision contract;
- added a mandatory namespace regression that parses the exact modules loaded together by the main worker and rejects duplicate function definitions.

Architecture authority: `docs/architecture/STRATEGY_LAB_OBSOLETE_SURFACES.md`.

Implementation log: `docs/devlog/2026-08-07-v0.3.3_9-module-order.md`.

## Remaining approved sequence

5. **Patch 5 — serialize worker state transitions.** Close `SL3-004`.
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

Next action after Patch 4 merge/verification: **Patch 5 — serialize worker state transitions**.

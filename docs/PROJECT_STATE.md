# os-zapret2-restyle — Current state

Project: `os-zapret2-restyle`
Primary branch: `main`
Published stable release/package: `v0.3.2` / `os-zapret2-restyle-0.3.2_1.pkg`
Latest published testing prerelease: `v0.3.3_5` / `os-zapret2-restyle-0.3.3_5.pkg`
Current source line: `VERSION=0.3.3`
Current corrective package revision: `PLUGIN_REVISION=8`
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

Status: **SOURCE IMPLEMENTED — PR/CI VERIFICATION PENDING**

Package revision: `_8`.

Implemented scope for `SL3-002`:

- circular stale recovery no longer calls protected normal-service restoration directly from the circular launcher/module context;
- the lifecycle-owned `strategy-lab-recover` transaction introduced in Patch 2 now detects and binds private circular-session state when no ordinary job state exists;
- circular stale recovery delegates to that transaction and accepts success only when persisted restoration proves verified semantic equality, unchanged strategy evidence, and clean temporary runtime;
- inconsistent or failed proof is forced unverified, persisted as `restore_failed/RESTORE_FAILED`, and keeps automatic retry blocked;
- circular configd actions use 180 seconds, `CircularController` uses 190 seconds, and the shared browser request envelope remains 200 seconds;
- focused circular-owner and recovery-contract regressions no longer mock the protected restore function inside `circular_owner.sh`.

Implementation log: `docs/devlog/2026-08-07-v0.3.3_8-circular-recovery.md`.

## Remaining approved sequence

4. **Patch 4 — remove load-order overrides and obsolete hooks.** Close `SL3-003` + `SL3-006`.
5. **Patch 5 — serialize worker state transitions.** Close `SL3-004`.
6. **Patch 6 — complete RU/EN progress localization.** Close `SL3-007`.
7. **Patch 7 — integrated third-audit regression gate.** Exercise corrected paths together and require the complete corrective matrix, repository CI, and FreeBSD 15 package build.
8. **Patch 8 — source/CI closure and live-test handoff.** Record exact evidence and designate the resulting FreeBSD 15 package for owner-assisted live verification.

Each packaged behavior patch keeps `VERSION=0.3.3`, increments `PLUGIN_REVISION` once, uses one task branch and Ready PR, passes focused validation plus required CI/package gates, and squash-merges to `main` with the expected head SHA. Documentation/CI-only patches do not increment package metadata.

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
- `docs/audit/STRATEGY_LAB_HARDENING_CLOSURE.md`;
- `docs/verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md`.

Next action after Patch 3 merge/verification: **Patch 4 — remove load-order overrides and obsolete hooks**.

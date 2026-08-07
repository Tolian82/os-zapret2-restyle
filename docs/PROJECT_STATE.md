# os-zapret2-restyle — Current state

Project: `os-zapret2-restyle`
Primary branch: `main`
Published stable release/package: `v0.3.2` / `os-zapret2-restyle-0.3.2_1.pkg`
Latest published testing prerelease: `v0.3.3_5` / `os-zapret2-restyle-0.3.3_5.pkg`
Current source line: `VERSION=0.3.3`
Current package revision before third-audit code changes: `PLUGIN_REVISION=6`
Target ABI: **FreeBSD:15:amd64 only**

## Historical live boundary

`v0.3.3_5` was built and published successfully for FreeBSD 15 amd64. Its first owner-assisted standard Strategy Lab run proved the prior PID/evidence correction but exposed a stage-50 candidate-runtime failure followed by stage-90 `RESTORE_FAILED`. That attempt remains failed historical evidence and is not converted into PASS by later changes.

Durable evidence:

`docs/verification/evidence/2026-08-07-v0.3.3_5-scenario-01-candidate-runtime-restore-failure.md`

Revision `_6` then corrected the confirmed candidate-runtime ownership/teardown and bounded stage-90 restoration defects. The exact corrective PR heads passed repository CI and FreeBSD 15 package verification; the final `_6` restoration PR head produced artifact `8980876980`, package `os-zapret2-restyle-0.3.3_6.pkg`, with manifest identity `0.3.3_6 / FreeBSD:15:amd64 / freebsd:15:x86:64 / FreeBSD_version 1500068`. Post-merge `main` CI also passed.

No `_6` testing prerelease was published and no `_6` owner-assisted OPNsense retest was performed.

## Third audit — corrective series reopened

Status: **IN PROGRESS**

A third source audit on 2026-08-07 found seven additional Strategy Lab defects/inconsistencies. The `_6` source/CI results remain valid historical evidence for the code they tested, but `_6` is no longer the next live candidate.

Authoritative audit and working plan:

`docs/audit/AUDIT-2026-08-07-STRATEGY-LAB-THIRD-AUDIT.md`

Stable findings:

- `SL3-001` — ordinary stale-worker recovery can falsely report semantic restoration;
- `SL3-002` — circular stale-worker recovery lacks lifecycle ownership;
- `SL3-003` — load-order override breaks Extended circular eligibility;
- `SL3-004` — `worker_skip_unfinished()` bypasses serialized state mutation;
- `SL3-005` — synchronous recovery caller timeouts are shorter than legitimate restoration;
- `SL3-006` — obsolete hook/load-order surfaces remain after declared cleanup;
- `SL3-007` — `cancel_requested` presentation is not completely localized.

## Approved patch sequence

The owner approved this serial corrective plan:

1. **Patch 1 — documentation and corrective plan.** Register the third audit, reopen closure, freeze scope/order, and pause the `_6` live retest. Documentation only; no package metadata change.
2. **Patch 2 — ordinary stale recovery and timeout chain.** Close `SL3-001` + `SL3-005` using the semantic stage-90 restoration contract and a valid outer timeout envelope.
3. **Patch 3 — circular stale recovery lifecycle ownership.** Close `SL3-002` by running protected restoration only inside a lifecycle-owned transaction.
4. **Patch 4 — remove load-order overrides and obsolete hooks.** Close `SL3-003` + `SL3-006`; centralize circular eligibility and prohibit unintended duplicate function definitions among jointly loaded modules.
5. **Patch 5 — serialize worker state transitions.** Close `SL3-004`; route skip/finalize/cancel-relevant state writes through the canonical lock/revision transform.
6. **Patch 6 — complete RU/EN progress localization.** Close `SL3-007` and enforce backend-vocabulary coverage in GUI presentation tests.
7. **Patch 7 — integrated third-audit regression gate.** Exercise the corrected paths together and require the full Strategy Lab corrective matrix, repository CI, and FreeBSD 15 package build.
8. **Patch 8 — source/CI closure and live-test handoff.** Documentation only; record exact evidence without claiming live PASS and designate the resulting FreeBSD 15 candidate for owner-assisted live verification.

Each logical packaged patch keeps `VERSION=0.3.3`, increments `PLUGIN_REVISION` once, uses one task branch and Ready PR, passes focused validation plus required CI/package gates, and squash-merges to `main` with the expected head SHA. Patch 1 and Patch 8 are documentation-only and do not change package metadata.

## Current verification boundary

Live OPNsense matrix: **PAUSED PENDING THIRD-AUDIT SOURCE/CI COMPLETION**.

The former next action, Scenario 1 retest on `_6`, is superseded by the third-audit corrective series. Scenario 1 resumes only after Patch 8 on the newly designated candidate. Dependent scenarios remain blocked until Scenario 1 passes.

The authoritative live plan remains:

`docs/verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md`

No source/CI result substitutes for owner-provided live OPNsense evidence.

## Current GitHub delivery rules

Evidence-first GitHub operations are authoritative through:

- `AGENTS.md`;
- `docs/GITHUB_PUBLICATION.md`;
- `docs/decisions/DEC-2026-08-06-evidence-first-github-operations.md`;
- `docs/decisions/DEC-2026-08-05-universal-versioned-github-titles.md`;
- `docs/decisions/DEC-2026-08-05-efficient-github-delivery.md`.

The connected GitHub plugin is the mandatory first repository interface. One logical scope uses one task branch and one Ready PR; same-scope repairs stay in that PR; merge is squash with the expected head SHA. Packaged patches increment `PLUGIN_REVISION` once. Documentation-only patches change neither version value.

## Release gate

Stable release preparation and pkg-repository promotion: **BLOCKED ON THIRD-AUDIT CORRECTIVE SERIES AND LIVE MATRIX**.

Testing prerelease publication for a later live candidate requires separate exact owner authorization and does not imply stable release or pkg-repository promotion.

Current product authority:

- `docs/audit/AUDIT-2026-08-07-STRATEGY-LAB-THIRD-AUDIT.md`;
- `docs/architecture/STRATEGY_LAB_CORRECTIVE_CONTRACT.md`;
- `docs/audit/STRATEGY_LAB_HARDENING_CLOSURE.md`;
- `docs/verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md`;
- `docs/audit/AUDIT-2026-08-05-STRATEGY-LAB-HARDENING.md`.

Next action: **Patch 2 — ordinary stale recovery and timeout chain**, after Patch 1 is merged and verified.

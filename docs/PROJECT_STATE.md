# os-zapret2-restyle — Current state

Project: `os-zapret2-restyle`
Primary branch: `main`
Published stable release/package: `v0.3.2` / `os-zapret2-restyle-0.3.2_1.pkg`
Latest published testing prerelease: `v0.3.3_5` / `os-zapret2-restyle-0.3.3_5.pkg`
Current corrective candidate: `os-zapret2-restyle-0.3.3_6.pkg`
Target ABI: **FreeBSD:15:amd64 only**

## Version 0.3.3 revision 5 — verified package, failed live scenario 1

`v0.3.3_5` was built and published by GitHub Actions run `31130265614`.
The FreeBSD 15 build, package manifest verification, prerelease publication, release
contract verification, and temporary publication-branch cleanup all completed
successfully.

Published release target: `68ad848cf62280de23907b0ccb63522be9b7bb15`.
Published asset: `os-zapret2-restyle-0.3.3_5.pkg`.
Asset digest: `sha256:68c96469132dd9b6fd715a782848f24625fbd695f991831cd773f54dec9431a3`.

The `_5` PID-file correction is confirmed live: before Strategy Lab execution,
`strategy-lab-evidence` correctly reported `state=RUNNING`, `child_running=true`, and
`supervisor_running=true`.

The subsequent standard Strategy Lab run against `rutracker.org` exposed the next defect:

- stages 00, 10, 20, 30, and 40 passed;
- stage 50 failed with `Temporary candidate runtime failed internally.`;
- stage 90 failed with `RESTORE_FAILED`;
- after the run, `configctl zapret status` reported an incomplete runtime state;
- semantic evidence reported `state=INCOMPLETE`, `child_running=false`, and
  `supervisor_running=false`;
- saved/effective configuration hashes remained unchanged.

Durable evidence:
`docs/verification/evidence/2026-08-07-v0.3.3_5-scenario-01-candidate-runtime-restore-failure.md`.

Scenario 1 therefore remains failed/pending correction. Dependent live Strategy Lab
scenarios must not continue until the stage-50 candidate runtime failure and stage-90
restoration failure are corrected.

## Version 0.3.3 revision 6 — current corrective line

Revision `_6` is the corrective candidate used to restore repository consistency and then
repair the confirmed Strategy Lab lifecycle failure.

The baseline `_6` reconciliation scope:

- advances `PLUGIN_REVISION` to `6` without changing `VERSION=0.3.3`;
- records the truthful `_5` live failure;
- restores the generic testing-prerelease publisher now that stale `publish/*` refs have
  been removed;
- reconciles GitHub governance/current-state tests and documentation with actual
  repository state;
- keeps the live matrix blocked while source correction is incomplete.

The remaining `_6` source work is deliberately split into two sequential logical patches:

1. correct the stage-50 temporary candidate runtime internal failure and merge that patch
   to `main` after full CI plus FreeBSD 15 package verification;
2. starting from that `main`, correct the stage-90 restoration path so the original
   service state is restored deterministically, then merge after the same repository
   verification.

The owner requested these source corrections to reach `main` without an intermediate
manual OPNsense test. Repository CI does not create a live PASS: owner-assisted live
scenario 1 remains deferred until both corrective patches are merged.

The detailed reconciliation ledger for this thread is:
`docs/devlog/2026-08-07-v0.3.3_6-repository-reconciliation.md`.

No `_6` live PASS or publication is claimed yet.

## Current GitHub state

The repository owner removed the stale temporary publication branches:

- `publish/v0.3.3_1`;
- `publish/v0.3.3_2`;
- `publish/v0.3.3_4`;
- `publish/v0.3.3_4-final`;
- `publish/v0.3.3_5`.

Evidence-first GitHub operations are authoritative through:

- `AGENTS.md`;
- `docs/GITHUB_PUBLICATION.md`;
- `docs/decisions/DEC-2026-08-06-evidence-first-github-operations.md`;
- `docs/decisions/DEC-2026-08-05-universal-versioned-github-titles.md`;
- `docs/decisions/DEC-2026-08-05-efficient-github-delivery.md`.

The connected GitHub plugin is the mandatory first repository interface. If it is
unavailable, non-responsive, or cannot provide authoritative repository state required
for safe work, GitHub work stops and the owner is informed. A fallback transport is
allowed only for one exact function or permission confirmed missing from an otherwise
responding plugin.

The repository uses one generic testing-prerelease workflow. Version-specific publisher
files are forbidden. A temporary `publish/v<VERSION>_<REVISION>` branch must match the
candidate identity derived from `VERSION` and `PLUGIN_REVISION`, permits one active
publication run, publishes neither GitHub Pages nor the pkg repository, verifies the
release contract, and removes itself after success.

## Release gate

Live OPNsense matrix: **BLOCKED ON SCENARIO 1 CORRECTION**.

Stable release preparation and pkg-repository promotion: **BLOCKED ON LIVE MATRIX**.

Current product authority:

- `docs/architecture/STRATEGY_LAB_CORRECTIVE_CONTRACT.md`;
- `docs/audit/STRATEGY_LAB_HARDENING_CLOSURE.md`;
- `docs/verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md`;
- `docs/audit/AUDIT-2026-08-05-STRATEGY-LAB-HARDENING.md`.

`VERSION=0.3.3`; `PLUGIN_REVISION=6`.

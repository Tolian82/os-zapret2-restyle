# os-zapret2-restyle — Current state

Project: `os-zapret2-restyle`
Primary branch: `main`
Published stable release/package: `v0.3.2` / `os-zapret2-restyle-0.3.2_1.pkg`
Current verified source baseline on `main`: `os-zapret2-restyle-0.3.2_47.pkg`
Current prerelease candidate: `os-zapret2-restyle-0.3.3_1.pkg`

Hardening revisions 25–47 are source-verified on `main`.

## Version 0.3.3 revision 1

- advance the test candidate from `0.3.2_47` to `0.3.3_1` without runtime behavior changes;
- preserve the FreeBSD 15 amd64-only package contract;
- build and publish the package as a GitHub prerelease asset for owner-assisted live OPNsense verification;
- keep stable release status and final pkg-repository promotion separate from the live verification gate.

## Completion status

Source and CI hardening: **COMPLETE**.

Target package ABI: **FREEBSD 15 AMD64 ONLY**.

Live OPNsense matrix: **PENDING OWNER** using `os-zapret2-restyle-0.3.3_1.pkg`.

Stable release preparation: **BLOCKED ON LIVE MATRIX**.

Authoritative closure records:

- `docs/audit/STRATEGY_LAB_HARDENING_CLOSURE.md`;
- `docs/verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md`;
- `docs/audit/AUDIT-2026-08-05-STRATEGY-LAB-HARDENING.md`.

No live appliance PASS is claimed. The `v0.3.3_1` GitHub prerelease is a testing distribution surface only and is not a stable product release.

## Current product authority

`docs/architecture/STRATEGY_LAB_CORRECTIVE_CONTRACT.md`, `STRATEGY_LAB_ACTIVATION.md`, `STRATEGY_LAB_PROFILE_OUTPUT.md`, `STRATEGY_LAB_UNIFIED_SHORTLIST.md`, `STRATEGY_LAB_UDP_INPUT.md`, `STRATEGY_LAB_CIRCULAR_ISOLATION.md`, `STRATEGY_LAB_CIRCULAR_OWNERSHIP.md`, `STRATEGY_LAB_SETTINGS_GUARD.md`, `STRATEGY_LAB_PERSISTED_RESULT_RELOAD.md`, `STRATEGY_LAB_STRUCTURED_RESULTS.md`, `STRATEGY_LAB_PROGRESS_LOCALIZATION.md`, `STRATEGY_LAB_OBSOLETE_SURFACES.md`, `STRATEGY_LAB_RETENTION.md`, `STRATEGY_LAB_CORRECTIVE_MATRIX.md`, `docs/audit/AUDIT-2026-08-05-STRATEGY-LAB-HARDENING.md`, `docs/audit/STRATEGY_LAB_HARDENING_CLOSURE.md`, and `docs/verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md`.

## GitHub governance

`docs/GITHUB_PUBLICATION.md`, `docs/decisions/DEC-2026-08-05-efficient-github-delivery.md`, and `docs/decisions/DEC-2026-08-05-universal-versioned-github-titles.md` remain authoritative. Every PR title, branch commit subject, and final squash subject uses the exact package-candidate prefix. `main` is never force-updated.

`VERSION=0.3.3`; `PLUGIN_REVISION=1` in this candidate.

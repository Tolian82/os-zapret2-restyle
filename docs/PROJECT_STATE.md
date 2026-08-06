# os-zapret2-restyle — Current state

Project: `os-zapret2-restyle`
Primary branch: `main`
Published stable release/package: `v0.3.2` / `os-zapret2-restyle-0.3.2_1.pkg`
Current verified source baseline on `main`: `os-zapret2-restyle-0.3.3_2.pkg`
Current source candidate: `os-zapret2-restyle-0.3.3_3.pkg`

Hardening revisions 25–47 and prerelease revisions `0.3.3_1`–`0.3.3_2` are source-verified on `main`.

## Version 0.3.3 revision 3

- stop automatic Diagnostics initialization from resurrecting the latest completed or failed Strategy Lab job;
- resume polling only when `active.job` identifies genuinely active work;
- preserve terminal evidence and explicit status/result access by validated job ID;
- return the Strategy Lab page to its initial idle presentation after navigation or reload;
- update the live scenario 15 contract and focused reload regression.

The live scenario 1 attempt on `0.3.3_2` still failed at stage 10 because semantic evidence reported both running daemon processes as absent. That runtime defect is independent of the reload presentation correction and requires the next same-scope patch before scenario 1 can be repeated.

## Completion status

Source and CI hardening: **COMPLETE**.

Target package ABI: **FREEBSD 15 AMD64 ONLY**.

Live OPNsense matrix: **PENDING OWNER**.

Stable release preparation: **BLOCKED ON LIVE MATRIX**.

Authoritative closure records:

- `docs/audit/STRATEGY_LAB_HARDENING_CLOSURE.md`;
- `docs/verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md`;
- `docs/audit/AUDIT-2026-08-05-STRATEGY-LAB-HARDENING.md`.

No live scenario PASS is claimed. GitHub prereleases in the `0.3.3` line are testing distribution surfaces only and are not stable product releases.

## Current product authority

`docs/architecture/STRATEGY_LAB_CORRECTIVE_CONTRACT.md`, `STRATEGY_LAB_ACTIVATION.md`, `STRATEGY_LAB_PROFILE_OUTPUT.md`, `STRATEGY_LAB_UNIFIED_SHORTLIST.md`, `STRATEGY_LAB_UDP_INPUT.md`, `STRATEGY_LAB_CIRCULAR_ISOLATION.md`, `STRATEGY_LAB_CIRCULAR_OWNERSHIP.md`, `STRATEGY_LAB_SETTINGS_GUARD.md`, `STRATEGY_LAB_PERSISTED_RESULT_RELOAD.md`, `STRATEGY_LAB_STRUCTURED_RESULTS.md`, `STRATEGY_LAB_PROGRESS_LOCALIZATION.md`, `STRATEGY_LAB_OBSOLETE_SURFACES.md`, `STRATEGY_LAB_RETENTION.md`, `STRATEGY_LAB_CORRECTIVE_MATRIX.md`, `docs/audit/AUDIT-2026-08-05-STRATEGY-LAB-HARDENING.md`, `docs/audit/STRATEGY_LAB_HARDENING_CLOSURE.md`, and `docs/verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md`.

## GitHub governance

`docs/GITHUB_PUBLICATION.md`, `docs/decisions/DEC-2026-08-05-efficient-github-delivery.md`, and `docs/decisions/DEC-2026-08-05-universal-versioned-github-titles.md` remain authoritative. Every PR title, branch commit subject, and final squash subject uses the exact package-candidate prefix. `main` is never force-updated.

`VERSION=0.3.3`; `PLUGIN_REVISION=3` in this candidate.

# os-zapret2-restyle — Current state

Project: `os-zapret2-restyle`
Primary branch: `main`
Published stable release/package: `v0.3.2` / `os-zapret2-restyle-0.3.2_1.pkg`
Current verified source baseline on `main`: `os-zapret2-restyle-0.3.3_3.pkg`
Current source candidate: `os-zapret2-restyle-0.3.3_4.pkg`

Hardening revisions 25–47 and prerelease revisions `0.3.3_1`–`0.3.3_3` are source-verified on `main`.

## Version 0.3.3 revision 4

- preserve the FreeBSD-safe `process_query.sh` binding inside the complete `zapret_service.sh` entry point;
- stop the service entry point from overwriting semantic process inspection with direct `/bin/ps`;
- make `strategy-lab-evidence` detect the running dvtws2 child and supervisor daemon consistently with shared backend checks;
- strengthen the regression test so it rejects any future service-level override back to `/bin/ps`;
- record the live `0.3.3_2` contradiction and require scenario 1 repetition on the corrected candidate.

The `0.3.3_2` live diagnostic proved that `process_query.sh` and `common_process_matches` detected both running processes while the complete `strategy-lab-evidence` path reported both as absent. The root cause was the later service-level variable override, not the wrapper itself. Scenario 1 remains pending until `0.3.3_4` is installed and tested.

Revision `0.3.3_3` independently corrected Diagnostics reload behavior: active jobs resume, while a newly opened page returns to the idle view after terminal work without deleting retained evidence.

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

`VERSION=0.3.3`; `PLUGIN_REVISION=4` in this candidate.

# os-zapret2-restyle — Current state

Project: `os-zapret2-restyle`
Primary branch: `main`
Published stable release/package: `v0.3.2` / `os-zapret2-restyle-0.3.2_1.pkg`
Current verified source baseline on `main`: `os-zapret2-restyle-0.3.3_4.pkg`
Current source candidate: `os-zapret2-restyle-0.3.3_5.pkg`

Hardening revisions 25–47 and prerelease revisions `0.3.3_1`–`0.3.3_4` are source-verified on `main`.

## Version 0.3.3 revision 5

- add one shared PID-file reader that accepts valid numeric PID files ending either with a newline or directly at EOF;
- use that reader in Strategy Lab semantic lifecycle evidence;
- reject empty, malformed, and PID 0/1 files;
- add regression coverage using a real no-newline PID fixture matching FreeBSD `daemon(8)` output;
- record the failed `0.3.3_4` live attempt without claiming scenario 1 PASS;
- repeat scenario 1 only after the FreeBSD 15 `_5` package is installed.

The `0.3.3_4` live diagnostic still returned `child_running:false` and `supervisor_running:false`. The process wrapper binding was correct, but `strategy_lab_semantic_pid_matches()` used `read ... || return 1`. FreeBSD `daemon(8)` PID files may end at EOF without a trailing newline; POSIX `read` assigns the PID but returns non-zero at EOF, causing both valid processes to be rejected before identity inspection.

Revision `0.3.3_3` independently corrected Diagnostics reload behavior: active jobs resume, while a newly opened page returns to the idle view after terminal work without deleting retained evidence.

## Completion status

Source and CI hardening: **COMPLETE THROUGH 0.3.3_4; 0.3.3_5 CORRECTIVE CANDIDATE IN PROGRESS**.

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

The separate governance PR is paused while the runtime correction is delivered. It must be rebased or refreshed from the post-`0.3.3_5` `main` before review and merge.

`docs/GITHUB_PUBLICATION.md`, `docs/decisions/DEC-2026-08-05-efficient-github-delivery.md`, and `docs/decisions/DEC-2026-08-05-universal-versioned-github-titles.md` remain authoritative until the conflict-audited governance patch is merged. Every PR title, branch commit subject, and final squash subject uses the exact package-candidate prefix. `main` is never force-updated.

`VERSION=0.3.3`; `PLUGIN_REVISION=5` in this candidate.

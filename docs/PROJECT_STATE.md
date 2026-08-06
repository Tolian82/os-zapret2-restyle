# os-zapret2-restyle — Current state

Project: `os-zapret2-restyle`
Primary branch: `main`
Published release/package: `v0.3.2` / `os-zapret2-restyle-0.3.2_1.pkg`
Current verified source baseline on `main`: `os-zapret2-restyle-0.3.2_45.pkg`
Current integration candidate: `os-zapret2-restyle-0.3.2_46.pkg`

Hardening revisions 25–45 are verified on `main`.

## Revision 46

- freeze the final Strategy Lab hardening closure record;
- record findings 1–15 as source-complete and covered by mandatory CI;
- provide an 18-scenario owner-assisted live OPNsense verification matrix;
- require appliance identity, lifecycle, process, firewall, result, and screenshot evidence;
- prohibit automatic or inferred live PASS claims from mocked tests, CI, or package builds;
- keep release preparation blocked until every required live row passes with owner evidence;
- make no Strategy Lab runtime behavior change.

## Completion status

Source and CI hardening: **COMPLETE**.

Live OPNsense matrix: **PENDING OWNER**.

Release preparation: **BLOCKED ON LIVE MATRIX**.

Authoritative closure records:

- `docs/audit/STRATEGY_LAB_HARDENING_CLOSURE.md`;
- `docs/verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md`;
- `docs/audit/AUDIT-2026-08-05-STRATEGY-LAB-HARDENING.md`.

No live appliance PASS is claimed by revision 46. Tagging, GitHub Release creation, release assets, and pkg-repository publication require completion of the live matrix and separate explicit owner authorization.

## Current product authority

`docs/architecture/STRATEGY_LAB_CORRECTIVE_CONTRACT.md`, `STRATEGY_LAB_ACTIVATION.md`, `STRATEGY_LAB_PROFILE_OUTPUT.md`, `STRATEGY_LAB_UNIFIED_SHORTLIST.md`, `STRATEGY_LAB_UDP_INPUT.md`, `STRATEGY_LAB_CIRCULAR_ISOLATION.md`, `STRATEGY_LAB_CIRCULAR_OWNERSHIP.md`, `STRATEGY_LAB_SETTINGS_GUARD.md`, `STRATEGY_LAB_PERSISTED_RESULT_RELOAD.md`, `STRATEGY_LAB_STRUCTURED_RESULTS.md`, `STRATEGY_LAB_PROGRESS_LOCALIZATION.md`, `STRATEGY_LAB_OBSOLETE_SURFACES.md`, `STRATEGY_LAB_RETENTION.md`, `STRATEGY_LAB_CORRECTIVE_MATRIX.md`, `docs/audit/AUDIT-2026-08-05-STRATEGY-LAB-HARDENING.md`, `docs/audit/STRATEGY_LAB_HARDENING_CLOSURE.md`, and `docs/verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md`.

## GitHub governance

`docs/GITHUB_PUBLICATION.md`, `docs/decisions/DEC-2026-08-05-efficient-github-delivery.md`, and `docs/decisions/DEC-2026-08-05-universal-versioned-github-titles.md` remain authoritative. Every PR title, branch commit subject, and final squash subject uses the exact package-candidate prefix. `main` is never force-updated.

`VERSION=0.3.2`; `PLUGIN_REVISION=46` in this candidate. No release publication is included.

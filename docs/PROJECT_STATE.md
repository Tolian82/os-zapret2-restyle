# os-zapret2-restyle — Current state

Project: `os-zapret2-restyle`
Primary branch: `main`
Published release/package: `v0.3.2` / `os-zapret2-restyle-0.3.2_1.pkg`
Current verified source baseline on `main`: `os-zapret2-restyle-0.3.2_46.pkg`
Current integration candidate: `os-zapret2-restyle-0.3.2_47.pkg`

Hardening revisions 25–46 are source-verified on `main`.

## Revision 47

- correct the pull-request package build from FreeBSD 14.2 to FreeBSD 15.0;
- require the build VM itself to report FreeBSD major version 15;
- inspect the generated package manifest and require `FreeBSD:15:amd64` / `freebsd:15:x86:64`;
- remove truncation-pipe warnings from package-content and manifest inspection;
- add a permanent GitHub workflow contract rejecting FreeBSD 14 package builders;
- replace revision 46 with revision 47 as the only valid live OPNsense candidate;
- make no Strategy Lab runtime behavior change.

The revision 46 source closure remains valid, but its PR package artifact was built with ABI `FreeBSD:14:amd64` and must not be installed or used for the live OPNsense matrix.

## Completion status

Source and CI hardening: **COMPLETE**.

Target package ABI: **FREEBSD 15 AMD64 ONLY**.

Live OPNsense matrix: **PENDING OWNER** using `os-zapret2-restyle-0.3.2_47.pkg`.

Release preparation: **BLOCKED ON LIVE MATRIX**.

Authoritative closure records:

- `docs/audit/STRATEGY_LAB_HARDENING_CLOSURE.md`;
- `docs/verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md`;
- `docs/audit/AUDIT-2026-08-05-STRATEGY-LAB-HARDENING.md`.

No live appliance PASS is claimed. Tagging, GitHub Release creation, release assets, and pkg-repository publication require completion of the live matrix and separate explicit owner authorization.

## Current product authority

`docs/architecture/STRATEGY_LAB_CORRECTIVE_CONTRACT.md`, `STRATEGY_LAB_ACTIVATION.md`, `STRATEGY_LAB_PROFILE_OUTPUT.md`, `STRATEGY_LAB_UNIFIED_SHORTLIST.md`, `STRATEGY_LAB_UDP_INPUT.md`, `STRATEGY_LAB_CIRCULAR_ISOLATION.md`, `STRATEGY_LAB_CIRCULAR_OWNERSHIP.md`, `STRATEGY_LAB_SETTINGS_GUARD.md`, `STRATEGY_LAB_PERSISTED_RESULT_RELOAD.md`, `STRATEGY_LAB_STRUCTURED_RESULTS.md`, `STRATEGY_LAB_PROGRESS_LOCALIZATION.md`, `STRATEGY_LAB_OBSOLETE_SURFACES.md`, `STRATEGY_LAB_RETENTION.md`, `STRATEGY_LAB_CORRECTIVE_MATRIX.md`, `docs/audit/AUDIT-2026-08-05-STRATEGY-LAB-HARDENING.md`, `docs/audit/STRATEGY_LAB_HARDENING_CLOSURE.md`, and `docs/verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md`.

## GitHub governance

`docs/GITHUB_PUBLICATION.md`, `docs/decisions/DEC-2026-08-05-efficient-github-delivery.md`, and `docs/decisions/DEC-2026-08-05-universal-versioned-github-titles.md` remain authoritative. Every PR title, branch commit subject, and final squash subject uses the exact package-candidate prefix. `main` is never force-updated.

`VERSION=0.3.2`; `PLUGIN_REVISION=47` in this candidate. No release publication is included.

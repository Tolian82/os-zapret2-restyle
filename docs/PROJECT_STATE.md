# os-zapret2-restyle — Current state

Project: `os-zapret2-restyle`
Primary branch: `main`
Published release/package: `v0.3.2` / `os-zapret2-restyle-0.3.2_1.pkg`
Current verified source baseline on `main`: `os-zapret2-restyle-0.3.2_44.pkg`
Current integration candidate: `os-zapret2-restyle-0.3.2_45.pkg`

Hardening revisions 25–44 are verified on `main`.

## Revision 45

- one authoritative nonrecursive Strategy Lab corrective matrix;
- focused domain diagnostics remains an independent single-purpose test;
- every discovered `test-strategy-lab-*.sh` contract runs exactly once in stable order;
- CI invokes the matrix once and no longer bypasses it through the old domain wrapper;
- matrix self-contract protects workflow, discovery, required artifacts, and nonrecursion;
- terminal-result and stale-worker fixtures explicitly mock UDP cleanup and emit no missing-function warnings;
- non-Strategy project, governance, release, package lifecycle, and FreeBSD package checks remain separate CI gates.

Revision 45 completes the source and CI portions of finding 15. Findings 1–15 are source-complete after this candidate.

Remaining work:

- `_46` final closure documentation and owner-assisted live OPNsense verification matrix.

The live appliance matrix remains a release gate and cannot be marked PASS without owner-provided OPNsense evidence.

## Current product authority

`docs/architecture/STRATEGY_LAB_CORRECTIVE_CONTRACT.md`, `STRATEGY_LAB_ACTIVATION.md`, `STRATEGY_LAB_PROFILE_OUTPUT.md`, `STRATEGY_LAB_UNIFIED_SHORTLIST.md`, `STRATEGY_LAB_UDP_INPUT.md`, `STRATEGY_LAB_CIRCULAR_ISOLATION.md`, `STRATEGY_LAB_CIRCULAR_OWNERSHIP.md`, `STRATEGY_LAB_SETTINGS_GUARD.md`, `STRATEGY_LAB_PERSISTED_RESULT_RELOAD.md`, `STRATEGY_LAB_STRUCTURED_RESULTS.md`, `STRATEGY_LAB_PROGRESS_LOCALIZATION.md`, `STRATEGY_LAB_OBSOLETE_SURFACES.md`, `STRATEGY_LAB_RETENTION.md`, `STRATEGY_LAB_CORRECTIVE_MATRIX.md`, and `docs/audit/AUDIT-2026-08-05-STRATEGY-LAB-HARDENING.md`.

## GitHub governance

`docs/GITHUB_PUBLICATION.md`, `docs/decisions/DEC-2026-08-05-efficient-github-delivery.md`, and `docs/decisions/DEC-2026-08-05-universal-versioned-github-titles.md` remain authoritative. Every PR title, branch commit subject, and final squash subject uses the exact package-candidate prefix. `main` is never force-updated.

`VERSION=0.3.2`; `PLUGIN_REVISION=45` in this candidate. No release publication is included.

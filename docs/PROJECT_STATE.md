# os-zapret2-restyle — Current state

Project: `os-zapret2-restyle`
Primary branch: `main`
Published release/package: `v0.3.2` / `os-zapret2-restyle-0.3.2_1.pkg`
Current verified source baseline on `main`: `os-zapret2-restyle-0.3.2_42.pkg`
Current integration candidate: `os-zapret2-restyle-0.3.2_43.pkg`

Hardening revisions 25–42 are verified on `main`.

## Revision 43

- remove global circular `state.json` and `stop` compatibility aliases;
- make private session state and `stop.request` the only circular lifecycle artifacts;
- update end-to-end circular coverage to use `active.session` and private session paths;
- require terminal circular `completed` state;
- remove the unused state-level unfinished-stage hook;
- retain explicit worker-local skip orchestration for cancellation, error, prerequisite, and timeout paths;
- add mandatory obsolete-surface regression coverage.

Remaining work:

- `_44` retention and cleanup policy;
- `_45` final mandatory corrective CI matrix;
- `_46` final documentation and owner-assisted live OPNsense verification matrix.

## Current product authority

`docs/architecture/STRATEGY_LAB_CORRECTIVE_CONTRACT.md`, `STRATEGY_LAB_ACTIVATION.md`, `STRATEGY_LAB_PROFILE_OUTPUT.md`, `STRATEGY_LAB_UNIFIED_SHORTLIST.md`, `STRATEGY_LAB_UDP_INPUT.md`, `STRATEGY_LAB_CIRCULAR_ISOLATION.md`, `STRATEGY_LAB_CIRCULAR_OWNERSHIP.md`, `STRATEGY_LAB_SETTINGS_GUARD.md`, `STRATEGY_LAB_PERSISTED_RESULT_RELOAD.md`, `STRATEGY_LAB_STRUCTURED_RESULTS.md`, `STRATEGY_LAB_PROGRESS_LOCALIZATION.md`, `STRATEGY_LAB_OBSOLETE_SURFACES.md`, and `docs/audit/AUDIT-2026-08-05-STRATEGY-LAB-HARDENING.md`.

## GitHub governance

`docs/GITHUB_PUBLICATION.md`, `docs/decisions/DEC-2026-08-05-efficient-github-delivery.md`, and `docs/decisions/DEC-2026-08-05-universal-versioned-github-titles.md` remain authoritative. Every PR title, branch commit subject, and final squash subject uses the exact package-candidate prefix. `main` is never force-updated.

`VERSION=0.3.2`; `PLUGIN_REVISION=43` in this candidate. No release publication is included.

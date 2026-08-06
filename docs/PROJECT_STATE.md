# os-zapret2-restyle — Current state

Project: `os-zapret2-restyle`
Primary branch: `main`
Published release/package: `v0.3.2` / `os-zapret2-restyle-0.3.2_1.pkg`
Current verified source baseline on `main`: `os-zapret2-restyle-0.3.2_43.pkg`
Current integration candidate: `os-zapret2-restyle-0.3.2_44.pkg`

Hardening revisions 25–43 are verified on `main`.

## Revision 44

- keep the 20 newest deletable automated jobs and circular sessions by default;
- allow bounded limits from 1 through 1000;
- run automated and circular cleanup under their respective launcher locks;
- protect active/latest, nonterminal, malformed, unverified-restoration, and `RESTORE_FAILED` evidence;
- remove automated worker logs together with eligible job directories;
- treat known pre-mutation circular failures as safely deletable terminal evidence;
- fail closed on invalid limits;
- add mandatory dynamic retention coverage.

Remaining work:

- `_45` final mandatory corrective CI matrix;
- `_46` final documentation and owner-assisted live OPNsense verification matrix.

## Current product authority

`docs/architecture/STRATEGY_LAB_CORRECTIVE_CONTRACT.md`, `STRATEGY_LAB_ACTIVATION.md`, `STRATEGY_LAB_PROFILE_OUTPUT.md`, `STRATEGY_LAB_UNIFIED_SHORTLIST.md`, `STRATEGY_LAB_UDP_INPUT.md`, `STRATEGY_LAB_CIRCULAR_ISOLATION.md`, `STRATEGY_LAB_CIRCULAR_OWNERSHIP.md`, `STRATEGY_LAB_SETTINGS_GUARD.md`, `STRATEGY_LAB_PERSISTED_RESULT_RELOAD.md`, `STRATEGY_LAB_STRUCTURED_RESULTS.md`, `STRATEGY_LAB_PROGRESS_LOCALIZATION.md`, `STRATEGY_LAB_OBSOLETE_SURFACES.md`, `STRATEGY_LAB_RETENTION.md`, and `docs/audit/AUDIT-2026-08-05-STRATEGY-LAB-HARDENING.md`.

## GitHub governance

`docs/GITHUB_PUBLICATION.md`, `docs/decisions/DEC-2026-08-05-efficient-github-delivery.md`, and `docs/decisions/DEC-2026-08-05-universal-versioned-github-titles.md` remain authoritative. Every PR title, branch commit subject, and final squash subject uses the exact package-candidate prefix. `main` is never force-updated.

`VERSION=0.3.2`; `PLUGIN_REVISION=44` in this candidate. No release publication is included.

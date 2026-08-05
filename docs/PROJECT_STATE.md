# os-zapret2-restyle — Current state

Project: `os-zapret2-restyle`
Primary branch: `main`
Published release/package: `v0.3.2` / `os-zapret2-restyle-0.3.2_1.pkg`
Current verified source baseline on `main`: `os-zapret2-restyle-0.3.2_40.pkg`
Current integration candidate: `os-zapret2-restyle-0.3.2_41.pkg`

Hardening revisions 25–40 are verified on `main`.

## Revision 41

- terminal summary for target, mode, outcome, and semantic restoration;
- per-candidate protocol, port, family, endpoint addresses, and exact replay count;
- complete replay-verified Traffic Strategy profile instead of an internal fragment;
- safe copy control using Clipboard API with a textarea fallback;
- profile bytes remain outside HTML attributes;
- same renderer for live completion and persisted reload.

Together, revisions 40–41 complete finding 13.

Remaining work:

- `_42` detailed progress and complete localization;
- `_43` remove obsolete load-order/hook behavior and circular transition aliases;
- `_44` retention and cleanup policy;
- `_45` final mandatory corrective CI matrix;
- `_46` final documentation and owner-assisted live OPNsense verification matrix.

## Current product authority

`docs/architecture/STRATEGY_LAB_CORRECTIVE_CONTRACT.md`, `STRATEGY_LAB_ACTIVATION.md`, `STRATEGY_LAB_PROFILE_OUTPUT.md`, `STRATEGY_LAB_UNIFIED_SHORTLIST.md`, `STRATEGY_LAB_UDP_INPUT.md`, `STRATEGY_LAB_CIRCULAR_ISOLATION.md`, `STRATEGY_LAB_CIRCULAR_OWNERSHIP.md`, `STRATEGY_LAB_SETTINGS_GUARD.md`, `STRATEGY_LAB_PERSISTED_RESULT_RELOAD.md`, `STRATEGY_LAB_STRUCTURED_RESULTS.md`, and `docs/audit/AUDIT-2026-08-05-STRATEGY-LAB-HARDENING.md`.

## GitHub governance

`docs/GITHUB_PUBLICATION.md`, `docs/decisions/DEC-2026-08-05-efficient-github-delivery.md`, and `docs/decisions/DEC-2026-08-05-universal-versioned-github-titles.md` remain authoritative. Every PR title, branch commit subject, and final squash subject uses the exact package-candidate prefix. `main` is never force-updated.

`VERSION=0.3.2`; `PLUGIN_REVISION=41` in this candidate. No release publication is included.

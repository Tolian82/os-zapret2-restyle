# os-zapret2-restyle — Current state

Project: `os-zapret2-restyle`
Primary branch: `main`
Published release/package: `v0.3.2` / `os-zapret2-restyle-0.3.2_1.pkg`
Current verified source baseline on `main`: `os-zapret2-restyle-0.3.2_39.pkg`
Current integration candidate: `os-zapret2-restyle-0.3.2_40.pkg`

Hardening revisions 25–39 are verified on `main`.

## Revision 40

- atomic validated `latest.job` pointer;
- migration fallback to the newest existing job directory;
- active job remains preferred over historical latest;
- Diagnostics reload renders terminal completed/error result immediately;
- nonterminal reload resumes polling;
- no reload path starts a new lifecycle transaction.

Revision 40 completes the persistence/reload half of finding 13. Remaining work:

- `_41` structured final-result GUI and copy-profile controls;
- `_42` detailed progress and complete localization;
- `_43` remove obsolete load-order/hook behavior and circular transition aliases;
- `_44` retention and cleanup policy;
- `_45` final mandatory corrective CI matrix;
- `_46` final documentation and owner-assisted live OPNsense verification matrix.

## Current product authority

- `docs/architecture/STRATEGY_LAB_CORRECTIVE_CONTRACT.md`;
- `docs/architecture/STRATEGY_LAB_ACTIVATION.md`;
- `docs/architecture/STRATEGY_LAB_PROFILE_OUTPUT.md`;
- `docs/architecture/STRATEGY_LAB_UNIFIED_SHORTLIST.md`;
- `docs/architecture/STRATEGY_LAB_UDP_INPUT.md`;
- `docs/architecture/STRATEGY_LAB_CIRCULAR_ISOLATION.md`;
- `docs/architecture/STRATEGY_LAB_CIRCULAR_OWNERSHIP.md`;
- `docs/architecture/STRATEGY_LAB_SETTINGS_GUARD.md`;
- `docs/architecture/STRATEGY_LAB_PERSISTED_RESULT_RELOAD.md`;
- `docs/audit/AUDIT-2026-08-05-STRATEGY-LAB-HARDENING.md`.

## GitHub governance

`docs/GITHUB_PUBLICATION.md`, `docs/decisions/DEC-2026-08-05-efficient-github-delivery.md`, and `docs/decisions/DEC-2026-08-05-universal-versioned-github-titles.md` remain authoritative. Every PR title, branch commit subject, and final squash subject uses the exact package-candidate prefix. `main` is never force-updated.

`VERSION=0.3.2`; `PLUGIN_REVISION=40` in this candidate. No release publication is included.

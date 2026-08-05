# os-zapret2-restyle — Current state

Project: `os-zapret2-restyle`
Primary branch: `main`
Published release/package: `v0.3.2` / `os-zapret2-restyle-0.3.2_1.pkg`
Current verified source baseline on `main`: `os-zapret2-restyle-0.3.2_38.pkg`
Current integration candidate: `os-zapret2-restyle-0.3.2_39.pkg`

Patches 1–13 of the initial Strategy Lab delivery, corrective patches through revision 24,
and hardening revisions 25–38 are verified on `main`.

## Revision 39 scope

- add one fail-closed backend authority for automated, circular, and raw lifecycle-lock
  ownership;
- reject Settings Apply before any model mutation when lifecycle is busy;
- repeat the guard while holding the configuration lock immediately before save;
- treat circular restoration failure and unknown guard output as blocking;
- preserve shared-lock reconfigure and rollback as the final race defense;
- expose a read-only Settings lifecycle endpoint;
- add mandatory dynamic and PHP/configd contract tests.

## Hardening status

Completed through revision 38:

- runtime cleanup/readiness, hard deadline, stale automated-worker recovery, serialized
  parent state, local-only automatic interception;
- endpoint-bound requests and IPFW interception evidence;
- complete replay-verified multi-protocol profiles and validated generic UDP input;
- immutable circular sessions, serialized ownership, PID-reuse protection, stale cleanup,
  semantic restoration, and retry blocking.

Revision 39 completes finding 12. Remaining planned work:

- `_40` — restore persisted terminal results after page reload;
- `_41` — structured final-result GUI and profile-copy controls;
- `_42` — detailed progress and complete localization;
- `_43` — remove obsolete load-order/hook behavior and transition aliases;
- `_44` — retention and cleanup policy;
- `_45` — final mandatory corrective CI matrix;
- `_46` — final documentation and owner-assisted live OPNsense verification matrix.

## Current product authority

- `docs/architecture/STRATEGY_LAB_CORRECTIVE_CONTRACT.md`;
- `docs/architecture/STRATEGY_LAB_ACTIVATION.md`;
- `docs/architecture/STRATEGY_LAB_PROFILE_OUTPUT.md`;
- `docs/architecture/STRATEGY_LAB_UNIFIED_SHORTLIST.md`;
- `docs/architecture/STRATEGY_LAB_UDP_INPUT.md`;
- `docs/architecture/STRATEGY_LAB_CIRCULAR_ISOLATION.md`;
- `docs/architecture/STRATEGY_LAB_CIRCULAR_OWNERSHIP.md`;
- `docs/architecture/STRATEGY_LAB_SETTINGS_GUARD.md`;
- `docs/audit/AUDIT-2026-08-05-STRATEGY-LAB-HARDENING.md`.

## GitHub governance

`docs/GITHUB_PUBLICATION.md`,
`docs/decisions/DEC-2026-08-05-efficient-github-delivery.md`, and
`docs/decisions/DEC-2026-08-05-universal-versioned-github-titles.md` remain authoritative.
Every PR title, branch commit subject, and final squash subject uses the exact
package-candidate prefix. `main` is never force-updated. Documentation accompanies each
logical product patch.

`VERSION=0.3.2`; `PLUGIN_REVISION=39` in this candidate.

No tag, release, release asset, or pkg-repository publication is part of revision 39.

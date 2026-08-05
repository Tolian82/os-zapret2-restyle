# os-zapret2-restyle — Current state

Project: `os-zapret2-restyle`
Primary branch: `main`
Published release/package: `v0.3.2` / `os-zapret2-restyle-0.3.2_1.pkg`
Current verified source baseline on `main`: `os-zapret2-restyle-0.3.2_37.pkg`
Current integration candidate: `os-zapret2-restyle-0.3.2_38.pkg`

Patches 1–13 of the initial Strategy Lab delivery, corrective patches through revision 24,
and hardening revisions 25–37 are verified on `main`.

## Revision 38 scope

- serialize every circular launcher operation with a dedicated lock;
- identify the worker by PID plus process-start token rather than PID alone;
- refresh ownership after daemon execution;
- recover an ownerless stale session before another start;
- clean session-local dvtws2, divert socket, runtime files, and reserved IPFW rules;
- restore and verify the original semantic Zapret2 RUNNING or STOPPED state;
- clear ownership only after successful restoration;
- retain `RESTORE_FAILED` ownership and block unsafe retry;
- add mandatory dynamic ownership and stale-recovery tests.

## Hardening status

Completed through revision 37:

- runtime cleanup/readiness, residue cleanup, hard deadline, stale automated-worker
  recovery, serialized parent state, local-only automatic interception;
- endpoint-bound requests and IPFW interception evidence;
- complete replay-verified Traffic Strategy profiles;
- unified TLS 1.3, TLS 1.2, HTTP, QUIC, and configured UDP shortlist;
- supported validated generic UDP input;
- immutable completed parent jobs and independent circular sessions.

Revision 38 completes finding 11. Remaining planned work:

- `_39` — block Settings Apply while Strategy Lab or circular validation owns lifecycle;
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
- `docs/audit/AUDIT-2026-08-05-STRATEGY-LAB-HARDENING.md`.

## GitHub governance

`docs/GITHUB_PUBLICATION.md`,
`docs/decisions/DEC-2026-08-05-efficient-github-delivery.md`, and
`docs/decisions/DEC-2026-08-05-universal-versioned-github-titles.md` remain authoritative.
Every PR title, branch commit subject, and final squash subject uses the exact
package-candidate prefix. `main` is never force-updated. Documentation accompanies each
logical product patch.

`VERSION=0.3.2`; `PLUGIN_REVISION=38` in this candidate.

No tag, release, release asset, or pkg-repository publication is part of revision 38.

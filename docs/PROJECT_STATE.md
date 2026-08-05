# os-zapret2-restyle — Current state

Project: `os-zapret2-restyle`
Primary branch: `main`
Published release/package: `v0.3.2` / `os-zapret2-restyle-0.3.2_1.pkg`
Current verified source baseline on `main`: `os-zapret2-restyle-0.3.2_36.pkg`
Current integration candidate: `os-zapret2-restyle-0.3.2_37.pkg`

Patches 1–13 of the initial Strategy Lab delivery, corrective patches through revision 24,
and hardening revisions 25–36 are verified on `main`.

## Revision 37 scope

- create an independent private session for every circular validation;
- snapshot parent status, circular shortlist, and endpoints;
- preserve the completed parent job as immutable evidence;
- move circular state, PID, stop control, log, temporary runtime, lifecycle snapshot, and
  restoration result into the session;
- preserve evidence fields across circular state transitions;
- keep the current GUI/API contract based on the parent job ID;
- retain transition-only legacy symlink aliases into the private session until revision 43;
- add mandatory parent-immutability, session-local-runtime, and end-to-end tests.

## Hardening status

Completed through revision 36:

- runtime cleanup/readiness, residue cleanup, hard deadline, stale automated-worker
  recovery, serialized parent state, local-only automatic interception;
- endpoint-bound requests and IPFW interception evidence;
- complete replay-verified Traffic Strategy profiles;
- unified TLS 1.3, TLS 1.2, HTTP, QUIC, and configured UDP shortlist;
- supported validated generic UDP input.

Revision 37 addresses the first half of finding 11. Remaining planned work:

- `_38` — circular launch serialization, owner validation, stale-session cleanup and
  restoration;
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
- `docs/audit/AUDIT-2026-08-05-STRATEGY-LAB-HARDENING.md`.

## GitHub governance

`docs/GITHUB_PUBLICATION.md`,
`docs/decisions/DEC-2026-08-05-efficient-github-delivery.md`, and
`docs/decisions/DEC-2026-08-05-universal-versioned-github-titles.md` remain authoritative.
Every PR title, branch commit subject, and final squash subject uses the exact
package-candidate prefix. `main` is never force-updated. Documentation accompanies each
logical product patch.

`VERSION=0.3.2`; `PLUGIN_REVISION=37` in this candidate.

No tag, release, release asset, or pkg-repository publication is part of revision 37.

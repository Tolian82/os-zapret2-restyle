# os-zapret2-restyle — Roadmap

Status: **CURRENT / FORWARD-LOOKING**
Updated: 2026-08-14

This file answers only: **what should be done next?**
Current facts: [`PROJECT_STATE.md`](PROJECT_STATE.md).
Exact handoff: [`START_HERE.md`](START_HERE.md).
Current-line chronology/completed detail: [`history/current/v0.4.x.md`](history/current/v0.4.x.md).

A newer unambiguous owner instruction supersedes conflicting roadmap text immediately. Completed
history belongs in the current-line ledger/archive rather than growing this file indefinitely.

## Current priority — v0.4.1_13

**Model-C-only production finalization.** Model selection is already closed.

Implement:

- make Model C the only normal production Stage-60 runtime;
- remove automatic production fallback `C -> B -> A`;
- keep Model-C infrastructure failures explicit and bounded;
- preserve planner/CandidateSpec/ResourceInventory semantics;
- preserve source-port leasing/attribution, profile-compatible segmentation and readiness;
- preserve adaptive budgets, GET-4K discovery, cleanup/cancellation and Stage-90 restoration;
- retain Model A/B only as useful reference/benchmark/test tooling.

Acceptance:

- no silent production B/A replay;
- explicit bounded Model-C infrastructure failure;
- correct cleanup, attribution and segmentation;
- complete Strategy Lab corrective matrix PASS;
- FreeBSD 15 package qualification PASS.

Then, when owner package testing is requested, publish deterministic `_13` package and run one
selected normal OPNsense Model-C-only regression. A PASS closes the fallback-removal transition.

## Current v0.4.x status — compact only

- [x] Strategy Lab Python migration/hardening;
- [x] Model A reference baseline;
- [x] Model B warm/parallel investigation;
- [x] Model C architecture/integration;
- [x] Model C source-port/budget/lifecycle/readiness work;
- [x] Model C selected for production;
- [x] Lua/BLOB/discovery/current lifecycle measurements closed;
- [x] three-level documentation memory and explicit release/version authority;
- [ ] `_13` remove production B/A fallback;
- [ ] one owner-live `_13` regression and evidence closure.

Details/evidence are intentionally not duplicated here; use the current `v0.4.x` ledger.

## After `_13` live acceptance

Choose the next item from owner priority and changed risk. Do not automatically reopen completed A/B/C,
Lua, BLOB, discovery or cross-batch experiments.

### Owner-assisted regression backlog

Risk-selected future/release coverage:

1. initial normal Zapret2 state STOPPED;
2. Extended TLS 1.2 and HTTP;
3. capability-gated QUIC precheck behavior;
4. configured Generic UDP;
5. already-accessible target;
6. cancellation/internal failure containment;
7. circular start/stop/TTL/stale recovery;
8. Settings Apply guards and service-state correctness;
9. Diagnostics persisted-result reload;
10. RU/EN presentation/localization;
11. retention/cleanup boundaries;
12. reboot/residue verification.

These are not unconditional blockers for every patch; select by changed risk.

### Deferred research/performance

Retain but do not activate by inertia:

- candidate parallel width > 3;
- endpoint-level parallelism;
- cross-batch keep-warm only if new evidence invalidates the accepted decision;
- BLOB/Lua/discovery optimization only after material architecture change/new evidence;
- Model-C timeout/deadline audit only when owner/roadmap selects it or a concrete containment defect
  requires it.

### Long-term product directions

- OPNsense-native runtime/service reliability;
- Strategy Lab correctness across supported protocol/capability branches;
- coherent Settings/Diagnostics/Circular/retention lifecycle;
- RU/EN GUI behavior and package/runtime version visibility;
- bol-van/zapret2 management through the approved `setup.sh` backend;
- additional BLOB-repository GUI work only after its technical contract is supplied/approved.

## Future second-numeric-component transition

The second numeric component is the `4` in `0.4.x`. It never changes automatically. Only after the
owner explicitly requests/approves a transition such as `v0.4.x -> v0.5.x`, the same change must:

1. finalize current `v0.4.x` ledger;
2. create/freeze `history/archive/v0.4.x.md`;
3. initialize `history/current/v0.5.x.md`;
4. update `INDEX.md`, `START_HERE.md`, `PROJECT_STATE.md` and the short lifetime path;
5. retain all deep detailed records unchanged;
6. perform the mandatory complete `README.md` revision;
7. complete the full project release, including verified package publication into the OPNsense
   Pages/pkg repository for Web GUI installation.

A full release may be requested independently while remaining in `v0.4.x`; it does not authorize a
change to the second numeric component.

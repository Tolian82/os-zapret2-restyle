# os-zapret2-restyle — Roadmap

Status: **CURRENT**
Updated: 2026-08-14

This file answers: **What should be done next?**

Permanent principles: `docs/PROJECT_PRINCIPLES.md`.
Current facts: `docs/PROJECT_STATE.md`.
Exact immediate handoff: `docs/START_HERE.md`.

A newer unambiguous owner instruction immediately supersedes conflicting roadmap text. Once owner
canon is settled, old roadmap/history cannot reopen it. Long-term items are retained explicitly as
completed, superseded, rejected or deferred rather than silently disappearing.

## Continuity / governance work completed

- [x] documentation treated as project architecture rather than chat memory;
- [x] concise always-read `PROJECT_PRINCIPLES` layer;
- [x] exact `START_HERE` operational handoff;
- [x] zero-memory recovery checkpoint contract;
- [x] newest owner instruction/fact takes precedence over conflicting old active docs;
- [x] canonical principles file made cumulative;
- [x] historical DNS problem recorded as fixed/closed;
- [x] Model C recorded as selected production direction;
- [x] canon-lock rule: one unambiguous owner statement/confirmation is enough;
- [x] `зафиксируй` defined as full active-authority reconciliation;
- [x] stale CI/test contracts cannot override current canon;
- [x] owner-facing status defaults to understandable Russian;
- [x] repository/temporary-branch hygiene made a normal silent completion obligation;
- [x] broad active-doc audit found and corrected stale `_31` / “A-B-C not selected” text in root
  architecture and base Strategy Lab architecture.

Current docs/governance corrective keeps `VERSION=0.4.1`, `PLUGIN_REVISION=12`.

## Current priority — Model C production finalization

Model selection is **already closed**. The current priority is not “choose between B and C”; it is to
finish removing the legacy fallback from the already-selected Model-C production architecture.

Current packaged source: `v0.4.1_12`.
Next packaged source change: **`v0.4.1_13` — Model-C-only production finalization**.

### 1. Implement `_13`

- make Model C the only normal production Stage-60 runtime;
- remove automatic production fallback `C -> B -> A`;
- expose Model-C infrastructure failures explicitly/bounded;
- preserve CandidateSpec/ResourceInventory/search semantics;
- preserve source-port leasing/attribution;
- preserve `_11` profile-compatible physical segmentation;
- preserve `_12` readiness;
- preserve `eligible-work-v1` budgets and GET-4K discovery;
- preserve cleanup/cancellation and Stage-90 exact restoration;
- keep B/A only where useful as reference/benchmark/test tooling.

Acceptance:

- normal production Stage 60 reaches Model C only;
- no silent B/A replay;
- injected Model-C infrastructure failure is explicit and bounded;
- cleanup and source-port attribution remain correct;
- complete Strategy Lab corrective matrix passes;
- FreeBSD 15 package qualification passes.

### 2. Publish/test `_13`

After verified merge and owner package/testing request:

- persist deterministic `os-zapret2-restyle-0.4.1_13.pkg` on GitHub;
- verify exact package/source identity;
- perform one selected normal OPNsense Model-C-only regression;
- verify result handling, cleanup/restoration and absence of temporary IPFW/process/socket residue;
- record owner-live evidence.

A PASS closes the **fallback-removal transition**, not model selection (which is already closed).
A FAIL triggers diagnosis of the concrete observed defect only.

## Model-C work already completed

- [x] Model A cold correctness/reference baseline;
- [x] Model B controlled warm/reference baseline;
- [x] Model C source-port dispatcher integrated;
- [x] source-port leasing/collision corrective;
- [x] finite `eligible-work-v1` adaptive budgets;
- [x] stable semantic `v0.4.1` release;
- [x] Lua initialization measurement — no production change;
- [x] BLOB startup/RSS and common-set scaling — no production change;
- [x] discovery measurement — bounded GET-4K retained;
- [x] lifecycle measurement/harness series;
- [x] profile-compatible Model-C segmentation (`_11`);
- [x] readiness polling corrective (`_12`);
- [x] cross-batch keep-warm/reuse rejected for current architecture by measured evidence.

These are completed facts, not questions to rediscover in a new chat.

## After `_13` live acceptance

Select the next item by the owner's newest priority and current risk. Do not automatically reopen old
A/B/C, Lua, BLOB, discovery or cross-batch experiments.

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

### Deferred research/performance work

Retain but do not activate by inertia:

- candidate parallel width greater than three;
- endpoint-level parallelism;
- renewed cross-batch keep-warm only if later evidence invalidates the accepted `_12` decision;
- renewed BLOB/Lua/discovery optimization only after material architecture change/new evidence;
- Model-C-only timeout/deadline audit only when selected by owner/roadmap or triggered by a concrete
  containment defect.

### Long-term product directions

- continue OPNsense-native runtime/service reliability;
- continue Strategy Lab correctness across supported protocol/capability branches;
- keep Settings/Diagnostics/Circular/retention lifecycle coherent;
- maintain RU/EN GUI behavior and package/runtime version visibility;
- keep bol-van/zapret2 management through the single approved `setup.sh` backend;
- activate the separately discussed additional BLOB-repository GUI work only after its technical
  contract is explicitly supplied/approved.

## Before every GitHub delivery

- reconcile active docs against the newest owner canon;
- if the owner said `зафиксируй`, perform the full active-authority sweep in that docs change;
- record the most recent completed logical work/current recovery boundary;
- state what changes and why, intended effect and acceptance;
- record exact next step and complete further plan;
- correct stale tests/contracts instead of bending current canon;
- verify/clean temporary repository state as part of completion.

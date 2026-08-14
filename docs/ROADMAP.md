# os-zapret2-restyle — Roadmap

Status: **CURRENT**
Updated: 2026-08-14

This file answers: **What should be done next?**

Permanent principles: `docs/PROJECT_PRINCIPLES.md`.
Current facts: `docs/PROJECT_STATE.md`.
Exact immediate handoff: `docs/START_HERE.md`.

Long-term items are never silently dropped. When priorities change, mark work completed, superseded,
rejected or deferred and preserve the reason.

## Current priority

Finish the B -> C production transition, then return to the broader product / Strategy Lab backlog.

Current packaged source: `v0.4.1_12`.
Next packaged source change: **`v0.4.1_13` — Model-C-only production finalization**.

## Immediate ordered plan

### 1. `v0.4.1_13` — Model-C-only production finalization

- make Model C the only normal production Stage-60 runtime;
- retire automatic production fallback `C -> B -> A`;
- expose Model-C infrastructure failures explicitly and within existing bounded behavior;
- preserve planner/candidate semantics, leasing, attribution, `_11` segmentation, `_12` readiness,
  adaptive budgets, GET-4K discovery, cleanup and Stage-90 restoration;
- keep B/A only where useful as benchmark/reference/test tooling.

Acceptance:

- normal production Stage 60 is Model-C-only;
- no silent B/A replay;
- injected Model-C infrastructure failure is explicit/bounded;
- cleanup and source-port attribution remain correct;
- full Strategy Lab corrective matrix PASS;
- FreeBSD 15 package qualification PASS.

Exact source surfaces and required specialist reading are in `docs/START_HERE.md`.

### 2. Publish/test `_13`

After verified merge and owner package/testing request:

- persist deterministic `os-zapret2-restyle-0.4.1_13.pkg` on GitHub;
- verify exact source/tag/asset identity;
- perform one selected normal OPNsense Model-C-only regression;
- verify result handling, cleanup/restoration and no temporary IPFW/process/socket residue;
- record owner-live evidence.

PASS closes the B -> C transition. FAIL triggers diagnosis of the concrete observed defect only.

## Model-C transition work already completed

- [x] Model A cold correctness/reference baseline;
- [x] Model B controlled warm/parallel reference;
- [x] Model C source-port dispatcher integrated (`v0.4.0_23`);
- [x] source-port lease/collision corrective (`_25`);
- [x] finite `eligible-work-v1` adaptive budgets (`_26`);
- [x] stable semantic `v0.4.1` release;
- [x] Lua initialization measurement (`v0.4.1_2`) — no production change;
- [x] BLOB startup/RSS and common-set scaling (`_3/_4`) — no production change;
- [x] discovery HEAD/GET-1/GET-4K measurement (`_5/_6`) — keep GET-4K;
- [x] lifecycle measurement/harness series (`_7` through `_10`);
- [x] Model-C profile-compatible segmentation (`_11`);
- [x] readiness polling corrective (`_12`);
- [x] cross-batch keep-warm/reuse decision closed for current architecture.

Do not treat these completed items as uninvestigated merely because a new chat starts. Reopen them
when the owner, roadmap, new reproducible evidence or a material architecture change requires it.

## After B -> C closure

Select the next item by owner priority and current risk rather than automatically opening another
Model-C optimization.

### Owner-assisted regression backlog

Risk-selected coverage retained for future work/release gates:

1. initial normal Zapret2 state STOPPED;
2. Extended TLS 1.2 and HTTP;
3. capability-gated QUIC;
4. configured Generic UDP;
5. already-accessible target;
6. cancellation/internal failure containment;
7. circular start/stop/TTL/stale recovery;
8. Settings Apply guards and service-state correctness;
9. Diagnostics persisted-result reload;
10. RU/EN presentation/localization;
11. retention/cleanup boundaries;
12. reboot/residue verification.

These are not unconditional blockers for every patch; select rows according to changed risk.

### Deferred research/performance work

Retain, do not activate by inertia:

- candidate parallel width greater than three;
- endpoint-level parallelism;
- renewed cross-batch keep-warm only if later evidence invalidates the `_12` decision;
- renewed BLOB/Lua/discovery optimization only after a material architecture change or new evidence;
- Model-C-only timeout/deadline audit when selected by owner/roadmap or triggered by a concrete
  containment defect.

### Long-term product directions

- continue OPNsense-native service/runtime management and maintenance reliability;
- continue Strategy Lab correctness across supported protocol/capability branches;
- keep Settings/Diagnostics/Circular/retention behavior coherent with Strategy Lab lifecycle;
- maintain RU/EN GUI behavior and package/runtime version visibility;
- keep bol-van/zapret2 management through the single approved `setup.sh` backend;
- activate the separately discussed additional BLOB-repository GUI work only after its repository and
  technical contract are explicitly supplied/approved.

## Before every GitHub delivery

Apply the documentation contract in `docs/PROJECT_PRINCIPLES.md`:

- what changes and why;
- expected result/acceptance;
- complete near-term and long-term/deferred plan;
- reconcile the plan immediately before publication and update changed priorities first.

# os-zapret2-restyle — Roadmap

Status: **CURRENT**
Updated: 2026-08-14

This file answers: **What should be done next?**

Permanent principles are canonical in `docs/PROJECT_PRINCIPLES.md`.
Current state is in `docs/PROJECT_STATE.md`.
Exact continuation handoff is in `docs/START_HERE.md`.

The roadmap records both immediate and long-term work. Long-term items are never silently dropped;
when priorities change they are explicitly completed, superseded, rejected or deferred.

## Current priority

Finish the Model-B -> Model-C production transition cleanly, then return to the broader product /
Strategy Lab backlog.

Current packaged source: `v0.4.1_12`.
Next packaged source change: **`v0.4.1_13` — Model-C-only production finalization**.

## Immediate ordered plan

### 0. Documentation/governance handoff — current docs-only change

Purpose:

- make permanent project principles guaranteed startup context;
- make documentation the reliable operational memory it was originally designed to be;
- remove stale `_6/_7` current-state/roadmap guidance;
- record exact `_12` state and `_13` next action;
- make every future GitHub delivery carry synchronized documentation for scope/reason, expected
  result and complete near/long-term plan;
- require plan reconciliation immediately before publication.

Expected result:

- a new chat reads `AGENTS -> PROJECT_PRINCIPLES -> START_HERE -> PROJECT_STATE` and can begin the
  documented task without reconstructing project history;
- audits remain valid when the plan/owner/evidence requires them;
- ordinary known-scope work no longer pays for unrelated full GitHub/repository inventory;
- current docs no longer point backward to `_6/_7` as the active boundary.

After merge: start `_13` directly if current repository state still matches the handoff.

### 1. `v0.4.1_13` — Model-C-only production finalization

What changes:

- make Model C the only normal production Stage-60 runtime;
- retire automatic production fallback `C -> B -> A`;
- surface Model-C infrastructure failure explicitly/bounded instead of silently replaying old
  engines;
- keep Model B/A code only where useful for benchmark/reference/test tooling;
- preserve leasing, attribution, `_11` profile segmentation, `_12` readiness, adaptive budgets,
  GET-4K discovery, cleanup and Stage-90 restoration.

Primary files:

- `src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/stage60_model_c.py`;
- `src/opnsense/scripts/OPNsense/Zapret/strategy_lab_python.py`;
- `src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/stage60_source_port_lease.py`;
- `scripts/test-strategy-lab-stage60-model-c-production.sh`;
- narrow-search hits that encode production fallback selection.

Acceptance:

- normal production Stage 60 is Model-C-only;
- no silent B/A replay after Model-C infrastructure failure;
- injected infrastructure failure is explicit/bounded;
- cleanup and source-port attribution remain correct;
- full Strategy Lab corrective matrix PASS;
- FreeBSD 15 package qualification PASS.

### 2. Publish/test `_13`

After verified merge and owner package/testing request:

- persist deterministic `os-zapret2-restyle-0.4.1_13.pkg` on GitHub;
- verify exact source/tag/asset identity;
- perform one selected normal OPNsense Model-C-only regression;
- verify result handling, cleanup/restoration and no temporary IPFW/process/socket residue;
- record owner-live evidence.

If PASS: close the B -> C transition.
If FAIL: diagnose the concrete defect from evidence and fix only that defect.

## Model-C transition work already completed

- [x] Model A cold correctness/reference baseline;
- [x] Model B controlled warm/parallel experiments and accepted reference;
- [x] Model C source-port dispatcher selected and integrated (`v0.4.0_23`);
- [x] source-port collision/lease corrective (`_25`);
- [x] `eligible-work-v1` finite adaptive budgets (`_26`);
- [x] stable semantic `v0.4.1` release;
- [x] Lua initialization measurement (`v0.4.1_2`) — no production change;
- [x] BLOB startup/RSS and common-set scaling (`_3/_4`) — no production change;
- [x] discovery HEAD/GET-1/GET-4K measurement (`_5/_6`) — keep GET-4K;
- [x] lifecycle amortization measurement series (`_7+`);
- [x] measurement-harness corrections (`_8/_9/_10`);
- [x] Model-C profile-compatible segmentation corrective (`_11`);
- [x] warm readiness polling corrective (`_12`);
- [x] cross-batch keep-warm/reuse decision closed with no further production architecture change.

Do not treat these completed items as uninvestigated in a new session. Reopen them when the owner,
roadmap, a new reproducible defect or material architecture change calls for a new audit/retest.

## After B -> C transition closure

Return to product/Strategy Lab work according to owner priority and current risk, rather than
opening another Model-C optimization automatically.

### Owner-assisted regression backlog

Retained risk-selected coverage:

1. initial normal Zapret2 state STOPPED;
2. Extended TLS 1.2 and HTTP paths;
3. capability-gated QUIC;
4. configured Generic UDP;
5. already-accessible target behavior;
6. cancellation/internal failure containment;
7. circular start/stop/TTL/stale recovery;
8. Settings Apply guards and service-state correctness;
9. Diagnostics persisted-result reload behavior;
10. RU/EN presentation/localization checks;
11. retention/cleanup boundaries;
12. reboot/residue verification.

These are not all unconditional blockers for every patch. Select rows according to the changed
risk. When a future release requires a broader matrix, record that gate explicitly before release.

### Deferred performance/research ideas

Retain, but do not activate by inertia:

- candidate parallel width greater than three;
- endpoint-level parallelism;
- renewed cross-batch keep-warm only if later architecture/evidence invalidates the `_12` decision;
- renewed BLOB/Lua/discovery optimization only if later architecture materially changes the accepted
  assumptions;
- Model-C-only timeout/deadline audit when selected by plan/owner or triggered by a concrete
  containment defect.

### Broader project/product work

After the current Strategy Lab transition is closed, use owner priority plus `REQUIREMENTS.md` and
current product state to select the next implementation area. Preserve existing working GUI/runtime
behavior and do not displace approved functionality with speculative redesign.

Known long-term product directions retained in project documentation include:

- continue OPNsense-native service/runtime management and maintenance reliability;
- continue Strategy Lab correctness and owner-assisted coverage for supported protocol/capability
  branches;
- keep Settings/Diagnostics/Circular/retention behavior coherent with the Strategy Lab lifecycle;
- maintain RU/EN GUI behavior and package/runtime version visibility;
- keep bol-van/zapret2 management through the single approved `setup.sh` backend rather than
  introducing a second installer;
- only activate the separately discussed additional BLOB-repository GUI work after its repository
  and technical contract are explicitly supplied/approved.

## Before every future GitHub delivery

Apply the documentation contract in `docs/PROJECT_PRINCIPLES.md`:

- record what changes and why;
- record the expected result/acceptance boundary;
- record the complete next plan, including long-term/deferred work;
- immediately before publication, reconcile this roadmap and current handoff with what was learned;
- update changed priorities **before** publishing.

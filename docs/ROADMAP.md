# os-zapret2-restyle — Roadmap

==================================================
DOCUMENT ROLE
==================================================

Question answered:
What should be done next?

Purpose:
Record ordered future work and gates without duplicating current-state or implementation history.

Updated when:
Priority, sequencing, or acceptance gates change.

Read after:
`docs/DEVLOG.md`.

Do not store here:
Detailed rationale, current live logs, or completed implementation internals.

==================================================
CURRENT PRIORITY
==================================================

Stable project publication `v0.4.1` / package `os-zapret2-restyle-0.4.1_1.pkg` is complete
and the owner reports successful upgrade/normal operation.

Current independent logical change: `v0.4.1_2` — measure common/current Model-C Lua
initialization against the candidate-minimal union without changing production Stage 60.

Source analysis already shows that all 16 native Stage-60 expansion candidates declare the
same `zapret-lib.lua` + `zapret-antidpi.lua` dependencies. Because the shared Model-C bucket
also necessarily loads `zapret-auto.lua` and `strategy_lab_model_c.lua`, current and
candidate-minimal initialization are expected to be the same four-file set.

Acceptance therefore requires truthful negative evidence: if the packaged measurement
reports `equivalent_init_set`, no timing/RSS speedup may be claimed and production Model C
must remain unchanged. Then advance directly to BLOB loading/startup/RSS measurement.

Current state authority: `docs/PROJECT_STATE.md`.
Lua measurement authority: `docs/architecture/STRATEGY_LAB_LUA_INITIALIZATION.md`.

==================================================
COMPLETED STRATEGY LAB FOUNDATION
==================================================

- [x] asynchronous Strategy Lab architecture, lifecycle, network precheck, candidate
  runtime/search/stability/extended/circular/GUI;
- [x] shell-era corrective series and semantic restoration hardening;
- [x] Python 3.13 state/stage/request/probe/candidate/search/result ownership;
- [x] live DNS/restoration corrections and risk-based owner-live policy.

==================================================
COMPLETED ADAPTIVE-SEARCH / RUNTIME SERIES
==================================================

Historical engineering labels `_28`-`_33` are completed work-item names, not package
revision suffixes.

- [x] Stage-50 evidence is priority only, not Stage-60 reachability gating;
- [x] immutable CandidateSpec + ResourceInventory;
- [x] deterministic native Zapret2 graph, fixed endpoint epoch and adaptive planner;
- [x] measured deadline containment and finalist validation;
- [x] cold Model A correctness/reference;
- [x] controlled width-three Model B fallback/reference with corrected failed attribution;
- [x] preferred one-worker Model C dispatcher;
- [x] `preferred-free-else-alternate` source-port leasing and fresh Model-B fallback lease;
- [x] `eligible-work-v1` adaptive finite budgets after Stage 30;
- [x] `_26` owner-live Extended `telegram.org`, `job.xhdgCU`, Model-C 16/16 no-fallback
  execution with exact budget persistence and clean restoration.

Do not repeat old Model-B architecture benchmarks unless later work invalidates their
assumptions.

==================================================
COMPLETED RELEASE CYCLE — `v0.4.1 / 0.4.1_1`
==================================================

- [x] VERSION `0.4.1`, revision reset to `1`;
- [x] PR/CI/FreeBSD 15 qualification;
- [x] semantic tag/Release/package/checksum/Pages/pkg repository publication;
- [x] durable publication evidence;
- [x] owner upgrade/install smoke: PASS, normal operation reported correct.

Published semantic tag `v0.4.1` remains immutable release history.

==================================================
OPTIMIZATION SEQUENCE
==================================================

### 1. Lua initialization — current `_2`

- [x] establish exact current CandidateSpec Lua dependencies;
- [x] establish Model-C shared requirements (`zapret-auto.lua`, dispatcher Lua);
- [ ] package deterministic equivalence report;
- [ ] CI/FreeBSD 15 qualification and testing prerelease;
- [ ] owner-installed report;
- [ ] if equivalent, close with no production change.

### 2. BLOB loading/startup/RSS — next if Lua sets are equivalent

Measure candidate/BLOB declaration loading cost independently. Compare startup/readiness and
RSS only where the rendered resource sets are genuinely distinct. Preserve exact BLOB
identity/class, attribution, deadlines and cleanup.

### 3. Later independent ideas

- lazy bucket creation versus eager bucket creation;
- candidate width greater than three;
- endpoint-level parallelism;
- broader dispatcher/bucket grouping beyond one adaptive frontier batch.

Every item requires its own evidence and must not silently weaken candidate attribution,
finite deadlines, cleanup or semantic restoration.

QUIC remains capability/precheck scope rather than an adaptive Stage-60 search priority.
IPv6 remains capability-gated and lower priority.

==================================================
BROADER OWNER-ASSISTED REGRESSION BACKLOG
==================================================

The canonical matrix remains `docs/verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md`.
Rows are selected per change/release risk; they are not all unconditional blockers.

Retained backlog includes initial Zapret2 STOPPED; Extended TLS1.2/HTTP and capability-gated
QUIC; Generic UDP; already-accessible target; cancellation/internal failure; circular
start/stop/TTL/stale recovery; Settings Apply guards; Diagnostics reload behavior;
RU/EN presentation; retention and reboot/residue checks.

==================================================
RELEASE BOUNDARY
==================================================

Stable `v0.4.1` remains the published semantic release. `v0.4.1_2` is an independent testing
package revision for measurement and must not mutate the semantic `v0.4.1` tag/asset history.
Future stable releases require their own exact VERSION authorization and release pipeline.

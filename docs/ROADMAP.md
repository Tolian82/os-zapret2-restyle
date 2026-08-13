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

The independent Model-C measurement sequence has now closed three optimization questions
without production changes:

- `_2`: common/current Lua initialization is already the candidate-minimal set;
- `_3` + `_4`: BLOB startup/readiness/RSS cost is not material for the current width-three
  architecture, including the representative common eager external-BLOB set;
- `_5` + `_6`: HEAD/GET-1/GET-4K discovery probes agree on comparable pairs, but the
  cheaper probes do not provide a material timing benefit; production discovery remains
  bounded GET-4K.

Current production remains:

`C-warm-bucket-source-port-dispatch -> B-warm-worker-parallel-batched -> A-cold-fallback`.

Next independent logical change: prepare a measurement-only `v0.4.1_7` experiment for
**Model-C bucket creation timing**. Compare the current production lifecycle with explicit
lazy-versus-eager bucket-start variants and measure whether avoiding creation of buckets
for search branches that are never reached produces a reproducible benefit.

The experiment must measure at least first-result latency, total Stage-60 wall time,
startup/readiness, ready/settled RSS, created/used/unused bucket counts, candidate
attribution, cleanup and semantic restoration. Production Model C must remain unchanged
until owner-live evidence demonstrates a material reproducible advantage outside normal
jitter with equivalent results and clean lifecycle behavior.

Current state authority: `docs/PROJECT_STATE.md`.
Adaptive-search experiment authority: `docs/verification/STRATEGY_LAB_ADAPTIVE_SEARCH_EXPERIMENTS.md`.
Model-C authority: `docs/architecture/STRATEGY_LAB_MODEL_C.md`.

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

### 1. Lua initialization — closed by `_2`

- [x] establish exact current CandidateSpec Lua dependencies;
- [x] establish Model-C shared requirements (`zapret-auto.lua`, dispatcher Lua);
- [x] package deterministic equivalence report;
- [x] CI/FreeBSD 15 qualification and testing prerelease;
- [x] owner-installed report;
- [x] close with no production change because current and candidate-minimal sets are equivalent.

### 2. BLOB loading/startup/RSS — closed by `_3` + `_4`

- [x] measure BLOB-free, built-in and representative external-BLOB startup/readiness/RSS;
- [x] measure representative common eager external-BLOB set at current width-three scale;
- [x] compare repeated samples against normal jitter;
- [x] owner-live acceptance;
- [x] close with no production change because no material startup/readiness/RSS penalty was measured.

Lazy BLOB loading is therefore not justified by the current evidence. Reopen only if later
runtime architecture materially increases BLOB-set width or otherwise invalidates the
accepted `_3`/`_4` assumptions.

### 3. Discovery probe agreement/cost — closed by `_5` + `_6`

- [x] compare HEAD, GET-1 and production GET-4K against the same native candidate corpus;
- [x] collect multidomain owner-live evidence;
- [x] correct the measurement finalizer boundary;
- [x] verify clean cleanup/restoration;
- [x] keep production GET-4K because the cheaper probes do not provide a material timing benefit.

### 4. Model-C bucket creation timing — next independent experiment

Prepare measurement-only `_7` without changing production search behavior.

Compare the current lifecycle with explicit lazy/eager bucket-start variants and record:

- first-result latency;
- total Stage-60 wall time;
- bucket startup/readiness timing;
- ready and settled RSS;
- created, used and unused bucket counts;
- exact candidate/result equivalence;
- candidate attribution;
- deadline containment;
- cleanup and semantic restoration.

A production change is allowed only after separate accepted evidence shows a reproducible
material advantage beyond normal jitter and all correctness/lifecycle gates remain PASS.

### 5. Later independent ideas

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

Stable `v0.4.1` remains the published semantic release. The latest published and owner-live
testing candidate is `v0.4.1_6`; the next packaged measurement change, if implemented, is
`v0.4.1_7` and must not mutate the semantic `v0.4.1` tag/asset history. Future stable
releases require their own exact VERSION authorization and release pipeline.

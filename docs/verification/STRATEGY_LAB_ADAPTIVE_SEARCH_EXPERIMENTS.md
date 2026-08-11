# Strategy Lab adaptive-search experiment plan

==================================================
DOCUMENT ROLE
==================================================

Question answered:
How are disputed Strategy Lab search/runtime optimizations measured before they become
production architecture?

Purpose:
Define reproducible A/B/C runtime experiments, validation/probe experiments, resource
loading measurements and timeout telemetry with explicit accept/reject evidence.

Raw appliance logs belong under `docs/verification/evidence/`.

==================================================
STATUS
==================================================

Approved experiment plan.

- **Model A is accepted as the cold correctness/performance reference** on `v0.4.0_11` / `job.TtZeaH`.
- **Model B three-worker coexistence is owner-live accepted**: first complete accept on `_16`, followed by five consecutive accepts with verified restoration on owner-installed `_17`.
- `_17` also closes the separate failed-readiness continuation in source regression without requiring an intentionally broken owner appliance run.
- **Current experiment: `_18` exhaustive no-candidate Model B benchmark.** It measures the same complete `graph_exhausted` Stage-60 corpus in exact order using batches of at most three warm workers.
- Model C, source-port dispatch, warm preload policy and true parallel candidate probing remain unexecuted/unapproved.
- No warm-runtime model is production-approved.

Accepted Model A medians are total candidate `1580 ms`, readiness `1046 ms`, prepare
`140 ms`, launch `17 ms`, probe `220 ms`, stop+cleanup `81 ms`, and RSS `4332 KiB`.

The `_17` repeated Model B coexistence set records mean pool startup `1163.6 ms`, mean
dispatch median `12.4 ms`, and mean probe median `200.3 ms`. The already-warm
`dispatch+probe` path is about `86.5%` below the cold candidate median. Amortizing one
three-worker startup over three probes gives about `600.6 ms/candidate`, roughly `62.0%`
below the cold median. These are mechanism-level estimates, not full-search speedups.

Exact evidence:

- `docs/verification/evidence/2026-08-10-v0.4.0_11-model-a-reference-collected.md`;
- `docs/verification/evidence/2026-08-10-v0.4.0_16-model-b-live-accept.md`;
- `docs/verification/evidence/2026-08-11-v0.4.0_17-model-b-reproducibility.md`.

==================================================
QUESTIONS TO ANSWER
==================================================

1. How much wall-clock time is spent in preparation, startup/readiness, network probe and cleanup?
2. Does keeping dvtws2 warm materially reduce total search time on the owner appliance?
3. Can several warm workers coexist with deterministic traffic ownership and no result changes?
4. Can one warm dvtws2 contain several compatible candidate chains and select one deterministically?
5. Does warm reuse leak conntrack/Lua/orchestrator state between candidate tests?
6. Is broad Lua/BLOB preload worth its startup/RSS cost?
7. Do external BLOB count/size and candidate count materially affect startup time or RSS?
8. Is lazy warm-bucket creation preferable to eager initialization?
9. Does true simultaneous probing save enough time to justify contention and attribution complexity?
10. Which lightweight discovery probe best agrees with finalist validation at lowest cost?
11. Which operation/stage timeouts remain inefficient or inconsistent after measured runtime changes?

==================================================
REFERENCE CONDITIONS
==================================================

Every comparison uses, as far as the tested hypothesis permits:

- the same OPNsense appliance and WAN path;
- the same installed Zapret2 release and current `ResourceInventory`;
- the same target hostname/SNI and pinned endpoint/search epoch;
- the same candidate corpus and order unless order is the tested variable;
- the same normal-service initial state;
- the same discovery probe implementation;
- clean semantic restoration before and after the experiment.

A faster result is invalid if candidate identity, endpoint identity or interception cannot
be proven.

==================================================
MODEL A — COLD REFERENCE
==================================================

Definition:
One candidate creates one fresh runtime and dvtws2, probes, then tears down completely
before the next candidate.

Accepted reference:

- package/job: `v0.4.0_11` / `job.TtZeaH` / Standard `rutracker.org`;
- 25 cold candidate samples;
- `conclusion=reference_collected`;
- total candidate median/p90/max: `1580 / 3411 / 3463 ms`;
- readiness median/p90/max: `1046 / 1052 / 1138 ms`;
- RSS minimum/median/p90/max: `4316 / 4332 / 4348 / 4356 KiB`;
- restoration verified and temporary runtime clean.

Model A remains the final verification fallback even if another discovery model wins.

==================================================
WHY WORST-CASE SEARCH USES A NO-CANDIDATE TARGET
==================================================

Adaptive Stage 60 stops when enough strong candidates have been found. A successful target
therefore under-samples the search graph and cannot measure maximum user wait time.

Existing owner evidence demonstrates the difference:

- Standard `telegram.org` `job.tU3wiL`: `NO_CANDIDATE`, all 16 Stage-60 candidates checked, `stopped_reason=graph_exhausted`, Stage 60 about `89.247 s`, total through restoration about `144.125 s`;
- Extended `telegram.org` `job.hsP8Ro`: all 16 candidates checked, total about `169.262 s`;
- Standard `rutracker.org` `job.UPRDlc`: three working candidates found, Stage 60 stopped after six candidates, total about `71.023 s`.

Worst-case runtime comparisons must therefore use a `NO_CANDIDATE / graph_exhausted`
reference, preferably collected immediately before the warm benchmark on the same package
and provider path.

==================================================
MODEL B — MULTIPLE WARM DVTWS2 WORKERS
==================================================

Definition:
Start compatible candidate workers ahead of probes. Each worker owns a distinct temporary
runtime identity and divert endpoint. Candidate probes remain sequential until a separate
parallelism experiment is approved.

Coexistence gate already proven owner-live:

- unique validated PID and divert identity;
- numeric per-worker and aggregate RSS;
- one selected IPFW route per probe;
- selected-rule counter movement and endpoint attribution;
- cold PASS/FAIL equivalence;
- repeated A -> B/C -> A stability;
- independent stop and controlled-death cleanup;
- semantic lifecycle restoration and no reserved-rule residue.

The first complete accept was `_16`; owner-installed `_17` repeated the same accepted path
five times with 5/5 accepts and 5/5 verified restoration.

==================================================
MODEL B `_18` — EXHAUSTIVE NO-CANDIDATE BENCHMARK
==================================================

Purpose:
Measure a complete no-winner Stage-60 workload rather than a small selected coexistence
corpus.

Reference requirements:

- fresh completed Standard domain job;
- terminal `NO_CANDIDATE`;
- Stage 60 `stopped_reason=graph_exhausted`;
- zero Stage-60 working candidates;
- complete persisted `candidates` and adaptive `schedule` arrays;
- verified restoration and clean temporary runtime;
- current `ResourceInventory` identical to the reference.

The exact persisted candidate corpus/order is replayed in **warm batches of at most three
workers**. This preserves the already proven coexistence width instead of introducing a new
16-resident-worker experiment.

For each batch:

1. verify dedicated ports/rules are clean;
2. render the exact retained CandidateSpecs into the three physical Model B slots;
3. start the batch before probes;
4. require stable readiness, unique PID/divert identity and numeric RSS;
5. probe candidates sequentially in original Stage-60 order;
6. allow only the selected temporary route;
7. require interception attribution and no inactive route;
8. require every cold no-candidate replay to remain non-PASS;
9. require remaining workers to stay healthy;
10. clean the complete batch before the next batch.

Measure:

- measured warm exhaustive candidate-runtime wall time;
- per-batch and total startup time;
- per-batch cleanup time;
- dispatch/probe medians;
- peak aggregate batch RSS;
- exact candidate-order completeness;
- result equivalence and route attribution;
- final semantic restoration.

Comparison fields:

- `candidate_runtime_speedup_percent` — measured warm exhaustive runtime versus the sum of the same persisted cold Stage-60 candidate durations;
- `projected_full_job_speedup_percent` — projection from `cold_job_total - cold_stage60_candidate_runtime + warm_exhaustive_search`.

The projected full-job value is explicitly not a measured production Model B job.

Reject the benchmark if any worker identity, route ownership, cold no-candidate equivalence,
batch cleanup or final restoration check fails.

Exact source contract:
`docs/patches/v0.4.0_18.md`.

==================================================
MODEL C — ONE WARM DVTWS2 WITH CANDIDATE BUCKET
==================================================

Model C remains future work. A compatible bucket may be initialized once only after a
minimal dispatcher proves exact candidate selection. Plain first-match profile ordering is
not sufficient.

Required evidence includes explicit candidate identity, stable selection for the whole
connection, no cross-candidate state, A -> B -> A equivalence, fail-closed dispatcher
behavior and complete cleanup. Only then compare wall time and RSS with Models A/B.

==================================================
CONTROLLED SOURCE-PORT SELECTOR HYPOTHESIS
==================================================

A source-port selector is only a hypothesis. Before use it must prove client source-port
control, visibility at the dvtws2 interception point, NAT stability or deliberate handling,
no selector collisions, bidirectional flow identity and retry safety. Failure rejects this
selector without necessarily rejecting Model C.

==================================================
LUA / BLOB PRELOAD EXPERIMENTS
==================================================

If warm buckets remain viable, compare candidate-minimal initialization with broader Lua
and realistic BLOB preload sets. Measure startup/readiness, RSS, log differences, result
equivalence and state retained across repeated flows. Preloading never changes functional
`CandidateSpec` dependencies.

==================================================
BUCKET COMPATIBILITY AND LAZY STARTUP
==================================================

Future warm buckets must group only semantically compatible candidates by IP family,
transport/port, L7 constraints, process-global arguments, Lua/BLOB requirements, stateful
requirements and firewall ownership.

Compare eager versus lazy initialization using time-to-first-result, total wall time, RSS
and unused work. Prefer lazy startup unless measurements show a repeatable disadvantage.

==================================================
PARALLEL CANDIDATE-PROBE EXPERIMENT
==================================================

True parallel candidate probing remains last. It may be attempted only after deterministic
sequential warm execution is accepted for the same corpus. Compare result equivalence,
route attribution, WAN contention, CPU/RSS, total wall time and cancellation/cleanup.
Reject parallel probing if attribution changes, results change or savings are too small.

==================================================
DISCOVERY / STABILITY / FINALIST EXPERIMENTS
==================================================

Discovery must minimize cost without false confidence relative to finalist validation.
Strict 3/3 stability remains fail-fast: any failure rejects the 3/3 criterion immediately,
while skipped later attempts are recorded as unnecessary rather than PASS.

Finalists keep a cold exact-profile replay and bounded GET/depth evidence. A successful
resource that ends before the configured depth remains `inconclusive`, not a false depth
PASS.

==================================================
TIMEOUT POLICY
==================================================

Timeout changes are evidence-driven. Do not derive new production stage limits from the
small coexistence harness. The exhaustive no-candidate benchmark is the appropriate Model B
input for maximum Stage-60 runtime analysis, but production timeout changes still require
review of complete job lifecycle/restoration and repeated owner evidence.

==================================================
ARCHITECTURE-SELECTION RULE
==================================================

A warm model may replace Model A discovery only after it proves, on comparable owner-live
workloads:

- deterministic candidate identity and interception;
- exact or explicitly acceptable result equivalence;
- bounded cleanup/cancellation/restoration;
- meaningful repeated wall-clock improvement including a no-candidate exhaustive case;
- acceptable RSS/process complexity;
- no need for unproven parallel probing to obtain the claimed benefit.

Until an explicit decision records those gates as satisfied, production Strategy Lab
continues to use Model A and all Model B/C reports retain `production_approved=false`.

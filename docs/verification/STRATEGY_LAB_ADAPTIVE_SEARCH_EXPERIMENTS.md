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

Updated when:
An experimental hypothesis, measurement, safety gate or architecture-selection criterion
changes.

Read after:
`docs/architecture/STRATEGY_LAB_ADAPTIVE_SEARCH.md` and
`docs/decisions/DEC-2026-08-08-strategy-lab-adaptive-search.md`.

Do not store here:
Raw logs from an individual OPNsense run. Those belong under `docs/verification/evidence/`
when the experiment is actually executed.

==================================================
STATUS
==================================================

Approved experiment plan. **Model A is accepted as the cold correctness/performance
reference. Model B three-worker coexistence is owner-live accepted/reproducible, and the
complete sequential no-candidate exhaustive Model B replay is owner-live ACCEPT 5/5 on
`v0.4.0_19`. Controlled parallel candidate probing is now the selected experiment on
`v0.4.0_20`.** Model C, warm-bucket selection and production warm-runtime adoption remain
unexecuted/unapproved.

Owner Standard `rutracker.org` job `job.TtZeaH` on `v0.4.0_11` produced 25 cold samples
and `conclusion=reference_collected`. Every machine-checkable Model A coverage gate passed,
including PASS/FAIL candidates, repetitions, `blob-free`/`builtin`/`external` resources,
`-d8`, overlapping TLS/443 candidates, numeric RSS and verified clean restoration.

Accepted `_11` reference medians are total candidate 1580 ms, readiness 1046 ms, prepare
140 ms, launch 17 ms, probe 220 ms and stop+cleanup 81 ms. Candidate-process RSS after
readiness is tightly clustered around 4332 KiB median, 4348 KiB p90 and 4356 KiB max.

The first complete owner-live Model B coexistence accept was collected on `_16`; `_17`
repeated the unchanged accepted ready-pool experiment five times. Those runs gave the
mechanism-level estimates of about 86.5% lower already-warm dispatch+probe cost and about
62.0% lower startup-amortized three-candidate cost versus the Model A 1580 ms cold median.
Those figures are not full-search speedups.

The complete sequential exhaustive comparison is now available from `_19`. Reference
`job.tMYnFA` is Standard `telegram.org`, `NO_CANDIDATE`, 16/16 Stage-60
`graph_exhausted`, with two pinned endpoints. Five unchanged `_19` warm replays all
returned `conclusion=accept` with verified restoration. Warm exhaustive search times were
74886, 74692, 75083, 74780 and 74600 ms: mean 74808.2 ms, median 74780 ms, total min/max
spread 483 ms. Against the retained 89012 ms cold Stage-60 candidate runtime this is about
15.96% mean measured candidate-runtime improvement. The full-job value remains explicitly
a projection rather than measured Model B full-job wall time.

Owner CPU context for that series was two logical CPUs on a Westmere-class virtual CPU.
That is evidence context only. **No experiment or candidate width is accepted/rejected by
CPU count.** The architecture must remain meaningful on other OPNsense systems, including
4/6/8+ logical-CPU appliances.

Exact accepted/repeated evidence:

- `docs/verification/evidence/2026-08-10-v0.4.0_11-model-a-reference-collected.md`;
- `docs/verification/evidence/2026-08-10-v0.4.0_16-model-b-live-accept.md`;
- `docs/verification/evidence/2026-08-11-v0.4.0_17-model-b-reproducibility.md`;
- `docs/verification/evidence/2026-08-11-v0.4.0_19-model-b-exhaustive-reproducibility.md`.

No warm-runtime model is production-approved by these results. Every selected optimization
must preserve the accepted cold reference result and Strategy Lab lifecycle safety.

==================================================
QUESTIONS TO ANSWER
==================================================

1. How much wall-clock time is currently spent in candidate preparation, Lua/BLOB
   initialization, dvtws2 startup/readiness and cleanup compared with the network probe?
2. Does keeping dvtws2 warm materially reduce time-to-result on OPNsense hardware?
3. Can several warm dvtws2 processes coexist on isolated divert ownership without
   capturing or changing one another's probe traffic?
4. Can one warm dvtws2 contain several compatible candidate chains and select exactly one
   deterministically for a probe?
5. Does warm reuse leak conntrack/Lua/orchestrator state from one candidate test into the
   next?
6. Is a common preloaded Lua bundle faster or slower enough than candidate-minimal
   initialization to justify the memory/complexity tradeoff?
7. Do external BLOB count/size and candidate count materially affect startup time or RSS?
8. Does lazy warm-bucket creation reduce work without harming search responsiveness?
9. Is any benefit gained by truly simultaneous candidate probes after warm coexistence is
   proven, or do WAN/CPU contention and diagnostic ambiguity outweigh it?
10. Which lightweight discovery probe gives the best agreement with finalist deep GET at
    the lowest cost?
11. Which current operation/stage timeouts are too small, too large or internally
    inconsistent?

==================================================
REFERENCE CONDITIONS
==================================================

Every comparison uses the same job-level controls:

- same OPNsense appliance and WAN path for one comparison set;
- same installed Zapret2 release and recorded `ResourceInventory`;
- same target hostname/SNI;
- same pinned endpoint/search epoch;
- same candidate corpus and order unless order itself is the tested variable;
- same normal-service initial state;
- same probe semantics for A/B/C equivalence measurement;
- clean restoration before and after the experiment set.

CPU count, CPU model and observed load are measurement metadata. They are retained to make
cross-appliance comparisons interpretable, but they do not silently change candidate
semantics, worker identity or acceptance criteria.

The candidate corpus must contain at least:

- a known passing candidate where the provider permits one;
- a known failing candidate;
- a BLOB-free candidate;
- a built-in-BLOB candidate;
- an external-file-BLOB candidate when its file is installed;
- candidates with different `out-range` values, including the agreed `-d8` regression;
- at least two otherwise overlapping TCP/443/TLS candidates to expose first-match or
  dispatch ambiguity.

All comparisons retain the same target/interception evidence. A faster result that cannot
prove which candidate handled the traffic is invalid.

For maximum search-time comparison, successful early-stop targets are insufficient. Owner
`_9` evidence shows Standard `telegram.org` exhausting all 16 Stage-60 candidates and
completing through restoration in about 144.125 s, while Standard `rutracker.org` stopped
Stage 60 after six candidates when three winners were found and completed in about 71.023
s. Exhaustive timing therefore uses a `NO_CANDIDATE / graph_exhausted` reference.

==================================================
MODEL A — COLD REFERENCE
==================================================

Definition:
One candidate creates one fresh candidate runtime and one fresh dvtws2, then tears it down
completely before the next candidate.

Purpose:
Provide the correctness reference and a complete timing breakdown.

Executed reference:

- package/job: `v0.4.0_11` / `job.TtZeaH` / Standard `rutracker.org`;
- 25 retained cold candidate samples;
- `conclusion=reference_collected` with no missing coverage checks;
- total candidate median/p90/max: 1580 / 3411 / 3463 ms;
- readiness median/p90/max: 1046 / 1052 / 1138 ms;
- RSS minimum/median/p90/max: 4316 / 4332 / 4348 / 4356 KiB;
- initial/final service: RUNNING -> RUNNING;
- restoration verified, strategy unchanged, temporary runtime clean.

Measure per candidate:

- `prepare_ms`;
- `resource_init_ms` when separable from launch;
- `launch_ms`;
- `ready_ms`;
- `probe_ms`;
- `stop_ms`;
- `cleanup_ms`;
- total candidate wall time;
- RSS after readiness;
- IPFW/divert identity and counter movement;
- probe classification and endpoint identity;
- process/rule/socket residue after cleanup.

Repeat enough times to distinguish normal variance from a stable startup cost. Record
median and a useful tail measure rather than relying on one best run.

Model A remains the final verification fallback even if another discovery model wins.

==================================================
MODEL B — MULTIPLE WARM DVTWS2 WORKERS
==================================================

Definition:
Start several compatible candidate workers ahead of their probes. Each worker owns
distinct temporary runtime identity and divert ownership. Candidate probes are initially
executed sequentially.

Required coexistence evidence:

- each worker has a unique validated PID/process identity;
- each worker is bound to its intended divert endpoint;
- IPFW rules send the selected probe to exactly the intended worker;
- the intended worker's interception counter proves traffic ownership;
- a probe result matches Model A for the same candidate;
- stopping one worker does not disturb the others;
- cancellation can remove all job-owned workers;
- Stage-90-equivalent restoration observes no candidate residue;
- repeated candidate selection does not change because another warm worker exists.

Measure:

- initial pool startup cost;
- amortized candidate dispatch/probe time;
- total search wall time for the same corpus;
- per-worker and aggregate RSS;
- process/socket/rule count;
- cleanup time with one and several workers;
- failure cleanup when one worker dies unexpectedly.

Reject Model B if worker identity, traffic ownership, cleanup or cold-equivalence is not
deterministic. A performance improvement cannot compensate for a false PASS/FAIL or leaked
interception state.

The coexistence portion is owner-live accepted: `_16` produced the first complete accept
and `_17` repeated it five times with verified restoration.

==================================================
MODEL B SEQUENTIAL EXHAUSTIVE NO-CANDIDATE BENCHMARK — `_18` / `_19`
==================================================

The benchmark consumes a completed Standard domain reference whose Stage 60 ended
`NO_CANDIDATE / graph_exhausted`. The reference must contain zero working Stage-60
candidates, a complete persisted candidate/schedule corpus, verified restoration and the
same current `ResourceInventory`.

The exact persisted Stage-60 candidate corpus/order is replayed in **warm batches of at
most three workers**. This retains the owner-proven Model B coexistence width instead of
introducing 16 resident workers.

For each sequential batch:

- verify dedicated Model B ports/rules are free;
- render the exact retained CandidateSpecs into the physical worker slots;
- start the whole batch before candidate probes;
- require stable readiness, unique PID/divert identity and numeric RSS;
- probe candidates sequentially in original Stage-60 order;
- replay every pinned endpoint sequentially for every candidate;
- keep one selected temporary IPFW route during one endpoint probe;
- require interception attribution;
- require every cold no-candidate replay to remain non-PASS;
- require workers to remain healthy during the batch;
- clean the entire batch before starting the next batch.

`_18` produced the full cold reference `job.tMYnFA` but exposed a single-endpoint harness
assumption. `_19` corrected multi-endpoint replay and is owner-live ACCEPT 5/5.

Measured `_19` sequential exhaustive result:

- cold candidate corpus runtime: 89012 ms;
- warm run values: 74886 / 74692 / 75083 / 74780 / 74600 ms;
- mean: 74808.2 ms;
- median: 74780 ms;
- mean measured candidate-runtime improvement: about 15.96%;
- peak aggregate three-worker RSS: 12976–12992 KiB;
- all five runs: result equivalence PASS and restoration verified.

The report separates:

- `candidate_runtime_speedup_percent` — measured warm exhaustive runtime versus the sum of
  the same persisted cold Stage-60 candidate durations;
- `projected_full_job_speedup_percent` — projection using
  `cold_job_total - cold_stage60_candidate_runtime + warm_exhaustive_search`.

The second value is explicitly not a measured Model B full Strategy Lab run.

Exact contracts:

- `docs/patches/v0.4.0_18.md`;
- `docs/patches/v0.4.0_19.md`.

==================================================
MODEL B CONTROLLED PARALLEL CANDIDATE-PROBE EXPERIMENT — `_20`
==================================================

True parallel testing is deliberately last and is now selected because Model B proved
both deterministic coexistence and reproducible complete sequential exhaustive replay.

`_20` changes only the experiment harness:

- the exact persisted `job.tMYnFA` corpus/order remains authoritative;
- at most three already-isolated warm dvtws2 workers exist in one batch;
- up to three **candidate tasks** execute concurrently;
- pinned endpoints **inside one candidate remain sequential**;
- production Strategy Lab remains Model A;
- `production_approved=false`.

The `_19` single-active-route assumption cannot be used when three candidate probes are in
flight. Multiple rules matching only `from me -> selected_ip:443` would be ambiguous. `_20`
therefore assigns one unique controlled TCP source port to every candidate/endpoint probe.
Each temporary IPFW rule must match:

- the dedicated Model B rule/divert identity;
- TCP;
- the exact requested local source port;
- the exact pinned destination IP;
- destination port 443;
- outbound WAN identity.

The requested source port must be free before the probe. The complete source-port plan must
be unique and bounded. Selected-rule counter growth, fixed endpoint identity and the source
port selector are retained as attribution evidence. All temporary rules must disappear by
batch cleanup.

Required `_20` acceptance:

- same current `ResourceInventory` and exact persisted corpus/order;
- all warm batches ready with unique worker PID/divert identity and numeric RSS;
- unique/free source-port plan;
- at most three candidate tasks concurrently;
- actual candidate overlap observed in each multi-worker batch;
- pinned endpoints sequential within each candidate;
- every endpoint uses its fixed selected IP and dedicated source-port-qualified route;
- no cold no-candidate result becomes PASS;
- workers remain healthy through each batch;
- batch cleanup succeeds and no Model B rule/listener residue remains;
- final semantic restoration is verified.

Measure and retain:

- `logical_cpu_count` and appliance CPU identity as context only;
- candidate parallel width and maximum observed overlap;
- per-batch parallel probe wall time;
- complete parallel exhaustive search wall time;
- endpoint-probe and candidate elapsed distributions;
- pool startup and cleanup cost;
- per-worker/aggregate RSS;
- source-port plan and route attribution;
- result equivalence;
- restoration.

Compare `_20` directly with the accepted `_19` sequential exhaustive distribution, not
with the earlier three-candidate mechanism-level estimate. A 2-core owner appliance is a
valid low-resource live test, not an architecture limit; other OPNsense systems may expose
more or less benefit.

Reject parallel probing if it introduces ambiguous attribution, changes pass/fail results,
violates the concurrency bound, prevents cleanup/restoration, or saves too little wall time
to justify lifecycle/debugging complexity.

Exact source contract:
`docs/patches/v0.4.0_20.md`.

==================================================
MODEL C — ONE WARM DVTWS2 WITH CANDIDATE BUCKET
==================================================

Definition:
A compatible bucket is initialized once in one dvtws2 process. A minimal laboratory
dispatcher selects exactly one preloaded candidate chain for the current probe flow.

Plain `--new` is insufficient because Zapret2 selects the first matching profile. Model C
does not pass until the selection mechanism proves exact chain identity.

Required dispatcher evidence:

- requested `candidate_id` is explicit and auditable;
- exactly that execution chain is invoked for the test flow;
- selection is stable for the complete connection;
- concurrent unrelated traffic cannot accidentally select a laboratory candidate;
- a candidate cannot inherit another candidate's per-flow state;
- repeated A -> B -> A matches cold A, cold B, cold A;
- dispatcher failure fails closed instead of falling through to another candidate;
- cleanup removes all dispatcher/bucket state.

Only after that contract is proven compare performance with Models A and B.

Measure bucket initialization, switch overhead, total search wall time, RSS/state growth,
result agreement and cleanup/restoration cost.

==================================================
CONTROLLED SOURCE-PORT SELECTOR HYPOTHESIS
==================================================

A controlled source port can encode or qualify laboratory flow identity. `_20` uses the
source port only to make **three separate IPFW divert rules deterministic**; this does not
by itself approve source-port selection for Model C.

For any future Model-C dispatcher use, still verify in order:

1. the chosen probe client can reserve/request the intended local source-port range;
2. dvtws2/Lua receives enough packet/flow context to observe the selector unambiguously;
3. NAT does not rewrite the selector before the relevant interception point, or the
   dispatcher deliberately uses the observed translated value;
4. IPFW/divert routing cannot cause a selector collision or bypass;
5. the connection retains its candidate identity bidirectionally for its flow lifetime;
6. connection retries cannot silently choose a different candidate;
7. adjacent candidate IDs cannot cross-select under repeated trials.

Failure rejects that dispatcher hypothesis without rejecting Model C as a whole.

==================================================
LUA PRELOAD EXPERIMENT
==================================================

Compare at least:

- candidate-minimal required Lua initialization;
- the current broad/all-available Lua initialization baseline;
- a proven common warm-bucket bundle if Model C reaches that stage.

Measure startup/readiness time, RSS, fatal/startup log differences, candidate result
equivalence and state retained across repeated flows.

`CandidateSpec` continues to record only functional dependencies regardless of preload
policy. Preloading is not allowed to redefine a candidate.

==================================================
BLOB LOADING EXPERIMENT
==================================================

Measure startup/readiness and RSS with controlled resource sets:

- no external BLOB;
- built-in BLOB only;
- small inline pattern;
- one representative external `.bin`;
- several semantically compatible external `.bin` resources.

Do not include unrelated protocol BLOBs simply to increase count. Missing required files
reject the candidate before runtime launch; they are not silently substituted.

==================================================
BUCKET COMPATIBILITY AND LAZY STARTUP
==================================================

If warm buckets remain viable, test compatibility grouping by:

- IP family;
- TCP/UDP and server port;
- L7/payload constraints;
- process-global dvtws2 arguments;
- Lua initialization set;
- BLOB set;
- stateful/orchestrator requirements;
- firewall/divert ownership.

Compare eager initialization with lazy initialization on first use. Measure time-to-first
result, total wall time, RSS and unused initialization work. Prefer lazy startup unless
measurements show a repeatable user-visible disadvantage that justifies eager cost.

==================================================
DISCOVERY PROBE EXPERIMENT
==================================================

The target architecture separates inexpensive discovery from finalist deep validation but
does not hardcode the cheapest probe before measurement.

Compare bounded TLS/HTTP connection checks and minimal response probes against finalist GET
reference. Record duration, agreement, false PASS/FAIL, timeout/inconclusive counts and
endpoint/interception evidence quality.

The selected discovery probe must minimize cost without creating false confidence that
materially degrades winner selection.

==================================================
3/3 FAIL-FAST EXPERIMENT
==================================================

Confirm strict stability semantics and fail-fast execution are equivalent:

- PASS/PASS/PASS -> accepted 3/3;
- any failure -> rejected immediately after that failure;
- skipped later attempts are recorded as unnecessary, not PASS;
- cancellation/timeout remains distinguishable from network FAIL.

Measure saved probe time and verify no fail-fast rejection could have satisfied 3/3.

==================================================
LONG-GET / 16-KIB VALIDATION EXPERIMENT
==================================================

For the best two to three candidates:

- use the pinned endpoint and original hostname/SNI;
- start from a clean connection;
- request a resource expected to produce a sufficiently long response;
- record response status and actual body bytes;
- require interception evidence for the exact candidate;
- distinguish network failure, HTTP failure, timeout and short-resource completion.

Classification:

- `pass` — required connection/protocol evidence passes and at least 16 KiB is received;
- `fail` — a required network/protocol condition fails;
- `inconclusive` — an otherwise valid selected resource completes successfully but cannot
  provide 16 KiB.

The last case must not become a false 16-KiB PASS or erase separately proven connectivity.

==================================================
TIMEOUT TELEMETRY EXPERIMENT
==================================================

Instrument and collect distributions for DNS, candidate/resource preparation, dvtws2
launch/readiness, discovery, stability, final GET, stop/TERM/KILL, firewall/runtime cleanup
and normal-service restoration.

For each deadline record measured normal/tail range, failure/timeout range, cleanup
allowance, containing parent deadline and remaining-budget admission rule.

The accepted model must satisfy:

`operation deadline <= candidate deadline <= stage deadline <= job deadline`.

A child must not be started when the remaining parent/job budget cannot contain its
required execution and cleanup envelope.

Do not derive production stage limits from a small coexistence or parallel harness. Any
timeout change requires complete lifecycle/restoration review.

==================================================
EVALUATION MATRIX
==================================================

Every A/B/C or hybrid proposal is scored on:

- result agreement with Model A;
- false PASS/FAIL count;
- deterministic candidate attribution;
- time-to-first-working-candidate;
- time-to-two/three stable finalists;
- total search wall time;
- startup/readiness overhead;
- RSS and process/rule/socket footprint;
- state leakage across candidates;
- WAN/CPU contention where concurrency is tested;
- cancellation behavior;
- cleanup/restoration correctness;
- implementation/debugging complexity.

Hard rejection conditions:

- any unexplained result mismatch against the cold reference;
- ambiguous candidate attribution;
- leaked dvtws2, IPFW rule, divert listener or job state;
- loss of mandatory restoration behavior;
- a dispatch mechanism that can silently execute the wrong candidate.

Among models that pass correctness/safety, prefer the simplest model whose measured
latency benefit is repeatable and materially larger than normal run-to-run variation.

==================================================
EVIDENCE AND DECISION OUTPUT
==================================================

Each experiment produces a dated evidence record with:

- exact plugin/main and Zapret2 runtime identities;
- appliance/OS/CPU identity relevant to timing;
- resource inventory;
- candidate corpus;
- commands or automated fixture used;
- raw per-phase timings;
- result/equivalence table;
- cleanup/restoration evidence;
- conclusion: `accept`, `reject`, or `inconclusive`;
- follow-up decision/document links.

Only an `accept` result followed by an updated decision may convert an experimental
mechanism into the production Strategy Lab architecture.

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

Approved experiment plan; experiments not yet executed.

No A/B/C result, source-port dispatcher, warm-worker preload policy or revised timeout is
considered production-approved merely because it is technically possible. Every selected
optimization must first preserve the cold reference result and Strategy Lab lifecycle
safety.

==================================================
QUESTIONS TO ANSWER
==================================================

1. How much wall-clock time is currently spent in candidate preparation, Lua/BLOB
   initialization, dvtws2 startup/readiness and cleanup compared with the network probe?
2. Does keeping dvtws2 warm materially reduce time-to-result on the owner's OPNsense
   hardware?
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
   proven, or do network contention and diagnostic ambiguity outweigh it?
10. Which lightweight discovery probe gives the best agreement with finalist deep GET at
    the lowest cost?
11. Which current operation/stage timeouts are too small, too large or internally
    inconsistent?

==================================================
REFERENCE CONDITIONS
==================================================

Every comparison uses the same job-level controls:

- same OPNsense appliance and WAN path for a comparison set;
- same installed Zapret2 release and recorded `ResourceInventory`;
- same target hostname/SNI;
- same pinned endpoint/search epoch;
- same candidate corpus and order unless order itself is the tested variable;
- same normal-service initial state;
- same probe implementation for A/B/C equivalence measurement;
- clean restoration before and after the experiment set.

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

==================================================
MODEL A — COLD REFERENCE
==================================================

Definition:
One candidate creates one fresh candidate runtime and one fresh dvtws2, then tears it down
completely before the next candidate.

Purpose:
Provide the correctness reference and a complete timing breakdown.

Measure per candidate:

- `prepare_ms`;
- `resource_init_ms` when it can be separated from launch;
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

The first experiment proves coexistence only. It does not test simultaneous different
strategies.

Required evidence:

- each worker has a unique validated PID/process identity;
- each worker is bound to its intended divert endpoint;
- IPFW rules send the selected probe to exactly the intended worker;
- only the intended worker's interception counter changes for that probe;
- a probe result matches Model A for the same candidate;
- stopping one worker does not disturb the others;
- cancellation can remove all job-owned workers;
- Stage-90 restoration observes no candidate residue;
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

==================================================
MODEL C — ONE WARM DVTWS2 WITH CANDIDATE BUCKET
==================================================

Definition:
A compatible bucket is initialized once in one dvtws2 process. A minimal laboratory
dispatcher selects exactly one preloaded candidate chain for the current probe flow.

Plain `--new` is insufficient because Zapret2 selects the first matching profile. Model C
therefore does not pass until the selection mechanism proves exact chain identity.

Required dispatcher evidence:

- requested `candidate_id` is explicit and auditable;
- exactly that execution chain is invoked for the test flow;
- selection is stable for the complete connection;
- concurrent unrelated traffic cannot accidentally select a laboratory candidate;
- a candidate cannot inherit another candidate's per-flow state;
- repeated selection of A -> B -> A produces the same result as cold A, cold B, cold A;
- dispatcher failure fails closed instead of falling through to an unintended candidate;
- cleanup removes all dispatcher/bucket state.

Only after that contract is proven compare performance with Models A and B.

Measure:

- bucket initialization time by candidate count;
- bucket initialization time by Lua/BLOB bundle size;
- steady-state candidate-switch overhead;
- total search wall time;
- RSS and state growth after repeated probes;
- result agreement with cold reference;
- cleanup/restoration cost.

==================================================
CONTROLLED SOURCE-PORT SELECTOR HYPOTHESIS
==================================================

One proposed Model-C selector encodes candidate identity in a controlled client source
port and lets the laboratory dispatcher map that flow to a candidate.

This is a hypothesis, not an approved dependency.

Verify in order:

1. the chosen probe client can reserve/request the intended local source-port range;
2. dvtws2/Lua receives enough packet/flow context to observe the selector unambiguously;
3. NAT on the tested OPNsense path does not rewrite the selector before the relevant
   interception point, or the dispatcher deliberately uses the observed translated value;
4. IPFW/divert routing does not cause a selector collision or bypass;
5. the same connection retains its candidate identity bidirectionally for the required
   flow lifetime;
6. connection retries cannot silently choose a different candidate;
7. two adjacent candidate IDs cannot cross-select under repeated trials.

Failure at any step rejects source-port dispatch without rejecting Model C as a whole; a
different deterministic selector may still be investigated separately.

==================================================
LUA PRELOAD EXPERIMENT
==================================================

Compare at least:

- candidate-minimal required Lua initialization;
- the current broad/all-available Lua initialization baseline;
- a proven common warm-bucket bundle if Model C reaches that stage.

For each, measure:

- startup/readiness time;
- RSS;
- fatal/startup log differences;
- candidate result equivalence;
- state retained across repeated flows.

`CandidateSpec` continues to record only functional dependencies regardless of which
preload policy is faster. Preloading is not allowed to redefine a candidate.

==================================================
BLOB LOADING EXPERIMENT
==================================================

Measure startup/readiness and RSS with controlled resource sets:

- no external BLOB;
- built-in BLOB only;
- small inline pattern;
- one representative external `.bin`;
- several semantically compatible external `.bin` resources.

Do not include unrelated protocol BLOBs simply to increase count. The objective is to
learn the cost of realistic preload strategies.

Record missing-resource behavior explicitly. A missing required file rejects the
candidate before runtime launch; it is not silently substituted with another BLOB.

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

Test two schedules:

- eager: initialize all predicted buckets before search;
- lazy: initialize a bucket only when adaptive search reaches its first candidate.

Measure time-to-first-result, total wall time, RSS and unused initialization work. Prefer
lazy startup unless measurements show a repeatable user-visible disadvantage that
justifies eager cost.

==================================================
PARALLEL CANDIDATE-PROBE EXPERIMENT
==================================================

True parallel testing is deliberately last.

It may be attempted only after Model B or C proves deterministic coexistence under
sequential probes.

Compare sequential versus simultaneous candidate probes for:

- result equivalence;
- IPFW/divert counter isolation;
- WAN contention;
- DNS/endpoint identity;
- CPU/RSS;
- total wall time;
- log/evidence attribution;
- cancellation and cleanup behavior.

Reject parallel probing if it introduces ambiguous attribution, changes pass/fail results
or saves too little wall time to justify the added lifecycle/debugging complexity.

==================================================
DISCOVERY PROBE EXPERIMENT
==================================================

The target architecture separates inexpensive discovery from finalist deep validation,
but does not hardcode the cheapest probe before measurement.

Compare candidate discovery signals such as a bounded TLS/HTTP connection check and a
minimal response probe against the final GET reference.

For each method record:

- duration;
- agreement with finalist deep validation;
- false PASS count;
- false FAIL count;
- timeout/inconclusive count;
- endpoint and interception evidence quality.

The selected discovery probe must minimize cost without producing a false confidence
signal that materially degrades final winner selection.

==================================================
3/3 FAIL-FAST EXPERIMENT
==================================================

Confirm that strict stability semantics and fail-fast execution are equivalent:

- PASS/PASS/PASS -> accepted 3/3;
- any failure -> rejected for the 3/3 criterion immediately after that failure;
- skipped later attempts are recorded as unnecessary, not PASS;
- cancellation/timeout remains distinguishable from a network FAIL.

Measure saved probe time on unstable candidates and verify that no candidate rejected by
fail-fast could have satisfied the required 3/3 result.

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
- `inconclusive` for the 16-KiB depth criterion — the otherwise valid selected resource
  completes successfully but cannot provide 16 KiB.

The last case must not be rewritten as a 16-KiB PASS. It also must not erase separately
proven connectivity/stability evidence.

==================================================
TIMEOUT TELEMETRY EXPERIMENT
==================================================

Instrument and collect distributions for:

- DNS A/AAAA operation;
- candidate argument/resource preparation;
- dvtws2 launch;
- readiness checks;
- discovery probe;
- stability probe;
- final long GET;
- stop/TERM grace/KILL fallback;
- firewall and runtime cleanup;
- normal-service restoration.

Review every current constant after data exists. For each deadline record:

- measured normal range and tail;
- failure/timeout range;
- required cleanup allowance;
- parent deadline that contains it;
- remaining-budget admission rule.

The accepted model must satisfy:

`operation deadline <= candidate deadline <= stage deadline <= job deadline`.

An operation may receive less than its nominal limit only when the remaining parent/job
budget is explicitly too small and the operation is not started. The parent must not
start a child with a nominal 15-second allowance and then kill it after five seconds.

==================================================
EVALUATION MATRIX
==================================================

Every A/B/C or hybrid proposal is scored on the same dimensions:

- result agreement with Model A;
- false PASS/FAIL count;
- deterministic candidate attribution;
- time-to-first-working-candidate;
- time-to-two/three stable finalists;
- total search wall time;
- startup/readiness overhead;
- RSS and process/rule/socket footprint;
- state leakage across candidates;
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
- appliance/OS identity relevant to timing;
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

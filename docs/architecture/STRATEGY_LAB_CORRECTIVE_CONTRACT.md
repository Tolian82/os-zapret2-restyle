# Strategy Lab corrective contract

==================================================
DOCUMENT ROLE
==================================================

Question answered:
What runtime, state-machine, cancellation, timeout, restoration, GUI, and verification
contracts must the activated Strategy Lab satisfy before live OPNsense validation?

Purpose:
Record the approved corrective contract derived from the 2026-08-05 source audit of
package candidate `0.3.2_15` and later live corrective evidence.

Authority:
This document supplements `docs/architecture/STRATEGY_LAB.md` and supersedes any
conflicting implementation assumptions in earlier Strategy Lab delivery documents.
The existing product architecture remains valid unless explicitly corrected here.

Search-policy amendment:
`docs/decisions/DEC-2026-08-08-strategy-lab-adaptive-search.md` supersedes this document
only where it describes family hard gating, QUIC candidate search, fixed candidate count,
fixed output range or one-cold-process search as a permanent policy. State, cancellation,
restoration and lifecycle safety remain authoritative. The `_27` executable path retains
its current behavior until the corresponding `_28`–`_33` source patch changes it.

Approved by the project owner on 2026-08-05 and extended by the `_6` corrective series.

==================================================
CORRECTIVE OBJECTIVE
==================================================

The activated Strategy Lab must become a deterministic asynchronous transaction that:

- progresses through an explicit monotonic stage sequence;
- records cancellation atomically and honors it during active probes;
- produces truthful terminal `state`, `outcome`, and localized messages;
- enforces one overall deadline in addition to per-operation and per-stage limits;
- constructs the final shortlist only after every applicable search branch;
- restores the initial Zapret2 semantic service state before exposing circular tests;
- never reports restoration failure as normal completion;
- retains completed partial evidence after cancel or timeout;
- keeps the saved Traffic Strategy immutable;
- is covered by an end-to-end regression state-machine test before live validation.

==================================================
EXPLICIT STAGE MACHINE
==================================================

The only approved user-visible stage order is:

```text
00 -> 10 -> 20 -> 30 -> 40 -> 50 -> 60 -> 70 -> 80 -> 85 -> 90 -> 99
```

Meaning:

- 00 — target initialization;
- 10 — lifecycle lock and initial-state snapshot;
- 20 — verified stop of the normal Zapret2 service when required;
- 30 — network capability precheck;
- 40 — clean target baseline;
- 50 — low-cost TLS 1.3 reconnaissance/evidence;
- 60 — adaptive TLS 1.3 candidate search;
- 70 — stability confirmation;
- 80 — extended TLS 1.2/HTTP/configured-UDP branches; QUIC remains only the fixed
  Stage-30 capability/precheck in the adaptive target;
- 85 — final shortlist and recommendation;
- 90 — temporary cleanup and semantic restoration;
- 99 — final report.

`current_stage` is monotonic. Stage 85 never runs before stage 80 has either completed
or been explicitly marked `SKIPPED`. Stage 90 and stage 99 are finalization stages and
are never bypassed after normal runtime mutation begins.

Worker orchestration must use explicit stage functions. Loading order must not select
control flow by overriding the same shell function from successive modules.

==================================================
JOB STATE AND OUTCOME CONTRACT
==================================================

Machine-readable `state` describes lifecycle position. `outcome` describes the final
product result.

Allowed non-terminal states:

- `queued`;
- `running`;
- `cancel_requested`.

Allowed terminal states:

- `completed`;
- `error`.

Approved terminal mapping:

| state | outcome | meaning |
|---|---|---|
| `completed` | `SUCCESS` | stable working shortlist produced |
| `completed` | `NO_CANDIDATE` | valid search completed without a stable candidate |
| `completed` | `TARGET_ACCESSIBLE` | clean baseline already reaches every required endpoint |
| `completed` | `PARTIAL` | controlled cancel or bounded incomplete result with restored service |
| `error` | `TIMEOUT` | overall or required stage deadline exhausted |
| `error` | `ERROR` | internal implementation failure prevented a valid result |
| `error` | `RESTORE_FAILED` | semantic restoration verification failed |

`RESTORE_FAILED` is always terminal `state=error`. It is never represented as
`state=completed`.

`PARTIAL` is not the default successful outcome. A fully executed standard or extended
search must finish as `SUCCESS`, `NO_CANDIDATE`, or `TARGET_ACCESSIBLE`.

The status document records at minimum:

- `job_id`;
- `state`;
- `outcome`;
- `current_stage`;
- `cancel_requested`;
- `started_at`;
- `deadline_at`;
- stage rows;
- recorded results;
- final restoration result;
- localized final message.

All status replacements are atomic.

==================================================
CANCELLATION CONTRACT
==================================================

A cancel request is a persistent state transition, not only a response body.

The cancel endpoint must atomically record:

- `state=cancel_requested`;
- `cancel_requested=true`;
- request timestamp;
- localized cancellation message;
- the cancel control file used by the worker.

Repeated cancel requests are idempotent. A terminal job is not changed.

Cancellation must be observed:

- between stages;
- while stage 60 expansion is active;
- while stage 70 stability probes are active;
- while any applicable TLS/HTTP/configured-UDP runner in stage 80 is active (the current
  `_27` compatibility path may still contain QUIC until its search-removal patch);
- during bounded helper operations where waiting for the full stage timeout would
  violate responsive cancellation.

A cancellation-aware runner must:

1. launch the controlled child operation;
2. poll both child state and the cancel control;
3. send `TERM` on cancellation;
4. wait for a bounded grace interval;
5. send `KILL` only when the child remains alive;
6. reap the child;
7. clean candidate dvtws2, firewall rules, and transient runtime;
8. mark interrupted and remaining search stages skipped;
9. run stage 90;
10. finish as `state=completed`, `outcome=PARTIAL`, `cancel_requested=true` when
    restoration succeeds.

Approved displayed skipped messages remain:

Russian: `SKIPPED — отменено`

English: `SKIPPED — canseled`

==================================================
TIME BUDGET CONTRACT
==================================================

Timeouts exist at operation, stage, and overall-job levels.

Overall budgets:

- standard automated search: 150 seconds;
- extended branches: an additional 120 seconds;
- cleanup and restoration remain bounded separately and must still run after search
  budget exhaustion.

At job start the worker records an absolute deadline. Every search operation receives
the minimum of:

- its own operation limit;
- its stage remaining budget;
- the overall remaining search budget.

Stage 80 has one shared 120-second implementation baseline. TLS 1.2/HTTP and configured
UDP do not each receive a fresh independent 120-second timeout. The current `_27` QUIC
branch shares that same bound until removed by the adaptive-search implementation.

The 2026-08-08 timeout redesign reopens all numeric search limits for telemetry-driven
review while preserving bounded execution. Future containment is
`operation <= candidate <= stage <= job`; an outer deadline may not knowingly expire
before an allowed child operation plus required cleanup can finish.

Stage 90 is outside the exhausted search budget when necessary to restore the router.
Its service-action bound must be large enough to contain the complete bounded native
service transaction it wraps. An outer timeout shorter than the sum of the native
launcher/supervisor waits is invalid because it can manufacture an `INCOMPLETE` service
state by killing a correct start operation in flight.

When a search budget is exhausted:

- already completed results are retained;
- active temporary work is stopped and cleaned;
- unfinished applicable stages receive the correct timeout or skipped status;
- stage 90 runs;
- terminal outcome follows the state/outcome table.

The GUI must not promise `1–3 minutes` unless the implemented mode and displayed budget
make that statement true. Standard and extended estimates are displayed separately.

==================================================
SHORTLIST AND CIRCULAR ELIGIBILITY
==================================================

Stage 85 constructs the final shortlist only after:

- stages 50, 60, and 70 are complete;
- stage 80 is complete in extended mode;
- stage 80 is explicitly `SKIPPED` in standard mode.

Circular validation controls are eligible only when all conditions are true:

- the Strategy Lab job is terminal;
- `state=completed`;
- `outcome=SUCCESS`;
- target type is `domain`;
- stage 85 is `PASS`;
- stage 90 is `PASS`;
- shortlist contains three to five candidates;
- no conflicting lifecycle operation is active.

The backend enforces eligibility. JavaScript visibility is not a security or lifecycle
boundary.

Circular controls must not overwrite a more important terminal or restoration message.
The GUI displays `state` and `outcome` separately.

==================================================
CANDIDATE RUNTIME OWNERSHIP CONTRACT
==================================================

A temporary candidate executed by Strategy Lab is job-owned runtime. In the current cold
Model-A implementation the candidate PID file
is the primary ownership proof after the PID has been validated against both the expected
dvtws2 executable and the reserved `--port=9989` command identity.

Port `9989` and single-candidate teardown are the current cold reference, not proof that a
warm multi-worker layout is safe. Models B/C must define non-overlapping ownership and
meet the dedicated A/B/C experiment gates before they change this runtime contract.

The same ownership proof must be used during teardown and absence verification. Cleanup
must:

1. read and validate the job-owned PID;
2. treat a still-valid owned PID as runtime-present even if secondary discovery misses it;
3. send TERM to that exact validated process;
4. use a bounded wait for owned-process/socket disappearance;
5. send KILL to that exact validated process when the grace interval expires;
6. additionally sweep globally for matching executable/port processes to remove
   duplicate or stale candidates;
7. require owned-PID absence, matching-process absence, and divert-port absence before
   declaring runtime teardown successful;
8. remove the candidate PID file only after absence is proven.

A global process listing and socket discovery are secondary evidence. They must never
replace an already proven pidfile owner as the sole termination or absence path. This
preserves the ownership relationship used at startup and avoids a FreeBSD-specific false
cleanup result when pid-specific inspection succeeds but a secondary snapshot omits or
formats the child differently.

Failure to prove candidate absence remains an internal error. The correction does not
permit stage 50 to continue while a candidate process or listener remains active.

==================================================
RESTORATION CONTRACT
==================================================

Restoration means semantic equivalence, not reuse of the same PID.

The initial snapshot records sufficient evidence to classify and verify:

- normal service state: RUNNING or STOPPED;
- expected supervisor presence;
- expected dvtws2 presence;
- active runtime identity/configuration evidence;
- plugin-owned normal firewall state;
- absence or presence of any pre-existing incomplete temporary state.

For initial RUNNING, stage 90 must use a bounded restoration-start window that exceeds
the complete native startup waits. The current native path can spend up to 10 seconds
waiting for the dvtws2 PID, then a 5-second stability interval, then up to 5 seconds
waiting for the supervisor, in addition to runtime generation/activation and firewall
work. A 15-second outer restoration bound is therefore forbidden. The corrective default
is 45 seconds.

A nonzero outer start result is not by itself semantic proof that restoration failed.
Stage 90 must immediately inspect the service state:

- healthy RUNNING is accepted and proceeds to semantic evidence verification;
- STOPPED may be used as the clean base for the one permitted recovery start;
- INCOMPLETE must first be normalized by bounded stop and verified STOPPED;
- an unknown/unclassifiable state fails restoration.

Exactly one bounded recovery start is permitted after the first unsuccessful or
semantically incomplete start. There is no automatic restart loop. If the second start
still does not establish healthy RUNNING, stage 90 performs a best-effort bounded
normalization to STOPPED and returns failure; semantic restoration remains failed because
the initial state was RUNNING.

After Strategy Lab cleanup and service-state recovery, final verification still requires:

- initial RUNNING becomes healthy RUNNING with supervisor and dvtws2;
- initial STOPPED remains fully STOPPED;
- no candidate dvtws2 remains;
- no Strategy Lab rules remain in reserved range `19100–19131`;
- no temporary listener remains on divert port `9989`;
- no active candidate runtime is left behind;
- the saved Traffic Strategy is unchanged;
- initial runtime args/effective configuration/normal firewall evidence match the final
  semantic evidence where semantic evidence is available.

A restoration verification failure produces:

```text
state=error
outcome=RESTORE_FAILED
stage 90=FAIL
stage 99=FAIL
```

The recovery attempt does not weaken this outcome contract. A successful command exit
without semantic RUNNING/evidence equivalence is not restoration success.

==================================================
TARGET CONTRACT
==================================================

The primary GUI workflow accepts a domain target.

A domain contract includes DNS, hostname/SNI, TLS version, required endpoint list, and
TCP/443 probe semantics.

A raw IP target is not treated as an implicit HTTPS domain. Future or backend-only IP
support must require an explicit target type, port, and probe contract. A raw IP must
not silently invent DNS or SNI semantics.

==================================================
MESSAGE CONTRACT
==================================================

Messages are generated from mode, state, outcome, and recorded stage results. Module
load order must not replace the final message contract.

Required truthful distinctions:

- standard success;
- extended success;
- no stable candidate;
- clean target accessible;
- controlled cancellation;
- timeout;
- internal error;
- restoration failure.

No final message may claim that extended branches ran in standard mode. No final
message may claim that circular validation is inactive when the feature is active.

==================================================
REGRESSION CONTRACT
==================================================

Focused tests remain required, but the corrective series must add one complete
mock-driven integration path:

```text
API/configd -> launcher -> lifecycle transaction -> worker -> stages 00–99
-> result -> optional circular validation
```

Required scenarios:

1. standard success;
2. extended success;
3. no candidate;
4. target accessible;
5. cancel during stages 60, 70, and every stage-80 branch;
6. overall timeout;
7. internal worker error;
8. restoration failure;
9. initial RUNNING restored to healthy RUNNING;
10. initial STOPPED restored to STOPPED;
11. circular start and stop;
12. process and IPFW cleanup;
13. saved Traffic Strategy immutability;
14. polling recovery after page reload;
15. candidate teardown when pid-specific ownership remains valid but secondary process
    and socket discovery omit the candidate;
16. first restoration start leaves INCOMPLETE, then one bounded normalization/recovery
    start reaches RUNNING;
17. outer start returns nonzero while semantic state is already healthy RUNNING, with no
    unnecessary second start;
18. two failed restoration starts return failure and best-effort normalize the service to
    STOPPED rather than accepting or intentionally retaining INCOMPLETE.

Tests must assert the event order and final persisted JSON, not only grep for source
strings.

==================================================
CORRECTIVE PATCH ORDER
==================================================

The approved implementation series is strictly serial:

1. corrective contract and documentation;
2. atomic cancel-state persistence;
3. cancellation-aware active runners;
4. explicit monotonic stage machine;
5. terminal state/outcome/message correction;
6. shared overall time budget;
7. stronger semantic restoration verification;
8. GUI and backend circular eligibility;
9. explicit domain/IP target contract;
10. end-to-end regression harness;
11. repository hygiene;
12. live-evidence candidate ownership correction;
13. live-evidence bounded restoration recovery.

Each patch follows:

`one logical change -> one task branch -> focused tests -> CI/package build -> one squash
merge -> post-merge verification -> verified branch deletion`.

For the `_6` live-evidence corrective pair, the owner explicitly requested repository
CI/package verification and merge to `main` without an intermediate manual OPNsense test.
Owner-assisted OPNsense scenario 1 is repeated only after both source corrections are in
`main`.

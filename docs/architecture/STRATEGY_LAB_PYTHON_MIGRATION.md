# Strategy Lab Python migration plan

==================================================
DOCUMENT ROLE
==================================================

Question answered:
How will the current Strategy Lab shell orchestration be migrated to Python without changing its approved product contract or weakening OPNsense lifecycle safety?

Purpose:
Provide the implementation map, responsibility boundary, migration stages, compatibility constraints, test requirements, and handoff entry point for the next development topic.

Updated when:
Migration scope, module ownership, compatibility boundaries, or patch sequence changes.

Read after:
`docs/ARCHITECTURE.md`, `docs/decisions/DEC-2026-08-07-strategy-lab-python-orchestration.md`, and `docs/PROJECT_STATE.md`.

Do not store here:
Chronological implementation results or final live evidence.

==================================================
STATUS
==================================================

Migration Patch 0 is complete. Patch 1 is merged as `_18`, Patch 2 as `_19`, Patch 3 as
`_20`, Patch 4 as `_21`, and Patch 5 as `_22`. Migration Patch 6 is the current source
candidate `v0.3.3_23` and is subject to the normal Ready-PR / corrective-CI / FreeBSD-15
qualification gate.

The stable outer production boundary remains compatible: `zapret_service.sh` launches
`strategy_lab_worker.sh`, which is a thin launcher into Python `orchestrate JOB_ID`.
Python owns numbered-stage order, wall-clock budgets, cancellation and terminal policy.
Patch 4 made Python the finite request/probe executor and parser. Patch 5 made Python the
standard candidate runtime/readiness/interception owner and Stage-50 family-screening
owner. Patch 6 extends that candidate owner across TLS 1.2, HTTP, QUIC and generic UDP and
moves Stage-60 expansion, Stage-70 stability/replay and Stage-80 extended-protocol search
policy to Python.

Stage-85 final result/shortlist ownership and dedicated obsolete-shell retirement remain
Patch 7. GUI/status reconciliation and the post-migration owner-assisted live gate remain
Patch 8.

==================================================
OBJECTIVE
==================================================

Move Strategy Lab responsibilities that require structured state, reliable subprocess
handling, explicit scoping, parsing, cancellation, and deterministic error classification
from large sourced POSIX-shell composition into Python without rewriting unrelated plugin
code.

The migration is successful when:

- public Strategy Lab API behavior remains compatible;
- lifecycle safety and exact restoration are preserved;
- Python owns the high-level job state machine and candidate/search orchestration;
- shell is reduced to small explicit system adapters where useful;
- obsolete shell orchestration is removed rather than retained as a fallback competitor;
- the current confirmed bug backlog is re-evaluated against focused tests and live evidence;
- the owner-assisted OPNsense matrix can resume from a documented Python candidate.

==================================================
TARGET COMPONENT BOUNDARY
==================================================

Target flow:

```text
Diagnostics GUI / JavaScript
        ↓
OPNsense PHP MVC/API
        ↓
configd action
        ↓
thin compatibility launcher
        ↓
Python Strategy Lab orchestration
        ↓
Python request/probe/candidate/family/search/extended execution + explicit system adapters
        ↓
zapret_service.sh, ipfw, drill/curl/openssl/nc, dvtws2, sockstat/ps and related FreeBSD tools
```

PHP remains responsible for HTTP request validation, API response shape, OPNsense MVC
integration, and configd invocation/bounded backend handling.

Python is the target owner for job state, persistence, stage progression/progress,
budgets, cancellation/finalization, structured subprocess execution/parsing, candidate
orchestration, family/search algorithms, result/shortlist assembly and diagnostic typing.

Shell may remain responsible for small explicit boundaries where preserving audited
OPNsense/FreeBSD behavior is safer or clearer: public service lifecycle entry points,
shared lifecycle locking until intentionally migrated, short `ipfw` mutation helpers,
audited process cleanup helpers, compatibility wrappers, and stage-specific responsibilities
not yet migrated. Such helpers must not choose Python-owned stage order, budget,
cancellation policy, terminal outcome, candidate readiness verdict, search order or
protocol result.

==================================================
PYTHON RUNTIME CONSTRAINT
==================================================

Migration Patch 1 established the supported OPNsense 26.7 / FreeBSD 15 contract:

- OPNsense selects FreeBSD 15.1 and `PYTHON=313`;
- supported interpreter family is Python 3.13;
- OPNsense core owns `/usr/local/bin/python3`;
- the plugin declares `python313` mapped to `lang/python313`;
- `.py` sources under `src/opnsense/` are packaged automatically;
- retained shell launchers remain executable.

The production launcher defaults to `/usr/local/bin/python3`; FreeBSD 15 CI uses
`/usr/local/bin/python3.13` explicitly. No third-party `pip` dependency is approved.

==================================================
STATE AND DATA MODEL
==================================================

Python represents migrated automated-job state explicitly rather than through reused
shell-global mutation pipelines. Public JSON schema is the compatibility authority.

Migration Patch 2 established `strategy_lab_py/state.py` as sole authoritative writer for
automated-job `status.json` and `events.ndjson`; shell state helpers are adapters only and
private circular-session `state.json` remains shell-owned.

Migration Patch 3 established `strategy_lab_py/orchestrator.py` as production owner of
stage order, Standard/Extended budgets, cancellation orchestration and terminal policy,
with inherited lifecycle lock fd 9 preserved across Python/adapters.

Migration Patch 4 established `strategy_lab_py/request.py` as the finite subprocess owner
and `strategy_lab_py/probe.py` as the Stage-30/40 execution/parsing owner. Candidate DNS
binding reuses the same ANSWER-section-aware parser.

Migration Patch 5 established `strategy_lab_py/candidate.py` as the standard TLS 1.3
candidate endpoint-binding/runtime-readiness/interception owner and `family.py` as the
ordered Stage-50 family-screening owner. `strategy_lab_candidate_adapter.sh` is the narrow
FreeBSD system adapter.

Migration Patch 6 establishes:

- `strategy_lab_py/search.py` as Stage-60 accepted-family expansion and Stage-70
  stability/replay owner;
- `strategy_lab_py/extended.py` as Stage-80 TLS 1.2/HTTP/QUIC/generic-UDP search owner;
- one generalized `candidate.py` owner for TLS 1.3, TLS 1.2, HTTP, QUIC and generic UDP;
- Patch-4 request ownership extended to exact selected-endpoint QUIC and generic-UDP
  payload/response execution;
- production expansion/stability/extended/QUIC/UDP runners reduced to Python launch
  boundaries;
- legacy shell search/extended modules retained only until Patch-7 dedicated retirement,
  not as authoritative production owners.

==================================================
PERSISTENCE CONTRACT
==================================================

Existing evidence locations remain stable during migration:

- `/var/run/zapret2-restyle/strategy-lab/`;
- `/var/log/zapret2/strategy-lab/`;
- per-job `status.json`;
- `events.ndjson`;
- stage/candidate evidence files required by current result contracts.

Patch-2 persistence invariants remain mandatory: schema 2, unchanged public stage/progress/
outcome fields, one revision increment per serialized mutation, Python state lock,
same-directory fsync + atomic replacement, valid NDJSON, and no competing shell state
transform. Private circular-session state keeps its separate shell contract.

Patch 4 keeps public `network.json` and `baseline.json` unchanged and records richer
subprocess diagnostics in sidecar evidence. Patch 5 preserves candidate and `family.json`
public evidence fields.

Patch 6 preserves the public Stage-60/70/80 result contracts:

- expansion: `total_available`, `completed`, `candidates`, `working`, `failed`, `stopped_reason`;
- stability: `total_candidates`, `completed`, `candidates`, `stable`, `unstable`, `stopped_reason`;
- extended TCP: independent TLS 1.2 / HTTP `tested` and `working` objects;
- QUIC: capability, skip reason, tested candidates, working candidate and `not_found`;
- generic UDP: configured port, skip reason, tested candidates, working candidate and `not_found`.

==================================================
STAGE / BUDGET / CANCELLATION CONTRACT
==================================================

Patch 3 production stage order remains exactly:

`00 -> 10 -> 20 -> 30 -> 40 -> 50 -> 60 -> 70 -> 80 -> 85 -> 90 -> 99`.

Python owns the Standard 150-second budget, Extended +120-second budget, per-operation
ceilings, Stage-80 shared deadline, typed timeout handling, cancellation process-group
termination and mandatory Stage 90/99 convergence.

Terminal mapping remains unchanged: `ERROR`, `TIMEOUT`, `RESTORE_FAILED` => terminal
`error` / report FAIL; `SUCCESS`, `NO_CANDIDATE`, `TARGET_ACCESSIBLE`, `PARTIAL` =>
terminal `completed` / report PASS; restoration failure overrides prior outcome.

Patch 6 does not change whole-job budget semantics. Search/protocol candidate limits are
clipped by `STRATEGY_LAB_OPERATION_TIMEOUT`; candidate subprocess groups are terminated on
timeout/cancellation and the audited candidate cleanup adapter is invoked before search
continues or exits.

==================================================
SUBPROCESS / PARSER / CANDIDATE CONTRACT
==================================================

Every migrated external command execution preserves independently:

- command and arguments;
- completion/timeout state;
- return code when one exists;
- stdout;
- stderr;
- timeout classification;
- termination/signal classification;
- duration.

Timeout is not flattened into generic code 1. Parser rejection is not indistinguishable
from command execution failure.

Patch 4 implements this contract for DNS/TLS/HTTP/TCP/QUIC-control/route requests and
ANSWER-section-aware DNS parsing. Patch 6 extends it to exact selected-endpoint QUIC and
generic-UDP payload/response execution.

The unified Python candidate owner uses explicit protocol specs:

- TLS 1.3: TCP 443, TLS L7;
- TLS 1.2: TCP 443, TLS L7;
- HTTP: TCP 80, HTTP L7;
- QUIC: UDP 443, QUIC L7;
- generic UDP: validated configured port, no L7 classifier, validated job-local payload.

For all protocols candidate PASS requires finite request success, exact selected endpoint
identity, and IPFW packet-counter growth. Runtime readiness remains process identity +
divert socket + clean startup log with two stable snapshots. Fatal startup-log text cannot
be reported as ready.

==================================================
SEARCH CONTRACT
==================================================

Stage 60 expansion:

- only candidates belonging to accepted Stage-50 families are considered;
- catalog order is preserved;
- candidates run one at a time;
- default target remains five working expansion candidates;
- stop reasons remain `no_accepted_family`, `enough_candidates`, `catalog_exhausted`;
- timeout is recorded as candidate failure evidence, not silently flattened.

Stage 70 stability:

- passing expansion and family candidates are combined;
- identical strategies are de-duplicated;
- ranking remains deterministic by line count, character count, then id;
- default limit remains five candidates;
- default replay remains three sequential fresh-connection attempts;
- default target remains three stable candidates;
- stop reasons remain `no_working_candidate`, `enough_stable_candidates`, `candidates_exhausted`.

Stage 80 extended protocols:

- TLS 1.2 and HTTP are independent first-working searches;
- unavailable QUIC capability is explicitly skipped using the existing capability reason;
- available QUIC candidates run sequentially until first working or `not_found`;
- generic UDP consumes validated job-local port/payload data and preserves explicit skip
  semantics when not configured;
- configured UDP candidates run sequentially until first working or `not_found`.

==================================================
LIFECYCLE SAFETY
==================================================

Migration invariants remain:

1. Snapshot exact initial Zapret2 state before mutation.
2. Use the shared lifecycle ownership boundary.
3. Stop normal runtime only through approved lifecycle paths.
4. Run one temporary candidate at a time.
5. Keep temporary firewall/divert ownership isolated.
6. Clean candidate runtime before moving to the next candidate.
7. Execute stage 90 on normal completion, timeout, cancel, signal or internal error.
8. Restore initial RUNNING to healthy RUNNING and initial STOPPED to STOPPED.
9. Never hide restoration failure behind a successful result.
10. Saved Traffic Strategy remains immutable.

Patch 6 still does not duplicate audited FreeBSD process/firewall mutation logic in Python.
`strategy_lab_candidate_adapter.sh` retains WAN lookup, candidate-file preparation, IPFW
install/remove/counters, temporary job-directory access, daemon launch/stop, process
identity and divert-socket observations. Protocol transport/port/L7 are explicit adapter
inputs; Python owns sequencing/readiness/search/outcome.

==================================================
CONFIRMED DEFECTS TO CARRY FORWARD
==================================================

At the frozen `_17` live boundary:

1. Standard `rutracker.org` still fails Stage 50; exact `_17` root cause is not established.
2. New-job GUI can show visible ERROR before terminal evidence.
3. Active GUI can show `Strategy Lab returned no output.` while work continues.
4. Visible progress can remain 0% until terminal.
5. Shell-global target-type corruption existed in the shell baseline path.
6. DNS parser could accept non-answer `IN A`/`IN AAAA` text.
7. DNS diagnostics flattened timeout, command failure and parser rejection.
8. Terminal reload/state presentation can resurrect retained terminal work incorrectly.
9. Candidate readiness log classification can miss fatal runtime log evidence.

Patch 4 replaces source mechanisms behind items 5–7. Patch 5 replaces the candidate
readiness mechanism behind item 9 and adds focused regression. Patch 6 extends that unified
candidate path to extended protocols. Live/UI closure is not claimed from source changes
alone. All owner-observed items remain open until required evidence closes them.

==================================================
MIGRATION PATCH SERIES
==================================================

Patch 0 — documentation/handoff: **COMPLETE**.

Patch 1 — Python platform and compatibility foundation: **COMPLETE / MERGED AS `_18`**.

Patch 2 — Python automated-job state, progress, and structured persistence: **COMPLETE / MERGED AS `_19`**.

Patch 3 — Python stage machine, budgets, cancellation, and finalization: **COMPLETE / MERGED AS `_20`**.

Patch 4 — Python request/probe execution and parsing: **COMPLETE / MERGED AS `_21`**.

Patch 5 — Python candidate runtime and family screening: **COMPLETE / MERGED AS `_22`**.

Patch 6 — Python expansion, stability/replay, and extended protocol orchestration: **CURRENT `_23` SOURCE CHANGE**.

- Stage-60 expansion and Stage-70 stability/replay policy moves to `search.py`;
- Stage-80 TLS 1.2/HTTP/QUIC/generic-UDP policy moves to `extended.py`;
- one generalized Python candidate owner serves all protocols;
- exact endpoint/IPFW evidence remains required;
- audited FreeBSD mutations remain behind `strategy_lab_candidate_adapter.sh`;
- public search/protocol result schemas and stop/skip reasons remain compatible;
- focused Linux and FreeBSD 15 regression qualifies the new ownership.

Patch 7 — Python final result/shortlist completion and shell-orchestration retirement: **NEXT AFTER PATCH 6 QUALIFICATION**.

Patch 8 — GUI/status reconciliation and post-migration live gate.

Patch numbering may be split further when one item becomes more than one logical change;
it must not be compressed into a monolithic rewrite.

==================================================
TEST STRATEGY
==================================================

Every migration patch includes focused coverage for the responsibility it moves.

Patches 1–5 retain their existing focused regressions and the full authoritative Strategy
Lab corrective matrix remains the cross-surface compatibility gate.

Patch 6 additionally requires:

- Python 3.13 import/`py_compile` for `search.py`, `extended.py`, generalized candidate and request owners;
- accepted-family expansion filtering, ordering, timeout and early-stop compatibility;
- stability source de-duplication/ranking, three sequential replay attempts and stable-target early stop;
- TLS 1.2 / HTTP independent first-working behavior;
- QUIC capability skip and available first-working behavior;
- generic UDP unconfigured skip, validated configured input, sequential search and first-working behavior;
- protocol environment/transport/port propagation into the unified candidate owner;
- endpoint/IPFW evidence invariant across standard and extended candidates;
- complete existing Strategy Lab corrective matrix;
- FreeBSD 15 execution with `python313`;
- built-package presence of `search.py` and `extended.py` plus all earlier Python migration layers.

Old fixtures remain compatibility tests when they express product behavior rather than
retired shell implementation details. No test may require shell ownership of Stage-60/70/
80 search policy or protocol candidate interception after Patch 6 switches those paths.

==================================================
CUTOVER RULE
==================================================

For each responsibility:

1. Add Python implementation behind the stable compatibility boundary.
2. Run focused parity tests against required behavior.
3. Switch the authoritative call path once.
4. Verify there is only one owner of mutations/state/control policy.
5. Remove obsolete shell implementation in the same logical scope when safe, or the immediately following dedicated retirement patch if necessary.

Patch 2 switched persistence; Patch 3 switched stage/budget/cancel/finalization ownership;
Patch 4 switched finite request/probe execution and parsing; Patch 5 switched candidate
runtime/readiness/interception and Stage-50 family screening; Patch 6 switches Stage-60/70
search and Stage-80 extended-protocol orchestration. Private circular-session state remains
shell-owned. Stage-85 final result/shortlist ownership and dedicated obsolete-shell
retirement remain Patch 7.
